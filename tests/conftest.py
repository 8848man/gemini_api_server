import asyncio
import os
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock

# 테스트 환경변수 설정
os.environ.update({
    "DEBUG": "True",
    "SECRET_KEY": "test-secret-key",
    "API_KEY": "test-api-key",
    "JWT_SECRET_KEY": "test-jwt-secret",
    "GEMINI_API_KEY": "test-gemini-key",
    "REDIS_URL": "redis://localhost:6379/1",  # 테스트용 DB
    "REQUESTS_PER_MINUTE": "100",
    "MAX_CONCURRENT_REQUESTS": "5",
})

from src.main import create_app
from src.services.redis_service_wrapper import redis_service
from src.services.gemini_service import gemini_service
from src.services.dictionary_service import dictionary_service


@pytest.fixture(scope="session")
def event_loop():
    """세션 레벨 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def app():
    """FastAPI 앱 인스턴스"""
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """동기 테스트 클라이언트"""
    return TestClient(app)


@pytest_asyncio.fixture(scope="session")
async def async_client(app):
    """비동기 테스트 클라이언트"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def setup_redis():
    """Redis 테스트 설정"""
    try:
        # FakeRedis를 사용한 모킹
        import fakeredis.aioredis
        
        # Redis 서비스를 FakeRedis로 교체
        fake_redis = fakeredis.aioredis.FakeRedis()
        redis_service.redis = fake_redis
        
        yield fake_redis
        
    except ImportError:
        # fakeredis가 없는 경우 모킹
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.exists.return_value = False
        mock_redis.ttl.return_value = -1
        mock_redis.sadd.return_value = True
        mock_redis.sismember.return_value = False
        
        redis_service.redis = mock_redis
        yield mock_redis


@pytest.fixture
def mock_gemini_service():
    """Gemini 서비스 모킹"""
    original_model = gemini_service.model
    
    # 모킹된 모델 설정
    mock_model = MagicMock()
    mock_model.model_name = "gemini-pro"
    gemini_service.model = mock_model
    
    yield mock_model
    
    # 원본 모델 복구
    gemini_service.model = original_model


@pytest.fixture
def auth_headers():
    """인증 헤더"""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def sample_chat_request():
    """샘플 채팅 요청 데이터"""
    from datetime import datetime
    
    return {
        "character_prompt": "친근하고 도움이 되는 AI 어시스턴트로 행동해주세요.",
        "messages": [
            {
                "user": "test_user",
                "message": "안녕하세요!",
                "sendDt": datetime.now().isoformat()
            },
            {
                "user": "assistant", 
                "message": "안녕하세요! 무엇을 도와드릴까요?",
                "sendDt": datetime.now().isoformat()
            }
        ]
    }


@pytest.fixture
def sample_dictionary_entry():
    """샘플 사전 데이터"""
    from src.models.dictionary import DictionaryEntry, EducationLevel
    
    return DictionaryEntry(
        word="apple",
        meanings=["사과", "애플 (회사명)"],
        level=EducationLevel.ELEMENTARY,
        synonyms=["fruit"],
        antonyms=[],
        example_sentence="I eat an apple every day.",
        example_translation="나는 매일 사과를 먹습니다.",
        confidence_score=0.95,
        pronunciation="/ˈæp.əl/",
        part_of_speech="noun"
    )


@pytest.fixture(autouse=True)
async def setup_test_data(setup_redis):
    """각 테스트 전 데이터 초기화"""
    # Redis 데이터 클리어
    if hasattr(setup_redis, 'flushdb'):
        await setup_redis.flushdb()
    
    yield
    
    # 테스트 후 정리
    if hasattr(setup_redis, 'flushdb'):
        await setup_redis.flushdb()


# 테스트용 상수
TEST_API_KEY = "test-api-key"
TEST_WORD = "test"
TEST_USER = "test_user"