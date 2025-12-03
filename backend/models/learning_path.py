from mongoengine import Document, StringField, ListField, IntField, BooleanField, DateTimeField, ReferenceField
from datetime import datetime
from .user import User
from .resource import Resource

class LearningPathStep(Document):
    user = ReferenceField(User, required=True)
    resource = ReferenceField(Resource, required=False)
    
    # Step information
    step_id = StringField(required=True)
    title = StringField(required=True)
    description = StringField()
    order = IntField(required=True)
    
    # Dependencies
    dependencies = ListField(StringField())  # List of step_ids that must be completed first
    
    # Progress tracking
    completed = BooleanField(default=False)
    started_at = DateTimeField()
    completed_at = DateTimeField()
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'learning_path_steps',
        'indexes': [
            ('user', 'order'),
            ('user', 'completed'),
            'step_id'
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'step_id': self.step_id,
            'title': self.title,
            'description': self.description,
            'resourceId': str(self.resource.id) if self.resource else None,
            'order': self.order,
            'dependencies': self.dependencies,
            'completed': self.completed,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.resource.duration if self.resource else None,
            'difficulty': self.resource.difficulty if self.resource else None
        }
    
    def save(self, *args, **kwargs):
        """Override save to update timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

class LearningPath(Document):
    user = ReferenceField(User, required=True, unique=True)
    
    # Path metadata
    title = StringField(default="My Learning Path")
    description = StringField()
    
    # Progress tracking
    total_steps = IntField(default=0)
    completed_steps = IntField(default=0)
    progress_percentage = IntField(default=0)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    last_accessed = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'learning_paths',
        'indexes': ['user']
    }
    
    def update_progress(self):
        """Calculate and update progress statistics"""
        steps = LearningPathStep.objects(user=self.user)
        self.total_steps = steps.count()
        self.completed_steps = steps.filter(completed=True).count()
        self.progress_percentage = int((self.completed_steps / self.total_steps * 100)) if self.total_steps > 0 else 0
        self.save()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'user_id': str(self.user.id),
            'title': self.title,
            'description': self.description,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'progress_percentage': self.progress_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }
    
    def save(self, *args, **kwargs):
        """Override save to update timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)