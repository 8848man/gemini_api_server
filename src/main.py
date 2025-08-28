import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.api.routes import chat, dictionary, health
from src.core.config import get_settings
from src.middleware.auth import AuthMiddleware
from src.middleware.logging import LoggingMiddleware
from src.middleware.rate_limit import RateLimitMiddleware
from src.models.common import ErrorResponse
from src.utils.logger import setup_logger
from src.services.firebase_service import initialize_firebase

from fastapi.routing import APIRoute

settings = get_settings()

# 로깅 설정
setup_logger()
logger = logging.getLogger(__name__)

# 애플리케이션 시작 시간
start_time = datetime.now()


# @app.on_event("startup")
# async def log_routes():
#     from fastapi.routing import APIRoute
#     for route in app.routes:
#         if isinstance(route, APIRoute):
#             print(f"Route: {route.path} [{','.join(route.methods)}]")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    logger.info("Starting Gemini API Server...")
    
    # 로그 디렉토리 생성
    log_path = Path(settings.LOG_FILE).parent
    log_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Server configuration: {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    try:
        initialize_firebase()
    except Exception as e:
        # 여기서 앱을 계속 띄울지, 중단시킬지는 정책에 따라 결정
        # 예: 필수 서비스니까 실패 시 서버 종료
        raise RuntimeError("Firebase initialization failed") from e
    
    yield
    
    logger.info("Shutting down Gemini API Server...")


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 생성 및 설정"""

    app = FastAPI(
        title="Gemini API Server",
        description="A FastAPI server for Gemini AI chat and dictionary services",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS 미들웨어 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )

    # 커스텀 미들웨어 추가
    app.add_middleware(LoggingMiddleware)
    # 기본적으로 redis 없음
    # app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)

    # 라우터 등록
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(dictionary.router, prefix="/api/v1", tags=["dictionary"])

    # for route in app.routes:
    #     if isinstance(route, APIRoute):
    #         methods = ",".join(route.methods)
    #         print(f"Path: {route.path} | Methods: {methods} | Name: {route.name}")

    # 글로벌 예외 처리기
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error for {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="Validation failed",
                error_code="VALIDATION_ERROR",
            ).dict(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception for {request.url}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal server error",
                error_code="INTERNAL_ERROR",
            ).dict(),
        )

    # 메트릭스 엔드포인트 (프로메테우스)
    @app.get("/metrics")
    async def metrics():
        return generate_latest().decode()

    # 루트 엔드포인트
    @app.get("/")
    async def root():
        uptime = (datetime.now() - start_time).total_seconds()
        return {
            "message": "Gemini API Server is running",
            "version": "1.0.0",
            "uptime": uptime,
            "docs": "/docs" if settings.DEBUG else None,
        }

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=settings.API_WORKERS if not settings.DEBUG else 1,
        log_level=settings.LOG_LEVEL.lower(),
    )