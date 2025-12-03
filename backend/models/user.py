from mongoengine import Document, StringField, ListField, DateTimeField, BooleanField, DictField
from datetime import datetime
import bcrypt

class User(Document):
    email = StringField(required=True, unique=True, max_length=255)
    password_hash = StringField(required=True)
    name = StringField(required=True, max_length=100)
    
    # Profile information
    interests = ListField(StringField(max_length=50))
    skill_level = StringField(choices=['Beginner', 'Intermediate', 'Advanced'], default='Beginner')
    learning_goal = StringField(max_length=500)
    goal_timeline = StringField(choices=['1 month', '3 months', '6 months', '1 year'])
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    last_activity = DateTimeField()
    is_onboarded = BooleanField(default=False)
    is_active = BooleanField(default=True)
    
    # User interactions tracking
    interactions = DictField()  # {resource_id: {status, viewed_at, completed_at}}
    
    meta = {
        'collection': 'users',
        'indexes': ['email', 'created_at']
    }
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'email': self.email,
            'name': self.name,
            'interests': self.interests,
            'skill_level': self.skill_level,
            'learning_goal': self.learning_goal,
            'goal_timeline': self.goal_timeline,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_onboarded': self.is_onboarded,
            'interactions': self.interactions
        }
    
    def save(self, *args, **kwargs):
        """Override save to update timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)