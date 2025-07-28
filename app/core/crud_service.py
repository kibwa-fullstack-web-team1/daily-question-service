from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
from sqlalchemy import func

from app import models, schemas

# Question CRUD operations
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

def delete_question(db: Session, question_id: int): # Corrected parameter name and logic
    db_question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if db_question:
        db.delete(db_question)
        db.commit()
    return db_question

# Answer CRUD operations
def create_answer_db(db: Session, answer: schemas.AnswerCreate): # Renamed to avoid conflict and clarify pure DB operation
    db_answer = models.Answer(
        question_id=answer.question_id,
        user_id=answer.user_id,
        audio_file_url=answer.audio_file_url,
        text_content=answer.text_content,
        cognitive_score=answer.cognitive_score,
        analysis_details=answer.analysis_details,
        semantic_score=answer.semantic_score
    )
    db.add(db_answer)
    db.commit()
    db.refresh(db_answer)
    return db_answer

def get_answers_by_user(
    db: Session,
    user_id: int,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None
) -> List[schemas.Answer]:
    # 각 question_id별로 최신 답변을 가져오기 위해 서브쿼리 사용
    subquery = db.query(
        models.Answer.question_id,
        func.max(models.Answer.created_at).label("max_created_at")
    ).filter(models.Answer.user_id == user_id)
    if start_date:
        subquery = subquery.filter(models.Answer.created_at >= start_date)
    if end_date:
        subquery = subquery.filter(models.Answer.created_at <= end_date)
    subquery = subquery.group_by(models.Answer.question_id).subquery()

    # 서브쿼리와 Answer, Question 테이블을 조인하여 최종 결과 가져오기
    query = db.query(models.Answer, models.Question.content.label("question_content")) \
        .join(subquery, 
              (models.Answer.question_id == subquery.c.question_id) & 
              (models.Answer.created_at == subquery.c.max_created_at)) \
        .join(models.Question, models.Answer.question_id == models.Question.id)
    
    # 결과를 schemas.Answer 형식에 맞게 변환
    answers_with_question_content = []
    for answer, question_content in query.all():
        answer_dict = answer.__dict__.copy() # 딕셔너리 복사본 사용
        answer_dict["question_content"] = question_content
        answers_with_question_content.append(schemas.Answer(**answer_dict))

    return answers_with_question_content

def get_answer_by_id(db: Session, answer_id: int) -> Optional[schemas.Answer]:
    return db.query(models.Answer).filter(models.Answer.id == answer_id).first()

def delete_answer(db: Session, answer_id: int):
    db_answer = db.query(models.Answer).filter(models.Answer.id == answer_id).first()
    if db_answer:
        db.delete(db_answer)
        db.commit()
    return db_answer