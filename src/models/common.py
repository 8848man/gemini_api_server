from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    success: bool = Field(..., description="API 호출 성공 여부")
    data: Optional[Any] = Field(None, description="응답 데이터")
    message: str = Field(default="", description="응답 메시지")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="API 호출 성공 여부")
    error: str = Field(..., description="오류 메시지")
    error_code: Optional[str] = Field(None, description="오류 코드")
    timestamp: datetime = Field(default_factory=datetime.now, description="오류 발생 시간")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="서비스 상태")
    timestamp: datetime = Field(default_factory=datetime.now, description="확인 시간")
    version: str = Field(..., description="서비스 버전")
    uptime: Optional[float] = Field(None, description="가동 시간 (초)")


class RateLimitInfo(BaseModel):
    requests_remaining: int = Field(..., description="남은 요청 수")
    reset_time: datetime = Field(..., description="제한 리셋 시간")
    window_size: int = Field(..., description="제한 시간 창 (초)")