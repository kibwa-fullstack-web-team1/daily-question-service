import os
from typing import Optional, List
from openai import OpenAI
import httpx

from app.schemas import question_schema

# OpenAI API 키를 환경 변수에서 가져옵니다.
from app.config.config import Config

OPENAI_API_KEY = Config.OPENAI_API_KEY
STORY_SERVICE_URL = "http://localhost:8011" # 스토리 서비스 URL (현재 개발 중, 추후 API 호출 가능하다고 가정)

async def get_embedding(text: str, dimensions: int = 1024) -> List[float]:
    """
    OpenAI Embeddings API를 호출하여 텍스트의 임베딩 벡터를 반환합니다.
    MRL(Matryoshka Representation Learning)을 활용하여 임베딩 차원을 조절할 수 있습니다.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    client = OpenAI(api_key=OPENAI_API_KEY)
    model = "text-embedding-3-large"
    try:
        print(f"Creating embedding with model: {model} and dimensions: {dimensions}")
        response = client.embeddings.create(
            input=text,
            model=model,
            dimensions=dimensions
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"OpenAI Embeddings API 호출 중 오류 발생: {e}")
        raise


async def get_recommended_question(user_id: int) -> Optional[question_schema.Question]:
    """
    OpenAI API를 호출하여 사용자에게 개인화된 '오늘의 질문'을 추천합니다.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    client = OpenAI(api_key=OPENAI_API_KEY)

    base_prompt = f"사용자 {user_id}에게 오늘 하루를 돌아볼 수 있는 질문 하나를 추천해 주세요." # TODO: 나중에 사용자 RAG 기반 질문으로 바꿀 예정
    json_format_instruction = """
JSON 형식:
{
  "question": "string",
  "expected_answers": [
    "기쁨: [기쁨을 표현하는 자연스러운 대화체 예시 답변]",
    "만족: [만족을 표현하는 자연스러운 대화체 예시 답변]",
    "평온: [평온을 표현하는 자연스러운 대화체 예시 답변]",
    "기대: [기대를 표현하는 자연스러운 대화체 예시 답변]",
    "슬픔: [슬픔을 표현하는 자연스러운 대화체 예시 답변]",
    "분노: [분노를 표현하는 자연스러운 대화체 예시 답변]",
    "불안: [불안을 표현하는 자연스러운 대화체 예시 답변]",
    "좌절: [좌절을 표현하는 자연스러운 대화체 예시 답변]",
    "무덤덤: [무덤덤함을 표현하는 자연스러운 대화체 예시 답변]",
    "복잡: [복잡한 감정을 표현하는 자연스러운 대화체 예시 답변]"
  ]
}
"""

    # 스토리 서비스에서 사용자 스토리 가져오기
    story_data = None
    async with httpx.AsyncClient() as http_client:
        try:
            # user_id를 story_id로 가정하고 호출
            response = await http_client.get(f"{STORY_SERVICE_URL}/api/v0/stories/{user_id}")
            response.raise_for_status() # 2xx 외의 응답은 예외 발생
            story_data = response.json().get("results")
        except httpx.HTTPStatusError as e:
            print(f"스토리 서비스 호출 중 HTTP 오류 발생: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            print(f"스토리 서비스 연결 오류 발생: {e}")
        except Exception as e:
            print(f"스토리 데이터 처리 중 오류 발생: {e}")

    prompt = ""
    if story_data:
        prompt = f"""{base_prompt}
이 이야기를 바탕으로 개인화된 질문과 그에 대한 다음 10가지 감정 카테고리별 자연스러운 대화체 예시 답변 리스트를 JSON 형식으로 반환해 주세요. 각 감정 카테고리별로 1개의 간결하고 자연스러운 대화체 예시 답변을 생성해 주세요.
감정 카테고리:
- 기쁨: 긍정적이고 즐거운 감정
- 만족: 목표 달성이나 상황에 대한 긍정적인 평가
- 평온: 고요하고 안정된 감정
- 기대: 앞으로 일어날 일에 대한 긍정적인 예측
- 슬픔: 상실감이나 실망감에서 오는 감정
- 분노: 불만이나 화가 나는 감정
- 불안: 불확실성이나 위험에 대한 걱정
- 좌절: 노력에도 불구하고 실패했을 때의 실망감
- 무덤덤: 특별한 감정 없이 평이한 상태
- 복잡: 여러 감정이 섞여 명확히 정의하기 어려운 상태

사용자 {user_id}의 최근 이야기입니다:
제목: {story_data.get("title", "")}
내용: {story_content}
세부 내용:
{segments_text}
{json_format_instruction}"""
    else:
        # If no story data, ask for a generic question and generic expected answers.
        prompt = f"""{base_prompt}
질문과 함께 다음 10가지 감정 카테고리별 자연스러운 대화체 예시 답변 리스트를 JSON 형식으로 반환해 주세요. 각 감정 카테고리별로 1개의 간결하고 자연스러운 대화체 예시 답변을 생성해 주세요.
감정 카테고리:
- 기쁨: 긍정적이고 즐거운 감정
- 만족: 목표 달성이나 상황에 대한 긍정적인 평가
- 평온: 고요하고 안정된 감정
- 기대: 앞으로 일어날 일에 대한 긍정적인 예측
- 슬픔: 상실감이나 실망감에서 오는 감정
- 분노: 불만이나 화가 나는 감정
- 불안: 불확실성이나 위험에 대한 걱정
- 좌절: 노력에도 불구하고 실패했을 때의 실망감
- 무덤덤: 특별한 감정 없이 평이한 상태
- 복잡: 여러 감정이 섞여 명확히 정의하기 어려운 상태
{json_format_instruction}"""

    try:
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "당신은 사용자에게 개인화된 질문과 그에 대한 예상 답변을 JSON 형식으로 추천해주는 친절한 AI입니다."},
                {"role": "user", "content": prompt}
            ]
        )
        
        response_content = chat_completion.choices[0].message.content.strip()
        import json
        response_json = json.loads(response_content)
        
        question_content = response_json.get("question", "오늘 하루는 어떠셨나요?")
        expected_answers = response_json.get("expected_answers", [])

        # 임시 ID와 생성 시간 사용 (실제 DB 저장 시에는 DB에서 할당)
        return question_schema.Question(
            id=0, # 임시 ID, 실제 DB 저장 시에는 DB에서 할당
            content=question_content,
            expected_answers=expected_answers, # 예상 답변 추가
            created_at="2025-07-11T00:00:00.000000" # 임시 시간
        )
    except json.JSONDecodeError as e:
        print(f"JSON 디코딩 오류 발생: {e}")
        return question_schema.Question(
            id=0,
            content="오늘 하루는 어떠셨나요?",
            expected_answers=[],
            created_at="2025-07-11T00:00:00.000000"
        )
    except Exception as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        # 오류 발생 시 기본 질문 반환 또는 예외 처리
        return question_schema.Question(
            id=0,
            content="오늘 하루는 어떠셨나요?",
            expected_answers=[],
            created_at="2025-07-11T00:00:00.000000"
        )

VOICE_ANALYSIS_SERVICE_URL = Config.VOICE_ANALYSIS_SERVICE_URL # 음성 분석 서비스 URL

async def convert_voice_to_text(audio_file_path: str) -> str:
    """
    음성 파일을 텍스트로 변환합니다 (STT).
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"음성-텍스트 변환 중 오류 발생: {e}")
        raise

async def analyze_voice_with_service(s3_url: str) -> dict:
    """
    음성 분석 서비스에 S3 URL을 보내 음성 분석 결과를 받아옵니다.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{VOICE_ANALYSIS_SERVICE_URL}/api/analyze",
                json={"s3_url": s3_url},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"음성 분석 서비스 HTTP 오류 발생: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            print(f"음성 분석 서비스 연결 오류 발생: {e}")
            raise
        except Exception as e:
            print(f"음성 분석 서비스 호출 중 오류 발생: {e}")
            raise
