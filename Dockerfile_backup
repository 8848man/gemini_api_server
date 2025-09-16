# Multi-stage build for Python application
FROM python:3.11-slim AS builder

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Poetry를 사용하지 않고 pip로 의존성 관리
WORKDIR /app
COPY requirements.txt .

# Python 의존성 설치
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim AS production

# 보안을 위한 비루트 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 필요한 런타임 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 작업 디렉토리 설정
WORKDIR /app

# Builder 단계에서 설치된 Python 패키지 복사
COPY --from=builder /root/.local /home/appuser/.local

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY pyproject.toml ./

# 로그 및 데이터 디렉토리 생성
RUN mkdir -p logs data && \
    chown -R appuser:appuser /app

# PATH에 사용자 local bin 추가
ENV PATH=/home/appuser/.local/bin:$PATH

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 헬스체크 스크립트 생성
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/api/v1/health || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown appuser:appuser /app/healthcheck.sh

# 비루트 사용자로 실행
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/app/healthcheck.sh"]

# 애플리케이션 실행
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM production AS development

# 개발용 의존성 추가
USER root
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy

# 개발용 볼륨 마운트 포인트
VOLUME ["/app/src", "/app/tests"]

USER appuser

# 개발 모드로 실행 (hot reload)
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]