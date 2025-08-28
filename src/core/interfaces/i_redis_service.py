from abc import ABC, abstractmethod
from typing import Any, Optional

class IRedisService(ABC):
    """Redis 서비스 인터페이스"""

    @abstractmethod
    async def connect(self) -> None:
        """Redis 연결 초기화"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Redis 연결 종료"""
        pass

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """키-값 조회"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """키-값 설정"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """키 삭제"""
        pass

    @abstractmethod
    async def incr(self, key: str, expire: Optional[int] = None) -> Optional[int]:
        """카운터 증가"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        pass

    @abstractmethod
    async def ttl(self, key: str) -> int:
        """키 TTL 조회"""
        pass

    @abstractmethod
    async def sadd(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set에 값 추가"""
        pass

    @abstractmethod
    async def sismember(self, key: str, value: str) -> bool:
        """Set 멤버십 확인"""
        pass