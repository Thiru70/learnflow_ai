from mongoengine import Document, StringField, IntField, BooleanField, DateTimeField, ReferenceField, FloatField
from datetime import datetime
from .user import User
from .resource import Resource

class Feedback(Document):
    user = ReferenceField(User, required=True)
    resource = ReferenceField(Resource, required=True)
    
    # Feedback data
    rating = IntField(min_value=1, max_value=5)
    helpful = BooleanField()
    comment = StringField(max_length=1000)
    
    # Feedback type
    feedback_type = StringField(choices=['rating', 'like', 'bookmark', 'comment'], default='rating')
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'feedback',
        'indexes': [
            ('user', 'resource'),
            'resource',
            'created_at',
            'feedback_type'
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'user_id': str(self.user.id),
            'resource_id': str(self.resource.id),
            'rating': self.rating,
            'helpful': self.helpful,
            'comment': self.comment,
            'feedback_type': self.feedback_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def save(self, *args, **kwargs):
        """Override save to update timestamp and resource metrics"""
        self.updated_at = datetime.utcnow()
        result = super().save(*args, **kwargs)
        
        # Update resource metrics
        if self.resource:
            self._update_resource_metrics()
        
        return result
    
    def _update_resource_metrics(self):
        """Update resource rating and engagement metrics"""
        # Calculate new average rating
        all_ratings = Feedback.objects(resource=self.resource, rating__exists=True)
        if all_ratings:
            total_rating = sum([f.rating for f in all_ratings])
            avg_rating = total_rating / len(all_ratings)
            
            self.resource.rating = round(avg_rating, 2)
            self.resource.rating_count = len(all_ratings)
            
        # Update likes count
        likes_count = Feedback.objects(resource=self.resource, helpful=True).count()
        self.resource.likes = likes_count
        
        self.resource.save()

class TaskFeedback(Document):
    user = ReferenceField(User, required=True)
    task_id = StringField(required=True)
    
    # Feedback data
    helpful = BooleanField(required=True)
    comment = StringField(max_length=500)
    difficulty_rating = IntField(min_value=1, max_value=5)
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'task_feedback',
        'indexes': [
            ('user', 'task_id'),
            'task_id',
            'created_at'
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'user_id': str(self.user.id),
            'task_id': self.task_id,
            'helpful': self.helpful,
            'comment': self.comment,
            'difficulty_rating': self.difficulty_rating,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }