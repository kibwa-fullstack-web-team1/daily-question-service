# Python 3.12 기반 이미지 사용
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY daily-question-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY daily-question-service/app ./app
COPY daily-question-service/daily-question-service_manage.py .

# 서비스 포트 노출
EXPOSE 8001

# 애플리케이션 실행 명령어
CMD ["python", "daily-question-service_manage.py"]
