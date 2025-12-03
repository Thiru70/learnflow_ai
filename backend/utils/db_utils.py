from mongoengine import connect, disconnect
from flask import current_app
import logging

def init_db(app):
    """Initialize MongoDB connection"""
    try:
        connect(host=app.config['MONGODB_URI'])
        logging.info("Connected to MongoDB successfully")
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {e}")
        raise

def close_db():
    """Close MongoDB connection"""
    try:
        disconnect()
        logging.info("Disconnected from MongoDB")
    except Exception as e:
        logging.error(f"Error disconnecting from MongoDB: {e}")

def create_indexes():
    """Create database indexes for better performance"""
    from models.user import User
    from models.resource import Resource
    from models.learning_path import LearningPath, LearningPathStep
    from models.feedback import Feedback, TaskFeedback
    from models.notification import Notification, Task
    
    try:
        # Ensure indexes are created
        User.ensure_indexes()
        Resource.ensure_indexes()
        LearningPath.ensure_indexes()
        LearningPathStep.ensure_indexes()
        Feedback.ensure_indexes()
        TaskFeedback.ensure_indexes()
        Notification.ensure_indexes()
        Task.ensure_indexes()
        
        logging.info("Database indexes created successfully")
    except Exception as e:
        logging.error(f"Error creating indexes: {e}")

def seed_sample_data():
    """Seed database with sample data for development"""
    from models.resource import Resource
    from models.notification import Task
    
    # Sample resources
    sample_resources = [
        {
            'title': 'Introduction to Python',
            'description': 'Learn Python basics and syntax',
            'type': 'course',
            'difficulty': 'Beginner',
            'duration': '8 hours',
            'url': 'https://example.com/python-intro',
            'tags': ['python', 'programming', 'basics'],
            'category': 'Programming',
            'author': 'Python Institute',
            'source': 'Online Course'
        },
        {
            'title': 'Machine Learning Fundamentals',
            'description': 'Understanding ML concepts and algorithms',
            'type': 'course',
            'difficulty': 'Intermediate',
            'duration': '12 hours',
            'url': 'https://example.com/ml-fundamentals',
            'tags': ['machine-learning', 'ai', 'algorithms'],
            'category': 'Machine Learning',
            'author': 'ML Academy',
            'source': 'Online Course'
        },
        {
            'title': 'Data Structures and Algorithms',
            'description': 'Master essential data structures and algorithms',
            'type': 'course',
            'difficulty': 'Intermediate',
            'duration': '15 hours',
            'url': 'https://example.com/dsa',
            'tags': ['algorithms', 'data-structures', 'programming'],
            'category': 'Computer Science',
            'author': 'CS Academy',
            'source': 'Online Course'
        }
    ]
    
    # Sample tasks - DISABLED to use CSV data
    sample_tasks = []
    
    try:
        # Create resources if they don't exist
        for resource_data in sample_resources:
            if not Resource.objects(title=resource_data['title']).first():
                resource = Resource(**resource_data)
                resource.save()
        
        # Create tasks if they don't exist
        for task_data in sample_tasks:
            if not Task.objects(task_id=task_data['task_id']).first():
                task = Task(**task_data)
                task.save()
        
        logging.info("Sample data seeded successfully")
    except Exception as e:
        logging.error(f"Error seeding sample data: {e}")