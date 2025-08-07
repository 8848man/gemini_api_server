from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class APIKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=10, description="API 인증 키")


class TokenData(BaseModel):
    api_key: Optional[str] = None
    expires_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    success: bool = Field(..., description="인증 성공 여부")
    message: str = Field(..., description="인증 결과 메시지")
    token: Optional[str] = Field(None, description="JWT 토큰")
    expires_at: Optional[datetime] = Field(None, description="토큰 만료 시간")