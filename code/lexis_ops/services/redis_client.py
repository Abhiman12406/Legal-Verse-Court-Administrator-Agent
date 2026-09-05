from __future__ import annotations

import asyncio
import collections
import hashlib
import json
import logging
import os
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

import redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

logger = logging.getLogger("lexis_ops.redis")

# Default Channel & Queue Keys
CHANNEL_CLERK_NOTIFICATIONS = "lexis:events:clerk_notifications"
CHANNEL_EMERGENCY_ALERTS = "lexis:events:emergency"
QUEUE_EMERGENCY = "lexis:queue:filings:emergency"
QUEUE_STANDARD = "lexis:queue:filings:standard"
QUEUE_QUARANTINE = "lexis:queue:filings:quarantine"
RECENT_NOTIFICATIONS_KEY = "lexis:notifications:recent"
CALENDAR_CACHE_PREFIX = "lexis:cache:calendar:"
SCHEDULE_CACHE_PREFIX = "lexis:cache:schedule:"


class InMemoryRedisFallback:
    """
    Hermetic in-memory fallback for local development or isolated testing
    when a live Redis daemon is not available.
    """

    def __init__(self):
        self._kv: Dict[str, str] = {}
        self._expirations: Dict[str, float] = {}
        self._queues: Dict[str, collections.deque] = {
            QUEUE_EMERGENCY: collections.deque(),
            QUEUE_STANDARD: collections.deque(),
            QUEUE_QUARANTINE: collections.deque(),
            RECENT_NOTIFICATIONS_KEY: collections.deque(maxlen=100),
        }
        self._subscribers: List[asyncio.Queue] = []
        self._sync_subscribers: List[Any] = []

    def get(self, key: str) -> Optional[str]:
        self._clean_expired(key)
        return self._kv.get(key)

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._kv[key] = value
        if ex:
            self._expirations[key] = time.time() + ex
        elif key in self._expirations:
            del self._expirations[key]
        return True

    def delete(self, *keys: str) -> int:
        deleted = 0
        for k in keys:
            if k in self._kv:
                del self._kv[k]
                if k in self._expirations:
                    del self._expirations[k]
                deleted += 1
        return deleted

    def keys(self, pattern: str = "*") -> List[str]:
        import fnmatch
        now = time.time()
        for k in list(self._expirations.keys()):
            if self._expirations[k] <= now:
                self._kv.pop(k, None)
                self._expirations.pop(k, None)
        return [k for k in self._kv.keys() if fnmatch.fnmatch(k, pattern)]


    def rpush(self, queue_name: str, *values: str) -> int:
        if queue_name not in self._queues:
            self._queues[queue_name] = collections.deque()
        for v in values:
            self._queues[queue_name].append(v)
        return len(self._queues[queue_name])

    def lpop(self, queue_name: str) -> Optional[str]:
        q = self._queues.get(queue_name)
        if q and len(q) > 0:
            return q.popleft()
        return None

    def llen(self, queue_name: str) -> int:
        q = self._queues.get(queue_name)
        return len(q) if q else 0

    def lrange(self, queue_name: str, start: int, end: int) -> List[str]:
        q = self._queues.get(queue_name)
        if not q:
            return []
        items = list(q)
        if end == -1:
            return items[start:]
        return items[start : end + 1]

    def _clean_expired(self, key: str):
        if key in self._expirations and self._expirations[key] <= time.time():
            self._kv.pop(key, None)
            self._expirations.pop(key, None)

    def publish(self, channel: str, message: str) -> int:
        delivered = 0
        dead_queues = []
        for q in self._subscribers:
            try:
                q.put_nowait(message)
                delivered += 1
            except Exception:
                dead_queues.append(q)
        for dq in dead_queues:
            self._subscribers.remove(dq)
        return delivered

    def register_async_subscriber(self, q: asyncio.Queue):
        self._subscribers.append(q)

    def unregister_async_subscriber(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)


class RedisService:
    """
    Unified Redis Service providing:
      1. High-Speed Calendar Availability Caching (sub-millisecond lookups)
      2. Priority Filing Queue Management (Emergency, Standard, Quarantine)
      3. Real-Time Pub/Sub Message Broker for Clerk Notifications
      4. Automatic resilient fallback for local or containerized environments
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0,
        socket_timeout: float = 1.0,
        socket_connect_timeout: float = 0.5,
    ):
        self.redis_url = (
            redis_url
            or os.environ.get("REDIS_URL")
            or f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:{os.environ.get('REDIS_PORT', '6379')}/{db}"
        )
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.fallback = InMemoryRedisFallback()
        self._client: Optional[redis.Redis] = None
        self._is_connected = False
        self._last_connect_attempt = 0.0


    @property
    def client(self) -> Optional[redis.Redis]:
        """Lazy connection to Redis server with cached fallback detection."""
        now = time.time()
        if self._client is not None:
            return self._client

        # Avoid spamming connection attempts if down (5s cool down)
        if now - self._last_connect_attempt < 5.0 and not self._is_connected:
            return None

        self._last_connect_attempt = now
        try:
            r = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=True,
            )
            r.ping()
            self._client = r
            self._is_connected = True
            logger.info(f"Connected to Redis broker at {self.redis_url}")
            return self._client
        except Exception as exc:
            self._client = None
            self._is_connected = False
            logger.warning(
                f"Redis connection failed ({exc}). LexisOps will operate using resilient in-memory fallback."
            )
            return None

    def ping(self) -> Dict[str, Any]:
        """Probe Redis server connectivity and measure round-trip latency."""
        t0 = time.perf_counter()
        c = self.client
        if c:
            try:
                res = c.ping()
                latency_ms = (time.perf_counter() - t0) * 1000.0
                return {
                    "status": "healthy",
                    "mode": "LIVE_REDIS",
                    "redis_url": self.redis_url,
                    "latency_ms": round(latency_ms, 2),
                    "ping": res,
                }
            except Exception as exc:
                self._is_connected = False
                self._client = None
                return {
                    "status": "degraded",
                    "mode": "FALLBACK_MEMORY",
                    "error": str(exc),
                    "redis_url": self.redis_url,
                    "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                }

        return {
            "status": "healthy",
            "mode": "FALLBACK_MEMORY",
            "redis_url": self.redis_url,
            "latency_ms": 0.05,
            "note": "Operating in resilient in-memory fallback mode (standalone or test environment).",
        }

    # ==========================================================================
    # 1. High-Speed Calendar Availability Caching
    # ==========================================================================

    @staticmethod
    def build_schedule_cache_key(
        case_number: str,
        candidate_judges: Optional[List[str]] = None,
        corporate_disclosures: Optional[List[Any]] = None,
        statutory_buffer_days: int = 21,
        accommodations: Optional[List[str]] = None,
        candidate_courtrooms: Optional[List[str]] = None,
    ) -> str:
        """
        Computes a deterministic MD5 hash key from scheduling constraint parameters.
        Ensures consistent cache hits for identical docket scheduling scenarios.
        """
        payload = {
            "case_number": case_number,
            "judges": sorted(candidate_judges or []),
            "courtrooms": sorted(candidate_courtrooms or []),
            "buffer": statutory_buffer_days,
            "accommodations": sorted(accommodations or []),
            "disclosures": [
                getattr(d, "filer_entity", str(d))
                for d in (corporate_disclosures or [])
            ],
        }
        raw = json.dumps(payload, sort_keys=True)
        hash_val = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"{SCHEDULE_CACHE_PREFIX}{case_number}:{hash_val}"

    def get_cached_schedule(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a cached OR-Tools CP-SAT scheduling solution in sub-millisecond time."""
        c = self.client
        try:
            if c:
                cached_val = c.get(cache_key)
            else:
                cached_val = self.fallback.get(cache_key)

            if cached_val:
                data = json.loads(cached_val)
                data["_from_cache"] = True
                return data
        except Exception as exc:
            logger.warning(f"Error reading schedule cache key {cache_key}: {exc}")
        return None

    def set_cached_schedule(
        self, cache_key: str, schedule_data: Dict[str, Any], ttl_seconds: int = 1800
    ) -> bool:
        """Stores computed CP-SAT scheduling solution in Redis with TTL (default 30 mins)."""
        try:
            raw = json.dumps(schedule_data)
            c = self.client
            if c:
                return bool(c.set(cache_key, raw, ex=ttl_seconds))
            return bool(self.fallback.set(cache_key, raw, ex=ttl_seconds))
        except Exception as exc:
            logger.warning(f"Error writing schedule cache key {cache_key}: {exc}")
            return False

    def invalidate_calendar_cache(self, pattern_or_case: str = "*") -> int:
        """
        Invalidates calendar slots and pre-computed solutions.
        Useful when an emergency hearing is scheduled or a judicial recusal occurs.
        """
        if not pattern_or_case.startswith(SCHEDULE_CACHE_PREFIX):
            pattern = f"{SCHEDULE_CACHE_PREFIX}*{pattern_or_case}*"
        else:
            pattern = pattern_or_case

        c = self.client
        deleted = 0
        try:
            if c:
                keys = c.keys(pattern)
                if keys:
                    deleted = c.delete(*keys)
            else:
                keys = self.fallback.keys(pattern)
                if keys:
                    deleted = self.fallback.delete(*keys)
        except Exception as exc:
            logger.warning(f"Error invalidating cache pattern {pattern}: {exc}")
        return deleted

    # ==========================================================================
    # 2. Priority Filing Queue Management
    # ==========================================================================

    def enqueue_filing(
        self,
        filing_id: str,
        case_number: str,
        priority: str = "STANDARD",
        filing_type: str = "PLEADING",
        is_emergency: bool = False,
        pro_se: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enqueues an incoming filing into the appropriate priority queue:
          - EMERGENCY: Fed. R. Civ. P. 65(b) SEV-1 Ex Parte TRO applications
          - QUARANTINE: Pro se pleadings flagged under Castro v. United States
          - STANDARD: General civil and commercial motions awaiting clerk review
        """
        priority_clean = priority.strip().upper()
        if is_emergency or priority_clean in ["EMERGENCY", "SEV-1", "CRITICAL"]:
            queue_name = QUEUE_EMERGENCY
            assigned_priority = "EMERGENCY"
        elif pro_se or priority_clean in ["QUARANTINE", "PRO_SE"]:
            queue_name = QUEUE_QUARANTINE
            assigned_priority = "QUARANTINE"
        else:
            queue_name = QUEUE_STANDARD
            assigned_priority = "STANDARD"

        item = {
            "queue_item_id": str(uuid.uuid4()),
            "filing_id": filing_id,
            "case_number": case_number,
            "filing_type": filing_type,
            "priority": assigned_priority,
            "is_emergency": is_emergency,
            "enqueued_at": time.time(),
            "metadata": metadata or {},
        }
        raw = json.dumps(item)

        c = self.client
        if c:
            try:
                c.rpush(queue_name, raw)
            except Exception:
                self.fallback.rpush(queue_name, raw)
        else:
            self.fallback.rpush(queue_name, raw)

        # Publish notification of new queued item
        self.publish_notification(
            event_type="FILING_ENQUEUED",
            payload={
                "filing_id": filing_id,
                "case_number": case_number,
                "queue": queue_name,
                "priority": assigned_priority,
                "is_emergency": is_emergency,
            },
            priority="CRITICAL" if is_emergency else "NORMAL",
        )

        return item

    def dequeue_filing(
        self, preferred_queue: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Pops the next filing to process, strictly prioritizing:
          1. Emergency TRO Queue (SEV-1)
          2. Standard Triage Queue
          3. Pro Se Quarantine Queue
        """
        queues_order = (
            [preferred_queue]
            if preferred_queue
            else [QUEUE_EMERGENCY, QUEUE_STANDARD, QUEUE_QUARANTINE]
        )

        c = self.client
        for q_name in queues_order:
            raw = None
            try:
                if c:
                    raw = c.lpop(q_name)
                else:
                    raw = self.fallback.lpop(q_name)
            except Exception:
                raw = self.fallback.lpop(q_name)

            if raw:
                try:
                    return json.loads(raw)
                except Exception:
                    return {"raw_item": raw, "queue": q_name}

        return None

    def get_queue_metrics(self) -> Dict[str, Any]:
        """Returns the real-time depth of all court filing queues."""
        c = self.client
        metrics = {}
        for name, q_key in [
            ("emergency", QUEUE_EMERGENCY),
            ("standard", QUEUE_STANDARD),
            ("quarantine", QUEUE_QUARANTINE),
        ]:
            try:
                if c:
                    metrics[name] = c.llen(q_key)
                else:
                    metrics[name] = self.fallback.llen(q_key)
            except Exception:
                metrics[name] = self.fallback.llen(q_key)

        metrics["total_depth"] = sum(metrics.values())
        metrics["timestamp"] = time.time()
        return metrics

    # ==========================================================================
    # 3. Pub/Sub Message Broker & Real-Time Notifications
    # ==========================================================================

    def publish_notification(
        self,
        event_type: str,
        payload: Dict[str, Any],
        channel: str = CHANNEL_CLERK_NOTIFICATIONS,
        priority: str = "NORMAL",
    ) -> Dict[str, Any]:
        """
        Publishes a real-time event to connected clerk consoles and saves to recent buffer.
        """
        notification = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "priority": priority.upper(),
            "channel": channel,
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "payload": payload,
        }
        raw = json.dumps(notification)

        c = self.client
        # Push to recent notifications circular buffer (last 50)
        try:
            if c:
                c.rpush(RECENT_NOTIFICATIONS_KEY, raw)
                c.ltrim(RECENT_NOTIFICATIONS_KEY, -50, -1)
                c.publish(channel, raw)
            else:
                self.fallback.rpush(RECENT_NOTIFICATIONS_KEY, raw)
                self.fallback.publish(channel, raw)
        except Exception as exc:
            logger.warning(f"Error publishing event {event_type} to Redis: {exc}")
            self.fallback.rpush(RECENT_NOTIFICATIONS_KEY, raw)
            self.fallback.publish(channel, raw)

        return notification

    def get_recent_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns the most recent notifications from the historical buffer."""
        c = self.client
        raw_items = []
        try:
            if c:
                raw_items = c.lrange(RECENT_NOTIFICATIONS_KEY, -limit, -1)
            else:
                raw_items = self.fallback.lrange(RECENT_NOTIFICATIONS_KEY, -limit, -1)
        except Exception:
            raw_items = self.fallback.lrange(RECENT_NOTIFICATIONS_KEY, -limit, -1)

        result = []
        for r in reversed(raw_items):
            try:
                result.append(json.loads(r))
            except Exception:
                continue
        return result

    async def subscribe_notifications_async(
        self, channel: str = CHANNEL_CLERK_NOTIFICATIONS
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronous generator yielding notifications in real-time.
        Perfect for FastAPI Server-Sent Events (SSE) `/notifications/stream`.
        """
        # If live Redis client is available, use redis.asyncio or background thread
        local_q: asyncio.Queue = asyncio.Queue()
        self.fallback.register_async_subscriber(local_q)

        # Also, if live redis connection exists, bridge pubsub into local_q
        pubsub_task = None
        stop_event = asyncio.Event()

        async def _redis_bridge():
            try:
                import redis.asyncio as aioredis
                async_r = aioredis.from_url(self.redis_url, decode_responses=True)
                ps = async_r.pubsub()
                await ps.subscribe(channel)
                while not stop_event.is_set():
                    msg = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if msg and msg.get("type") == "message":
                        await local_q.put(msg["data"])
                    await asyncio.sleep(0.05)
                await ps.unsubscribe(channel)
                await async_r.close()
            except Exception:
                pass

        c = self.client
        if c:
            pubsub_task = asyncio.create_task(_redis_bridge())

        try:
            while True:
                msg_str = await local_q.get()
                if isinstance(msg_str, str):
                    try:
                        yield json.loads(msg_str)
                    except Exception:
                        yield {"raw": msg_str}
                elif isinstance(msg_str, dict):
                    yield msg_str
        finally:
            self.fallback.unregister_async_subscriber(local_q)
            stop_event.set()
            if pubsub_task:
                pubsub_task.cancel()


# Singleton instance
_global_redis_service: Optional[RedisService] = None


def get_redis_service() -> RedisService:
    global _global_redis_service
    if _global_redis_service is None:
        _global_redis_service = RedisService()
    return _global_redis_service
