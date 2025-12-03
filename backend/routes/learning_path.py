from flask import Blueprint, request, jsonify
from models.learning_path import LearningPath, LearningPathStep
from models.resource import Resource
from models.notification import Task
from utils.auth_utils import token_required, validate_json_input
from services.ml_service import ml_service
from datetime import datetime
import logging

learning_path_bp = Blueprint('learning_path', __name__, url_prefix='/api/learning-path')

@learning_path_bp.route('/test', methods=['GET'])
def get_learning_path_test():
    """Get sample learning path without authentication for testing"""
    try:
        # Return Web Development learning path steps
        sample_steps = [
            {
                'id': '1',
                'step_id': 'step_1',
                'title': 'Step 1: JavaScript Essentials',
                'description': 'Master JavaScript fundamentals including DOM manipulation and ES6+ features',
                'resourceId': '1',
                'duration': '8 hours',
                'difficulty': 'Beginner',
                'completed': False,
                'order': 1,
                'dependencies': [],
                'resource': {
                    'id': '1',
                    'title': 'JavaScript Essentials',
                    'description': 'Master JavaScript fundamentals including DOM manipulation and ES6+ features',
                    'type': 'course',
                    'difficulty': 'Beginner',
                    'duration': '8 hours',
                    'category': 'Web Development',
                    'tags': ['javascript', 'frontend', 'es6'],
                    'author': 'freeCodeCamp'
                }
            },
            {
                'id': '2',
                'step_id': 'step_2',
                'title': 'Step 2: Responsive Web Design',
                'description': 'Learn HTML5, CSS3, and accessibility standards for mobile-friendly sites',
                'resourceId': '2',
                'duration': '12 hours',
                'difficulty': 'Beginner',
                'completed': False,
                'order': 2,
                'dependencies': ['step_1'],
                'resource': {
                    'id': '2',
                    'title': 'Responsive Web Design',
                    'description': 'Learn HTML5, CSS3, and accessibility standards for mobile-friendly sites',
                    'type': 'course',
                    'difficulty': 'Beginner',
                    'duration': '12 hours',
                    'category': 'Web Development',
                    'tags': ['html', 'css', 'responsive'],
                    'author': 'freeCodeCamp'
                }
            },
            {
                'id': '3',
                'step_id': 'step_3',
                'title': 'Step 3: React for Beginners',
                'description': 'Build interactive UI components with React and JSX',
                'resourceId': '3',
                'duration': '18 hours',
                'difficulty': 'Beginner',
                'completed': False,
                'order': 3,
                'dependencies': ['step_2'],
                'resource': {
                    'id': '3',
                    'title': 'React for Beginners',
                    'description': 'Build interactive UI components with React and JSX',
                    'type': 'course',
                    'difficulty': 'Beginner',
                    'duration': '18 hours',
                    'category': 'React',
                    'tags': ['react', 'javascript', 'ui'],
                    'author': 'Scrimba'
                }
            }
        ]
        
        return jsonify({
            'success': True,
            'data': sample_steps
        }), 200
    except Exception as e:
        logging.error(f"Get test learning path error: {e}")
        return jsonify({'error': 'Failed to fetch learning path'}), 500

@learning_path_bp.route('/demo/<user_id>', methods=['GET'])
def get_learning_path_demo(user_id):
    """Get user's learning path without authentication for demo purposes"""
    try:
        from models.user import User
        user = User.objects(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Generate learning path based on user interests using recommended courses
        if user.interests:
            matching_courses = []
            
            for interest in user.interests:
                interest_lower = interest.lower()
                
                # Get courses for each difficulty level (Beginner -> Intermediate -> Advanced)
                for difficulty in ['Beginner', 'Intermediate', 'Advanced']:
                    try:
                        # Try category matching first
                        category_courses = Resource.objects(
                            category__icontains=interest,
                            difficulty=difficulty
                        ).order_by('-rating', '-likes').limit(2)
                        
                        for course in category_courses:
                            if course not in matching_courses and len(matching_courses) < 6:
                                matching_courses.append(course)
                        
                        # If no category matches, try tag matching
                        if len([c for c in matching_courses if c.difficulty == difficulty]) == 0:
                            tag_courses = Resource.objects(
                                tags__icontains=interest_lower,
                                difficulty=difficulty
                            ).order_by('-rating', '-likes').limit(1)
                            
                            for course in tag_courses:
                                if course not in matching_courses and len(matching_courses) < 6:
                                    matching_courses.append(course)
                    
                    except Exception as e:
                        logging.warning(f"Course query failed for {interest}, {difficulty}: {e}")
                        continue
            
            # Create actual learning path steps in database
            existing_steps = LearningPathStep.objects(user=user)
            if not existing_steps:
                for i, course in enumerate(matching_courses):
                    step = LearningPathStep(
                        user=user,
                        resource=course,
                        step_id=f"step_{i+1}",
                        title=f"Step {i+1}: {course.title}",
                        description=course.description,
                        order=i+1,
                        dependencies=[f"step_{i}"] if i > 0 else []
                    )
                    step.save()
            
            # Get the created/existing steps
            steps = LearningPathStep.objects(user=user).order_by('order')
            steps_data = []
            for step in steps:
                step_dict = step.to_dict()
                if step.resource:
                    resource_dict = step.resource.to_dict()
                    step_dict['resource'] = resource_dict
                steps_data.append(step_dict)
            
            return jsonify({
                'success': True,
                'data': steps_data,
                'user_interests': user.interests,
                'total_steps': len(steps_data)
            }), 200
        
        # Fallback to existing learning path steps
        steps = LearningPathStep.objects(user=user).order_by('order')
        steps_data = []
        for step in steps:
            step_dict = step.to_dict()
            if step.resource:
                resource_dict = step.resource.to_dict()
                step_dict['resource'] = resource_dict
            steps_data.append(step_dict)
        
        return jsonify({
            'success': True,
            'data': steps_data,
            'user_interests': user.interests,
            'total_steps': len(steps_data)
        }), 200
    
    except Exception as e:
        logging.error(f"Get demo learning path error: {e}")
        return jsonify({'error': 'Failed to fetch learning path'}), 500

@learning_path_bp.route('/<user_id>', methods=['GET'])
@token_required
def get_learning_path(current_user, user_id):
    """Get user's learning path"""
    try:
        # Ensure user can only access their own learning path
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get learning path steps
        steps = LearningPathStep.objects(user=current_user).order_by('order')
        
        # If no learning path exists, generate one automatically
        if not steps and current_user.is_onboarded and current_user.interests:
            try:
                logging.info(f"Auto-generating learning path for user {current_user.email}")
                
                # Find recommended courses matching user interests
                matching_courses = []
                
                for interest in current_user.interests:
                    interest_lower = interest.lower()
                    
                    # Get courses for each difficulty level (Beginner -> Intermediate -> Advanced)
                    for difficulty in ['Beginner', 'Intermediate', 'Advanced']:
                        try:
                            # Try category matching first
                            category_courses = Resource.objects(
                                category__icontains=interest,
                                difficulty=difficulty
                            ).order_by('-rating', '-likes').limit(2)
                            
                            for course in category_courses:
                                if course not in matching_courses and len(matching_courses) < 6:
                                    matching_courses.append(course)
                                    logging.info(f"Added {course.title} ({course.category}, {course.difficulty})")
                            
                            # If no category matches, try tag matching
                            if len([c for c in matching_courses if c.difficulty == difficulty]) == 0:
                                tag_courses = Resource.objects(
                                    tags__icontains=interest_lower,
                                    difficulty=difficulty
                                ).order_by('-rating', '-likes').limit(1)
                                
                                for course in tag_courses:
                                    if course not in matching_courses and len(matching_courses) < 6:
                                        matching_courses.append(course)
                                        logging.info(f"Added {course.title} ({course.category}, {course.difficulty})")
                        
                        except Exception as e:
                            logging.warning(f"Course query failed for {interest}, {difficulty}: {e}")
                            continue
                
                # Create learning path steps from matching courses
                if matching_courses:
                    for i, course in enumerate(matching_courses):
                        step = LearningPathStep(
                            user=current_user,
                            resource=course,
                            step_id=f"step_{i+1}",
                            title=f"Step {i+1}: {course.title}",
                            description=course.description,
                            order=i+1,
                            dependencies=[f"step_{i}"] if i > 0 else []
                        )
                        step.save()
                        logging.info(f"Created learning path step: {step.title} (Difficulty: {course.difficulty})")
                    
                    # Re-fetch the created steps
                    steps = LearningPathStep.objects(user=current_user).order_by('order')
                    logging.info(f"Generated {steps.count()} learning path steps")
                
            except Exception as e:
                logging.error(f"Error auto-generating learning path: {e}")
        
        # Convert to dict format
        steps_data = []
        for step in steps:
            step_dict = step.to_dict()
            
            # Add resource information
            if step.resource:
                resource_dict = step.resource.to_dict()
                step_dict['resource'] = resource_dict
            
            steps_data.append(step_dict)
        
        return jsonify({
            'success': True,
            'data': steps_data,
            'user_interests': current_user.interests,
            'total_steps': len(steps_data)
        }), 200
    
    except Exception as e:
        logging.error(f"Get learning path error: {e}")
        return jsonify({'error': 'Failed to fetch learning path'}), 500

@learning_path_bp.route('/<user_id>', methods=['POST'])
@token_required
@validate_json_input(['steps'])
def update_learning_path(current_user, user_id, data):
    """Update user's learning path (reorder steps, add/remove steps)"""
    try:
        # Ensure user can only update their own learning path
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        steps_data = data['steps']
        
        # Delete existing steps
        LearningPathStep.objects(user=current_user).delete()
        
        # Create new steps
        for step_data in steps_data:
            # Find the resource
            resource = None
            if 'resource_id' in step_data:
                resource = Resource.objects(id=step_data['resource_id']).first()
            
            step = LearningPathStep(
                user=current_user,
                resource=resource,
                step_id=step_data['step_id'],
                title=step_data['title'],
                description=step_data.get('description', ''),
                order=step_data['order'],
                dependencies=step_data.get('dependencies', []),
                completed=step_data.get('completed', False)
            )
            
            if step_data.get('completed') and not step.completed_at:
                step.completed_at = datetime.utcnow()
            
            step.save()
        
        # Update learning path progress
        learning_path = LearningPath.objects(user=current_user).first()
        if learning_path:
            learning_path.update_progress()
        
        return jsonify({
            'success': True,
            'message': 'Learning path updated successfully'
        }), 200
    
    except Exception as e:
        logging.error(f"Update learning path error: {e}")
        return jsonify({'error': 'Failed to update learning path'}), 500

@learning_path_bp.route('/<user_id>/step/complete', methods=['POST'])
@token_required
@validate_json_input(['step_id'])
def mark_step_completed(current_user, user_id, data):
    """Mark a learning path step as completed"""
    try:
        logging.info(f"Marking step completed for user {user_id}, step_id: {data.get('step_id')}")
        
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        step_id = data['step_id']
        step = LearningPathStep.objects(user=current_user, step_id=step_id).first()
        if not step:
            logging.warning(f"Step not found: {step_id} for user {user_id}")
            # Try to find by id as fallback
            step = LearningPathStep.objects(user=current_user, id=step_id).first()
            if not step:
                return jsonify({'error': 'Step not found'}), 404
        
        step.completed = True
        step.completed_at = datetime.utcnow()
        if not step.started_at:
            step.started_at = datetime.utcnow()
        step.save()
        
        # Update user interactions
        if step.resource:
            if not current_user.interactions:
                current_user.interactions = {}
            resource_id = str(step.resource.id)
            if resource_id not in current_user.interactions:
                current_user.interactions[resource_id] = {}
            current_user.interactions[resource_id]['status'] = 'completed'
            current_user.interactions[resource_id]['completed_at'] = datetime.utcnow().isoformat()
            current_user.save()
        
        # Update learning path progress
        learning_path = LearningPath.objects(user=current_user).first()
        if learning_path:
            learning_path.update_progress()
        
        return jsonify({
            'success': True,
            'message': 'Step completed successfully',
            'data': step.to_dict()
        }), 200
    
    except Exception as e:
        logging.error(f"Mark step completed error: {e}")
        return jsonify({'error': 'Failed to mark step as completed'}), 500

@learning_path_bp.route('/<user_id>/step/<step_id>/complete', methods=['POST'])
@token_required
def mark_step_completed_alt(current_user, user_id, step_id):
    """Alternative endpoint for marking step as completed (for URL-based step_id)"""
    try:
        logging.info(f"Marking step completed (alt) for user {user_id}, step_id: {step_id}")
        
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        step = LearningPathStep.objects(user=current_user, step_id=step_id).first()
        if not step:
            logging.warning(f"Step not found (alt): {step_id} for user {user_id}")
            # Try to find by id as fallback
            step = LearningPathStep.objects(user=current_user, id=step_id).first()
            if not step:
                return jsonify({'error': 'Step not found'}), 404
        
        step.completed = True
        step.completed_at = datetime.utcnow()
        if not step.started_at:
            step.started_at = datetime.utcnow()
        step.save()
        
        # Update user interactions
        if step.resource:
            if not current_user.interactions:
                current_user.interactions = {}
            resource_id = str(step.resource.id)
            if resource_id not in current_user.interactions:
                current_user.interactions[resource_id] = {}
            current_user.interactions[resource_id]['status'] = 'completed'
            current_user.interactions[resource_id]['completed_at'] = datetime.utcnow().isoformat()
            current_user.save()
        
        # Update learning path progress
        learning_path = LearningPath.objects(user=current_user).first()
        if learning_path:
            learning_path.update_progress()
        
        return jsonify({
            'success': True,
            'message': 'Step completed successfully',
            'data': step.to_dict()
        }), 200
    
    except Exception as e:
        logging.error(f"Mark step completed error: {e}")
        return jsonify({'error': 'Failed to mark step as completed'}), 500

@learning_path_bp.route('/<user_id>/step/start', methods=['POST'])
@token_required
@validate_json_input(['step_id'])
def start_step(current_user, user_id, data):
    """Mark a learning path step as started"""
    try:
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        step_id = data['step_id']
        step = LearningPathStep.objects(user=current_user, step_id=step_id).first()
        if not step:
            return jsonify({'error': 'Step not found'}), 404
        
        if not step.started_at:
            step.started_at = datetime.utcnow()
            step.save()
        
        if step.resource:
            if not current_user.interactions:
                current_user.interactions = {}
            resource_id = str(step.resource.id)
            if resource_id not in current_user.interactions:
                current_user.interactions[resource_id] = {}
            current_user.interactions[resource_id]['status'] = 'in-progress'
            current_user.interactions[resource_id]['viewed_at'] = datetime.utcnow().isoformat()
            current_user.save()
        
        return jsonify({
            'success': True,
            'message': 'Step started successfully',
            'data': step.to_dict()
        }), 200
    
    except Exception as e:
        logging.error(f"Start step error: {e}")
        return jsonify({'error': 'Failed to start step'}), 500

@learning_path_bp.route('/<user_id>/step/<step_id>/start', methods=['POST'])
@token_required
def start_step_alt(current_user, user_id, step_id):
    """Alternative endpoint for starting a step (for URL-based step_id)"""
    try:
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        step = LearningPathStep.objects(user=current_user, step_id=step_id).first()
        if not step:
            return jsonify({'error': 'Step not found'}), 404
        
        if not step.started_at:
            step.started_at = datetime.utcnow()
            step.save()
        
        if step.resource:
            if not current_user.interactions:
                current_user.interactions = {}
            resource_id = str(step.resource.id)
            if resource_id not in current_user.interactions:
                current_user.interactions[resource_id] = {}
            current_user.interactions[resource_id]['status'] = 'in-progress'
            current_user.interactions[resource_id]['viewed_at'] = datetime.utcnow().isoformat()
            current_user.save()
        
        return jsonify({
            'success': True,
            'message': 'Step started successfully',
            'data': step.to_dict()
        }), 200
    
    except Exception as e:
        logging.error(f"Start step error: {e}")
        return jsonify({'error': 'Failed to start step'}), 500

@learning_path_bp.route('/<user_id>/generate', methods=['POST'])
@token_required
def generate_learning_path(current_user, user_id):
    """Generate a new learning path for the user"""
    try:
        # Ensure user can only generate their own learning path
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if user is onboarded
        if not current_user.is_onboarded:
            return jsonify({'error': 'User must complete onboarding first'}), 400
        
        # Delete existing learning path
        LearningPathStep.objects(user=current_user).delete()
        
        # Find recommended courses matching user interests
        matching_courses = []
        
        for interest in current_user.interests:
            interest_lower = interest.lower()
            
            # Get courses for each difficulty level (Beginner -> Intermediate -> Advanced)
            for difficulty in ['Beginner', 'Intermediate', 'Advanced']:
                try:
                    # Try category matching first
                    category_courses = Resource.objects(
                        category__icontains=interest,
                        difficulty=difficulty
                    ).order_by('-rating', '-likes').limit(2)
                    
                    for course in category_courses:
                        if course not in matching_courses and len(matching_courses) < 6:
                            matching_courses.append(course)
                    
                    # If no category matches, try tag matching
                    if len([c for c in matching_courses if c.difficulty == difficulty]) == 0:
                        tag_courses = Resource.objects(
                            tags__icontains=interest_lower,
                            difficulty=difficulty
                        ).order_by('-rating', '-likes').limit(1)
                        
                        for course in tag_courses:
                            if course not in matching_courses and len(matching_courses) < 6:
                                matching_courses.append(course)
                
                except Exception as e:
                    logging.warning(f"Course query failed for {interest}, {difficulty}: {e}")
                    continue
        
        # Create learning path steps from matching courses
        created_steps = []
        if matching_courses:
            for i, course in enumerate(matching_courses):
                step = LearningPathStep(
                    user=current_user,
                    resource=course,
                    step_id=f"step_{i+1}",
                    title=f"Step {i+1}: {course.title}",
                    description=course.description,
                    order=i+1,
                    dependencies=[f"step_{i}"] if i > 0 else []
                )
                step.save()
                created_steps.append(step.to_dict())
        
        # Create or update learning path
        learning_path = LearningPath.objects(user=current_user).first()
        if not learning_path:
            learning_path = LearningPath(user=current_user)
        
        learning_path.title = f"{current_user.name}'s Learning Path"
        learning_path.description = f"Personalized path for {current_user.learning_goal}"
        learning_path.save()
        learning_path.update_progress()
        
        return jsonify({
            'success': True,
            'message': 'Learning path generated successfully',
            'data': {
                'learning_path': learning_path.to_dict(),
                'steps': created_steps
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Generate learning path error: {e}")
        return jsonify({'error': 'Failed to generate learning path'}), 500

@learning_path_bp.route('/<user_id>/debug', methods=['GET'])
@token_required
def debug_learning_path(current_user, user_id):
    """Debug endpoint to check learning path steps"""
    try:
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        steps = LearningPathStep.objects(user=current_user)
        debug_info = {
            'user_id': user_id,
            'total_steps': steps.count(),
            'steps': []
        }
        
        for step in steps:
            debug_info['steps'].append({
                'id': str(step.id),
                'step_id': step.step_id,
                'title': step.title,
                'completed': step.completed,
                'order': step.order
            })
        
        return jsonify({
            'success': True,
            'data': debug_info
        }), 200
    
    except Exception as e:
        logging.error(f"Debug learning path error: {e}")
        return jsonify({'error': 'Failed to debug learning path'}), 500

@learning_path_bp.route('/<user_id>/progress', methods=['GET'])
@token_required
def get_learning_path_progress(current_user, user_id):
    """Get learning path progress statistics"""
    try:
        # Ensure user can only access their own progress
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get learning path
        learning_path = LearningPath.objects(user=current_user).first()
        if not learning_path:
            return jsonify({
                'success': True,
                'data': {
                    'total_steps': 0,
                    'completed_steps': 0,
                    'progress_percentage': 0,
                    'current_step': None
                }
            }), 200
        
        # Get current step (first incomplete step)
        current_step = LearningPathStep.objects(
            user=current_user,
            completed=False
        ).order_by('order').first()
        
        progress_data = learning_path.to_dict()
        progress_data['current_step'] = current_step.to_dict() if current_step else None
        
        return jsonify({
            'success': True,
            'data': progress_data
        }), 200
    
    except Exception as e:
        logging.error(f"Get learning path progress error: {e}")
        return jsonify({'error': 'Failed to fetch progress'}), 500