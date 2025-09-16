import logging
from typing import List, Optional

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from src.core.config import get_settings
from src.models.chat import ChatMessage, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiService:
    """Google Gemini AI 서비스"""

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not configured")
            self.model = None
            return

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # 안전 설정
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }

            # 모델 초기화
            self.model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                safety_settings=safety_settings
            )
            logger.info(f"Gemini model initialized: {settings.GEMINI_MODEL}")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None

    async def generate_chat_response(self, chat_request: ChatRequest) -> ChatResponse:
        """채팅 응답 생성"""
        if not self.model:
            raise RuntimeError("Gemini model not initialized")
        try:
            # 대화 히스토리 구성
            conversation_history = self._build_conversation_history(
                chat_request.character_prompt,
                chat_request.messages
            )

            # Gemini API 호출
            response = await self._call_gemini_api(conversation_history)
            # 응답 처리
            response_text = response.text if response else "죄송합니다. 응답을 생성할 수 없습니다."
            # 신뢰도 점수 계산 (간단한 휴리스틱)
            confidence_score = self._calculate_confidence_score(response)

            return ChatResponse(
                message=response_text,
                model_used=settings.GEMINI_MODEL,
                confidence_score=confidence_score
            )

        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return ChatResponse(
                message="죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                model_used=settings.GEMINI_MODEL,
                confidence_score=0.0
            )

    def _build_conversation_history(self, character_prompt: str, messages: List[ChatMessage]) -> str:
        """대화 히스토리 구성"""
        # 시스템 프롬프트
        conversation = f"[캐릭터 설정]\n{character_prompt}\n\n"
        conversation += "[대화 지침]\n"
        conversation += "- 위 캐릭터 설정에 따라 자연스럽고 일관된 응답을 생성하세요.\n"
        conversation += "- 사용자와의 대화 맥락을 고려하여 응답하세요.\n"
        conversation += "- 부적절하거나 해로운 내용은 피해주세요.\n\n"
        
        # 대화 히스토리 추가
        conversation += "[대화 기록]\n"
        for msg in messages[-20:]:  # 최근 20개 메시지만 사용
            timestamp = msg.sendDt.strftime("%Y-%m-%d %H:%M:%S")
            conversation += f"[{timestamp}] {msg.user}: {msg.message}\n"
        
        conversation += "\n[응답 생성]\n위 대화 맥락을 바탕으로 자연스러운 응답을 생성해주세요:"
        
        return conversation

    async def _call_gemini_api(self, prompt: str):
        """Gemini API 호출"""
        try:
            # 동기적 호출을 비동기로 래핑
            import asyncio
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(prompt)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise

    def _calculate_confidence_score(self, response) -> float:
        """응답 신뢰도 점수 계산"""
        if not response or not response.text:
            return 0.0
        
        # 간단한 휴리스틱 기반 신뢰도 계산
        text = response.text
        score = 0.5  # 기본 점수
        
        # 길이 기반 조정
        if 10 <= len(text) <= 500:
            score += 0.2
        elif len(text) > 500:
            score += 0.1
        
        # 완전한 문장 여부 확인
        if text.endswith(('.', '!', '?', '다', '요', '습니다')):
            score += 0.2
        
        # 반복적인 패턴 검사
        words = text.split()
        if len(set(words)) / max(len(words), 1) > 0.7:  # 단어 다양성
            score += 0.1
        
        return min(1.0, max(0.0, score))


# 전역 Gemini 서비스 인스턴스
gemini_service = GeminiService()