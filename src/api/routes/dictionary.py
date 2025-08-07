import logging
from typing import List

from fastapi import APIRouter, HTTPException, Path, Query, Request, status

from src.models.common import APIResponse, ErrorResponse
from src.models.dictionary import DictionaryResponse
from src.services.dictionary_service import dictionary_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dictionary/{word}", response_model=APIResponse)
async def lookup_word(
    request: Request,
    word: str = Path(
        ...,
        min_length=1,
        max_length=50,
        regex=r"^[a-zA-Z\-']+$",
        description="조회할 영단어"
    )
):
    """
    영단어 사전 조회 API
    
    영단어를 입력받아 상세한 사전 정보를 반환합니다.
    
    - **word**: 조회할 영단어 (1-50자, 영문자만)
    
    ## 응답 정보
    - **meanings**: 주요 의미 목록
    - **level**: 교육 수준 태그 (초등/중등/고등)
    - **synonyms**: 유의어 목록
    - **antonyms**: 반의어 목록
    - **example_sentence**: 영어 예문
    - **example_translation**: 예문 해석
    - **confidence_score**: 정보 신뢰도 점수 (0.0-1.0)
    - **pronunciation**: 발음 기호 (선택사항)
    - **part_of_speech**: 품사 (선택사항)
    """
    
    try:
        # 요청 로깅
        client_id = getattr(request.state, "user", {}).get("api_key", "unknown")
        logger.info(f"Dictionary lookup request from client: {client_id}, word: {word}")
        
        # 단어 조회
        result = await dictionary_service.lookup_word(word)
        
        if result.success:
            logger.info(f"Dictionary lookup successful for word: {word}")
            return APIResponse(
                success=True,
                data=result.data.dict() if result.data else None,
                message="Word definition retrieved successfully"
            )
        else:
            logger.warning(f"Dictionary lookup failed for word: {word}, error: {result.error_message}")
            
            # 단어를 찾을 수 없는 경우
            if "not found" in result.error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error=f"Word '{word}' not found in dictionary",
                        error_code="WORD_NOT_FOUND"
                    ).dict()
                )
            
            # 기타 오류
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=result.error_message,
                    error_code="DICTIONARY_ERROR"
                ).dict()
            )
            
    except HTTPException:
        # FastAPI HTTPException은 그대로 전파
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in dictionary lookup for '{word}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="An unexpected error occurred during dictionary lookup",
                error_code="INTERNAL_ERROR"
            ).dict()
        )


@router.get("/dictionary/suggest/{prefix}")
async def get_word_suggestions(
    request: Request,
    prefix: str = Path(
        ...,
        min_length=2,
        max_length=20,
        description="자동완성할 단어 접두사"
    ),
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="반환할 제안 단어 수 (최대 50개)"
    )
):
    """
    단어 자동완성 제안 API
    
    입력된 접두사로 시작하는 영단어 목록을 반환합니다.
    
    - **prefix**: 자동완성할 단어의 접두사 (2-20자)
    - **limit**: 반환할 제안 개수 (기본값: 10, 최대: 50)
    """
    
    try:
        # 요청 로깅
        client_id = getattr(request.state, "user", {}).get("api_key", "unknown")
        logger.info(f"Word suggestion request from client: {client_id}, prefix: {prefix}")
        
        # 자동완성 제안 조회
        suggestions = await dictionary_service.get_word_suggestions(prefix, limit)
        
        logger.info(f"Word suggestions retrieved for prefix: {prefix}, count: {len(suggestions)}")
        
        return APIResponse(
            success=True,
            data={
                "prefix": prefix,
                "suggestions": suggestions,
                "count": len(suggestions)
            },
            message="Word suggestions retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in word suggestions for prefix '{prefix}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="An unexpected error occurred during word suggestion",
                error_code="INTERNAL_ERROR"
            ).dict()
        )


@router.get("/dictionary/random")
async def get_random_word(
    request: Request,
    level: str = Query(
        None,
        regex=r"^(초등|중등|고등)$",
        description="교육 수준 필터 (초등/중등/고등)"
    )
):
    """
    랜덤 단어 조회 API
    
    학습용 랜덤 영단어를 반환합니다.
    
    - **level**: 교육 수준 필터 (선택사항)
    """
    
    try:
        # 요청 로깅
        client_id = getattr(request.state, "user", {}).get("api_key", "unknown")
        logger.info(f"Random word request from client: {client_id}, level: {level}")
        
        # 간단한 랜덤 단어 목록 (실제로는 데이터베이스나 외부 API 사용)
        import random
        
        word_pools = {
            "초등": ["apple", "book", "cat", "dog", "elephant", "fish", "good", "happy"],
            "중등": ["beautiful", "computer", "different", "education", "important", "information"],
            "고등": ["appropriate", "circumstances", "development", "environment", "establishment", "fundamental"]
        }
        
        if level and level in word_pools:
            random_word = random.choice(word_pools[level])
        else:
            all_words = []
            for words in word_pools.values():
                all_words.extend(words)
            random_word = random.choice(all_words)
        
        # 선택된 단어의 상세 정보 조회
        result = await dictionary_service.lookup_word(random_word)
        
        if result.success:
            return APIResponse(
                success=True,
                data=result.data.dict() if result.data else None,
                message="Random word retrieved successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error="Failed to retrieve random word details",
                    error_code="RANDOM_WORD_ERROR"
                ).dict()
            )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in random word retrieval: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="An unexpected error occurred during random word retrieval",
                error_code="INTERNAL_ERROR"
            ).dict()
        )