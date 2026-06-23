FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 패키지 복사 및 의존성 주입
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# [★핵심] PlayMCP in KC의 컨테이너 포트 가이드 설정과 uvicorn 포트를 일치시킵니다.
EXPOSE 8000

# 인프라 내부 바인딩 오류 방지를 위해 0.0.0.0 강제 적용
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
