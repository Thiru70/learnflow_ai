import requests
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from flask import current_app
import logging
from typing import List, Dict, Any
import random

class MLService:
    def __init__(self):
        self.sentence_model = None
        self.ml_service_url = None
    
    def initialize(self, app):
        """Initialize ML service with app config"""
        self.ml_service_url = app.config.get('ML_SERVICE_URL')
        
        try:
            # Initialize sentence transformer for embeddings
            model_name = app.config.get('SENTENCE_TRANSFORMER_MODEL', 'all-MiniLM-L6-v2')
            self.sentence_model = SentenceTransformer(model_name)
            logging.info(f"Initialized SentenceTransformer model: {model_name}")
        except Exception as e:
            logging.error(f"Failed to initialize SentenceTransformer: {e}")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            if not self.sentence_model:
                raise Exception("SentenceTransformer model not initialized")
            
            embeddings = self.sentence_model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logging.error(f"Error generating embeddings: {e}")
            return []
    
    def semantic_search(self, query: str, resource_embeddings: List[Dict], top_k: int = 10) -> List[Dict]:
        """Perform semantic search using embeddings"""
        try:
            if not self.sentence_model or not resource_embeddings:
                return []
            
            # Generate query embedding
            query_embedding = self.sentence_model.encode([query])
            
            # Calculate similarities
            similarities = []
            for resource in resource_embeddings:
                if 'embedding' in resource and resource['embedding']:
                    resource_emb = np.array(resource['embedding']).reshape(1, -1)
                    similarity = cosine_similarity(query_embedding, resource_emb)[0][0]
                    similarities.append({
                        'resource': resource,
                        'similarity': float(similarity)
                    })
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
        
        except Exception as e:
            logging.error(f"Error in semantic search: {e}")
            return []
    
    def generate_learning_path(self, user_data: Dict) -> List[Dict]:
        """Generate personalized learning path based on user data"""
        try:
            # Mock ML service call - replace with actual ML service
            if self.ml_service_url:
                response = requests.post(
                    f"{self.ml_service_url}/generate-path",
                    json=user_data,
                    timeout=30
                )
                if response.status_code == 200:
                    return response.json().get('learning_path', [])
            
            # Fallback: Generate mock learning path
            return self._generate_mock_learning_path(user_data)
        
        except Exception as e:
            logging.error(f"Error generating learning path: {e}")
            return self._generate_mock_learning_path(user_data)
    
    def predict_progress(self, user_data: Dict) -> Dict:
        """Predict user progress and risk factors"""
        try:
            # Mock ML service call - replace with actual ML service
            if self.ml_service_url:
                try:
                    response = requests.post(
                        f"{self.ml_service_url}/predict-progress",
                        json=user_data,
                        timeout=5  # Reduced timeout
                    )
                    if response.status_code == 200:
                        return response.json()
                except requests.exceptions.ConnectionError:
                    # ML service not available, use fallback
                    pass
            
            # Fallback: Generate mock prediction
            return self._generate_mock_prediction(user_data)
        
        except Exception as e:
            logging.error(f"Error predicting progress: {e}")
            return self._generate_mock_prediction(user_data)
    
    def recommend_next_tasks(self, user_data: Dict) -> List[str]:
        """Recommend next best tasks for the user"""
        try:
            # Mock ML service call - replace with actual ML service
            if self.ml_service_url:
                try:
                    response = requests.post(
                        f"{self.ml_service_url}/recommend-tasks",
                        json=user_data,
                        timeout=5  # Reduced timeout
                    )
                    if response.status_code == 200:
                        return response.json().get('tasks', [])
                except requests.exceptions.ConnectionError:
                    # ML service not available, use fallback
                    pass
            
            # Fallback: Generate mock recommendations
            return self._generate_mock_task_recommendations(user_data)
        
        except Exception as e:
            logging.error(f"Error recommending tasks: {e}")
            return self._generate_mock_task_recommendations(user_data)
    
    def _generate_mock_learning_path(self, user_data: Dict) -> List[Dict]:
        """Generate mock learning path for development"""
        skill_level = user_data.get('skill_level', 'Beginner')
        interests = user_data.get('interests', [])
        
        # Mock path based on skill level
        if skill_level == 'Beginner':
            return [
                {
                    'step_id': '1',
                    'title': 'Introduction to Programming',
                    'description': 'Learn programming fundamentals',
                    'order': 1,
                    'dependencies': []
                },
                {
                    'step_id': '2',
                    'title': 'Python Basics',
                    'description': 'Master Python syntax and concepts',
                    'order': 2,
                    'dependencies': ['1']
                },
                {
                    'step_id': '3',
                    'title': 'Data Structures',
                    'description': 'Learn essential data structures',
                    'order': 3,
                    'dependencies': ['2']
                }
            ]
        else:
            return [
                {
                    'step_id': '1',
                    'title': 'Advanced Python',
                    'description': 'Advanced Python concepts',
                    'order': 1,
                    'dependencies': []
                },
                {
                    'step_id': '2',
                    'title': 'Machine Learning',
                    'description': 'Introduction to ML',
                    'order': 2,
                    'dependencies': ['1']
                }
            ]
    
    def _generate_mock_prediction(self, user_data: Dict) -> Dict:
        """Generate mock progress prediction"""
        statuses = ['on-track', 'at-risk', 'behind']
        status = random.choice(statuses)
        
        predictions = {
            'on-track': {
                'status': 'on-track',
                'confidence': 0.85,
                'message': "You're on track to complete your learning goals!",
                'factors': ['Consistent daily practice', 'Good completion rate', 'Active engagement'],
                'recommendations': ['Continue current pace', 'Try advanced topics']
            },
            'at-risk': {
                'status': 'at-risk',
                'confidence': 0.72,
                'message': "You might fall behind. Consider increasing study time.",
                'factors': ['Irregular study pattern', 'Lower completion rate'],
                'recommendations': ['Set daily reminders', 'Focus on fundamentals']
            },
            'behind': {
                'status': 'behind',
                'confidence': 0.68,
                'message': "You're behind schedule. Let's get back on track!",
                'factors': ['Long gaps between sessions', 'Incomplete tasks'],
                'recommendations': ['Start with easier tasks', 'Set smaller goals']
            }
        }
        
        return predictions[status]
    
    def _generate_mock_task_recommendations(self, user_data: Dict) -> List[str]:
        """Generate mock task recommendations using actual task IDs from database"""
        try:
            from models.notification import Task
            
            skill_level = user_data.get('skill_level', 'Beginner')
            interests = user_data.get('interests', [])
            
            # Get actual tasks from database
            query = {'is_active': True}
            
            # Filter by skill level if available
            if skill_level:
                if skill_level == 'Beginner':
                    query['difficulty'] = 'Easy'
                elif skill_level == 'Intermediate':
                    query['difficulty__in'] = ['Easy', 'Medium']
                else:  # Advanced
                    query['skill_level__in'] = ['Intermediate', 'Advanced']
            
            # Get tasks from database
            tasks = Task.objects(**query).limit(10)
            task_ids = [task.task_id for task in tasks]
            
            # If we have interests, prioritize matching tasks
            if interests and task_ids:
                interest_tasks = []
                other_tasks = []
                
                for task_id in task_ids:
                    task = Task.objects(task_id=task_id).first()
                    if task and task.tags:
                        task_tags = task.tags.lower() if isinstance(task.tags, str) else ','.join(task.tags).lower()
                        if any(interest.lower() in task_tags for interest in interests):
                            interest_tasks.append(task_id)
                        else:
                            other_tasks.append(task_id)
                
                # Return interest-based tasks first, then others
                return (interest_tasks + other_tasks)[:5]
            
            return task_ids[:5] if task_ids else ['python-variables', 'list-operations']
        
        except Exception as e:
            logging.error(f"Error getting actual task IDs: {e}")
            # Fallback to hardcoded task IDs that should exist
            return ['python-variables', 'list-operations', 'python-functions']
    
    def generate_task_guidance(self, task_data: Dict) -> List[Dict]:
        """Generate AI-powered guidance steps for a task"""
        try:
            # Try to use AI service first
            from services.ai_service import ai_service
            
            ai_guidance = ai_service.generate_task_guidance(task_data)
            if ai_guidance:
                return ai_guidance
            
            # Fallback to existing steps or basic guidance
            existing_steps = task_data.get('existing_steps', {})
            
            if existing_steps:
                guidance_steps = []
                for i, (key, step_content) in enumerate(existing_steps.items(), 1):
                    guidance_steps.append({
                        'step': i,
                        'title': f'Step {i}',
                        'content': step_content,
                        'codeExample': self._generate_code_example(step_content, task_data.get('category', ''))
                    })
                return guidance_steps
            
            # Generate basic guidance steps
            return self._generate_basic_guidance(
                task_data.get('title', ''),
                task_data.get('description', ''),
                task_data.get('difficulty', 'Easy'),
                task_data.get('category', '')
            )
        
        except Exception as e:
            logging.error(f"Error generating task guidance: {e}")
            return self._generate_fallback_guidance(task_data)
    
    def _generate_code_example(self, step_content: str, category: str) -> str:
        """Generate code example based on step content and category"""
        step_lower = step_content.lower()
        
        if 'variable' in step_lower and 'python' in category.lower():
            if 'string' in step_lower:
                return 'name = "John Doe"'
            elif 'integer' in step_lower or 'age' in step_lower:
                return 'age = 25'
            elif 'list' in step_lower:
                return 'colors = ["red", "blue", "green"]'
            else:
                return 'my_variable = "value"'
        elif 'function' in step_lower:
            return 'def my_function(param1, param2):\n    return param1 + param2'
        elif 'print' in step_lower:
            return 'print(f"Hello, {name}!")'
        else:
            return '# Your code here'
    
    def _generate_basic_guidance(self, title: str, description: str, difficulty: str, category: str) -> List[Dict]:
        """Generate basic guidance steps"""
        return [
            {
                'step': 1,
                'title': 'Understanding the Task',
                'content': f'Let\'s break down "{title}": {description}',
                'codeExample': '# Start by understanding what we need to accomplish'
            },
            {
                'step': 2,
                'title': 'Implementation',
                'content': 'Now let\'s implement the solution step by step.',
                'codeExample': '# Write your implementation here'
            },
            {
                'step': 3,
                'title': 'Testing',
                'content': 'Test your implementation to make sure it works correctly.',
                'codeExample': '# Test your code with different inputs'
            }
        ]
    
    def _generate_fallback_guidance(self, task_data: Dict) -> List[Dict]:
        """Generate fallback guidance when AI fails"""
        return [
            {
                'step': 1,
                'title': 'Getting Started',
                'content': task_data.get('description', 'Complete this task step by step.'),
                'codeExample': '# Start here'
            }
        ]
    
    def recommend_tasks_based_on_feedback(self, user_data: Dict) -> List[str]:
        """Advanced feedback-based task recommendations using ML patterns"""
        try:
            from models.notification import Task
            
            feedback_history = user_data.get('feedback_history', [])
            skill_level = user_data.get('skill_level', 'Beginner')
            interests = user_data.get('interests', [])
            
            if not feedback_history:
                return self._generate_mock_task_recommendations(user_data)
            
            # Advanced feedback analysis
            helpful_tasks = [f for f in feedback_history if f.get('helpful', False)]
            unhelpful_tasks = [f for f in feedback_history if not f.get('helpful', True)]
            difficulty_ratings = [f.get('difficulty_rating', 3) for f in feedback_history if f.get('difficulty_rating')]
            
            # Calculate user's preferred difficulty
            avg_difficulty = sum(difficulty_ratings) / len(difficulty_ratings) if difficulty_ratings else 3
            
            # Analyze task categories user likes
            liked_categories = set()
            liked_tags = set()
            
            for feedback in helpful_tasks:
                task = Task.objects(task_id=feedback['task_id']).first()
                if task:
                    if task.category:
                        liked_categories.add(task.category)
                    if task.tags:
                        tags = task.tags.split(',') if isinstance(task.tags, str) else [task.tags]
                        liked_tags.update([tag.strip() for tag in tags])
            
            # Build recommendation query
            recommended_tasks = []
            
            # Strategy 1: Similar categories to liked tasks
            if liked_categories:
                for category in liked_categories:
                    category_tasks = Task.objects(
                        category=category,
                        is_active=True,
                        task_id__nin=[f['task_id'] for f in feedback_history]
                    ).limit(3)
                    recommended_tasks.extend([task.task_id for task in category_tasks])
            
            # Strategy 2: Similar tags to liked tasks
            if liked_tags:
                for tag in list(liked_tags)[:3]:  # Limit to top 3 tags
                    tag_tasks = Task.objects(
                        tags__icontains=tag,
                        is_active=True,
                        task_id__nin=[f['task_id'] for f in feedback_history]
                    ).limit(2)
                    recommended_tasks.extend([task.task_id for task in tag_tasks])
            
            # Strategy 3: Adjust difficulty based on feedback
            target_difficulty = None
            if avg_difficulty <= 2.5:  # User finds tasks easy
                if skill_level == 'Beginner':
                    target_difficulty = ['Easy', 'Medium']
                else:
                    target_difficulty = ['Medium', 'Hard']
            elif avg_difficulty >= 4:  # User finds tasks hard
                target_difficulty = ['Easy']
            else:  # User is comfortable
                target_difficulty = ['Easy', 'Medium'] if skill_level == 'Beginner' else ['Medium', 'Hard']
            
            if target_difficulty:
                difficulty_tasks = Task.objects(
                    difficulty__in=target_difficulty,
                    is_active=True,
                    task_id__nin=[f['task_id'] for f in feedback_history]
                ).limit(3)
                recommended_tasks.extend([task.task_id for task in difficulty_tasks])
            
            # Strategy 4: Interest-based recommendations
            if interests:
                for interest in interests:
                    interest_lower = interest.lower()
                    
                    # Map interests to categories
                    category_mapping = {
                        'web development': 'Web Development',
                        'python': 'Python',
                        'javascript': 'JavaScript',
                        'react': 'React',
                        'machine learning': 'Machine Learning',
                        'data science': 'Data Science',
                        'node.js': 'Node.js',
                        'database': 'Database Design',
                        'cloud': 'Cloud Computing',
                        'devops': 'DevOps',
                        'mobile': 'Mobile Development',
                        'ui/ux': 'UI/UX Design'
                    }
                    
                    for key, category in category_mapping.items():
                        if key in interest_lower:
                            interest_tasks = Task.objects(
                                category=category,
                                is_active=True,
                                task_id__nin=[f['task_id'] for f in feedback_history]
                            ).limit(2)
                            recommended_tasks.extend([task.task_id for task in interest_tasks])
                            break
            
            # Strategy 5: Semantic similarity using embeddings
            if helpful_tasks and self.sentence_model:
                try:
                    # Get embeddings of liked tasks
                    liked_task_texts = []
                    for feedback in helpful_tasks[-3:]:  # Last 3 helpful tasks
                        task = Task.objects(task_id=feedback['task_id']).first()
                        if task:
                            text = f"{task.title} {task.description} {task.tags or ''}"
                            liked_task_texts.append(text)
                    
                    if liked_task_texts:
                        # Find similar tasks using embeddings
                        all_tasks = Task.objects(
                            is_active=True,
                            task_id__nin=[f['task_id'] for f in feedback_history],
                            embedding__exists=True
                        ).limit(20)
                        
                        if all_tasks:
                            # Calculate similarity with liked tasks
                            liked_embeddings = self.sentence_model.encode(liked_task_texts)
                            avg_liked_embedding = np.mean(liked_embeddings, axis=0).reshape(1, -1)
                            
                            similarities = []
                            for task in all_tasks:
                                if task.embedding:
                                    task_embedding = np.array(task.embedding).reshape(1, -1)
                                    similarity = cosine_similarity(avg_liked_embedding, task_embedding)[0][0]
                                    similarities.append((task.task_id, similarity))
                            
                            # Sort by similarity and take top 3
                            similarities.sort(key=lambda x: x[1], reverse=True)
                            similar_tasks = [task_id for task_id, _ in similarities[:3]]
                            recommended_tasks.extend(similar_tasks)
                
                except Exception as e:
                    logging.error(f"Error in semantic similarity: {e}")
            
            # Remove duplicates and limit results
            unique_recommendations = list(dict.fromkeys(recommended_tasks))  # Preserve order
            
            # If we don't have enough recommendations, fill with general ones
            if len(unique_recommendations) < 5:
                fallback_tasks = Task.objects(
                    is_active=True,
                    skill_level=skill_level,
                    task_id__nin=[f['task_id'] for f in feedback_history] + unique_recommendations
                ).limit(5 - len(unique_recommendations))
                unique_recommendations.extend([task.task_id for task in fallback_tasks])
            
            return unique_recommendations[:8]  # Return up to 8 recommendations
        
        except Exception as e:
            logging.error(f"Error in advanced feedback-based recommendations: {e}")
            return self._generate_mock_task_recommendations(user_data)

# Global ML service instance
ml_service = MLService()