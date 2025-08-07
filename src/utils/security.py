import hashlib
import hmac
import logging

from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

from src.core.config import get_settings
from src.services.firebase_service import verify_firebase_token

logger = logging.getLogger(__name__)
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_api_key(api_key: str) -> bool:
    """API 키 검증"""
    if not api_key or not settings.API_KEY:
        return False
    return hmac.compare_digest(api_key, settings.API_KEY)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Firebase 또는 JWT 토큰 검증"""
    # 1. Firebase 검증 시도
    try:
        decoded_token = verify_firebase_token(token)
        decoded_token['auth_type'] = 'firebase'
        return decoded_token
    except Exception as e:
        logger.debug(f"Firebase token verification failed: {e}")

    # 2. 기존 JWT 검증 시도
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        payload['auth_type'] = 'jwt'
        return payload
    except jwt.JWTError as e:
        logger.debug(f"JWT token verification failed: {e}")
        return None


def hash_password(password: str) -> str:
    """비밀번호 해시화"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def generate_request_hash(user_id: str, content: str) -> str:
    """요청 해시 생성 (중복 요청 방지용)"""
    combined = f"{user_id}:{content}:{datetime.now().strftime('%Y%m%d%H%M')}"
    return hashlib.sha256(combined.encode()).hexdigest()


def sanitize_input(input_string: str, max_length: int = 2000) -> str:
    """입력 데이터 sanitization"""
    if not input_string:
        return ""
    
    # 길이 제한
    sanitized = input_string[:max_length]
    
    # 위험한 문자 제거
    dangerous_chars = {
        "<": "&lt;",
        ">": "&gt;",
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#x27;",
        "/": "&#x2F;",
    }
    
    for char, replacement in dangerous_chars.items():
        sanitized = sanitized.replace(char, replacement)
    
    return sanitized.strip()


def is_valid_ip(ip_address: str) -> bool:
    """IP 주소 유효성 검증"""
    try:
        parts = ip_address.split(".")
        return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
    except (ValueError, AttributeError):
        return False