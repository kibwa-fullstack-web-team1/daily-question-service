from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# Question 스키마
class QuestionBase(BaseModel):
    content: str

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

class Answer(AnswerBase):
    id: int
    question_id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# 답변 조회 시, 관련된 질문 정보까지 포함하는 상세 스키마
class AnswerWithQuestion(Answer):
    question: Question
