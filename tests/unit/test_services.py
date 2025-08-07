import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.redis_service import RedisService
from src.services.gemini_service import GeminiService
from src.services.dictionary_service import DictionaryService
from src.models.chat import ChatRequest, ChatMessage
from src.models.dictionary import EducationLevel


class TestRedisService:
    """Redis 서비스 테스트"""

    @pytest.fixture
    def redis_service(self):
        service = RedisService()
        service.redis = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_get_success(self, redis_service):
        """Redis GET 성공 테스트"""
        redis_service.redis.get.return_value = '"test_value"'
        
        result = await redis_service.get("test_key")
        
        assert result == "test_value"
        redis_service.redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_not_found(self, redis_service):
        """Redis GET 키 없음 테스트"""
        redis_service.redis.get.return_value = None
        
        result = await redis_service.get("nonexistent_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, redis_service):
        """Redis SET 성공 테스트"""
        redis_service.redis.set.return_value = True
        
        result = await redis_service.set("test_key", "test_value", expire=60)
        
        assert result is True
        redis_service.redis.set.assert_called_once_with("test_key", "test_value", ex=60)

    @pytest.mark.asyncio
    async def test_set_dict_value(self, redis_service):
        """Redis SET 딕셔너리 값 테스트"""
        redis_service.redis.set.return_value = True
        test_dict = {"key": "value", "number": 123}
        
        result = await redis_service.set("test_key", test_dict)
        
        assert result is True
        # JSON 직렬화된 값으로 호출되었는지 확인
        call_args = redis_service.redis.set.call_args
        assert '"key": "value"' in call_args[0][1]

    @pytest.mark.asyncio
    async def test_incr_success(self, redis_service):
        """Redis INCR 성공 테스트"""
        redis_service.redis.pipeline.return_value = AsyncMock()
        pipeline_mock = redis_service.redis.pipeline.return_value
        pipeline_mock.execute.return_value = [5]  # INCR 결과
        
        result = await redis_service.incr("counter_key", expire=60)
        
        assert result == 5
        pipeline_mock.incr.assert_called_once_with("counter_key")
        pipeline_mock.expire.assert_called_once_with("counter_key", 60)

    @pytest.mark.asyncio
    async def test_exists_true(self, redis_service):
        """Redis EXISTS 참 테스트"""
        redis_service.redis.exists.return_value = 1
        
        result = await redis_service.exists("existing_key")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, redis_service):
        """Redis EXISTS 거짓 테스트"""
        redis_service.redis.exists.return_value = 0
        
        result = await redis_service.exists("nonexistent_key")
        
        assert result is False


class TestGeminiService:
    """Gemini 서비스 테스트"""

    @pytest.fixture
    def gemini_service(self):
        service = GeminiService()
        service.model = MagicMock()
        service.model.model_name = "gemini-pro"
        return service

    @pytest.fixture
    def sample_chat_request(self):
        return ChatRequest(
            character_prompt="Be helpful",
            messages=[
                ChatMessage(
                    user="test_user",
                    message="Hello!",
                    sendDt=datetime.now()
                )
            ]
        )

    @pytest.mark.asyncio
    async def test_generate_chat_response_success(self, gemini_service, sample_chat_request):
        """채팅 응답 생성 성공 테스트"""
        mock_response = MagicMock()
        mock_response.text = "안녕하세요! 무엇을 도와드릴까요?"
        
        with patch.object(gemini_service, '_call_gemini_api', return_value=mock_response):
            result = await gemini_service.generate_chat_response(sample_chat_request)
            
            assert result.message == "안녕하세요! 무엇을 도와드릴까요?"
            assert result.model_used == "gemini-pro"
            assert 0.0 <= result.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_generate_chat_response_no_model(self, sample_chat_request):
        """모델 없이 채팅 응답 생성 테스트"""
        service = GeminiService()
        service.model = None
        
        with pytest.raises(RuntimeError):
            await service.generate_chat_response(sample_chat_request)

    @pytest.mark.asyncio
    async def test_generate_chat_response_api_error(self, gemini_service, sample_chat_request):
        """API 오류 시 채팅 응답 테스트"""
        with patch.object(gemini_service, '_call_gemini_api', side_effect=Exception("API Error")):
            result = await gemini_service.generate_chat_response(sample_chat_request)
            
            assert "오류가 발생했습니다" in result.message
            assert result.confidence_score == 0.0

    def test_build_conversation_history(self, gemini_service, sample_chat_request):
        """대화 히스토리 구성 테스트"""
        history = gemini_service._build_conversation_history(
            sample_chat_request.character_prompt,
            sample_chat_request.messages
        )
        
        assert "[캐릭터 설정]" in history
        assert "Be helpful" in history
        assert "[대화 기록]" in history
        assert "test_user: Hello!" in history

    def test_calculate_confidence_score_good_response(self, gemini_service):
        """좋은 응답의 신뢰도 점수 테스트"""
        mock_response = MagicMock()
        mock_response.text = "안녕하세요! 도움이 필요하시면 언제든 말씀해주세요."
        
        score = gemini_service._calculate_confidence_score(mock_response)
        
        assert 0.5 <= score <= 1.0

    def test_calculate_confidence_score_no_response(self, gemini_service):
        """응답 없을 때 신뢰도 점수 테스트"""
        score = gemini_service._calculate_confidence_score(None)
        
        assert score == 0.0


class TestDictionaryService:
    """사전 서비스 테스트"""

    @pytest.fixture
    def dictionary_service(self):
        service = DictionaryService()
        service.gemini_model = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_lookup_word_invalid_format(self, dictionary_service):
        """잘못된 형식의 단어 조회 테스트"""
        result = await dictionary_service.lookup_word("123invalid")
        
        assert result.success is False
        assert "Invalid English word format" in result.error_message

    @pytest.mark.asyncio
    async def test_lookup_word_cached(self, dictionary_service):
        """캐시된 단어 조회 테스트"""
        from src.models.dictionary import DictionaryEntry
        
        cached_entry = DictionaryEntry(
            word="apple",
            meanings=["사과"],
            level=EducationLevel.ELEMENTARY,
            example_sentence="I eat an apple.",
            example_translation="나는 사과를 먹는다.",
            confidence_score=0.9
        )
        
        with patch.object(dictionary_service, '_get_cached_word', return_value=cached_entry):
            result = await dictionary_service.lookup_word("apple")
            
            assert result.success is True
            assert result.data.word == "apple"

    @pytest.mark.asyncio
    async def test_lookup_word_generate_new(self, dictionary_service):
        """새 단어 조회 및 생성 테스트"""
        from src.models.dictionary import DictionaryEntry
        
        generated_entry = DictionaryEntry(
            word="test",
            meanings=["테스트", "시험"],
            level=EducationLevel.MIDDLE,
            example_sentence="This is a test.",
            example_translation="이것은 테스트입니다.",
            confidence_score=0.85
        )
        
        with patch.object(dictionary_service, '_get_cached_word', return_value=None), \
             patch.object(dictionary_service, '_generate_dictionary_entry', return_value=generated_entry), \
             patch.object(dictionary_service, '_cache_word', return_value=None):
            
            result = await dictionary_service.lookup_word("test")
            
            assert result.success is True
            assert result.data.word == "test"

    def test_is_valid_english_word_valid(self, dictionary_service):
        """유효한 영단어 검증 테스트"""
        valid_words = ["apple", "test", "hello-world", "it's", "CAPS"]
        
        for word in valid_words:
            assert dictionary_service._is_valid_english_word(word) is True

    def test_is_valid_english_word_invalid(self, dictionary_service):
        """유효하지 않은 영단어 검증 테스트"""
        invalid_words = ["", "123", "한글", "test123", "a" * 51, "test@domain"]
        
        for word in invalid_words:
            assert dictionary_service._is_valid_english_word(word) is False

    @pytest.mark.asyncio
    async def test_get_word_suggestions(self, dictionary_service):
        """단어 제안 테스트"""
        suggestions = await dictionary_service.get_word_suggestions("app", limit=5)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
        # 'app'로 시작하는 단어가 있는지 확인
        assert any(word.startswith("app") for word in suggestions)

    @pytest.mark.asyncio
    async def test_get_word_suggestions_short_prefix(self, dictionary_service):
        """짧은 접두사 제안 테스트"""
        suggestions = await dictionary_service.get_word_suggestions("a", limit=10)
        
        assert suggestions == []  # 2글자 미만은 빈 리스트

    @pytest.mark.asyncio
    async def test_generate_fallback_entry(self, dictionary_service):
        """fallback 사전 항목 생성 테스트"""
        entry = await dictionary_service._generate_fallback_entry("test")
        
        assert entry is not None
        assert entry.word == "test"
        assert entry.confidence_score == 0.3  # 낮은 신뢰도
        assert len(entry.meanings) > 0

    def test_parse_gemini_response_valid_json(self, dictionary_service):
        """유효한 JSON 응답 파싱 테스트"""
        response_text = '''
        여기 단어 정보입니다:
        {
            "meanings": ["테스트", "시험"],
            "level": "중등",
            "synonyms": ["exam"],
            "antonyms": [],
            "example_sentence": "This is a test.",
            "example_translation": "이것은 테스트입니다.",
            "pronunciation": "/test/",
            "part_of_speech": "noun"
        }
        이상입니다.
        '''
        
        entry = dictionary_service._parse_gemini_response("test", response_text)
        
        assert entry is not None
        assert entry.word == "test"
        assert len(entry.meanings) == 2
        assert entry.level == EducationLevel.MIDDLE

    def test_parse_gemini_response_invalid_json(self, dictionary_service):
        """유효하지 않은 JSON 응답 파싱 테스트"""
        response_text = "이것은 JSON이 아닙니다."
        
        entry = dictionary_service._parse_gemini_response("test", response_text)
        
        assert entry is None