import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.utils.security import (
    verify_api_key,
    create_access_token,
    verify_token,
    hash_password,
    verify_password,
    generate_request_hash,
    sanitize_input,
    is_valid_ip,
)


class TestSecurity:
    """보안 유틸리티 테스트"""

    def test_verify_api_key_valid(self):
        """유효한 API 키 검증 테스트"""
        with patch('src.utils.security.settings.API_KEY', 'test-api-key'):
            assert verify_api_key('test-api-key') is True

    def test_verify_api_key_invalid(self):
        """유효하지 않은 API 키 검증 테스트"""
        with patch('src.utils.security.settings.API_KEY', 'test-api-key'):
            assert verify_api_key('wrong-key') is False
            assert verify_api_key('') is False
            assert verify_api_key(None) is False

    def test_create_access_token(self):
        """JWT 토큰 생성 테스트"""
        data = {"sub": "test_user", "role": "user"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """만료시간이 있는 JWT 토큰 생성 테스트"""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        assert isinstance(token, str)
        
        # 토큰 검증
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"

    def test_verify_token_valid(self):
        """유효한 JWT 토큰 검증 테스트"""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["role"] == "admin"

    def test_verify_token_invalid(self):
        """유효하지 않은 JWT 토큰 검증 테스트"""
        assert verify_token("invalid.token.here") is None
        assert verify_token("") is None
        assert verify_token(None) is None

    def test_hash_password(self):
        """비밀번호 해싱 테스트"""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_verify_password(self):
        """비밀번호 검증 테스트"""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_generate_request_hash(self):
        """요청 해시 생성 테스트"""
        user_id = "test_user"
        content = "test content"
        
        hash1 = generate_request_hash(user_id, content)
        hash2 = generate_request_hash(user_id, content)
        
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex string
        # 같은 시간대에 생성되면 같은 해시
        assert hash1 == hash2

    def test_sanitize_input_basic(self):
        """기본 입력 sanitization 테스트"""
        dangerous_input = "<script>alert('xss')</script>"
        sanitized = sanitize_input(dangerous_input)
        
        assert "&lt;" in sanitized
        assert "&gt;" in sanitized
        assert "<script>" not in sanitized

    def test_sanitize_input_length_limit(self):
        """입력 길이 제한 테스트"""
        long_input = "a" * 3000
        sanitized = sanitize_input(long_input, max_length=100)
        
        assert len(sanitized) <= 100

    def test_sanitize_input_empty(self):
        """빈 입력 처리 테스트"""
        assert sanitize_input("") == ""
        assert sanitize_input(None) == ""

    def test_sanitize_input_special_chars(self):
        """특수 문자 sanitization 테스트"""
        test_cases = [
            ("<div>", "&lt;div&gt;"),
            ("'quote'", "&#x27;quote&#x27;"),
            ('"double"', "&quot;double&quot;"),
            ("path/to/file", "path&#x2F;to&#x2F;file"),
            ("a & b", "a &amp; b"),
        ]
        
        for input_str, expected in test_cases:
            result = sanitize_input(input_str)
            assert expected == result

    def test_is_valid_ip_valid(self):
        """유효한 IP 주소 테스트"""
        valid_ips = [
            "192.168.1.1",
            "127.0.0.1",
            "0.0.0.0",
            "255.255.255.255",
            "10.0.0.1",
        ]
        
        for ip in valid_ips:
            assert is_valid_ip(ip) is True

    def test_is_valid_ip_invalid(self):
        """유효하지 않은 IP 주소 테스트"""
        invalid_ips = [
            "256.1.1.1",
            "192.168.1",
            "192.168.1.1.1",
            "not.an.ip.address",
            "",
            None,
            "192.168.-1.1",
        ]
        
        for ip in invalid_ips:
            assert is_valid_ip(ip) is False