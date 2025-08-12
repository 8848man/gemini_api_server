# ---------- Builder stage ----------
FROM python:3.11-slim AS builder

# 시스템 의존성 설치 (컴파일러 등)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 파일 복사 (requirements.txt 기준)
COPY requirements.txt .

# Python 패키지 전역 설치 (멀티스테이지 빌드 복사 편리)
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Production stage ----------
FROM python:3.11-slim AS production

# 비루트 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 필요한 런타임 패키지 설치 (curl 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Builder에서 설치한 패키지 복사 (전역 설치 경로)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY requirements.txt .

# 로그 및 데이터 디렉토리 생성 및 권한 설정
RUN mkdir -p logs data && chown -R appuser:appuser /app

# 환경 변수 설정
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 헬스체크 스크립트 생성
RUN echo '#!/bin/sh\ncurl -f http://localhost:8080/api/v1/health || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown appuser:appuser /app/healthcheck.sh

# 비루트 사용자로 전환
USER appuser

# 포트 노출 (로컬 개발용, Cloud Run 배포시 PORT 환경변수 이용 권장)
EXPOSE 8080

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/app/healthcheck.sh"]

# 앱 실행 커맨드 (uvicorn 직접 실행)
# CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
CMD ["sh", "-c", "python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

# ---------- Development stage ----------
FROM production AS development

USER root

# 개발용 패키지 설치 (버전 고정 가능)
RUN pip install --no-cache-dir \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    black==23.11.0 \
    isort==5.12.0 \
    flake8==6.1.0 \
    mypy==1.7.1

USER appuser

# 개발용 볼륨 마운트 설정
VOLUME ["/app/src", "/app/tests"]

# 개발 모드(핫 리로드)로 실행
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]