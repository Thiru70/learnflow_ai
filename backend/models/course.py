from mongoengine import Document, StringField, IntField, FloatField, ListField, DateTimeField, BooleanField
from datetime import datetime

class Course(Document):
    course_id = StringField(required=True, unique=True)
    title = StringField(required=True, max_length=200)
    description = StringField(required=True, max_length=1000)
    type = StringField(choices=['course', 'tutorial', 'bootcamp'], default='course')
    difficulty = StringField(choices=['Beginner', 'Intermediate', 'Advanced'], default='Beginner')
    duration = StringField()  # e.g., "10 hours"
    tags = StringField()
    category = StringField()
    author = StringField()
    rating = FloatField(default=0.0)
    likes = IntField(default=0)
    url = StringField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'courses'}
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'difficulty': self.difficulty,
            'duration': self.duration,
            'tags': self.tags.split(',') if self.tags else [],
            'category': self.category,
            'author': self.author,
            'rating': self.rating,
            'likes': self.likes,
            'url': self.url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CourseCompletion(Document):
    user = StringField(required=True)  # User ID
    course_id = StringField(required=True)
    status = StringField(choices=['not_started', 'in_progress', 'completed'], default='not_started')
    progress_percentage = IntField(default=0)  # 0-100
    started_at = DateTimeField()
    completed_at = DateTimeField()
    last_accessed = DateTimeField(default=datetime.utcnow)
    rating = IntField(min_value=1, max_value=5)  # User's rating after completion
    review = StringField(max_length=500)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'course_completions',
        'indexes': [
            ('user', 'course_id'),  # Compound index for efficient queries
            'user',
            'course_id'
        ]
    }
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user': self.user,
            'course_id': self.course_id,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'rating': self.rating,
            'review': self.review,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }