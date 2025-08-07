import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.chat import ChatMessage, ChatRequest, ChatResponse
from src.models.dictionary import DictionaryEntry, DictionaryResponse, EducationLevel
from src.models.auth import APIKeyRequest, TokenData, AuthResponse
from src.models.common import APIResponse, ErrorResponse, HealthCheckResponse


class TestChatModels:
    """채팅 모델 테스트"""

    def test_chat_message_valid(self):
        """유효한 채팅 메시지 테스트"""
        message = ChatMessage(
            user="test_user",
            message="Hello, world!",
            sendDt=datetime.now()
        )
        
        assert message.user == "test_user"
        assert message.message == "Hello, world!"
        assert isinstance(message.sendDt, datetime)

    def test_chat_message_sanitization(self):
        """채팅 메시지 sanitization 테스트"""
        message = ChatMessage(
            user="test_user",
            message="<script>alert('xss')</script>",
            sendDt=datetime.now()
        )
        
        # sanitization이 적용되어야 함
        assert "<script>" not in message.message
        assert "script" in message.message  # 태그는 제거되지만 내용은 남음

    def test_chat_message_validation_errors(self):
        """채팅 메시지 유효성 검증 오류 테스트"""
        # 사용자명 길이 초과
        with pytest.raises(ValidationError):
            ChatMessage(
                user="a" * 51,
                message="test",
                sendDt=datetime.now()
            )
        
        # 메시지 길이 초과
        with pytest.raises(ValidationError):
            ChatMessage(
                user="test",
                message="a" * 2001,
                sendDt=datetime.now()
            )

    def test_chat_request_valid(self):
        """유효한 채팅 요청 테스트"""
        messages = [
            ChatMessage(user="user1", message="Hello", sendDt=datetime.now())
        ]
        
        request = ChatRequest(
            character_prompt="Be helpful",
            messages=messages
        )
        
        assert request.character_prompt == "Be helpful"
        assert len(request.messages) == 1

    def test_chat_request_validation_errors(self):
        """채팅 요청 유효성 검증 오류 테스트"""
        # 메시지가 없는 경우
        with pytest.raises(ValidationError):
            ChatRequest(
                character_prompt="Be helpful",
                messages=[]
            )
        
        # 메시지 개수 초과
        messages = [
            ChatMessage(user=f"user{i}", message="test", sendDt=datetime.now())
            for i in range(51)
        ]
        
        with pytest.raises(ValidationError):
            ChatRequest(
                character_prompt="Be helpful",
                messages=messages
            )

    def test_chat_response_valid(self):
        """유효한 채팅 응답 테스트"""
        response = ChatResponse(
            message="Hello there!",
            model_used="gemini-pro",
            confidence_score=0.95
        )
        
        assert response.message == "Hello there!"
        assert response.model_used == "gemini-pro"
        assert response.confidence_score == 0.95
        assert isinstance(response.timestamp, datetime)


class TestDictionaryModels:
    """사전 모델 테스트"""

    def test_dictionary_entry_valid(self):
        """유효한 사전 항목 테스트"""
        entry = DictionaryEntry(
            word="apple",
            meanings=["사과", "애플"],
            level=EducationLevel.ELEMENTARY,
            synonyms=["fruit"],
            antonyms=[],
            example_sentence="I eat an apple.",
            example_translation="나는 사과를 먹는다.",
            confidence_score=0.9
        )
        
        assert entry.word == "apple"
        assert len(entry.meanings) == 2
        assert entry.level == EducationLevel.ELEMENTARY
        assert entry.confidence_score == 0.9

    def test_dictionary_entry_confidence_validation(self):
        """신뢰도 점수 유효성 검증 테스트"""
        # 유효 범위 (0.0 - 1.0)
        entry = DictionaryEntry(
            word="test",
            meanings=["테스트"],
            level=EducationLevel.MIDDLE,
            example_sentence="Test sentence",
            example_translation="테스트 문장",
            confidence_score=0.5
        )
        assert entry.confidence_score == 0.5
        
        # 범위 초과 시 오류
        with pytest.raises(ValidationError):
            DictionaryEntry(
                word="test",
                meanings=["테스트"],
                level=EducationLevel.MIDDLE,
                example_sentence="Test",
                example_translation="테스트",
                confidence_score=1.5
            )

    def test_education_level_enum(self):
        """교육 수준 enum 테스트"""
        assert EducationLevel.ELEMENTARY == "초등"
        assert EducationLevel.MIDDLE == "중등"
        assert EducationLevel.HIGH == "고등"

    def test_dictionary_response_success(self):
        """성공 사전 응답 테스트"""
        entry = DictionaryEntry(
            word="test",
            meanings=["테스트"],
            level=EducationLevel.MIDDLE,
            example_sentence="Test",
            example_translation="테스트",
            confidence_score=0.8
        )
        
        response = DictionaryResponse(success=True, data=entry)
        
        assert response.success is True
        assert response.data == entry
        assert response.error_message is None

    def test_dictionary_response_error(self):
        """오류 사전 응답 테스트"""
        response = DictionaryResponse(
            success=False,
            error_message="Word not found"
        )
        
        assert response.success is False
        assert response.data is None
        assert response.error_message == "Word not found"


class TestAuthModels:
    """인증 모델 테스트"""

    def test_api_key_request_valid(self):
        """유효한 API 키 요청 테스트"""
        request = APIKeyRequest(api_key="test-api-key-12345")
        
        assert request.api_key == "test-api-key-12345"

    def test_api_key_request_validation_error(self):
        """API 키 요청 유효성 검증 오류 테스트"""
        # 최소 길이 미달
        with pytest.raises(ValidationError):
            APIKeyRequest(api_key="short")

    def test_token_data(self):
        """토큰 데이터 테스트"""
        token_data = TokenData(
            api_key="test-key",
            expires_at=datetime.now()
        )
        
        assert token_data.api_key == "test-key"
        assert isinstance(token_data.expires_at, datetime)

    def test_auth_response(self):
        """인증 응답 테스트"""
        response = AuthResponse(
            success=True,
            message="Authentication successful",
            token="jwt-token",
            expires_at=datetime.now()
        )
        
        assert response.success is True
        assert response.message == "Authentication successful"
        assert response.token == "jwt-token"


class TestCommonModels:
    """공통 모델 테스트"""

    def test_api_response_success(self):
        """성공 API 응답 테스트"""
        response = APIResponse(
            success=True,
            data={"key": "value"},
            message="Operation successful"
        )
        
        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.message == "Operation successful"
        assert isinstance(response.timestamp, datetime)

    def test_error_response(self):
        """오류 응답 테스트"""
        response = ErrorResponse(
            error="Something went wrong",
            error_code="TEST_ERROR"
        )
        
        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.error_code == "TEST_ERROR"
        assert isinstance(response.timestamp, datetime)

    def test_health_check_response(self):
        """헬스 체크 응답 테스트"""
        response = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            uptime=3600.5
        )
        
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.uptime == 3600.5
        assert isinstance(response.timestamp, datetime)