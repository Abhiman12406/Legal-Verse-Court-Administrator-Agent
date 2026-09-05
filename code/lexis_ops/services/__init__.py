"""
LexisOps Core Services Layer
"""
from lexis_ops.services.redis_client import RedisService, get_redis_service

__all__ = ["RedisService", "get_redis_service"]
