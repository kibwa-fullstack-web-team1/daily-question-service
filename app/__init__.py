from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware
from app.utils.db import engine, Base
from app.api import question_router
from app.config.config import Config

# 모든 모델을 임포트하여 Base.metadata에 등록
from app.models.question import Question, Answer

def create_app():
    app = FastAPI()

    # Add CORS middleware
    origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.config = Config()

    Base.metadata.create_all(bind=engine)

    app.include_router(question_router.router) # 프리픽스 제거

    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Daily Question Service"}

    return app