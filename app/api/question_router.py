from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from app.schemas import question_schema
from app.utils.db import get_db
from app.config.config import Config
from app.helper import question_helper
from app.core.s3_service import S3Service
from app.core import crud_service # crud_service 임포트 추가

router = APIRouter(
    prefix="/questions",
    tags=["Questions"]
)

@router.get("/daily-questions", response_model=question_schema.Question)
async def get_daily_question(user_id: int, db: Session = Depends(get_db)):
    recommended_question = await question_helper.get_daily_question(user_id, db)
    if not recommended_question:
        raise HTTPException(status_code=404, detail="No recommended question available")
    return recommended_question

@router.post("/", response_model=question_schema.Question)
def create_question(question: question_schema.QuestionCreate, db: Session = Depends(get_db)):
    return crud_service.create_question(db=db, question=question) # crud_service로 변경

@router.get("/", response_model=List[question_schema.Question])
def read_questions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_service.read_questions(db=db, skip=skip, limit=limit) # crud_service로 변경

@router.get("/answers", response_model=List[question_schema.Answer])
def get_answers_by_user(
    user_id: int,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    db: Session = Depends(get_db)
):
    answers = crud_service.get_answers_by_user(db=db, user_id=user_id, start_date=start_date, end_date=end_date) # crud_service로 변경
    return answers

@router.get("/{question_id}", response_model=question_schema.Question)
def read_question(question_id: int, db: Session = Depends(get_db)):
    question = crud_service.read_question(db=db, question_id=question_id) # crud_service로 변경
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.put("/{question_id}", response_model=question_schema.Question)
def update_question(question_id: int, question: question_schema.QuestionCreate, db: Session = Depends(get_db)):
    db_question = crud_service.update_question(db=db, question_id=question_id, question=question) # crud_service로 변경
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return db_question

@router.delete("/{question_id}", response_model=question_schema.Question)
def delete_question(question_id: int, db: Session = Depends(get_db)):
    db_question = crud_service.delete_question(db=db, question_id=question_id) # crud_service로 변경
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return db_question

@router.get("/answers/{answer_id}", response_model=question_schema.Answer)
def get_answer_by_id(answer_id: int, db: Session = Depends(get_db)):
    answer = crud_service.get_answer_by_id(db=db, answer_id=answer_id) # crud_service로 변경
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found")
    return answer

@router.delete("/answers/{answer_id}", response_model=question_schema.Answer)
def delete_answer(answer_id: int, db: Session = Depends(get_db)):
    db_answer = crud_service.delete_answer(db=db, answer_id=answer_id) # crud_service로 변경
    if db_answer is None:
        raise HTTPException(status_code=404, detail="Answer not found")
    return db_answer

@router.post("/voice-answers", response_model=question_schema.Answer)
async def upload_voice_answer(
    question_id: int = Form(...),
    user_id: int = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    db_answer, error_message = await question_helper.upload_and_save_voice_answer(
        db=db,
        question_id=question_id,
        user_id=user_id,
        audio_file=audio_file
    )
    if error_message:
        print(f"Error message from helper: {error_message}") # Debugging line
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)
    
    # db_answer가 None일 경우 404 반환
    if db_answer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer could not be created or found.")
        
    return db_answer