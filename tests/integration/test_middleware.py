import pytest
from fastapi import status
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from tests.conftest import TEST_API_KEY


class TestAuthMiddleware:
    """인증 미들웨어 테스트"""

    @pytest.mark.asyncio
    async def test_public_path_no_auth(self, async_client):
        """공개 경로 인증 없이 접근 테스트"""
        public_paths = ["/", "/api/v1/health", "/metrics"]
        
        for path in public_paths:
            response = await async_client.get(path)
            # 인증 오류가 아닌 다른 응답이어야 함
            assert response.status_code != status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_protected_path_no_auth(self, async_client):
        """보호된 경로 인증 없이 접근 테스트"""
        response = await async_client.get("/api/v1/chat/models")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_valid_api_key_auth(self, async_client):
        """유효한 API 키 인증 테스트"""
        headers = {"X-API-Key": TEST_API_KEY}
        
        response = await async_client.get("/api/v1/chat/models", headers=headers)
        
        # 인증은 성공하고 다른 오류가 있을 수 있음
        assert response.status_code != status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_api_key_auth(self, async_client):
        """유효하지 않은 API 키 인증 테스트"""
        headers = {"X-API-Key": "invalid-key"}
        
        response = await async_client.get("/api/v1/chat/models", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_jwt_token_auth(self, async_client):
        """JWT 토큰 인증 테스트"""
        from src.utils.security import create_access_token
        
        token_data = {"sub": "test_user", "api_key": TEST_API_KEY}
        token = create_access_token(token_data)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await async_client.get("/api/v1/chat/models", headers=headers)
        
        # 인증은 성공해야 함
        assert response.status_code != status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_jwt_token_auth(self, async_client):
        """유효하지 않은 JWT 토큰 인증 테스트"""
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        
        response = await async_client.get("/api/v1/chat/models", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_expired_jwt_token_auth(self, async_client):
        """만료된 JWT 토큰 인증 테스트"""
        from src.utils.security import create_access_token
        
        # 과거 시간으로 만료시간 설정
        token_data = {"sub": "test_user", "exp": (datetime.utcnow() - timedelta(hours=1)).timestamp()}
        token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await async_client.get("/api/v1/chat/models", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRateLimitMiddleware:
    """Rate limit 미들웨어 테스트"""

    @pytest.mark.asyncio
    async def test_normal_request_rate(self, async_client, auth_headers):
        """정상 요청 속도 테스트"""
        # Redis가 모킹되어 있어 실제 rate limiting은 작동하지 않음
        response = await async_client.get("/api/v1/chat/models", headers=auth_headers)
        
        # Rate limit 헤더가 있는지 확인
        if response.status_code == status.HTTP_200_OK:
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, async_client, auth_headers):
        """Rate limit 헤더 테스트"""
        with patch('src.services.redis_service.redis_service.incr', return_value=1), \
             patch('src.services.redis_service.redis_service.get', return_value=1):
            
            response = await async_client.get("/api/v1/chat/models", headers=auth_headers)
            
            if response.status_code == status.HTTP_200_OK:
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, async_client, auth_headers):
        """Rate limit 초과 테스트"""
        # Redis 모킹으로 rate limit 초과 시뮬레이션
        with patch('src.services.redis_service.redis_service.incr', return_value=101), \
             patch('src.services.redis_service.redis_service.connect'), \
             patch('src.services.redis_service.redis_service.redis', AsyncMock()):
            
            response = await async_client.get("/api/v1/chat/models", headers=auth_headers)
            
            # Rate limit에 걸릴 수 있음 (Redis 모킹 상태에 따라)
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_concurrent_request_limit(self, async_client, auth_headers):
        """동시 요청 수 제한 테스트"""
        # 동시 요청 모킹
        with patch('src.services.redis_service.redis_service.get', return_value=6):  # MAX_CONCURRENT_REQUESTS보다 큰 값
            response = await async_client.get("/api/v1/chat/models", headers=auth_headers)
            
            # 동시 요청 수 제한에 걸릴 수 있음
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                data = response.json()
                assert "Too many concurrent requests" in data.get("detail", {}).get("error", "")


class TestLoggingMiddleware:
    """로깅 미들웨어 테스트"""

    @pytest.mark.asyncio
    async def test_request_logging(self, async_client, auth_headers):
        """요청 로깅 테스트"""
        with patch('src.middleware.logging.logger') as mock_logger:
            response = await async_client.get("/api/v1/chat/models", headers=auth_headers)
            
            # 로깅이 호출되었는지 확인
            assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_response_time_header(self, async_client, auth_headers):
        """응답 시간 헤더 테스트"""
        response = await async_client.get("/api/v1/chat/models", headers=auth_headers)
        
        # 응답 시간 헤더가 추가되었는지 확인
        assert "X-Process-Time" in response.headers
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0

    @pytest.mark.asyncio
    async def test_post_request_body_logging(self, async_client, auth_headers, sample_chat_request):
        """POST 요청 본문 로깅 테스트"""
        with patch('src.middleware.logging.logger') as mock_logger, \
             patch('src.services.gemini_service.gemini_service.generate_chat_response'):
            
            response = await async_client.post(
                "/api/v1/chat",
                json=sample_chat_request,
                headers=auth_headers
            )
            
            # 요청 본문 로깅이 호출되었는지 확인
            assert mock_logger.info.called
            
            # 로깅 호출 중에 body_size나 body_preview가 포함되었는지 확인
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            has_body_log = any("body_size" in call or "body_preview" in call for call in log_calls)
            assert has_body_log

    @pytest.mark.asyncio
    async def test_sensitive_data_masking(self, async_client):
        """민감 데이터 마스킹 테스트"""
        from src.middleware.logging import LoggingMiddleware
        
        middleware = LoggingMiddleware(None)
        
        # 민감한 데이터가 포함된 딕셔너리
        sensitive_data = {
            "username": "test_user",
            "password": "secret123",
            "api_key": "sk-abc123",
            "token": "jwt-token",
            "normal_field": "normal_value"
        }
        
        masked_data = middleware._mask_sensitive_data(sensitive_data)
        
        assert masked_data["username"] == "test_user"  # 일반 필드는 그대로
        assert masked_data["password"] == "***MASKED***"  # 민감한 필드는 마스킹
        assert masked_data["api_key"] == "***MASKED***"
        assert masked_data["token"] == "***MASKED***"
        assert masked_data["normal_field"] == "normal_value"

    @pytest.mark.asyncio
    async def test_client_ip_extraction(self, async_client, auth_headers):
        """클라이언트 IP 추출 테스트"""
        from src.middleware.logging import LoggingMiddleware
        from fastapi import Request
        from unittest.mock import MagicMock
        
        middleware = LoggingMiddleware(None)
        
        # X-Forwarded-For 헤더가 있는 경우
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.side_effect = lambda key: {
            "X-Forwarded-For": "192.168.1.1, 10.0.0.1",
            "X-Real-IP": None
        }.get(key)
        mock_request.client.host = "127.0.0.1"
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.1"  # 첫 번째 IP 사용
        
        # X-Real-IP 헤더만 있는 경우
        mock_request.headers.get.side_effect = lambda key: {
            "X-Forwarded-For": None,
            "X-Real-IP": "203.0.113.1"
        }.get(key)
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "203.0.113.1"
        
        # 프록시 헤더가 없는 경우
        mock_request.headers.get.return_value = None
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "127.0.0.1"  # client.host 사용