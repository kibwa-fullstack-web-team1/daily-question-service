from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import os
from fastapi import UploadFile # UploadFile 임포트
import tempfile

from app import models, schemas
from app.core.llm_service import get_recommended_question, convert_voice_to_text # convert_voice_to_text 임포트
from app.config.config import Config
from app.core.s3_service import S3Service # S3Service 임포트

USER_SERVICE_URL = Config.USER_SERVICE_URL

def create_question(db: Session, question: schemas.QuestionCreate):
    db_question = models.Question(content=question.content)
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
        # LLM에서 받은 질문을 DB에 저장
        db_question = create_question(db=db, question=schemas.QuestionCreate(content=recommended_question.content))
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
        text_content=answer.text_content
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
    if not s3_service.upload_file(file_content, object_name):
        return None, "오디오 파일을 S3에 업로드하지 못했습니다."

    audio_file_url = s3_service.get_file_url(object_name)
    if not audio_file_url:
        return None, "S3 파일 URL을 가져오지 못했습니다."

    # S3에서 오디오 파일 다운로드 및 STT 변환
    text_content = None
    try:
        # 임시 파일에 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name

        text_content = await convert_voice_to_text(tmp_file_path)
    except Exception as e:
        print(f"STT 변환 중 오류 발생: {e}")
        # STT 변환 실패 시에도 S3 URL은 저장
    finally:
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path) # 임시 파일 삭제

    answer_create = schemas.AnswerCreate(
        question_id=question_id,
        user_id=user_id,
        audio_file_url=audio_file_url,
        text_content=text_content # STT 변환 결과 저장
    )
    db_answer, error_message = await create_answer(db=db, answer=answer_create)
    if error_message:
        return None, error_message

    # 음성 분석 서비스로 파일 전송 (KT1-36)
    await send_voice_to_analysis_service(audio_file_url, user_id)

    return db_answer, None

async def send_voice_to_analysis_service(audio_file_url: str, user_id: int):
    """
    음성 파일을 외부 분석 서비스로 전송합니다.
    """
    ANALYSIS_SERVICE_URL = "http://analyze-alarm-service:8002/analyze-voice" # analyze-alarm-service의 실제 엔드포인트로 변경 필요
    
    payload = {
        "audio_file_url": audio_file_url,
        "user_id": user_id
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(ANALYSIS_SERVICE_URL, json=payload)
            response.raise_for_status() # 2xx 외의 응답은 예외 발생
            print(f"음성 파일 분석 서비스 전송 성공: {response.json()}")
        except httpx.RequestError as e:
            print(f"음성 파일 분석 서비스 연결 오류: {e}")
        except httpx.HTTPStatusError as e:
            print(f"음성 파일 분석 서비스 응답 오류: {e.response.status_code} - {e.response.text}")