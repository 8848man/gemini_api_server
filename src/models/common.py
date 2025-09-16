from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


from pydantic import BaseModel, Field
from datetime import datetime

class APIResponse(BaseModel):
    success: bool = Field(..., description="API 호출 성공 여부")
    data: Optional[Any] = Field(None, description="응답 데이터")
    message: str = Field(default="", description="응답 메시지")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="응답 시간"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="API 호출 성공 여부")
    error: str = Field(..., description="오류 메시지")
    error_code: Optional[str] = Field(None, description="오류 코드")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="오류 발생 시간"
    )


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="서비스 상태")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="확인 시간"
    )
    version: str = Field(..., description="서비스 버전")
    uptime: Optional[float] = Field(None, description="가동 시간 (초)")


class RateLimitInfo(BaseModel):
    requests_remaining: int = Field(..., description="남은 요청 수")
    reset_time: str = Field(..., description="제한 리셋 시간")  # 문자열로 변경
    window_size: int = Field(..., description="제한 시간 창 (초)")

    # 편의를 위한 클래스 메서드 추가 (선택사항)
    @classmethod
    def create_with_datetime(
            cls,
            requests_remaining: int,
            reset_time: datetime,
            window_size: int
    ) -> "RateLimitInfo":
        """datetime 객체를 받아서 문자열로 변환하여 생성"""
        return cls(
            requests_remaining=requests_remaining,
            reset_time=reset_time.isoformat(),
            window_size=window_size
        )