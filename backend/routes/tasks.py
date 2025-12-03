from flask import Blueprint, request, jsonify
from models.notification import Task
from models.feedback import TaskFeedback
from utils.auth_utils import token_required, validate_json_input
from services.ml_service import ml_service
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@tasks_bp.route('/test', methods=['GET'])
def get_tasks_test():
    """Get tasks without authentication for testing"""
    try:
        tasks = Task.objects(is_active=True).limit(15)  # Increased limit
        tasks_data = []
        
        for task in tasks:
            task_dict = task.to_dict()
            # Add recommendation reasons for test data
            if any(tag in task.tags.lower() for tag in ['python', 'programming']):
                task_dict['recommendation_reason'] = 'Great for learning programming fundamentals'
            elif any(tag in task.tags.lower() for tag in ['machine-learning', 'ml']):
                task_dict['recommendation_reason'] = 'Build your ML skills'
            elif any(tag in task.tags.lower() for tag in ['data', 'visualization']):
                task_dict['recommendation_reason'] = 'Develop data analysis skills'
            else:
                task_dict['recommendation_reason'] = 'Popular learning task'
            
            task_dict['completed'] = False  # Default for test
            tasks_data.append(task_dict)
        
        return jsonify({
            'success': True,
            'data': tasks_data,
            'total_available': Task.objects(is_active=True).count()
        }), 200
    except Exception as e:
        logging.error(f"Get test tasks error: {e}")
        return jsonify({'error': 'Failed to fetch tasks'}), 500

@tasks_bp.route('/<user_id>', methods=['GET'])
@token_required
def get_recommended_tasks(current_user, user_id):
    """Get recommended micro-tasks for the user"""
    try:
        # Ensure user can only access their own tasks
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get user data for ML recommendations
        user_data = {
            'user_id': str(current_user.id),
            'skill_level': current_user.skill_level,
            'interests': current_user.interests,
            'interactions': current_user.interactions or {}
        }
        
        # Use ML-powered recommendations with embeddings and feedback
        tasks = []
        ml_success = False
        
        try:
            # Check if ML service is available
            if not ml_service.sentence_model:
                raise Exception("SentenceTransformer model not initialized")
            
            # Get user feedback history for learning
            user_feedback_history = TaskFeedback.objects(user=current_user)
            feedback_data = [{
                'task_id': f.task_id,
                'helpful': f.helpful,
                'difficulty_rating': f.difficulty_rating or 3
            } for f in user_feedback_history]
            
            # Create user interest query for embeddings
            interest_query = ' '.join(current_user.interests) if current_user.interests else 'learning programming'
            logging.info(f"ML query for user {current_user.email}: {interest_query}")
            
            # Get all tasks with embeddings
            all_tasks = Task.objects(is_active=True, embedding__exists=True)
            
            if all_tasks.count() > 0:
                # Generate query embedding from user interests
                query_embedding = ml_service.sentence_model.encode([interest_query])
                
                # Calculate similarities and apply feedback learning
                task_scores = []
                completed_task_ids = [f['task_id'] for f in feedback_data]
                
                for task in all_tasks:
                    if task.task_id in completed_task_ids:
                        continue  # Skip completed tasks
                    
                    try:
                        # Calculate semantic similarity
                        task_embedding = np.array(task.embedding).reshape(1, -1)
                        similarity = cosine_similarity(query_embedding, task_embedding)[0][0]
                        
                        # Apply feedback-based learning boost
                        feedback_boost = 0
                        if feedback_data:
                            # Boost tasks similar to helpful ones
                            for feedback in feedback_data:
                                if feedback['helpful']:
                                    similar_task = Task.objects(task_id=feedback['task_id']).first()
                                    if similar_task and similar_task.embedding:
                                        similar_embedding = np.array(similar_task.embedding).reshape(1, -1)
                                        feedback_similarity = cosine_similarity(task_embedding, similar_embedding)[0][0]
                                        feedback_boost += feedback_similarity * 0.3  # 30% boost for similar helpful tasks
                        
                        # Skill level matching bonus
                        skill_bonus = 0.1 if task.skill_level == current_user.skill_level else 0
                        
                        final_score = similarity + feedback_boost + skill_bonus
                        task_scores.append((task, final_score))
                        
                    except Exception as task_error:
                        logging.warning(f"Error processing task {task.task_id}: {task_error}")
                        continue
                
                # Sort by score and get top tasks
                task_scores.sort(key=lambda x: x[1], reverse=True)
                
                for task, score in task_scores[:15]:
                    task_dict = task.to_dict()
                    user_feedback = TaskFeedback.objects(user=current_user, task_id=task.task_id).first()
                    task_dict['completed'] = user_feedback is not None
                    task_dict['user_feedback'] = user_feedback.to_dict() if user_feedback else None
                    task_dict['ml_score'] = round(score, 3)
                    task_dict['recommendation_reason'] = f'ML-recommended based on your interests and learning patterns (score: {round(score, 2)})'
                    tasks.append(task_dict)
                
                ml_success = True
                logging.info(f"ML recommendations generated: {len(tasks)} tasks for user {current_user.email}")
            
        except Exception as e:
            logging.error(f"ML recommendation error: {e}")
            ml_success = False
        
        # If ML recommendations failed, use fallback
        if not tasks:
            # Strategy 1: Direct category matching first
            if current_user.interests and len(current_user.interests) > 0:
                for interest in current_user.interests:
                    # Direct exact category match
                    category_tasks = Task.objects(category=interest, is_active=True)
                    for task in category_tasks.limit(10):
                        if len(tasks) < 15:
                            task_dict = task.to_dict()
                            user_feedback = TaskFeedback.objects(user=current_user, task_id=task.task_id).first()
                            task_dict['completed'] = user_feedback is not None
                            task_dict['user_feedback'] = user_feedback.to_dict() if user_feedback else None
                            task_dict['recommendation_reason'] = f'{interest} task based on your interest'
                            
                            if not any(t['task_id'] == task.task_id for t in tasks):
                                tasks.append(task_dict)
            
            # Strategy 2: If still need more tasks, use mapping logic
            if len(tasks) < 10 and current_user.interests:
                interest_mapping = {
                    'web development': {
                        'categories': ['Web Development'],
                        'tags': ['web-development', 'html', 'css', 'javascript', 'react', 'responsive', 'flexbox']
                    },
                    'data science': {
                        'categories': ['Data Science'],
                        'tags': ['data-science', 'eda', 'pandas', 'descriptive', 'hypothesis']
                    },
                    'python': {
                        'categories': ['Python'],
                        'tags': ['python', 'syntax', 'functions', 'collections']
                    },
                    'machine learning': {
                        'categories': ['Machine Learning'],
                        'tags': ['machine-learning', 'linear', 'logistic', 'svm', 'clustering']
                    }
                }
                
                for interest in current_user.interests:
                    interest_lower = interest.lower()
                    matched_categories = []
                    matched_tags = []
                    
                    for key, mapping in interest_mapping.items():
                        if key in interest_lower:
                            matched_categories.extend(mapping['categories'])
                            matched_tags.extend(mapping['tags'])
                    
                    # Get tasks by mapped categories
                    for category in matched_categories:
                        category_tasks = Task.objects(category=category, is_active=True)
                        for task in category_tasks.limit(3):
                            if len(tasks) < 15:
                                task_dict = task.to_dict()
                                user_feedback = TaskFeedback.objects(user=current_user, task_id=task.task_id).first()
                                task_dict['completed'] = user_feedback is not None
                                task_dict['user_feedback'] = user_feedback.to_dict() if user_feedback else None
                                task_dict['recommendation_reason'] = f'{category} task for {interest}'
                                
                                if not any(t['task_id'] == task.task_id for t in tasks):
                                    tasks.append(task_dict)
            
            # Strategy 2: Fill remaining slots with skill-appropriate tasks
            if len(tasks) < 15:
                query = {'is_active': True}
                if current_user.skill_level:
                    query['skill_level'] = current_user.skill_level
                else:
                    query['skill_level'] = 'Beginner'  # Default for new users
                
                # Exclude already selected tasks
                if tasks:
                    existing_task_ids = [t['task_id'] for t in tasks]
                    query['task_id__nin'] = existing_task_ids
                
                remaining_slots = 15 - len(tasks)
                default_tasks = Task.objects(**query).limit(remaining_slots)
                for task in default_tasks:
                    task_dict = task.to_dict()
                    
                    user_feedback = TaskFeedback.objects(user=current_user, task_id=task.task_id).first()
                    task_dict['completed'] = user_feedback is not None
                    task_dict['user_feedback'] = user_feedback.to_dict() if user_feedback else None
                    task_dict['recommendation_reason'] = f'Suitable for {current_user.skill_level or "Beginner"} level'
                    
                    tasks.append(task_dict)
        
        # If still no tasks, get any active tasks
        if len(tasks) < 10:  # Always ensure we have at least 10 tasks
            remaining_slots = 15 - len(tasks)
            existing_task_ids = [t['task_id'] for t in tasks] if tasks else []
            
            fallback_query = {'is_active': True}
            if existing_task_ids:
                fallback_query['task_id__nin'] = existing_task_ids
            
            fallback_tasks = Task.objects(**fallback_query).limit(remaining_slots)
            for task in fallback_tasks:
                task_dict = task.to_dict()
                user_feedback = TaskFeedback.objects(user=current_user, task_id=task.task_id).first()
                task_dict['completed'] = user_feedback is not None
                task_dict['user_feedback'] = user_feedback.to_dict() if user_feedback else None
                
                # Better recommendation reasons based on task content
                if any(tag in task.tags.lower() for tag in ['python', 'programming']):
                    task_dict['recommendation_reason'] = 'Great for learning programming fundamentals'
                elif any(tag in task.tags.lower() for tag in ['machine-learning', 'ml']):
                    task_dict['recommendation_reason'] = 'Build your ML skills'
                elif any(tag in task.tags.lower() for tag in ['data', 'visualization']):
                    task_dict['recommendation_reason'] = 'Develop data analysis skills'
                else:
                    task_dict['recommendation_reason'] = 'Popular learning task'
                
                tasks.append(task_dict)
        
        # Debug logging
        logging.info(f"Generated {len(tasks)} task recommendations for user {current_user.email} with interests {current_user.interests}")
        
        return jsonify({
            'success': True,
            'data': tasks,
            'total_available': Task.objects(is_active=True).count(),
            'user_interests': current_user.interests,
            'message': f'Found {len(tasks)} personalized tasks'
        }), 200
    
    except Exception as e:
        logging.error(f"Get recommended tasks error: {e}")
        return jsonify({'error': 'Failed to fetch recommended tasks'}), 500

@tasks_bp.route('/<task_id>', methods=['GET'])
@token_required
def get_task_details(current_user, task_id):
    """Get detailed information about a specific task"""
    try:
        task = Task.objects(task_id=task_id, is_active=True).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        task_dict = task.to_dict()
        
        # Check if user has completed this task
        user_feedback = TaskFeedback.objects(user=current_user, task_id=task_id).first()
        task_dict['completed'] = user_feedback is not None
        task_dict['user_feedback'] = user_feedback.to_dict() if user_feedback else None
        
        # Increment attempt count
        task.total_attempts += 1
        task.save()
        
        return jsonify({
            'success': True,
            'data': task_dict
        }), 200
    
    except Exception as e:
        logging.error(f"Get task details error: {e}")
        return jsonify({'error': 'Failed to fetch task details'}), 500

@tasks_bp.route('/<user_id>/complete', methods=['POST'])
@token_required
@validate_json_input(['task_id'])
def complete_task(current_user, user_id, data):
    """Mark a task as completed and submit feedback"""
    try:
        # Ensure user can only complete their own tasks
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        task_id = data['task_id']
        helpful = data.get('helpful', True)
        comment = data.get('comment', '')
        difficulty_rating = data.get('difficulty_rating')
        
        # Check if task exists
        task = Task.objects(task_id=task_id, is_active=True).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Check if already completed - allow re-completion for testing
        existing_feedback = TaskFeedback.objects(user=current_user, task_id=task_id).first()
        if existing_feedback:
            # Update existing feedback instead of creating new one
            existing_feedback.helpful = helpful
            existing_feedback.comment = comment
            if difficulty_rating:
                existing_feedback.difficulty_rating = difficulty_rating
            existing_feedback.save()
            
            return jsonify({
                'success': True,
                'message': 'Task feedback updated successfully',
                'data': {
                    'task_id': task_id,
                    'feedback': existing_feedback.to_dict()
                }
            }), 200
        
        # Create task feedback
        feedback = TaskFeedback(
            user=current_user,
            task_id=task_id,
            helpful=helpful,
            comment=comment,
            difficulty_rating=difficulty_rating
        )
        feedback.save()
        
        # Update task completion rate
        try:
            total_feedback = TaskFeedback.objects(task_id=task_id).count()
            if total_feedback > 0 and task.total_attempts > 0:
                task.completion_rate = int((total_feedback / task.total_attempts) * 100)
            else:
                task.completion_rate = 0
            
            # Update average rating if ratings are provided
            ratings = TaskFeedback.objects(task_id=task_id, difficulty_rating__exists=True)
            if ratings:
                avg_rating = sum([f.difficulty_rating for f in ratings]) / len(ratings)
                task.average_rating = round(avg_rating, 1)
            
            task.save()
        except Exception as task_update_error:
            logging.warning(f"Failed to update task stats: {task_update_error}")
            # Don't fail the whole operation if task stats update fails
        
        return jsonify({
            'success': True,
            'message': 'Task completed successfully',
            'data': {
                'task_id': task_id,
                'feedback': feedback.to_dict()
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Complete task error: {e}")
        return jsonify({'error': 'Failed to complete task'}), 500

@tasks_bp.route('/feedback', methods=['GET', 'POST'])
@token_required
def submit_task_feedback(current_user, data=None):
    """Submit or get feedback for a task"""
    if request.method == 'GET':
        # Get user's feedback history
        try:
            user_feedback = TaskFeedback.objects(user=current_user)
            feedback_data = [feedback.to_dict() for feedback in user_feedback]
            return jsonify({
                'success': True,
                'data': feedback_data
            }), 200
        except Exception as e:
            logging.error(f"Get feedback error: {e}")
            return jsonify({'error': 'Failed to get feedback'}), 500
    
    # POST method - validate input
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    if not data or 'task_id' not in data or 'helpful' not in data:
        return jsonify({'error': 'Missing required fields: task_id, helpful'}), 400
    
    try:
        task_id = data['task_id']
        helpful = data['helpful']
        comment = data.get('comment', '')
        difficulty_rating = data.get('difficulty_rating')
        
        # Check if task exists
        task = Task.objects(task_id=task_id, is_active=True).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Check if feedback already exists
        existing_feedback = TaskFeedback.objects(user=current_user, task_id=task_id).first()
        if existing_feedback:
            # Update existing feedback
            existing_feedback.helpful = helpful
            existing_feedback.comment = comment
            if difficulty_rating:
                existing_feedback.difficulty_rating = difficulty_rating
            existing_feedback.save()
            feedback = existing_feedback
        else:
            # Create new feedback
            feedback = TaskFeedback(
                user=current_user,
                task_id=task_id,
                helpful=helpful,
                comment=comment,
                difficulty_rating=difficulty_rating
            )
            feedback.save()
        
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully',
            'data': feedback.to_dict()
        }), 200
    
    except Exception as e:
        logging.error(f"Submit task feedback error: {e}")
        return jsonify({'error': 'Failed to submit feedback'}), 500

@tasks_bp.route('/<task_id>/guidance', methods=['GET'])
def get_task_guidance(task_id):
    """Get AI-generated guidance steps for a task"""
    try:
        # Try to find by task_id first, then by MongoDB ObjectId
        task = Task.objects(task_id=task_id, is_active=True).first()
        if not task:
            try:
                task = Task.objects(id=task_id, is_active=True).first()
            except:
                pass
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Generate AI guidance steps
        guidance_steps = ml_service.generate_task_guidance({
            'task_id': task.task_id,
            'title': task.title,
            'description': task.description,
            'difficulty': task.difficulty,
            'category': task.category,
            'existing_steps': task.steps,
            'hints': task.hints
        })
        
        return jsonify({
            'success': True,
            'data': guidance_steps
        }), 200
    
    except Exception as e:
        logging.error(f"Get task guidance error: {e}")
        return jsonify({'error': 'Failed to generate guidance'}), 500

@tasks_bp.route('/categories', methods=['GET'])
@token_required
def get_task_categories(current_user):
    """Get available task categories"""
    try:
        # Get distinct categories
        categories = Task.objects(is_active=True).distinct('category')
        
        # Get task counts per category
        category_data = []
        for category in categories:
            if category:  # Skip None values
                count = Task.objects(category=category, is_active=True).count()
                category_data.append({
                    'name': category,
                    'count': count
                })
        
        return jsonify({
            'success': True,
            'data': category_data
        }), 200
    
    except Exception as e:
        logging.error(f"Get task categories error: {e}")
        return jsonify({'error': 'Failed to fetch task categories'}), 500

@tasks_bp.route('/<user_id>/recommendations', methods=['GET'])
@token_required
def get_ml_recommendations(current_user, user_id):
    """Get ML-based task recommendations based on user feedback and performance"""
    try:
        # Ensure user can only access their own recommendations
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get user's feedback history
        user_feedback = TaskFeedback.objects(user=current_user)
        
        # Prepare user data for ML service
        feedback_data = []
        for feedback in user_feedback:
            feedback_data.append({
                'task_id': feedback.task_id,
                'helpful': feedback.helpful,
                'difficulty_rating': feedback.difficulty_rating,
                'comment': feedback.comment,
                'created_at': feedback.created_at.isoformat()
            })
        
        user_data = {
            'user_id': str(current_user.id),
            'skill_level': current_user.skill_level,
            'interests': current_user.interests,
            'feedback_history': feedback_data,
            'interactions': current_user.interactions or {}
        }
        
        # Get ML recommendations (non-blocking)
        recommended_task_ids = []
        try:
            recommended_task_ids = ml_service.recommend_tasks_based_on_feedback(user_data)
        except Exception as e:
            logging.warning(f"ML service unavailable for feedback recommendations: {e}")
            recommended_task_ids = []
        
        # Fetch actual tasks
        recommended_tasks = []
        for task_id in recommended_task_ids:
            task = Task.objects(task_id=task_id, is_active=True).first()
            if task:
                task_dict = task.to_dict()
                
                # Check completion status
                user_task_feedback = TaskFeedback.objects(user=current_user, task_id=task_id).first()
                task_dict['completed'] = user_task_feedback is not None
                task_dict['user_feedback'] = user_task_feedback.to_dict() if user_task_feedback else None
                
                recommended_tasks.append(task_dict)
        
        return jsonify({
            'success': True,
            'data': recommended_tasks,
            'recommendation_reason': 'Based on your feedback and learning patterns'
        }), 200
    
    except Exception as e:
        logging.error(f"Get ML recommendations error: {e}")
        return jsonify({'error': 'Failed to get recommendations'}), 500