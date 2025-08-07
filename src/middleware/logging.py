import json
import logging
import time
from typing import Dict, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # 요청 정보 로깅
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", ""),
            "timestamp": time.time(),
        }

        # 요청 바디 로깅 (민감한 정보 제외)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # 민감한 필드 마스킹
                    body_str = body.decode("utf-8")
                    request_info["body_size"] = len(body_str)
                    
                    # JSON인 경우 구조적 로깅
                    try:
                        body_json = json.loads(body_str)
                        masked_body = self._mask_sensitive_data(body_json)
                        request_info["body_preview"] = str(masked_body)[:500]
                    except json.JSONDecodeError:
                        request_info["body_preview"] = body_str[:100]
            except Exception as e:
                logger.warning(f"Failed to read request body: {e}")

        logger.info(f"Request: {json.dumps(request_info)}")

        # 요청 처리
        try:
            response = await call_next(request)
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url} - "
                f"Error: {str(e)} - Time: {processing_time:.3f}s"
            )
            raise

        # 응답 정보 로깅
        processing_time = time.time() - start_time
        response_info = {
            "status_code": response.status_code,
            "processing_time": round(processing_time, 3),
            "response_size": len(getattr(response, "body", b"")),
        }

        logger.info(f"Response: {json.dumps(response_info)}")

        # 응답 헤더에 처리 시간 추가
        response.headers["X-Process-Time"] = str(processing_time)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출 (프록시 고려)"""
        # 리버스 프록시를 통한 경우 실제 IP 확인
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        
        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip
            
        return request.client.host if request.client else "unknown"

    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """민감한 데이터 마스킹"""
        if not isinstance(data, dict):
            return data

        sensitive_keys = {
            "password", "token", "api_key", "secret", "key",
            "authorization", "auth", "credential", "private"
        }

        masked_data = {}
        for key, value in data.items():
            lower_key = key.lower()
            if any(sensitive in lower_key for sensitive in sensitive_keys):
                masked_data[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked_data[key] = self._mask_sensitive_data(value)
            elif isinstance(value, list):
                masked_data[key] = [
                    self._mask_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value[:5]  # 첫 5개 항목만 로깅
                ]
            else:
                masked_data[key] = value

        return masked_data