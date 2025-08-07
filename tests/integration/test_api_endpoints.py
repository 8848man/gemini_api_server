import pytest
from fastapi import status
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from tests.conftest import TEST_API_KEY


class TestHealthEndpoints:
    """헬스 체크 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, async_client):
        """기본 헬스 체크 테스트"""
        response = await async_client.get("/api/v1/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, async_client):
        """상세 헬스 체크 테스트"""
        response = await async_client.get("/api/v1/health/detailed")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "redis" in data["checks"]


class TestChatEndpoints:
    """채팅 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_chat_success(self, async_client, sample_chat_request, auth_headers):
        """채팅 성공 테스트"""
        mock_response = MagicMock()
        mock_response.message = "안녕하세요! 무엇을 도와드릴까요?"
        mock_response.model_used = "gemini-pro"
        mock_response.confidence_score = 0.95
        mock_response.dict.return_value = {
            "message": "안녕하세요! 무엇을 도와드릴까요?",
            "model_used": "gemini-pro",
            "confidence_score": 0.95,
            "timestamp": datetime.now().isoformat()
        }
        
        with patch('src.services.gemini_service.gemini_service.generate_chat_response', 
                  return_value=mock_response):
            response = await async_client.post(
                "/api/v1/chat",
                json=sample_chat_request,
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["message"] == "안녕하세요! 무엇을 도와드릴까요?"

    @pytest.mark.asyncio
    async def test_chat_unauthorized(self, async_client, sample_chat_request):
        """채팅 인증 실패 테스트"""
        response = await async_client.post(
            "/api/v1/chat",
            json=sample_chat_request
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_chat_invalid_request(self, async_client, auth_headers):
        """채팅 잘못된 요청 테스트"""
        invalid_request = {
            "character_prompt": "",  # 빈 프롬프트
            "messages": []  # 빈 메시지
        }
        
        response = await async_client.post(
            "/api/v1/chat",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_chat_service_unavailable(self, async_client, sample_chat_request, auth_headers):
        """채팅 서비스 불가 테스트"""
        with patch('src.services.gemini_service.gemini_service.generate_chat_response',
                  side_effect=RuntimeError("Service unavailable")):
            response = await async_client.post(
                "/api/v1/chat",
                json=sample_chat_request,
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_get_available_models(self, async_client, auth_headers):
        """사용 가능한 모델 조회 테스트"""
        response = await async_client.get(
            "/api/v1/chat/models",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "models" in data["data"]

    @pytest.mark.asyncio
    async def test_validate_chat_request(self, async_client, sample_chat_request, auth_headers):
        """채팅 요청 검증 테스트"""
        response = await async_client.post(
            "/api/v1/chat/validate",
            json=sample_chat_request,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is True


class TestDictionaryEndpoints:
    """사전 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_lookup_word_success(self, async_client, auth_headers, sample_dictionary_entry):
        """단어 조회 성공 테스트"""
        from src.models.dictionary import DictionaryResponse
        
        mock_response = DictionaryResponse(success=True, data=sample_dictionary_entry)
        
        with patch('src.services.dictionary_service.dictionary_service.lookup_word',
                  return_value=mock_response):
            response = await async_client.get(
                "/api/v1/dictionary/apple",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["word"] == "apple"

    @pytest.mark.asyncio
    async def test_lookup_word_not_found(self, async_client, auth_headers):
        """단어 조회 실패 테스트"""
        from src.models.dictionary import DictionaryResponse
        
        mock_response = DictionaryResponse(
            success=False,
            error_message="Word 'nonexistent' not found in dictionary"
        )
        
        with patch('src.services.dictionary_service.dictionary_service.lookup_word',
                  return_value=mock_response):
            response = await async_client.get(
                "/api/v1/dictionary/nonexistent",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_lookup_word_invalid_format(self, async_client, auth_headers):
        """잘못된 형식 단어 조회 테스트"""
        response = await async_client.get(
            "/api/v1/dictionary/123invalid",
            headers=auth_headers
        )
        
        # Path validation에서 걸러져야 함
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_lookup_word_unauthorized(self, async_client):
        """단어 조회 인증 실패 테스트"""
        response = await async_client.get("/api/v1/dictionary/apple")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_word_suggestions(self, async_client, auth_headers):
        """단어 제안 테스트"""
        mock_suggestions = ["apple", "application", "apply"]
        
        with patch('src.services.dictionary_service.dictionary_service.get_word_suggestions',
                  return_value=mock_suggestions):
            response = await async_client.get(
                "/api/v1/dictionary/suggest/app",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["suggestions"]) == 3
        assert "apple" in data["data"]["suggestions"]

    @pytest.mark.asyncio
    async def test_word_suggestions_with_limit(self, async_client, auth_headers):
        """제한된 단어 제안 테스트"""
        mock_suggestions = ["apple", "application"]
        
        with patch('src.services.dictionary_service.dictionary_service.get_word_suggestions',
                  return_value=mock_suggestions):
            response = await async_client.get(
                "/api/v1/dictionary/suggest/app?limit=2",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]["suggestions"]) == 2

    @pytest.mark.asyncio
    async def test_random_word(self, async_client, auth_headers, sample_dictionary_entry):
        """랜덤 단어 조회 테스트"""
        from src.models.dictionary import DictionaryResponse
        
        mock_response = DictionaryResponse(success=True, data=sample_dictionary_entry)
        
        with patch('src.services.dictionary_service.dictionary_service.lookup_word',
                  return_value=mock_response):
            response = await async_client.get(
                "/api/v1/dictionary/random",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "word" in data["data"]

    @pytest.mark.asyncio
    async def test_random_word_with_level(self, async_client, auth_headers, sample_dictionary_entry):
        """교육 수준별 랜덤 단어 조회 테스트"""
        from src.models.dictionary import DictionaryResponse
        
        mock_response = DictionaryResponse(success=True, data=sample_dictionary_entry)
        
        with patch('src.services.dictionary_service.dictionary_service.lookup_word',
                  return_value=mock_response):
            response = await async_client.get(
                "/api/v1/dictionary/random?level=초등",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True


class TestRootEndpoints:
    """루트 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        """루트 엔드포인트 테스트"""
        response = await async_client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "uptime" in data

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, async_client):
        """메트릭스 엔드포인트 테스트"""
        response = await async_client.get("/metrics")
        
        # 프로메테우스 메트릭스 형식인지 확인
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/plain; charset=utf-8"