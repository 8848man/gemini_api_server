import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import get_settings
from src.services.redis_service import redis_service
from src.utils.security import generate_request_hash

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting 및 중복 요청 방지 미들웨어"""

    def __init__(self, app):
        super().__init__(app)
        self.concurrent_requests: Dict[str, int] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Redis 연결 확인
        if not redis_service.redis:
            try:
                await redis_service.connect()
            except Exception as e:
                logger.warning(f"Redis not available, rate limiting disabled: {e}")
                return await call_next(request)

        client_id = self._get_client_identifier(request)
        
        # Rate limiting 체크
        if await self._is_rate_limited(client_id):
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": 60,
                    "limit": settings.REQUESTS_PER_MINUTE,
                },
                headers={"Retry-After": "60"}
            )

        # 동시 요청 수 제한
        if await self._check_concurrent_limit(client_id):
            logger.warning(f"Concurrent request limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too many concurrent requests",
                    "max_concurrent": settings.MAX_CONCURRENT_REQUESTS,
                }
            )

        # 중복 요청 체크 (POST 요청만)
        if request.method == "POST":
            request_hash = await self._get_request_hash(request, client_id)
            if request_hash and await self._is_duplicate_request(request_hash):
                logger.warning(f"Duplicate request detected: {request_hash}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Duplicate request detected. Please wait before retrying."
                )

        # 동시 요청 카운터 증가
        await self._increment_concurrent_requests(client_id)

        try:
            # 요청 처리
            response = await call_next(request)
            
            # 응답 헤더에 rate limit 정보 추가
            remaining = await self._get_remaining_requests(client_id)
            response.headers["X-RateLimit-Limit"] = str(settings.REQUESTS_PER_MINUTE)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int((datetime.now() + timedelta(minutes=1)).timestamp()))
            
            return response

        finally:
            # 동시 요청 카운터 감소
            await self._decrement_concurrent_requests(client_id)

    def _get_client_identifier(self, request: Request) -> str:
        """클라이언트 식별자 생성"""
        # 인증된 사용자가 있는 경우 사용자 정보 사용
        if hasattr(request.state, "user") and request.state.user:
            user_info = request.state.user
            if "api_key" in user_info:
                return f"api_key:{hash(user_info['api_key']) % 10000}"
            elif "sub" in user_info:  # JWT payload의 subject
                return f"user:{user_info['sub']}"
        
        # IP 주소 기반 식별
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"

    async def _is_rate_limited(self, client_id: str) -> bool:
        """Rate limit 확인"""
        key = f"rate_limit:{client_id}"
        current_count = await redis_service.incr(key, expire=60)
        
        if current_count is None:
            return False
            
        return current_count > settings.REQUESTS_PER_MINUTE

    async def _get_remaining_requests(self, client_id: str) -> int:
        """남은 요청 수 조회"""
        key = f"rate_limit:{client_id}"
        current_count = await redis_service.get(key)
        
        if current_count is None:
            return settings.REQUESTS_PER_MINUTE
            
        remaining = settings.REQUESTS_PER_MINUTE - int(current_count)
        return max(0, remaining)

    async def _check_concurrent_limit(self, client_id: str) -> bool:
        """동시 요청 수 제한 확인"""
        key = f"concurrent:{client_id}"
        current_concurrent = await redis_service.get(key)
        
        if current_concurrent is None:
            current_concurrent = 0
        else:
            current_concurrent = int(current_concurrent)
        
        return current_concurrent >= settings.MAX_CONCURRENT_REQUESTS

    async def _increment_concurrent_requests(self, client_id: str) -> None:
        """동시 요청 카운터 증가"""
        key = f"concurrent:{client_id}"
        await redis_service.incr(key, expire=300)  # 5분 TTL

    async def _decrement_concurrent_requests(self, client_id: str) -> None:
        """동시 요청 카운터 감소"""
        key = f"concurrent:{client_id}"
        current = await redis_service.get(key)
        
        if current and int(current) > 0:
            new_value = int(current) - 1
            if new_value <= 0:
                await redis_service.delete(key)
            else:
                await redis_service.set(key, new_value, expire=300)

    async def _get_request_hash(self, request: Request, client_id: str) -> Optional[str]:
        """요청 해시 생성"""
        try:
            body = await request.body()
            if body:
                body_str = body.decode("utf-8")
                # 간단한 해시 생성 (시간 정보 포함하지 않음)
                content = f"{request.method}:{request.url.path}:{body_str}"
                return generate_request_hash(client_id, content)
        except Exception as e:
            logger.error(f"Failed to generate request hash: {e}")
        
        return None

    async def _is_duplicate_request(self, request_hash: str) -> bool:
        """중복 요청 확인"""
        key = f"duplicate:{request_hash}"
        
        # 요청 해시가 이미 존재하는지 확인
        if await redis_service.exists(key):
            return True
        
        # 새로운 요청으로 마킹 (10분간 유지)
        window_seconds = settings.DUPLICATE_REQUEST_WINDOW_MINUTES * 60
        await redis_service.set(key, "1", expire=window_seconds)
        return False