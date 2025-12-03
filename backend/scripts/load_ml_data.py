#!/usr/bin/env python3
"""
Load and prepare data for ML service
- Generate embeddings for resources
- Load sample learning content
- Initialize ML models
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.resource import Resource
from models.notification import Task
from services.ml_service import ml_service
import logging

def load_sample_resources():
    """Load comprehensive sample resources with embeddings"""
    
    sample_resources = [
        {
            'title': 'Python Fundamentals for Beginners',
            'description': 'Learn Python programming from scratch. Cover variables, data types, loops, functions, and basic object-oriented programming concepts.',
            'type': 'course',
            'difficulty': 'Beginner',
            'duration': '8 hours',
            'url': 'https://example.com/python-fundamentals',
            'tags': ['python', 'programming', 'basics', 'variables', 'functions'],
            'category': 'Programming',
            'author': 'Python Institute',
            'source': 'Online Course',
            'rating': 4.5,
            'likes': 150
        },
        {
            'title': 'Machine Learning with Python',
            'description': 'Introduction to machine learning using Python. Learn scikit-learn, pandas, numpy, and build your first ML models including regression and classification.',
            'type': 'course',
            'difficulty': 'Intermediate',
            'duration': '12 hours',
            'url': 'https://example.com/ml-python',
            'tags': ['machine-learning', 'python', 'scikit-learn', 'pandas', 'numpy', 'regression', 'classification'],
            'category': 'Machine Learning',
            'author': 'ML Academy',
            'source': 'Online Course',
            'rating': 4.7,
            'likes': 230
        },
        {
            'title': 'Data Structures and Algorithms in Python',
            'description': 'Master essential data structures like arrays, linked lists, trees, graphs and algorithms including sorting, searching, and dynamic programming.',
            'type': 'course',
            'difficulty': 'Intermediate',
            'duration': '15 hours',
            'url': 'https://example.com/dsa-python',
            'tags': ['algorithms', 'data-structures', 'python', 'sorting', 'searching', 'trees', 'graphs'],
            'category': 'Computer Science',
            'author': 'CS Academy',
            'source': 'Online Course',
            'rating': 4.6,
            'likes': 180
        },
        {
            'title': 'Deep Learning with TensorFlow',
            'description': 'Build neural networks and deep learning models using TensorFlow. Cover CNNs, RNNs, and advanced architectures for image and text processing.',
            'type': 'course',
            'difficulty': 'Advanced',
            'duration': '20 hours',
            'url': 'https://example.com/deep-learning-tf',
            'tags': ['deep-learning', 'tensorflow', 'neural-networks', 'cnn', 'rnn', 'ai'],
            'category': 'Deep Learning',
            'author': 'AI Institute',
            'source': 'Online Course',
            'rating': 4.8,
            'likes': 320
        }
    ]
    
    created_resources = []
    
    for resource_data in sample_resources:
        existing = Resource.objects(title=resource_data['title']).first()
        if existing:
            created_resources.append(existing)
            continue
        
        resource = Resource(**resource_data)
        resource.save()
        created_resources.append(resource)
        logging.info(f"Created resource: {resource_data['title']}")
    
    return created_resources

def generate_embeddings_for_resources():
    """Generate embeddings for all resources"""
    
    resources = Resource.objects(embedding__exists=False)
    
    if not resources:
        logging.info("No resources need embeddings")
        return
    
    logging.info(f"Generating embeddings for {resources.count()} resources...")
    
    texts = []
    resource_list = list(resources)
    
    for resource in resource_list:
        text = f"{resource.title}. {resource.description}. Tags: {', '.join(resource.tags)}"
        texts.append(text)
    
    embeddings = ml_service.generate_embeddings(texts)
    
    if not embeddings:
        logging.error("Failed to generate embeddings")
        return
    
    for i, resource in enumerate(resource_list):
        if i < len(embeddings):
            resource.embedding = embeddings[i]
            resource.save()
            logging.info(f"Saved embedding for: {resource.title}")

def main():
    """Main function to load all ML data"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        app = create_app('development')
        
        with app.app_context():
            logger.info("Loading ML data...")
            
            ml_service.initialize(app)
            
            logger.info("Loading sample resources...")
            resources = load_sample_resources()
            
            logger.info("Generating embeddings...")
            generate_embeddings_for_resources()
            
            logger.info("ML data loading completed successfully!")
            
            total_resources = Resource.objects().count()
            resources_with_embeddings = Resource.objects(embedding__exists=True).count()
            
            print(f"\n📊 ML Data Summary:")
            print(f"   Resources: {total_resources}")
            print(f"   Resources with embeddings: {resources_with_embeddings}")
            print(f"\n✅ Ready for ML-powered recommendations!")
    
    except Exception as e:
        logger.error(f"Error loading ML data: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()