import os

class Config:
    PHASE = 'default'
    DATABASE_URL = os.environ.get('DATABASE_URL')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://localhost:8000')
    VOICE_ANALYSIS_SERVICE_URL = os.environ.get('VOICE_ANALYSIS_SERVICE_URL', 'http://localhost:8003')
    KAFKA_BROKER_URL = os.environ.get('KAFKA_BROKER_URL', 'kafka:9092')
    
    # AWS S3 관련 환경 변수 추가
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION')
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')

class ProductionConfig(Config):
    PHASE = 'production'

class DevelopmentConfig(Config):
    PHASE = 'development'

config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig,
)