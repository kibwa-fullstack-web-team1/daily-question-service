import os

class Config:
    PHASE = 'default'
    DATABASE_URL = os.environ.get('DATABASE_URL')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://localhost:8000')

class ProductionConfig(Config):
    PHASE = 'production'

class DevelopmentConfig(Config):
    PHASE = 'development'

config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig,
)
