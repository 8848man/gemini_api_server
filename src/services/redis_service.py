import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisService:
    """Redis 서비스 클래스"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.connection_pool = None

    async def connect(self):
        """Redis 연결 초기화"""
        try:
            self.connection_pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
            )
            self.redis = aioredis.Redis(connection_pool=self.connection_pool)
            
            # 연결 테스트
            await self.redis.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
            raise

    async def disconnect(self):
        """Redis 연결 종료"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        """키-값 조회"""
        if not self.redis:
            return None
            
        try:
            value = await self.redis.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """키-값 설정"""
        if not self.redis:
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = await self.redis.set(key, value, ex=expire)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """키 삭제"""
        if not self.redis:
            return False
            
        try:
            result = await self.redis.delete(key)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def incr(self, key: str, expire: Optional[int] = None) -> Optional[int]:
        """카운터 증가"""
        if not self.redis:
            return None
            
        try:
            # 파이프라인을 사용해 원자적 연산
            pipe = self.redis.pipeline()
            await pipe.incr(key)
            if expire:
                await pipe.expire(key, expire)
            results = await pipe.execute()
            return results[0]
        except RedisError as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return None

    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        if not self.redis:
            return False
            
        try:
            return bool(await self.redis.exists(key))
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """키의 TTL 조회"""
        if not self.redis:
            return -1
            
        try:
            return await self.redis.ttl(key)
        except RedisError as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return -1

    async def sadd(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set에 값 추가"""
        if not self.redis:
            return False
            
        try:
            pipe = self.redis.pipeline()
            await pipe.sadd(key, value)
            if expire:
                await pipe.expire(key, expire)
            results = await pipe.execute()
            return bool(results[0])
        except RedisError as e:
            logger.error(f"Redis SADD error for key {key}: {e}")
            return False

    async def sismember(self, key: str, value: str) -> bool:
        """Set 멤버십 확인"""
        if not self.redis:
            return False
            
        try:
            return bool(await self.redis.sismember(key, value))
        except RedisError as e:
            logger.error(f"Redis SISMEMBER error for key {key}: {e}")
            return False


# 전역 Redis 서비스 인스턴스
redis_service = RedisService()