from sqlalchemy.orm import Session
from typing import List, Optional

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