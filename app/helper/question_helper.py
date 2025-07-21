from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import os
from fastapi import UploadFile # UploadFile 임포트
import tempfile

from app import models, schemas
from app.core.llm_service import get_recommended_question, convert_voice_to_text, analyze_voice_with_service, get_embedding
from app.config.config import Config
from app.core.s3_service import S3Service
from app.utils.functions import cosine_similarity

USER_SERVICE_URL = Config.USER_SERVICE_URL

def create_question(db: Session, question: schemas.QuestionCreate):
    db_question = models.Question(content=question.content, expected_answers=question.expected_answers)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

def read_questions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Question).offset(skip).limit(limit).all()

def read_question(db: Session, question_id: int):
    return db.query(models.Question).filter(models.Question.id == question_id).first()

def update_question(db: Session, question_id: int, question: schemas.QuestionCreate):
    db_question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if db_question:
        db_question.content = question.content
        db_question.expected_answers = question.expected_answers
        db.commit()
        db.refresh(db_question)
    return db_question

def delete_question(db: Session, question_id: int):
    db_question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if db_question:
        db.delete(db_question)
        db.commit()
    return db_question

async def get_daily_question(user_id: int, db: Session) -> Optional[schemas.Question]:
    recommended_question = await get_recommended_question(user_id)
    if recommended_question:
        # LLM에서 받은 질문과 예상 답변을 DB에 저장
        db_question = models.Question(
            content=recommended_question.content,
            expected_answers=recommended_question.expected_answers
        )
        db.add(db_question)
        db.commit()
        db.refresh(db_question)
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
    question = db.query(models.Question).filter(models.Question.id == answer.question_id).first()
    if not question:
        return None, f"Question with ID {answer.question_id} not found"

    # 3. 답변 저장
    db_answer = models.Answer(
        question_id=answer.question_id,
        user_id=answer.user_id,
        audio_file_url=answer.audio_file_url,
        text_content=answer.text_content,
        cognitive_score=answer.cognitive_score,
        analysis_details=answer.analysis_details,
        semantic_score=answer.semantic_score # semantic_score 추가
    )
    db.add(db_answer)
    db.commit()
    db.refresh(db_answer)
    return db_answer, None

def get_answers_by_user(db: Session, user_id: int) -> List[schemas.Answer]:
    return db.query(models.Answer).filter(models.Answer.user_id == user_id).all()

def get_answer_by_id(db: Session, answer_id: int) -> Optional[schemas.Answer]:
    return db.query(models.Answer).filter(models.Answer.id == answer_id).first()

def delete_answer(db: Session, answer_id: int):
    db_answer = db.query(models.Answer).filter(models.Answer.id == answer_id).first()
    if db_answer:
        db.delete(db_answer)
        db.commit()
    return db_answer

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
        question = db.query(models.Question).filter(models.Question.id == question_id).first()
        if question and question.expected_answers:
            user_answer_embedding = await get_embedding(text_content)
            if user_answer_embedding:
                max_similarity = 0.0
                for expected_ans in question.expected_answers:
                    expected_ans_embedding = await get_embedding(expected_ans)
                    if expected_ans_embedding:
                        similarity = cosine_similarity(user_answer_embedding, expected_ans_embedding)
                        if similarity > max_similarity:
                            max_similarity = similarity
                semantic_score = round((max_similarity + 1) / 2 * 100, 2) # -1~1 스케일을 0~100 스케일로 변환
                print(f"Semantic similarity score: {semantic_score}")

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
    return db_answer, None