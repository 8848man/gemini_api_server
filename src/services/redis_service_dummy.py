from src.core.interfaces.i_redis_service import IRedisService
from typing import Any, Optional

class RedisServiceDummy(IRedisService):
    """Redis 서버가 없을 때 사용하는 Dummy 서비스"""

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def get(self, key: str) -> Optional[Any]:
        return None

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        return True

    async def delete(self, key: str) -> bool:
        return True

    async def incr(self, key: str, expire: Optional[int] = None) -> Optional[int]:
        return 0

    async def exists(self, key: str) -> bool:
        return False

    async def ttl(self, key: str) -> int:
        return -1

    async def sadd(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        return True

    async def sismember(self, key: str, value: str) -> bool:
        return False