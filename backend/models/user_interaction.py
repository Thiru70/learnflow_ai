from mongoengine import Document, StringField, IntField, BooleanField, DateTimeField, ReferenceField
from datetime import datetime
from models.user import User
from models.resource import Resource

class UserInteraction(Document):
    user = ReferenceField(User, required=True)
    resource = ReferenceField(Resource, required=True)
    interaction_type = StringField(choices=['viewed', 'in-progress', 'completed', 'bookmarked', 'liked', 'rated'], required=True)
    rating = IntField(min_value=1, max_value=5)
    helpful = BooleanField()
    timestamp = DateTimeField(default=datetime.utcnow)
    completion_time_minutes = IntField()
    
    meta = {
        'collection': 'user_interactions',
        'indexes': [
            ('user', 'resource'),
            'timestamp',
            'interaction_type'
        ]
    }
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user.id),
            'resource_id': str(self.resource.id),
            'interaction_type': self.interaction_type,
            'rating': self.rating,
            'helpful': self.helpful,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'completion_time_minutes': self.completion_time_minutes
        }