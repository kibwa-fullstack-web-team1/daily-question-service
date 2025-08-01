from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Text, Float, JSON, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from app.utils.db import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    expected_answers = Column(JSON, nullable=True) # LLM이 생성한 예상 답변 목록
    user_id = Column(Integer, nullable=True, index=True) # 사용자 ID 추가
    daily_date = Column(Date, nullable=True) # 오늘의 질문 날짜 (YYYY-MM-DD)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint('user_id', 'daily_date', name='_user_daily_question_uc'),)

    answers = relationship("Answer", back_populates="question")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    
    # Question과의 관계 (같은 서비스 내이므로 FK 사용)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    
    # User와의 관계 (다른 서비스이므로 FK 없이 ID만 저장)
    user_id = Column(Integer, index=True, nullable=False)
    
    audio_file_url = Column(String, nullable=False) # S3에 저장된 음성 파일의 URL
    text_content = Column(Text, nullable=True) # STT 변환 결과
    cognitive_score = Column(Float, nullable=True) # 음성 분석 결과 - 인지 점수
    analysis_details = Column(JSON, nullable=True) # 음성 분석 결과 - 상세 정보 (JSON)
    semantic_score = Column(Float, nullable=True) # 의미 유사도 점수

    created_at = Column(DateTime, server_default=func.now())

    question = relationship("Question", back_populates="answers")
