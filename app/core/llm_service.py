import os
from typing import Optional
from openai import OpenAI
import httpx

from app.schemas import question_schema

# OpenAI API 키를 환경 변수에서 가져옵니다.
from app.config.config import Config

OPENAI_API_KEY = Config.OPENAI_API_KEY
STORY_SERVICE_URL = "http://localhost:8011" # 스토리 서비스 URL (현재 개발 중, 추후 API 호출 가능하다고 가정)

async def get_recommended_question(user_id: int) -> Optional[question_schema.Question]:
    """
    OpenAI API를 호출하여 사용자에게 개인화된 '오늘의 질문'을 추천합니다.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    client = OpenAI(api_key=OPENAI_API_KEY)

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

    prompt = f"사용자 {user_id}에게 오늘 하루를 돌아볼 수 있는 질문 하나를 추천해 주세요. 질문만 간결하게 답변해주세요."

    if story_data:
        story_content = story_data.get("content", "")
        story_segments = story_data.get("segments", [])
        
        segments_text = "\n".join([s.get("segment_text", "") for s in story_segments])

        base_prompt = f"사용자 {user_id}에게 오늘 하루를 돌아볼 수 있는 질문 하나를 추천해 주세요."
    json_format_instruction = """
JSON 형식:
{
  "question": "string",
  "expected_answers": ["answer1", "answer2", "answer3"]
}
"""

    prompt = "" # prompt 변수 초기화
    if story_data:
        story_content = story_data.get("content", "")
        story_segments = story_data.get("segments", [])
        segments_text = "\n".join([s.get("segment_text", "") for s in story_segments])

        prompt = f"""{base_prompt}
이 이야기를 바탕으로 개인화된 질문과 그에 대한 3개의 간결한 예상 모범 답변 리스트를 JSON 형식으로 반환해 주세요.
사용자 {user_id}의 최근 이야기입니다:
제목: {story_data.get("title", "")}
내용: {story_content}
세부 내용:
{segments_text}
{json_format_instruction}"""
    else:
        # If no story data, ask for a generic question and generic expected answers.
        prompt = f"""{base_prompt}
질문과 함께 3개의 간결한 예상 모범 답변 리스트를 JSON 형식으로 반환해 주세요.
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
