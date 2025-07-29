from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date # date 타입 임포트

# Question 스키마
class QuestionBase(BaseModel):
    content: str
    expected_answers: Optional[List[str]] = None
    user_id: Optional[int] = None # user_id 추가
    daily_date: Optional[date] = None # daily_date 추가

class QuestionCreate(QuestionBase):
    pass

class Question(QuestionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Answer 스키마
class AnswerBase(BaseModel):
    audio_file_url: str
    text_content: Optional[str] = None

class AnswerCreate(AnswerBase):
    question_id: int
    user_id: int
    cognitive_score: Optional[float] = None
    analysis_details: Optional[dict] = None
    semantic_score: Optional[float] = None

class Answer(AnswerBase):
    id: int
    question_id: int
    user_id: int
    cognitive_score: Optional[float] = None
    analysis_details: Optional[dict] = None
    semantic_score: Optional[float] = None
    created_at: datetime
    question_content: Optional[str] = None # 추가

    model_config = ConfigDict(from_attributes=True)

# 답변 조회 시, 관련된 질문 정보까지 포함하는 상세 스키마
class AnswerWithQuestion(Answer):
    question: Question
