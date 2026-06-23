# 1. 경량화된 Python 공식 이미지 사용
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 필수 시스템 패키지 설치 (필요시 컴파일러 추가, slim 이미지 최적화)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. 의존성 파일 복사 및 설치 (캐싱 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스 코드 복사
COPY . .

# 6. 중요: PlayMCP가 접속할 FastAPI 웹 서버 포트(8000) 개방
EXPOSE 8000

# 7. uvicorn을 이용해 FastAPI 앱 실행 (외부 접속 허용을 위해 0.0.0.0 바인딩)
# 'main:app'에서 main은 실행할 파일명(main.py), app은 FastAPI 인스턴스 변수명입니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
