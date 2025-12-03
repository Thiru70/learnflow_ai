import pandas as pd
import os
import logging
from models.resource import Resource
from models.notification import Task
from models.user import User
from services.ml_service import ml_service
from datetime import datetime

class CSVDataLoader:
    """Service for loading data from CSV files"""
    
    @staticmethod
    def load_courses_from_csv(file_path: str = None):
        """Load courses from CSV file"""
        if not file_path:
            file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'courses.csv')
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            created_count = 0
            
            for _, row in df.iterrows():
                # Check if resource already exists
                existing = Resource.objects(title=row['title']).first()
                if existing:
                    continue
                
                # Parse tags
                tags = [tag.strip() for tag in row['tags'].split(',')]
                
                # Create resource
                resource = Resource(
                    title=row['title'],
                    description=row['description'],
                    type=row['type'],
                    difficulty=row['difficulty'],
                    duration=row['duration'],
                    tags=tags,
                    category=row['category'],
                    author=row['author'],
                    rating=float(row['rating']),
                    likes=int(row['likes']),
                    url=row['url']
                )
                resource.save()
                created_count += 1
                logging.info(f"Created resource: {row['title']}")
            
            logging.info(f"Loaded {created_count} courses from CSV")
            return created_count
            
        except Exception as e:
            logging.error(f"Error loading courses from CSV: {e}")
            return 0
    
    @staticmethod
    def load_tasks_from_csv(file_path: str = None):
        """Load tasks from CSV file"""
        if not file_path:
            file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'tasks.csv')
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            created_count = 0
            
            for _, row in df.iterrows():
                # Check if task already exists
                existing = Task.objects(task_id=row['task_id']).first()
                if existing:
                    continue
                
                # Parse JSON strings for steps and hints
                steps = {}
                hints = {}
                
                if pd.notna(row['steps']):
                    try:
                        import json
                        steps = json.loads(row['steps'])
                    except json.JSONDecodeError:
                        steps = {}
                
                if pd.notna(row['hints']):
                    try:
                        hints = json.loads(row['hints'])
                    except json.JSONDecodeError:
                        hints = {}
                
                # Create task
                task = Task(
                    task_id=row['task_id'],
                    title=row['title'],
                    description=row['description'],
                    type=row['type'],
                    difficulty=row['difficulty'],
                    estimated_time=row['estimated_time'],
                    category=row['category'],
                    skill_level=row['skill_level'],
                    tags=row['tags'],
                    steps=steps,
                    hints=hints,
                    video_url=row.get('video_url', ''),
                    web_url=row.get('web_url', '')
                )
                task.save()
                created_count += 1
                logging.info(f"Created task: {row['title']}")
            
            logging.info(f"Loaded {created_count} tasks from CSV")
            return created_count
            
        except Exception as e:
            logging.error(f"Error loading tasks from CSV: {e}")
            return 0
    
    @staticmethod
    def generate_embeddings_for_csv_resources():
        """Generate embeddings for resources loaded from CSV"""
        try:
            resources = Resource.objects(embedding__exists=False)
            
            if not resources:
                logging.info("No resources need embeddings")
                return 0
            
            logging.info(f"Generating embeddings for {resources.count()} resources...")
            
            # Prepare texts for embedding
            texts = []
            resource_list = list(resources)
            
            for resource in resource_list:
                # Combine title, description, and tags for embedding
                text = f"{resource.title}. {resource.description}. Tags: {', '.join(resource.tags)}"
                texts.append(text)
            
            # Generate embeddings
            embeddings = ml_service.generate_embeddings(texts)
            
            if not embeddings:
                logging.error("Failed to generate embeddings")
                return 0
            
            # Save embeddings to resources
            updated_count = 0
            for i, resource in enumerate(resource_list):
                if i < len(embeddings):
                    resource.embedding = embeddings[i]
                    resource.save()
                    updated_count += 1
                    logging.info(f"Saved embedding for: {resource.title}")
            
            return updated_count
            
        except Exception as e:
            logging.error(f"Error generating embeddings: {e}")
            return 0
    
    @staticmethod
    def load_user_interactions_from_csv(file_path: str = None):
        """Load user interactions for ML training"""
        if not file_path:
            file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'user_interactions.csv')
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            interactions_data = []
            
            for _, row in df.iterrows():
                interaction = {
                    'user_id': row['user_id'],
                    'resource_id': str(row['resource_id']),
                    'interaction_type': row['interaction_type'],
                    'rating': row['rating'] if pd.notna(row['rating']) else None,
                    'helpful': row['helpful'] if pd.notna(row['helpful']) else None,
                    'timestamp': row['timestamp'],
                    'completion_time_minutes': row['completion_time_minutes'] if pd.notna(row['completion_time_minutes']) else None
                }
                interactions_data.append(interaction)
            
            logging.info(f"Loaded {len(interactions_data)} user interactions from CSV")
            return interactions_data
            
        except Exception as e:
            logging.error(f"Error loading user interactions from CSV: {e}")
            return []
    
    @staticmethod
    def export_training_data():
        """Export current data for ML model training"""
        try:
            # Export resources
            resources = Resource.objects()
            resource_data = []
            
            for resource in resources:
                resource_data.append({
                    'id': str(resource.id),
                    'title': resource.title,
                    'description': resource.description,
                    'type': resource.type,
                    'difficulty': resource.difficulty,
                    'tags': ','.join(resource.tags),
                    'category': resource.category,
                    'rating': resource.rating,
                    'likes': resource.likes,
                    'embedding': resource.embedding
                })
            
            # Export tasks
            tasks = Task.objects()
            task_data = []
            
            for task in tasks:
                task_data.append({
                    'task_id': task.task_id,
                    'title': task.title,
                    'description': task.description,
                    'type': task.type,
                    'difficulty': task.difficulty,
                    'category': task.category,
                    'skill_level': task.skill_level,
                    'tags': task.tags,
                    'completion_rate': task.completion_rate,
                    'average_rating': task.average_rating
                })
            
            # Export users and interactions
            users = User.objects()
            user_data = []
            interaction_data = []
            
            for user in users:
                user_data.append({
                    'user_id': str(user.id),
                    'skill_level': user.skill_level,
                    'interests': ','.join(user.interests or []),
                    'learning_goal': user.learning_goal,
                    'goal_timeline': user.goal_timeline
                })
                
                # Export user interactions
                if user.interactions:
                    for resource_id, interaction in user.interactions.items():
                        interaction_data.append({
                            'user_id': str(user.id),
                            'resource_id': resource_id,
                            'status': interaction.get('status'),
                            'viewed_at': interaction.get('viewed_at'),
                            'completed_at': interaction.get('completed_at')
                        })
            
            # Save to CSV files
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports')
            os.makedirs(data_dir, exist_ok=True)
            
            pd.DataFrame(resource_data).to_csv(os.path.join(data_dir, 'resources_export.csv'), index=False)
            pd.DataFrame(task_data).to_csv(os.path.join(data_dir, 'tasks_export.csv'), index=False)
            pd.DataFrame(user_data).to_csv(os.path.join(data_dir, 'users_export.csv'), index=False)
            pd.DataFrame(interaction_data).to_csv(os.path.join(data_dir, 'interactions_export.csv'), index=False)
            
            logging.info("Training data exported successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error exporting training data: {e}")
            return False

# Global CSV loader instance
csv_loader = CSVDataLoader()