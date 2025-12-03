#!/usr/bin/env python3
"""
Celery worker for background ML tasks
"""

from services.ml_training_service import celery_app

if __name__ == '__main__':
    celery_app.start()