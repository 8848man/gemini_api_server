import logging
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.models.chat import ChatRequest, ChatResponse
from src.models.common import APIResponse, ErrorResponse
from src.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def chat(request: Request, chat_request: ChatRequest):
    """
    대화 API

    캐릭터 프롬프트와 메시지 히스토리를 기반으로 AI 응답을 생성합니다.

    - **character_prompt**: 캐릭터 설정 프롬프트 (1-1000자)
    - **messages**: 대화 메시지 배열 (1-50개)
        - **user**: 사용자 이름 (1-50자)
        - **message**: 메시지 내용 (1-2000자)
        - **sendDt**: 전송 시간 (ISO 8601 형식)

    ## 응답
    - **message**: AI 생성 응답 메시지
    - **timestamp**: 응답 생성 시간
    - **model_used**: 사용된 AI 모델명
    - **confidence_score**: 응답 신뢰도 점수 (0.0-1.0)
    """

    try:
        # 요청 로깅
        client_id = getattr(request.state, "user", {}).get("api_key", "unknown")
        logger.info(f"Chat request from client: {client_id}, messages: {len(chat_request.messages)}")

        # Gemini 서비스를 통한 응답 생성
        response = await gemini_service.generate_chat_response(chat_request)

        logger.info(f"Chat response generated, confidence: {response.confidence_score}")

        return APIResponse(
            success=True,
            data=response.dict(),
            message="Chat response generated successfully"
        )

    except RuntimeError as e:
        logger.error(f"Gemini service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="AI service is currently unavailable",
                error_code="SERVICE_UNAVAILABLE"
            ).dict()
        )

    except ValueError as e:
        logger.warning(f"Invalid request data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="Invalid request data",
                error_code="INVALID_REQUEST"
            ).dict()
        )

    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="An unexpected error occurred",
                error_code="INTERNAL_ERROR"
            ).dict()
        )


@router.get("/chat/models")
async def get_available_models():
    """사용 가능한 AI 모델 목록 조회"""

    return APIResponse(
        success=True,
        data={
            "models": [
                {
                    "name": "gemini-pro",
                    "description": "Google's Gemini Pro model for general conversation",
                    "max_tokens": 30720,
                    "supported_languages": ["ko", "en", "ja", "zh"]
                }
            ],
            "current_model": gemini_service.model.model_name if gemini_service.model else None
        },
        message="Available models retrieved successfully"
    )


@router.post("/chat/validate")
async def validate_chat_request(chat_request: ChatRequest):
    """채팅 요청 데이터 유효성 검증"""
    
    try:
        # 기본 Pydantic 검증은 이미 완료됨
        
        # 추가 비즈니스 로직 검증
        if not chat_request.messages:
            raise ValueError("At least one message is required")
            
        if len(chat_request.messages) > 50:
            raise ValueError("Too many messages (max: 50)")
            
        # 메시지 시간순 정렬 확인
        sorted_messages = sorted(chat_request.messages, key=lambda x: x.sendDt)
        if chat_request.messages != sorted_messages:
            logger.warning("Messages are not in chronological order")
        
        return APIResponse(
            success=True,
            data={
                "valid": True,
                "message_count": len(chat_request.messages),
                "character_prompt_length": len(chat_request.character_prompt)
            },
            message="Request validation passed"
        )
        
    except ValueError as e:
        return APIResponse(
            success=False,
            data={"valid": False, "errors": [str(e)]},
            message="Request validation failed"
        )