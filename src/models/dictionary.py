from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EducationLevel(str, Enum):
    ELEMENTARY = "초등"
    MIDDLE = "중등"
    HIGH = "고등"


class DictionaryEntry(BaseModel):
    word: str = Field(..., description="영단어")
    meanings: List[str] = Field(..., description="단어 뜻 목록")
    level: EducationLevel = Field(..., description="교육 수준 태그")
    synonyms: List[str] = Field(default=[], description="유의어 목록")
    antonyms: List[str] = Field(default=[], description="반의어 목록")
    example_sentence: str = Field(..., description="영어 예문")
    example_translation: str = Field(..., description="예문 해석")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="정보 신뢰도 점수"
    )
    pronunciation: Optional[str] = Field(None, description="발음 기호")
    part_of_speech: Optional[str] = Field(None, description="품사")


class DictionaryResponse(BaseModel):
    success: bool = Field(..., description="조회 성공 여부")
    data: Optional[DictionaryEntry] = Field(None, description="사전 데이터")
    error_message: Optional[str] = Field(None, description="오류 메시지")