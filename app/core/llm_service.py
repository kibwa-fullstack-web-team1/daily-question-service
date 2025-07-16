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

        prompt = f"""사용자 {user_id}의 최근 이야기입니다:
제목: {story_data.get("title", "")}
내용: {story_content}
세부 내용:
{segments_text}

이 이야기를 바탕으로 사용자에게 오늘 하루를 돌아볼 수 있는 개인화된 질문 하나를 추천해 주세요. 질문만 간결하게 답변해주세요.
"""

    try:
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 사용자에게 개인화된 질문을 추천해주는 친절한 AI입니다."}, 
                {"role": "user", "content": prompt}
            ]
        )
        question_content = chat_completion.choices[0].message.content.strip()

        # 임시 ID와 생성 시간 사용 (실제 DB 저장 시에는 DB에서 할당)
        return question_schema.Question(
            id=0, # 임시 ID, 실제 DB 저장 시에는 DB에서 할당
            content=question_content,
            created_at="2025-07-11T00:00:00.000000" # 임시 시간
        )
    except Exception as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        # 오류 발생 시 기본 질문 반환 또는 예외 처리
        return question_schema.Question(
            id=0, 
            content="오늘 하루는 어떠셨나요?",
            created_at="2025-07-11T00:00:00.000000"
        )

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
