from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import os
from fastapi import UploadFile # UploadFile 임포트
import tempfile
import datetime # datetime 모듈 임포트

from app import models, schemas
from app.core.llm_service import get_recommended_question, convert_voice_to_text, analyze_voice_with_service, get_embedding
from app.config.config import Config
from app.core.s3_service import S3Service
from app.core.kafka_producer_service import publish_score_update # publish_score_update 함수 임포트
from app.core import crud_service # crud_service 임포트
from app.utils.functions import cosine_similarity, sigmoid_mapping

USER_SERVICE_URL = Config.USER_SERVICE_URL

# 기존 create_question, read_questions, read_question, update_question, delete_question 함수는 crud_service로 이동했으므로 제거
# 기존 get_answers_by_user, get_answer_by_id, delete_answer 함수는 crud_service로 이동했으므로 제거

async def get_daily_question(user_id: int, db: Session) -> Optional[schemas.Question]:
    recommended_question = await get_recommended_question(user_id)
    if recommended_question:
        # LLM에서 받은 질문과 예상 답변을 DB에 저장
        db_question = crud_service.create_question(db=db, question=recommended_question) # crud_service.create_question 사용
        # LLM에서 받은 질문의 ID를 DB에 저장된 질문의 ID로 업데이트
        recommended_question.id = db_question.id
        recommended_question.created_at = db_question.created_at
    return recommended_question

async def create_answer(db: Session, answer: schemas.AnswerCreate):
    # 1. user-service를 호출하여 user_id 유효성 검증
    async with httpx.AsyncClient() as client:
        try:
            user_response = await client.get(f"{USER_SERVICE_URL}/users/{answer.user_id}")
            user_response.raise_for_status()  # 2xx 외의 응답은 예외 발생
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None, f"User with ID {answer.user_id} not found"
            return None, f"User service error: {e}"
        except httpx.RequestError as e:
            return None, f"Could not connect to user service: {e}"

    # 2. question_id 유효성 검증 (daily-question-service 내에서)
    question = crud_service.read_question(db=db, question_id=answer.question_id) # crud_service.read_question 사용
    if not question:
        return None, f"Question with ID {answer.question_id} not found"

    # 3. 답변 저장 (crud_service의 create_answer_db 사용)
    db_answer = crud_service.create_answer_db(db=db, answer=answer)
    return db_answer, None

async def upload_and_save_voice_answer(
    db: Session,
    question_id: int,
    user_id: int,
    audio_file: UploadFile
):
    s3_service = S3Service()

    file_content = await audio_file.read()
    file_extension = os.path.splitext(audio_file.filename)[1]
    object_name = f"voice_answers/{user_id}_{question_id}_{os.urandom(4).hex()}{file_extension}"

    # S3에 오디오 파일 업로드
    print(f"Attempting S3 upload for object: {object_name}")
    if not s3_service.upload_file(file_content, object_name):
        print("S3 upload failed.")
        return None, "오디오 파일을 S3에 업로드하지 못했습니다."
    print("S3 upload successful.")

    audio_file_url = s3_service.get_file_url(object_name)
    if not audio_file_url:
        print("Failed to get S3 file URL.")
        return None, "S3 파일 URL을 가져오지 못했습니다."
    print(f"S3 file URL: {audio_file_url}")

    # S3에서 오디오 파일 다운로드 및 STT 변환
    text_content = None
    tmp_file_path = None
    try:
        # 임시 파일에 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        print(f"Temporary audio file saved to: {tmp_file_path}")

        text_content = await convert_voice_to_text(tmp_file_path)
        print(f"STT conversion successful. Text: {text_content}")
    except Exception as e:
        print(f"STT 변환 중 오류 발생: {e}")
        # STT 변환 실패 시에도 S3 URL은 저장
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path) # 임시 파일 삭제
            print(f"Temporary file removed: {tmp_file_path}")

    # 음성 분석 서비스 호출
    cognitive_score = None
    analysis_details = None
    try:
        print(f"Calling voice analysis service for URL: {audio_file_url}")
        analysis_result = await analyze_voice_with_service(audio_file_url)
        cognitive_score = analysis_result.get("cognitive_score")
        analysis_details = analysis_result.get("details")
        print(f"Voice analysis successful. Score: {cognitive_score}, Details: {analysis_details}")
    except Exception as e:
        print(f"음성 분석 서비스 호출 중 오류 발생: {e}")
        # 분석 실패 시에도 답변은 저장

    # 의미 유사도 점수 계산
    semantic_score = None
    if text_content and question_id:
        question = crud_service.read_question(db=db, question_id=question_id) # crud_service.read_question 사용
        if question and question.content:
            question_embedding = await get_embedding(question.content, dimensions=1024)
            user_answer_embedding = await get_embedding(text_content, dimensions=1024)

            if question_embedding and user_answer_embedding:
                relevance_similarity = cosine_similarity(user_answer_embedding, question_embedding)
                print(f"Relevance similarity between user answer and question: {relevance_similarity}")

                # 관련성 게이트: 유사도 임계값 이하일 경우 semantic_score를 0으로 설정
                if relevance_similarity < 0.2: # 임계값 설정 (조정 가능)
                    semantic_score = 0.0
                    print(f"Relevance gate activated: semantic_score set to {semantic_score}")
                else:
                    similarities = []
                    for expected_ans in question.expected_answers:
                        expected_ans_embedding = await get_embedding(expected_ans, dimensions=1024)
                        if expected_ans_embedding:
                            similarity = cosine_similarity(user_answer_embedding, expected_ans_embedding)
                            similarities.append(similarity)
                    
                    if similarities:
                        # 유사도 점수를 내림차순으로 정렬하고 상위 3개의 평균을 계산
                        similarities.sort(reverse=True)
                        top_n_similarities = similarities[:3] # 상위 3개 선택
                        average_similarity = sum(top_n_similarities) / len(top_n_similarities)
                        semantic_score = round((average_similarity + 1) / 2 * 100, 2) # -1~1 스케일을 0~100 스케일로 변환
                        
                        # 시그모이드 매핑 적용
                        mapped_semantic_score = sigmoid_mapping(semantic_score, k=0.1, x0=50.0)
                        semantic_score = round(mapped_semantic_score, 2)

                        print(f"Semantic similarity scores: {similarities}")
                        print(f"Top 3 average semantic similarity score (before sigmoid): {round((average_similarity + 1) / 2 * 100, 2)}")
                        print(f"Mapped semantic score (after sigmoid): {semantic_score}")

    answer_create = schemas.AnswerCreate(
        question_id=question_id,
        user_id=user_id,
        audio_file_url=audio_file_url,
        text_content=text_content, # STT 변환 결과 저장
        cognitive_score=cognitive_score, # 인지 점수 저장
        analysis_details=analysis_details, # 분석 상세 정보 저장
        semantic_score=semantic_score # 의미 유사도 점수 저장
    )
    print(f"Attempting to create answer with data: {answer_create.model_dump_json()}")
    db_answer, error_message = await create_answer(db=db, answer=answer_create)
    print(f"create_answer returned: db_answer={db_answer}, error_message={error_message}")
    if error_message:
        return None, error_message

    # Kafka 메시지 발행
    if cognitive_score is not None and semantic_score is not None:
        current_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        publish_score_update(
            user_id=str(user_id),
            answer_id=str(db_answer.id) if db_answer else "", # db_answer가 None일 경우 빈 문자열
            cognitive_score=cognitive_score,
            semantic_score=semantic_score,
            timestamp=current_timestamp
        )

    return db_answer, None