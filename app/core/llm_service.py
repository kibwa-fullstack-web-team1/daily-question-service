import os
from typing import Optional, List
from openai import OpenAI
import httpx
import json

from app.schemas import question_schema
from app.config.config import Config

OPENAI_API_KEY = Config.OPENAI_API_KEY
DIFY_API_URL = Config.DIFY_API_URL
DIFY_WORKFLOW_ID = Config.DIFY_WORKFLOW_ID
DIFY_APP_API_KEY = Config.DIFY_APP_API_KEY

async def get_context_from_dify(user_id: int, prompt: str) -> Optional[str]:
    """
    Dify 워크플로우를 호출하여 개인화된 컨텍스트를 가져옵니다.
    """
    print(f"Dify API URL: {DIFY_API_URL}, Workflow ID: {DIFY_WORKFLOW_ID}, App API Key: {DIFY_APP_API_KEY}") # 디버깅을 위한 print 문 추가
    if not DIFY_API_URL or not DIFY_WORKFLOW_ID or not DIFY_APP_API_KEY:
        print("Dify API 설정이 완료되지 않았습니다.")
        return None

    url = f"{DIFY_API_URL}/v1/workflows/run"
    headers = {
        "Authorization": f"Bearer {DIFY_APP_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {
            "sys_user_id": str(user_id),
            "llm_prompt": prompt,
            "workflow_id": DIFY_WORKFLOW_ID # workflow_id 추가
        },
        "response_mode": "blocking",
        "user": f"user_{user_id}"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            
            # Dify 워크플로우 응답 구조에 따라 llm_output 추출
            llm_output = result.get("data", {}).get("outputs", {}).get("llm_output")
            if llm_output:
                print(f"Dify workflow successfully returned context for user {user_id}.")
                return llm_output
            else:
                print(f"Dify workflow returned no llm_output for user {user_id}. Response: {result}")
                return None
        except httpx.HTTPStatusError as e:
            print(f"Dify 워크플로우 호출 중 HTTP 오류 발생: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Dify 워크플로우 연결 오류 발생: {e}")
            return None
        except Exception as e:
            print(f"Dify 워크플로우 호출 중 알 수 없는 오류 발생: {e}")
            return None

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
    # Random Seed Word 전략을 위한 키워드 목록
    seed_words = ["가족", "친구", "추억", "행복", "도전", "변화", "성장", "감사", "용서", "미래"]
    import random
    random_seed_word = random.choice(seed_words)

    # Dify 워크플로우 호출을 위한 프롬프트 생성
    dify_prompt = f"""# 역할
당신은 사용자의 기억을 바탕으로 질문을 던지는, 친절하고 따뜻한 AI 동반자입니다.

# 지시
주어진 컨텍스트를 바탕으로, 사용자 {user_id}의 최근 이야기에서 {random_seed_word}와 관련된 내용을 찾아 사용자가 자신의 감정을 깊이 성찰할 수 있도록 유도하는 개인화된 '오늘의 질문과 답변'을 생성해주세요.

# 출력 규칙
응답은 반드시 아래의 예시와 동일한 JSON 형식이어야 합니다.
- "question" 키에는 생성된 개인화 질문을 담아주세요.
- "expected_answers" 키에는 10개의 감정(기쁨, 만족, 평온, 기대, 슬픔, 분노, 불안, 좌절, 무덤덤, 복잡)에 대해, 생성된 질문에 대해 컨텍스트 기반으로 나올 수 있는 자연스러운 1인칭 대화체 답변 예시를 각각 담아주세요.

# 예시
{{
  "question": "재호의 돌잔치 날, 가장 기억에 남는 순간은 무엇이었나요? 그 순간 어떤 감정을 느끼셨는지 궁금해요.",
  "expected_answers": [
    "기쁨: 온 가족이 모여서 재호의 첫 생일을 축하해 주니 정말 기쁘고 행복했어요.",
    "만족: 제가 직접 준비한 음식을 다들 맛있게 먹어줘서 정말 뿌듯하고 만족스러웠습니다.",
    "평온: 재호가 제 품에 안겨 평온하게 잠든 모습을 보니 마음이 참 편안해졌어요.",
    "기대: 돌잡이에서 붓을 잡았으니, 앞으로 얼마나 똑똑하고 멋지게 자랄지 기대가 돼요.",
    "슬픔: 멀리 살아 자주 못 보는 아들 내외가 돌아갈 때 조금 슬펐어요.",
    "분노: 행사가 조금 어수선해서 손님들을 제대로 챙기지 못한 것 같아 제 자신에게 화가 났어요.",
    "불안: 아이가 컨디션이 안 좋을까 봐 행사 내내 조금 불안했어요.",
    "좌절: 정성껏 준비한 순서 하나를 깜빡하고 지나가서 아쉽고 좌절스러웠어요.",
    "무덤덤: 정신없이 하루가 지나가서 솔직히 무슨 감정이었는지 잘 모르겠어요.",
    "복잡: 기쁘면서도, 아이를 키우느라 고생할 자식들 생각에 마음이 복잡했어요."
  ]
}}

사용자 {user_id}의 최근 이야기에서 {random_seed_word}와 관련된 내용을 찾아 요약해 주세요.
"""
    rag_context = await get_context_from_dify(user_id, dify_prompt)

    try:
        if rag_context:
            # Dify 워크플로우의 outputs.result 필드에 JSON 문자열이 있으므로 이를 파싱
            dify_response_data = json.loads(rag_context)
            
            # 실제 질문과 예상 답변은 이 파싱된 JSON 안에 있음
            question_content = dify_response_data.get("question", "오늘 하루는 어떠셨나요?")
            expected_answers = dify_response_data.get("expected_answers", [])

            return question_schema.Question(
                id=0, # 임시 ID, 실제 DB 저장 시에는 DB에서 할당
                content=question_content,
                expected_answers=expected_answers, # 예상 답변 추가
                created_at="2025-07-11T00:00:00.000000" # 임시 시간
            )
        else:
            print("Dify 워크플로우에서 유효한 응답을 받지 못했습니다.")
            return question_schema.Question(
                id=0,
                content="오늘 하루는 어떠셨나요?",
                expected_answers=[],
                created_at="2025-07-11T00:00:00.000000"
            )
    except json.JSONDecodeError as e:
        print(f"Dify 워크플로우 응답 JSON 디코딩 오류 발생: {e}")
        return question_schema.Question(
            id=0,
            content="오늘 하루는 어떠셨나요?",
            expected_answers=[],
            created_at="2025-07-11T00:00:00.000000"
        )
    except Exception as e:
        print(f"질문 생성 중 알 수 없는 오류 발생: {e}")
        return question_schema.Question(
            id=0,
            content="오늘 하루는 어떠셨나요?",
            expected_answers=[],
            created_at="2025-07-11T00:00:00.000000"
        )

VOICE_ANALYSIS_SERVICE_URL = Config.VOICE_ANALYSIS_SERVICE_URL # 음성 분석 서비스 서비스 URL

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
