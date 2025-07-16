import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional

from app.schemas import question_schema
from app.utils.db import get_db
from app.config.config import Config
from app.helper import question_helper
from app.core.s3_service import S3Service

router = APIRouter(
    prefix="/questions",
    tags=["Questions"]
)

@router.get("/daily-questions", response_model=question_schema.Question)
async def get_daily_question(user_id: int, db: Session = Depends(get_db)):
    recommended_question = await question_helper.get_daily_question(user_id)
    if not recommended_question:
        raise HTTPException(status_code=404, detail="No recommended question available")
    return recommended_question

@router.post("/", response_model=question_schema.Question)
def create_question(question: question_schema.QuestionCreate, db: Session = Depends(get_db)):
    return question_helper.create_question(db=db, question=question)

@router.get("/", response_model=List[question_schema.Question])
def read_questions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return question_helper.read_questions(db=db, skip=skip, limit=limit)

@router.get("/answers", response_model=List[question_schema.Answer])
def get_answers_by_user(user_id: int, db: Session = Depends(get_db)):
    answers = question_helper.get_answers_by_user(db=db, user_id=user_id)
    return answers

@router.get("/{question_id}", response_model=question_schema.Question)
def read_question(question_id: int, db: Session = Depends(get_db)):
    question = question_helper.read_question(db=db, question_id=question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.put("/{question_id}", response_model=question_schema.Question)
def update_question(question_id: int, question: question_schema.QuestionCreate, db: Session = Depends(get_db)):
    db_question = question_helper.update_question(db=db, question_id=question_id, question=question)
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return db_question

@router.delete("/{question_id}", response_model=question_schema.Question)
def delete_question(question_id: int, db: Session = Depends(get_db)):
    db_question = question_helper.delete_question(db=db, question_id=question_id)
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return db_question

@router.get("/answers/{answer_id}", response_model=question_schema.Answer)
def get_answer_by_id(answer_id: int, db: Session = Depends(get_db)):
    answer = question_helper.get_answer_by_id(db=db, answer_id=answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found")
    return answer

@router.delete("/answers/{answer_id}", response_model=question_schema.Answer)
def delete_answer(answer_id: int, db: Session = Depends(get_db)):
    db_answer = question_helper.delete_answer(db=db, answer_id=answer_id)
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)
    return db_answer