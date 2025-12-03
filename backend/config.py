import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    MONGODB_URI = os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/learning_system'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # ML Service Configuration
    ML_SERVICE_URL = os.environ.get('ML_SERVICE_URL') or 'http://localhost:5001'
    SENTENCE_TRANSFORMER_MODEL = 'all-MiniLM-L6-v2'
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')

class DevelopmentConfig(Config):
    DEBUG = True
    MONGODB_URI = 'mongodb://localhost:27017/learning_system_dev'

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    MONGODB_URI = 'mongodb://localhost:27017/learning_system_test'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}