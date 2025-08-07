from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class ChatMessage(BaseModel):
    user: str = Field(..., min_length=1, max_length=50, description="사용자 이름")
    message: str = Field(..., min_length=1, max_length=2000, description="메시지 내용")
    sendDt: datetime = Field(..., description="전송 시간")

    @validator("message")
    def sanitize_message(cls, v: str) -> str:
        # XSS 방지를 위한 기본 sanitization
        dangerous_chars = ["<", ">", "&", '"', "'"]
        for char in dangerous_chars:
            v = v.replace(char, "")
        return v.strip()


class ChatRequest(BaseModel):
    character_prompt: str = Field(
        ..., min_length=1, max_length=1000, description="캐릭터 프롬프트"
    )
    messages: List[ChatMessage] = Field(
        ..., min_items=1, max_items=50, description="대화 메시지 목록"
    )

    @validator("character_prompt")
    def sanitize_prompt(cls, v: str) -> str:
        # 기본 sanitization
        dangerous_chars = ["<", ">", "&", '"', "'"]
        for char in dangerous_chars:
            v = v.replace(char, "")
        return v.strip()


class ChatResponse(BaseModel):
    message: str = Field(..., description="AI 응답 메시지")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")
    model_used: str = Field(..., description="사용된 AI 모델")
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="응답 신뢰도 점수"
    )