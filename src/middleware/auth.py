import logging
from typing import Optional

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.security import verify_api_key, verify_token
from src.services.firebase_service import verify_firebase_token

logger = logging.getLogger(__name__)

# 인증이 필요없는 경로
# PUBLIC_PATHS = {
#     "/",
#     "/docs",
#     "/redoc",
#     "/openapi.json",
#     "/api/v1/health",
#     "/metrics",
# }

PUBLIC_PATH_PREFIXES = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/health",
    "/metrics",
    "/flutter_service_worker.js",
]

class AuthMiddleware(BaseHTTPMiddleware):
    """API 키 및 JWT 토큰 인증 미들웨어"""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # OPTIONS 요청은 무조건 인증 생략
        if request.method == "OPTIONS":
            return await call_next(request)

        # 공개 경로는 인증 생략
        # if path in PUBLIC_PATHS or path.startswith("/static"):
        #     return await call_next(request)
        # 공개 경로는 인증 생략
        if any(path == p or path.startswith(p + "/") for p in PUBLIC_PATH_PREFIXES):
            return await call_next(request)



        # API 키 또는 JWT 토큰 확인
        auth_header = request.headers.get("Authorization")
        api_key = request.headers.get("X-API-Key")

        user_info = None

        # JWT 토큰 인증 (Bearer 토큰)
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user_info = verify_token(token)
            if not user_info:
                logger.warning(f"Invalid JWT token for {request.client.host}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )

        # API 키 인증
        elif api_key:
            if not verify_api_key(api_key):
                logger.warning(f"Invalid API key from {request.client.host}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                )
            user_info = {"api_key": api_key}

        else:
            logger.warning(f"No authentication provided for {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # 사용자 정보를 request state에 저장
        request.state.user = user_info

        return await call_next(request)