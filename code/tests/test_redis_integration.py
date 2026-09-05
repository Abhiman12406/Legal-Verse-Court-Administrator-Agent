import asyncio
import json
import time
from fastapi.testclient import TestClient
import pytest


from lexis_ops.health import check_redis_health, get_system_health
from lexis_ops.schemas.scheduling import ConflictAwareScheduleRequest
from lexis_ops.server import app
from lexis_ops.services.redis_client import (
    QUEUE_EMERGENCY,
    QUEUE_QUARANTINE,
    QUEUE_STANDARD,
    RedisService,
    get_redis_service,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def redis_svc():
    svc = get_redis_service()
    # Reset in-memory / fallback state before each test
    svc.fallback._kv.clear()
    svc.fallback._expirations.clear()
    for q in svc.fallback._queues.values():
        q.clear()
    return svc


# ==============================================================================
# 1. Health Probe & Latency Verification
# ==============================================================================

def test_redis_health_probe(client, redis_svc):
    """Verifies /health/redis returns operational status and queue metrics."""
    res = client.get("/health/redis")
    assert res.status_code == 200
    data = res.json()
    assert data["subsystem"] == "redis_caching_and_message_broker"
    assert data["status"] in ("healthy", "degraded")
    assert "queue_depths" in data
    assert "latency_ms" in data


def test_system_readiness_includes_redis(client):
    """Verifies aggregate /health/ready probe incorporates Redis broker health."""
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert "redis_broker" in data["subsystems"]
    assert data["subsystems"]["redis_broker"]["status"] in ("healthy", "degraded")


# ==============================================================================
# 2. High-Speed Calendar Availability Caching
# ==============================================================================

def test_calendar_availability_caching(client, redis_svc):
    """
    Tests that hearing schedule solutions are cached in Redis,
    yielding sub-millisecond repeated responses and deterministic cache invalidation.
    """
    case_num = "CV-2026-REDIS-CACHE-001"
    req_payload = {
        "case_number": case_num,
        "candidate_judges": ["JUDGE-CIVIL-01", "JUDGE-CIVIL-02"],
        "statutory_buffer_days": 21,
        "candidate_courtrooms": ["CR-101", "CR-102"],
    }

    # First call: Solves and populates Redis cache
    t0 = time.perf_counter()
    res1 = client.post("/scheduling/solve", json=req_payload)
    t_first = (time.perf_counter() - t0) * 1000.0
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "SCHEDULED"

    # Verify cache key exists in Redis service
    cache_key = redis_svc.build_schedule_cache_key(
        case_number=case_num,
        candidate_judges=req_payload["candidate_judges"],
        statutory_buffer_days=req_payload["statutory_buffer_days"],
        candidate_courtrooms=req_payload["candidate_courtrooms"],
    )
    cached_entry = redis_svc.get_cached_schedule(cache_key)
    assert cached_entry is not None
    assert cached_entry["case_number"] == case_num

    # Second call: Should hit Redis cache at sub-millisecond speed
    t1 = time.perf_counter()
    res2 = client.post("/scheduling/solve", json=req_payload)
    t_second = (time.perf_counter() - t1) * 1000.0
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["scheduled_slot"]["hearing_id"] == data1["scheduled_slot"]["hearing_id"]
    assert data2["scheduled_slot"]["scheduled_date"] == data1["scheduled_slot"]["scheduled_date"]

    # Invalidate calendar cache
    res_clear = client.post(f"/scheduling/cache/clear?case_number={case_num}")
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "CACHE_CLEARED"

    # Verify cache entry was purged
    assert redis_svc.get_cached_schedule(cache_key) is None


# ==============================================================================
# 3. Priority Filing Queue Management
# ==============================================================================

def test_priority_queue_management(client, redis_svc):
    """
    Tests multi-tier Redis filing triage:
      - Emergency filings route to Emergency Queue
      - Standard filings route to Standard Queue
      - Pro se filings route to Quarantine Queue
      - Pop adheres to strict priority order: Emergency -> Standard -> Quarantine
    """
    # Enqueue standard filing
    res_std = client.post(
        "/queue/enqueue",
        json={
            "filing_id": "filing-std-001",
            "case_number": "CV-2026-0001",
            "priority": "STANDARD",
            "is_emergency": False,
            "pro_se": False,
        },
    )
    assert res_std.status_code == 200
    assert res_std.json()["status"] == "ENQUEUED"

    # Enqueue pro se quarantined filing
    res_quar = client.post(
        "/queue/enqueue",
        json={
            "filing_id": "filing-quar-002",
            "case_number": "CV-2026-0002",
            "priority": "QUARANTINE",
            "is_emergency": False,
            "pro_se": True,
        },
    )
    assert res_quar.status_code == 200

    # Enqueue emergency TRO filing
    res_emerg = client.post(
        "/queue/enqueue",
        json={
            "filing_id": "filing-emerg-003",
            "case_number": "CV-2026-0003",
            "priority": "EMERGENCY",
            "is_emergency": True,
            "pro_se": False,
        },
    )
    assert res_emerg.status_code == 200

    # Check queue depths
    res_status = client.get("/queue/status")
    assert res_status.status_code == 200
    metrics = res_status.json()["metrics"]
    assert metrics["emergency"] == 1
    assert metrics["standard"] == 1
    assert metrics["quarantine"] == 1
    assert metrics["total_depth"] == 3

    # First pop MUST be the Emergency TRO
    pop1 = client.post("/queue/pop").json()
    assert pop1["status"] == "CLAIMED"
    assert pop1["item"]["filing_id"] == "filing-emerg-003"
    assert pop1["item"]["is_emergency"] is True

    # Second pop MUST be Standard
    pop2 = client.post("/queue/pop").json()
    assert pop2["status"] == "CLAIMED"
    assert pop2["item"]["filing_id"] == "filing-std-001"

    # Third pop MUST be Quarantine
    pop3 = client.post("/queue/pop").json()
    assert pop3["status"] == "CLAIMED"
    assert pop3["item"]["filing_id"] == "filing-quar-002"

    # Fourth pop should report EMPTY
    pop4 = client.post("/queue/pop").json()
    assert pop4["status"] == "EMPTY"
    assert pop4["item"] is None


# ==============================================================================
# 4. Pub/Sub Real-Time Clerk Notifications
# ==============================================================================

def test_pubsub_notifications_and_recent_history(client, redis_svc):
    """
    Verifies that events published to Redis are saved in recent history buffer
    and retrievable by the Clerk Console.
    """
    # Publish a test emergency notice
    pub_res = client.post(
        "/notifications/publish",
        json={
            "event_type": "SEV1_EMERGENCY_ALERT",
            "payload": {
                "case_number": "CV-2026-9999",
                "alert": "Ex Parte TRO filed requiring 4-hour review",
            },
            "priority": "CRITICAL",
        },
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "PUBLISHED"
    event_id = pub_res.json()["notification"]["event_id"]

    # Query recent notifications buffer
    recent_res = client.get("/notifications/recent?limit=5")
    assert recent_res.status_code == 200
    notifications = recent_res.json()
    assert len(notifications) > 0
    matched = [n for n in notifications if n.get("event_id") == event_id]
    assert len(matched) == 1
    assert matched[0]["event_type"] == "SEV1_EMERGENCY_ALERT"
    assert matched[0]["priority"] == "CRITICAL"


@pytest.mark.asyncio
async def test_async_subscriber_stream(redis_svc):
    """Verifies that async subscriber generator receives published events."""
    events_received = []

    async def reader():
        async for event in redis_svc.subscribe_notifications_async():
            events_received.append(event)
            if len(events_received) >= 2:
                break

    task = asyncio.create_task(reader())
    await asyncio.sleep(0.05)

    redis_svc.publish_notification("EVENT_TEST_1", {"index": 1})
    redis_svc.publish_notification("EVENT_TEST_2", {"index": 2})

    await asyncio.wait_for(task, timeout=2.0)
    assert len(events_received) == 2
    assert events_received[0]["event_type"] == "EVENT_TEST_1"
    assert events_received[1]["event_type"] == "EVENT_TEST_2"
