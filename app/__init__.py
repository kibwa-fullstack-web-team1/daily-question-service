from fastapi import FastAPI
from app.utils.db import engine, Base
from app.api import question_router
from app.config.config import Config

def create_app():
    app = FastAPI()

    app.config = Config()

    Base.metadata.create_all(bind=engine)

    app.include_router(question_router.router)

    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Daily Question Service"}

    return app