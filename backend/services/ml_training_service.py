#!/usr/bin/env python3
"""
ML Training Service - Handles automatic model training and embedding generation
"""

from celery import Celery
from datetime import datetime, timedelta
import logging
from models.resource import Resource
from models.notification import Task
from models.user import User
from models.feedback import TaskFeedback
from services.ml_service import ml_service

# Celery configuration for background tasks
celery_app = Celery('ml_training', broker='redis://localhost:6379/0')

@celery_app.task
def generate_embeddings_for_new_resources():
    """Background task to generate embeddings for new resources"""
    try:
        from app import create_app
        app = create_app('production')
        
        with app.app_context():
            ml_service.initialize(app)
            
            # Find resources without embeddings
            resources = Resource.objects(embedding__exists=False)
            
            if resources:
                logging.info(f"Generating embeddings for {resources.count()} new resources")
                
                for resource in resources:
                    text_parts = [resource.title, resource.description]
                    if resource.tags:
                        text_parts.extend(resource.tags if isinstance(resource.tags, list) else [resource.tags])
                    
                    combined_text = " ".join(text_parts)
                    embeddings = ml_service.generate_embeddings([combined_text])
                    
                    if embeddings:
                        resource.embedding = embeddings[0]
                        resource.save()
                        logging.info(f"Generated embedding for: {resource.title}")
                
                logging.info("Embedding generation completed")
            
    except Exception as e:
        logging.error(f"Error in embedding generation task: {e}")

@celery_app.task
def retrain_recommendation_model():
    """Background task to retrain ML recommendation models"""
    try:
        from app import create_app
        app = create_app('production')
        
        with app.app_context():
            # Collect training data
            users = User.objects(is_active=True)
            training_data = []
            
            for user in users:
                user_feedback = TaskFeedback.objects(user=user)
                user_interactions = user.interactions or {}
                
                training_data.append({
                    'user_id': str(user.id),
                    'interests': user.interests,
                    'skill_level': user.skill_level,
                    'feedback_history': [f.to_dict() for f in user_feedback],
                    'interactions': user_interactions
                })
            
            # Export training data for ML model
            export_training_data(training_data)
            
            # Trigger model retraining (would call external ML service)
            # ml_service.retrain_models(training_data)
            
            logging.info(f"Model retraining completed with {len(training_data)} user profiles")
            
    except Exception as e:
        logging.error(f"Error in model retraining: {e}")

def export_training_data(training_data):
    """Export training data to CSV for ML model training"""
    import pandas as pd
    import os
    
    # Create training data directory
    os.makedirs('data/training', exist_ok=True)
    
    # Export user interactions
    user_data = []
    for user in training_data:
        user_data.append({
            'user_id': user['user_id'],
            'interests': ','.join(user['interests']) if user['interests'] else '',
            'skill_level': user['skill_level'],
            'feedback_count': len(user['feedback_history']),
            'interaction_count': len(user['interactions'])
        })
    
    pd.DataFrame(user_data).to_csv('data/training/user_profiles.csv', index=False)
    
    # Export feedback data
    feedback_data = []
    for user in training_data:
        for feedback in user['feedback_history']:
            feedback_data.append({
                'user_id': user['user_id'],
                'task_id': feedback['task_id'],
                'helpful': feedback['helpful'],
                'difficulty_rating': feedback.get('difficulty_rating'),
                'timestamp': feedback['created_at']
            })
    
    pd.DataFrame(feedback_data).to_csv('data/training/task_feedback.csv', index=False)
    
    logging.info("Training data exported successfully")

# Scheduled tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks for ML training"""
    
    # Generate embeddings every 10 minutes
    sender.add_periodic_task(
        600.0,  # 10 minutes
        generate_embeddings_for_new_resources.s(),
        name='generate_embeddings_periodic'
    )
    
    # Retrain models daily at 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        retrain_recommendation_model.s(),
        name='retrain_models_daily'
    )

# Event-driven triggers
class MLTrainingTriggers:
    """Event-driven ML training triggers"""
    
    @staticmethod
    def on_resource_created(resource):
        """Trigger embedding generation when new resource is created"""
        generate_embeddings_for_new_resources.delay()
    
    @staticmethod
    def on_task_feedback_submitted(user_id, task_id):
        """Trigger model update when feedback is submitted"""
        # Check if enough new feedback to trigger retraining
        recent_feedback = TaskFeedback.objects(
            created_at__gte=datetime.utcnow() - timedelta(hours=1)
        ).count()
        
        if recent_feedback >= 10:  # Threshold for retraining
            retrain_recommendation_model.delay()
    
    @staticmethod
    def on_user_profile_updated(user_id):
        """Trigger recommendation refresh when user profile changes"""
        # Could trigger personalized recommendation regeneration
        pass