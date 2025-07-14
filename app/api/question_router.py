import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas import question_schema
from app.models import question as question_model
from app.utils.db import get_db
from app.core.llm_service import get_recommended_question # 추가
from app.config.config import Config

router = APIRouter(
    prefix="/questions",
    tags=["Questions"]
)

USER_SERVICE_URL = Config.USER_SERVICE_URL # user-service의 기본 URL

@router.get("/daily-questions", response_model=question_schema.Question)
async def get_daily_question(user_id: int, db: Session = Depends(get_db)):
    """
    LLM을 연동하여 사용자에게 개인화된 '오늘의 질문'을 추천합니다.
    """
    recommended_question = await get_recommended_question(user_id)
    if not recommended_question:
        raise HTTPException(status_code=404, detail="No recommended question available")
    return recommended_question

@router.post("/", response_model=question_schema.Question)
def create_question(question: question_schema.QuestionCreate, db: Session = Depends(get_db)):
    db_question = question_model.Question(content=question.content)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

@router.get("/", response_model=List[question_schema.Question])
def read_questions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    questions = db.query(question_model.Question).offset(skip).limit(limit).all()
    return questions

@router.get("/{question_id}", response_model=question_schema.Question)
def read_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(question_model.Question).filter(question_model.Question.id == question_id).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.put("/{question_id}", response_model=question_schema.Question)
def update_question(question_id: int, question: question_schema.QuestionCreate, db: Session = Depends(get_db)):
    db_question = db.query(question_model.Question).filter(question_model.Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    db_question.content = question.content
    db.commit()
    db.refresh(db_question)
    return db_question

@router.delete("/{question_id}", response_model=question_schema.Question)
def delete_question(question_id: int, db: Session = Depends(get_db)):
    db_question = db.query(question_model.Question).filter(question_model.Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(db_question)
    db.commit()
    return db_question

@router.post("/answers", response_model=question_schema.Answer)
async def create_answer(answer: question_schema.AnswerCreate, db: Session = Depends(get_db)):
    # 1. user-service를 호출하여 user_id 유효성 검증
    async with httpx.AsyncClient() as client:
        try:
            user_response = await client.get(f"{USER_SERVICE_URL}/users/{answer.user_id}")
            user_response.raise_for_status()  # 2xx 외의 응답은 예외 발생
            # user_data = user_response.json() # 필요하다면 사용자 정보를 활용할 수 있습니다.
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {answer.user_id} not found")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"User service error: {e}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to user service: {e}")

    # 2. question_id 유효성 검증 (daily-question-service 내에서)
    question = db.query(question_model.Question).filter(question_model.Question.id == answer.question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with ID {answer.question_id} not found")

    # 3. 답변 저장
    db_answer = question_model.Answer(
        question_id=answer.question_id,
        user_id=answer.user_id,
        audio_file_url=answer.audio_file_url,
        text_content=answer.text_content
    )
    db.add(db_answer)
    db.commit()
    db.refresh(db_answer)
    return db_answer
