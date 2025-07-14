import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas import question_schema
from app.utils.db import get_db
from app.config.config import Config
from app.helper import question_helper

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

@router.post("/answers", response_model=question_schema.Answer)
async def create_answer(answer: question_schema.AnswerCreate, db: Session = Depends(get_db)):
    db_answer, error_message = await question_helper.create_answer(db=db, answer=answer)
    if error_message:
        raise HTTPException(status_code=404, detail=error_message)
    return db_answer