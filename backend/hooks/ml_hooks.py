"""
ML Hooks - Event-driven triggers for ML training and updates
"""

from services.ml_training_service import MLTrainingTriggers
import logging

class MLHooks:
    """Database hooks for ML training triggers"""
    
    @staticmethod
    def setup_hooks():
        """Setup all ML-related database hooks"""
        
        # Resource creation hook
        from models.resource import Resource
        Resource.register_post_save_hook(MLHooks.on_resource_saved)
        
        # Task feedback hook
        from models.feedback import TaskFeedback
        TaskFeedback.register_post_save_hook(MLHooks.on_feedback_saved)
        
        # User profile update hook
        from models.user import User
        User.register_post_save_hook(MLHooks.on_user_saved)
        
        logging.info("ML hooks registered successfully")
    
    @staticmethod
    def on_resource_saved(sender, document, created, **kwargs):
        """Triggered when a resource is created or updated"""
        if created:
            logging.info(f"New resource created: {document.title}")
            MLTrainingTriggers.on_resource_created(document)
    
    @staticmethod
    def on_feedback_saved(sender, document, created, **kwargs):
        """Triggered when task feedback is submitted"""
        if created:
            logging.info(f"New feedback submitted for task: {document.task_id}")
            MLTrainingTriggers.on_task_feedback_submitted(
                str(document.user.id), 
                document.task_id
            )
    
    @staticmethod
    def on_user_saved(sender, document, created, **kwargs):
        """Triggered when user profile is updated"""
        if not created:  # Only for updates, not new users
            logging.info(f"User profile updated: {document.email}")
            MLTrainingTriggers.on_user_profile_updated(str(document.id))