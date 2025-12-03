from mongoengine import Document, StringField, ListField, IntField, FloatField, DateTimeField, URLField
from datetime import datetime

class Resource(Document):
    title = StringField(required=True, max_length=200)
    description = StringField(required=True, max_length=1000)
    type = StringField(required=True, choices=['video', 'article', 'course', 'book', 'tutorial'])
    difficulty = StringField(required=True, choices=['Beginner', 'Intermediate', 'Advanced'])
    duration = StringField(required=True)  # e.g., "2 hours", "30 minutes"
    url = URLField()
    
    # Categorization
    tags = ListField(StringField(max_length=50))
    category = StringField(max_length=50)
    
    # Engagement metrics
    likes = IntField(default=0)
    views = IntField(default=0)
    rating = FloatField(default=0.0, min_value=0.0, max_value=5.0)
    rating_count = IntField(default=0)
    
    # Content metadata
    author = StringField(max_length=100)
    source = StringField(max_length=100)
    language = StringField(default='English')
    
    # ML features
    embedding = ListField(FloatField())  # For semantic search
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'resources',
        'indexes': [
            'type',
            'difficulty',
            'tags',
            'category',
            'rating',
            'created_at',
            ('tags', 'difficulty'),  # Compound index
            ('type', 'difficulty')   # Compound index
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'difficulty': self.difficulty,
            'duration': self.duration,
            'url': self.url,
            'tags': self.tags,
            'category': self.category,
            'likes': self.likes,
            'views': self.views,
            'rating': self.rating,
            'rating_count': self.rating_count,
            'author': self.author,
            'source': self.source,
            'language': self.language,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def save(self, *args, **kwargs):
        """Override save to update timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)