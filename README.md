# daily-question-service

'기억의 정원' 프로젝트의 '오늘의 질문' 서비스를 관리합니다.

## 서비스 개요
이 서비스는 사용자에게 개인화된 질문을 제공하며, LLM(Large Language Model)을 활용하여 질문을 생성하고 관리합니다.

## 주요 기능
- LLM 기반 질문 추천
- 질문 CRUD
- 사용자 답변 저장

## 프로젝트 구조
```
daily-question-service/
├── app/
│   ├── api/            # API 엔드포인트 정의 (라우터)
│   ├── config/         # 설정 관리
│   ├── core/           # 핵심 비즈니스 로직 및 외부 서비스 연동 (LLM 서비스 등)
│   ├── helper/         # 비즈니스 로직 (현재는 비어있음, 필요 시 추가)
│   ├── models/         # 데이터베이스 모델
│   ├── schemas/        # Pydantic 스키마 (데이터 유효성 검사 및 직렬화)
│   ├── utils/          # 유틸리티 함수 (데이터베이스 연결 등)
│   └── __init__.py     # FastAPI 앱 팩토리
├── .github/            # GitHub 관련 설정 (CODEOWNERS 등)
├── .venv/              # Python 가상 환경
├── daily-question-service_manage.py # 앱 실행 파일
├── .env                # 환경 변수 (Gitignore에 포함)
├── requirements.txt    # Python 의존성 목록
├── .gitignore          # Git 무시 파일
```

## 개발 환경 설정

1.  **가상 환경 생성 및 활성화**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **의존성 설치**
    ```bash
    pip install -r requirements.txt
    ```

3.  **환경 변수 설정**
    `.env` 파일을 생성하고 다음 환경 변수를 설정합니다.
    ```
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
    DATABASE_URL="postgresql://user:password@host:port/dbname"
    USER_SERVICE_URL="http://localhost:8000"
    ```

4.  **서비스 실행**
    ```bash
    uvicorn daily-question-service_manage:app --host 0.0.0.0 --port 8001
    ```

## API 문서
서비스가 실행 중일 때, `/docs` 또는 `/redoc` 경로에서 API 문서를 확인할 수 있습니다.
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`