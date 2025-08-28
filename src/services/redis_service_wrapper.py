from src.core.interfaces.i_redis_service import IRedisService
from src.services.redis_service import RedisService
from src.services.redis_service_dummy import RedisServiceDummy
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)



class RedisServiceWrapper(IRedisService):
    def __init__(self, real_service: IRedisService, dummy_service: IRedisService):
        self.real_service = real_service
        self.dummy_service = dummy_service
        self.connected = False

    async def _ensure_connected(self):
        if not self.connected:
            try:
                await self.real_service.connect()
                self.connected = True
            except Exception as e:
                logger.warning(f"Redis connection failed, fallback to dummy: {e}")
                self.connected = False

    async def connect(self) -> None:
        await self._ensure_connected()

    async def disconnect(self) -> None:
        if self.connected:
            try:
                await self.real_service.disconnect()
            except Exception as e:
                logger.error(f"Redis disconnect failed: {e}")
        self.connected = False

    async def get(self, key: str) -> Optional[Any]:
        await self._ensure_connected()
        try:
            if self.connected:
                return await self.real_service.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed, fallback to dummy: {e}")
        return await self.dummy_service.get(key)

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        await self._ensure_connected()
        try:
            if self.connected:
                return await self.real_service.set(key, value, expire)
        except Exception as e:
            logger.error(f"Redis SET failed, fallback to dummy: {e}")
        return await self.dummy_service.set(key, value, expire)

    async def delete(self, key: str) -> bool:
        await self._ensure_connected()
        try:
            if self.connected:
                return await self.real_service.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE failed, fallback to dummy: {e}")
        return await self.dummy_service.delete(key)

    async def incr(self, key: str, expire: Optional[int] = None) -> Optional[int]:
        await self._ensure_connected()
        try:
            if self.connected:
                return await self.real_service.incr(key, expire)
        except Exception as e:
            logger.error(f"Redis INCR failed, fallback to dummy: {e}")
        return await self.dummy_service.incr(key, expire)

    async def exists(self, key: str) -> bool:
        await self._ensure_connected()
        try:
            if self.connected:
                return await self.real_service.exists(key)
        except Exception as e:
            logger.error(f"Redis EXISTS failed, fallback to dummy: {e}")
        return await self.dummy_service.exists(key)

    async def ttl(self, key: str) -> int:
        await self._ensure_connected()
        try:
            if self.connected:
                return await self.real_service.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL failed, fallback to dummy: {e}")
        return await self.dummy_service.ttl(key)

    async def sadd(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        await self._ensure_connected()
        try:
            if self.connected:
                return await self.real_service.sadd(key, value, expire)
        except Exception as e:
            logger.error(f"Redis SADD failed, fallback to dummy: {e}")
        return await self.dummy_service.sadd(key, value, expire)

    async def sismember(self, key: str, value: str) -> bool:
        await self._ensure_connected()
        try:
            if self.connected:
                return await self.real_service.sismember(key, value)
        except Exception as e:
            logger.error(f"Redis SISMEMBER failed, fallback to dummy: {e}")
        return await self.dummy_service.sismember(key, value)
    # 전역 Redis 서비스 인스턴스

redis_service: IRedisService = RedisServiceWrapper(
    real_service=RedisService(),
    dummy_service=RedisServiceDummy()
)