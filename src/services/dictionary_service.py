import json
import logging
import re
from typing import Dict, List, Optional

import httpx
from google.generativeai import GenerativeModel

from src.core.config import get_settings
from src.models.dictionary import DictionaryEntry, DictionaryResponse, EducationLevel
from src.services.redis_service_wrapper import redis_service

logger = logging.getLogger(__name__)
settings = get_settings()


class DictionaryService:
    """영단어 사전 서비스"""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.gemini_model = None
        
        # Gemini 모델 초기화 (사전 생성용)
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_model = GenerativeModel(model_name=settings.GEMINI_MODEL)
                logger.info("Dictionary service initialized with Gemini")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini for dictionary: {e}")

    async def lookup_word(self, word: str) -> DictionaryResponse:
        """영단어 조회"""
        
        # 입력 검증
        if not self._is_valid_english_word(word):
            return DictionaryResponse(
                success=False,
                error_message="Invalid English word format"
            )

        # 캐시에서 조회
        cached_result = await self._get_cached_word(word.lower())
        if cached_result:
            logger.info(f"Dictionary cache hit for word: {word}")
            return DictionaryResponse(success=True, data=cached_result)

        try:
            # AI를 통한 단어 정보 생성
            dictionary_entry = await self._generate_dictionary_entry(word)
            
            if dictionary_entry:
                # 캐시에 저장 (24시간)
                await self._cache_word(word.lower(), dictionary_entry)
                logger.info(f"Dictionary entry generated for word: {word}")
                return DictionaryResponse(success=True, data=dictionary_entry)
            else:
                return DictionaryResponse(
                    success=False,
                    error_message="Word not found or could not generate definition"
                )

        except Exception as e:
            logger.error(f"Error looking up word '{word}': {e}")
            return DictionaryResponse(
                success=False,
                error_message="Internal server error during word lookup"
            )

    def _is_valid_english_word(self, word: str) -> bool:
        """영단어 형식 검증"""
        if not word or len(word) > 50:
            return False
        
        # 영문자만 허용 (하이픈, 어포스트로피 포함)
        pattern = r"^[a-zA-Z\-']+$"
        return bool(re.match(pattern, word))

    #async def _get_cached_word(self, word: str) -> Optional[DictionaryEntry]:
    #     """캐시된 단어 정보 조회"""
    #     cache_key = f"dict:{word}"
    #     cached_data = await redis_service.get(cache_key)
    #
    #     if cached_data:
    #         try:
    #             return DictionaryEntry(**cached_data)
    #         except Exception as e:
    #             logger.warning(f"Invalid cached data for word {word}: {e}")
    #             await redis_service.delete(cache_key)
    #
    #     return None
    async def _get_cached_word(self, word: str) -> Optional[DictionaryEntry]:
        """캐시된 단어 정보 조회"""
        cache_key = f"dict:{word}"
        try:
            cached_data = await redis_service.get(cache_key)
        except Exception as e:
            logger.error(f"Redis error while getting cache for {word}: {e}")
            # Redis 오류 시 캐시를 못 읽었으니 None 리턴해서 정상 흐름 유지
            return None

        if cached_data:
            try:
                return DictionaryEntry(**cached_data)
            except Exception as e:
                logger.warning(f"Invalid cached data for word {word}: {e}")
                try:
                    await redis_service.delete(cache_key)
                except Exception as e2:
                    logger.error(f"Failed to delete invalid cache for {word}: {e2}")
        return None

    async def _cache_word(self, word: str, entry: DictionaryEntry) -> None:

        try:
            """단어 정보 캐시 저장"""
            cache_key = f"dict:{word}"
            await redis_service.set(cache_key, entry.dict(), expire=86400)  # 24시간
        except Exception as e:
            logger.warning(f"redis server is not available! no cached in redis!")

    async def _generate_dictionary_entry(self, word: str) -> Optional[DictionaryEntry]:
        """AI를 통한 사전 정보 생성"""
        if not self.gemini_model:
            return await self._generate_fallback_entry(word)

        try:
            prompt = self._build_dictionary_prompt(word)

            # Gemini API 호출
            response = await self._call_gemini_for_dictionary(prompt)
            
            if response and response.text:
                return self._parse_gemini_response(word, response.text)
            
        except Exception as e:
            logger.error(f"Gemini dictionary generation failed for '{word}': {e}")
        
        # fallback 처리
        return await self._generate_fallback_entry(word)

    def _build_dictionary_prompt(self, word: str) -> str:
        """사전 생성용 프롬프트 구성"""
        return f"""
영단어 "{word}"에 대한 상세한 사전 정보를 **순수 JSON 오브젝트** 형식으로만 출력해 주세요.  
반드시 JSON 문법만 포함하며, 다른 텍스트, 설명, 주석, 또는 인사말은 포함하지 마세요.
또, 현재 응답에 사용된 AI 버전도 포함해주세요.

다음 형식으로 정확히 응답하세요:
{{
  "meanings": ["주요 의미1", "주요 의미2", "주요 의미3"],
  "level": "초등|중등|고등|토익|토플",
  "tags": ["토익", "고등", "일상", "음식", "행동", "동사"],
  "synonyms": ["유의어1", "유의어2"],
  "antonyms": ["반의어1", "반의어2"],
  "example_sentence": "영어 예문",
  "example_translation": "예문 한국어 번역",
  "pronunciation": "발음기호",
  "part_of_speech": "품사"
  "gemini_version" : "현재 응답에 사용된 AI 버전"
}}

예시:  
{{
  "meanings": ["높은", "고급의", "고음의"],
  "level": "중등",
  "tags": ["중등", "토익", "형용사" ... etc]
  "synonyms": ["tall", "lofty"],
  "antonyms": ["low", "short"],
  "example_sentence": "The mountain is very high.",
  "example_translation": "그 산은 매우 높다.",
  "pronunciation": "haɪ",
  "part_of_speech": "형용사"
  "gemini_version" : "Gemini 2.0 Flash"
}}

단어: {word}
"""
#         return f"""
# 영단어 "{word}"에 대한 상세한 사전 정보를 JSON 형식으로 제공해주세요.
#
# 다음 형식으로 응답해주세요:
# {{
#     "meanings": ["주요 의미1", "주요 의미2", "주요 의미3"],
#     "level": "초등|중등|고등",
#     "synonyms": ["유의어1", "유의어2"],
#     "antonyms": ["반의어1", "반의어2"],
#     "example_sentence": "영어 예문",
#     "example_translation": "예문 한국어 번역",
#     "pronunciation": "발음기호",
#     "part_of_speech": "품사"
# }}
#
# 요구사항:
# 1. 한국 교육과정 기준으로 초등/중등/고등 수준 분류
# 2. 가장 일반적이고 중요한 의미 3개 이하
# 3. 실용적이고 자연스러운 예문
# 4. 정확한 한국어 번역
# 5. JSON 형식만 응답 (다른 텍스트 없이)
# 예시 :
# {{
#   "meanings": ["높은", "고급의", "고음의"],
#   "level": "중등",
#   "synonyms": ["tall", "lofty"],
#   "antonyms": ["low", "short"],
#   "example_sentence": "The mountain is very high.",
#   "example_translation": "그 산은 매우 높다.",
#   "pronunciation": "haɪ",
#   "part_of_speech": "형용사"
# }}
#
# 단어: {word}
# """

    async def _call_gemini_for_dictionary(self, prompt: str):
        """사전용 Gemini API 호출"""
        import asyncio
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.gemini_model.generate_content(prompt)
        )
        return response

    def _parse_gemini_response(self, word: str, response_text: str) -> Optional[DictionaryEntry]:
        """Gemini 응답 파싱"""
        try:
            # JSON 추출
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                logger.warning(f"No JSON found in Gemini response for '{word}'")
                return None
            
            data = json.loads(json_match.group())
            
            # 교육 수준 변환
            level_map = {"초등": EducationLevel.ELEMENTARY, "중등": EducationLevel.MIDDLE, "고등": EducationLevel.HIGH}
            level = level_map.get(data.get("level", "중등"), EducationLevel.MIDDLE)
            
            return DictionaryEntry(
                word=word,
                meanings=data.get("meanings", [f"Definition for {word}"]),
                level=level,
                synonyms=data.get("synonyms", []),
                antonyms=data.get("antonyms", []),
                example_sentence=data.get("example_sentence", f"This is an example with {word}."),
                example_translation=data.get("example_translation", f"이것은 {word}를 사용한 예문입니다."),
                pronunciation=data.get("pronunciation"),
                part_of_speech=data.get("part_of_speech"),
                confidence_score=0.85  # Gemini 생성의 경우 높은 신뢰도
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response for '{word}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing Gemini response for '{word}': {e}")
            return None

    async def _generate_fallback_entry(self, word: str) -> Optional[DictionaryEntry]:
        """기본 사전 정보 생성 (AI 실패 시)"""
        
        # 간단한 규칙 기반 분류
        level = EducationLevel.MIDDLE
        if len(word) <= 4:
            level = EducationLevel.ELEMENTARY
        elif len(word) > 8:
            level = EducationLevel.HIGH
        
        return DictionaryEntry(
            word=word,
            meanings=[f"English word: {word}"],
            level=level,
            synonyms=[],
            antonyms=[],
            example_sentence=f"Please use {word} in context.",
            example_translation=f"{word}를 문맥에 맞게 사용해보세요.",
            confidence_score=0.3  # 낮은 신뢰도
        )

    async def get_word_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """단어 자동완성 제안"""
        if not prefix or len(prefix) < 2:
            return []
        
        # 간단한 구현 (실제로는 단어 데이터베이스나 API 사용)
        common_words = [
            "apple", "application", "apply", "appreciate", "approach", "appropriate",
            "book", "beautiful", "because", "before", "behind", "believe", "benefit",
            "computer", "complete", "community", "company", "consider", "continue",
            "different", "development", "decision", "difficult", "discover", "discuss",
            "education", "experience", "example", "environment", "especially", "every",
            "important", "information", "interest", "international", "internet", "issue"
        ]
        
        matching_words = [
            word for word in common_words 
            if word.lower().startswith(prefix.lower())
        ]
        
        return matching_words[:limit]


# 전역 사전 서비스 인스턴스
dictionary_service = DictionaryService()