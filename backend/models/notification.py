from mongoengine import Document, StringField, BooleanField, DateTimeField, ReferenceField, DictField, IntField, ListField, FloatField
from datetime import datetime
from .user import User

class Notification(Document):
    user = ReferenceField(User, required=True)
    
    # Notification content
    title = StringField(required=True, max_length=200)
    message = StringField(required=True, max_length=1000)
    notification_type = StringField(
        required=True,
        choices=['reminder', 'success', 'warning', 'info', 'achievement']
    )
    
    # Status
    read = BooleanField(default=False)
    
    # Action data
    action_url = StringField()
    action_data = DictField()  # Additional data for the action
    
    # Priority and scheduling
    priority = StringField(choices=['low', 'medium', 'high'], default='medium')
    scheduled_for = DateTimeField()  # For future notifications
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    read_at = DateTimeField()
    
    meta = {
        'collection': 'notifications',
        'indexes': [
            ('user', '-created_at'),
            ('user', 'read'),
            'scheduled_for',
            'notification_type'
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'title': self.title,
            'message': self.message,
            'type': self.notification_type,
            'read': self.read,
            'action_url': self.action_url,
            'action_data': self.action_data,
            'priority': self.priority,
            'timestamp': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.read = True
        self.read_at = datetime.utcnow()
        self.save()

class Task(Document):
    # Task identification
    task_id = StringField(required=True, unique=True)
    title = StringField(required=True, max_length=200)
    description = StringField(required=True, max_length=1000)
    
    # Task content
    type = StringField(choices=['coding', 'reading', 'practice', 'quiz', 'project'], default='practice')
    difficulty = StringField(choices=['Easy', 'Medium', 'Hard'], default='Easy')
    estimated_time = StringField()  # e.g., "15 minutes"
    
    # Task steps and guidance
    steps = DictField()  # Structured task steps
    hints = DictField()  # Hints for the task
    solution = DictField()  # Solution or explanation
    
    # Learning resources
    video_url = StringField()  # Video tutorial URL
    web_url = StringField()  # Web resource URL
    
    # Categorization
    tags = StringField()
    category = StringField()
    skill_level = StringField(choices=['Beginner', 'Intermediate', 'Advanced'])
    
    # Engagement metrics
    completion_rate = IntField(default=0)  # Percentage of users who completed
    average_rating = IntField(default=0)
    total_attempts = IntField(default=0)
    
    # ML features
    embedding = ListField(FloatField())  # Vector embedding for semantic search
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    is_active = BooleanField(default=True)
    
    meta = {
        'collection': 'tasks',
        'indexes': [
            'task_id',
            'difficulty',
            'category',
            'skill_level',
            'is_active'
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'task_id': self.task_id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'difficulty': self.difficulty,
            'estimated_time': self.estimated_time,
            'steps': self.steps,
            'hints': self.hints,
            'tags': self.tags,
            'category': self.category,
            'skill_level': self.skill_level,
            'completion_rate': self.completion_rate,
            'average_rating': self.average_rating,
            'video_url': self.video_url,
            'web_url': self.web_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def save(self, *args, **kwargs):
        """Override save to update timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)