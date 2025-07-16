import os
from typing import Optional
from openai import OpenAI

from app.schemas import question_schema

# OpenAI API 키를 환경 변수에서 가져옵니다.
from app.config.config import Config

OPENAI_API_KEY = Config.OPENAI_API_KEY

async def get_recommended_question(user_id: int) -> Optional[question_schema.Question]:
    """
    OpenAI API를 호출하여 사용자에게 개인화된 '오늘의 질문'을 추천합니다.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    client = OpenAI(api_key=OPENAI_API_KEY)

    # TODO: user_id를 기반으로 사용자 메타데이터/활동을 가져와 프롬프트에 활용
    # 현재는 간단한 프롬프트로 시작합니다.
    prompt = f"사용자 {user_id}에게 오늘 하루를 돌아볼 수 있는 질문 하나를 추천해 주세요. 질문만 간결하게 답변해주세요."

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
