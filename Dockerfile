FROM python:3.11-slim

WORKDIR /app

# 필수 시스템 빌드 도구 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 패키지 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 소스 코드 복사
COPY . .

# PlayMCP 원격 통신을 위한 웹 서버 포트 개방
EXPOSE 8000

# 가이드라인 준수: Stateless 원격 구동을 위한 uvicorn 실행 (0.0.0.0 필수)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
