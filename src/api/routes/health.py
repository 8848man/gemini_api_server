from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.models.common import HealthCheckResponse
from src.services.redis_service_wrapper import redis_service

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """서비스 상태 확인"""
    
    # Redis 연결 상태 확인
    redis_status = "connected"
    try:
        if redis_service.redis:
            await redis_service.redis.ping()
        else:
            redis_status = "disconnected"
    except Exception:
        redis_status = "error"
    
    status = "healthy" if redis_status == "connected" else "degraded"
    
    return HealthCheckResponse(
        status=status,
        version="1.0.0",
        uptime=None  # 실제 구현에서는 시작 시간으로부터 계산
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """상세 상태 확인"""
    
    checks = {}
    
    # Redis 상태
    try:
        if redis_service.redis:
            await redis_service.redis.ping()
            checks["redis"] = {"status": "healthy", "response_time": "< 1ms"}
        else:
            checks["redis"] = {"status": "disconnected", "error": "Not connected"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
    
    # 전체 상태 결정
    overall_status = "healthy"
    if any(check["status"] != "healthy" for check in checks.values()):
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "checks": checks
    }