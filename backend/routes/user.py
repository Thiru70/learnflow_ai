from flask import Blueprint, request, jsonify
from models.user import User
from models.learning_path import LearningPath, LearningPathStep
from models.resource import Resource
from utils.auth_utils import token_required, validate_json_input
from services.ml_service import ml_service
from datetime import datetime
import logging

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

@user_bp.route('/<user_id>', methods=['GET'])
@token_required
def get_user_profile(current_user, user_id):
    """Get user profile"""
    try:
        # Ensure user can only access their own profile
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'data': current_user.to_dict()
        }), 200
    
    except Exception as e:
        logging.error(f"Get user profile error: {e}")
        return jsonify({'error': 'Failed to fetch user profile'}), 500

@user_bp.route('/<user_id>', methods=['PUT'])
@token_required
@validate_json_input()
def update_user_profile(current_user, user_id, data):
    """Update user profile and complete onboarding"""
    try:
        # Ensure user can only update their own profile
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update allowed fields
        allowed_fields = ['name', 'interests', 'skill_level', 'learning_goal', 'goal_timeline']
        updated_fields = []
        
        for field in allowed_fields:
            if field in data:
                setattr(current_user, field, data[field])
                updated_fields.append(field)
        
        # Mark as onboarded if required fields are present
        if all(field in data for field in ['interests', 'skill_level', 'learning_goal', 'goal_timeline']):
            current_user.is_onboarded = True
            updated_fields.append('is_onboarded')
            
            # Generate initial recommendations after onboarding
            try:
                from services.recommendation_service import RecommendationService
                initial_recommendations = RecommendationService.get_personalized_recommendations(current_user)
                logging.info(f"Generated {len(initial_recommendations)} recommendations after onboarding")
            except Exception as e:
                logging.error(f"Failed to generate recommendations after onboarding: {e}")
            
            # Generate learning path after onboarding
            try:
                learning_path_data = ml_service.generate_learning_path({
                    'user_id': str(current_user.id),
                    'interests': current_user.interests,
                    'skill_level': current_user.skill_level,
                    'learning_goal': current_user.learning_goal,
                    'goal_timeline': current_user.goal_timeline
                })
                
                # Create or update learning path
                learning_path = LearningPath.objects(user=current_user).first()
                if not learning_path:
                    learning_path = LearningPath(user=current_user)
                    learning_path.save()
                
                # Create learning path steps
                for step_data in learning_path_data:
                    # Find matching resource (you might need to create resources first)
                    resource = Resource.objects().first()  # Placeholder - implement proper matching
                    
                    if resource:
                        step = LearningPathStep(
                            user=current_user,
                            resource=resource,
                            step_id=step_data['step_id'],
                            title=step_data['title'],
                            description=step_data['description'],
                            order=step_data['order'],
                            dependencies=step_data.get('dependencies', [])
                        )
                        step.save()
                
                learning_path.update_progress()
                
            except Exception as e:
                logging.error(f"Error generating learning path: {e}")
        
        current_user.save()
        
        return jsonify({
            'success': True,
            'message': f'Profile updated: {", ".join(updated_fields)}',
            'data': current_user.to_dict()
        }), 200
    
    except Exception as e:
        logging.error(f"Update user profile error: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500

@user_bp.route('/<user_id>/interactions', methods=['POST'])
@token_required
@validate_json_input(['resource_id', 'status'])
def update_user_interaction(current_user, user_id, data):
    """Update user interaction with a resource"""
    try:
        logging.info(f"User interaction request data: {data}")
        # Ensure user can only update their own interactions
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        resource_id = data['resource_id']
        status = data['status']
        
        # Validate status
        valid_statuses = ['viewed', 'in-progress', 'completed', 'bookmarked']
        if status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400
        
        # Update interactions
        if not current_user.interactions:
            current_user.interactions = {}
        
        if resource_id not in current_user.interactions:
            current_user.interactions[resource_id] = {}
        
        current_user.interactions[resource_id]['status'] = status
        
        if status == 'viewed':
            current_user.interactions[resource_id]['viewed_at'] = data.get('viewed_at')
        elif status == 'completed':
            current_user.interactions[resource_id]['completed_at'] = data.get('completed_at')
        
        current_user.save()
        
        # Update last activity timestamp
        current_user.last_activity = datetime.utcnow()
        current_user.save()
        
        # Store interaction for ML purposes
        from models.user_interaction import UserInteraction
        from models.resource import Resource
        from routes.notifications import create_system_notification
        
        resource = Resource.objects(id=resource_id).first()
        if resource:
            UserInteraction(
                user=current_user,
                resource=resource,
                interaction_type=status,
                timestamp=datetime.utcnow(),
                completion_time_minutes=data.get('completion_time_minutes')
            ).save()
            
            # Create notifications based on status
            if status == 'completed':
                create_system_notification(
                    user=current_user,
                    title='Course Completed! 🎉',
                    message=f'Congratulations! You completed "{resource.title}".',
                    notification_type='success',
                    action_url='/profile'
                )
            elif status == 'in-progress':
                create_system_notification(
                    user=current_user,
                    title='Learning Started! 📚',
                    message=f'You started learning "{resource.title}". Keep it up!',
                    notification_type='info',
                    action_url='/dashboard'
                )
        
        # Update learning path progress if applicable
        try:
            learning_path = LearningPath.objects(user=current_user).first()
            if learning_path:
                learning_path.update_progress()
        except Exception as e:
            logging.error(f"Error updating learning path progress: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Interaction updated successfully',
            'data': {
                'resource_id': resource_id,
                'status': status
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Update interaction error: {e}")
        return jsonify({'error': 'Failed to update interaction'}), 500

@user_bp.route('/<user_id>/bookmarks', methods=['GET'])
@token_required
def get_user_bookmarks(current_user, user_id):
    """Get user's bookmarked resources"""
    try:
        # Ensure user can only access their own bookmarks
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get bookmarked resource IDs from user interactions
        interactions = current_user.interactions or {}
        logging.info(f"Debug: All user interactions: {interactions}")
        
        # Check both old and new bookmark formats
        bookmarked_ids = []
        for resource_id, interaction in interactions.items():
            is_bookmarked = interaction.get('bookmarked', False) or interaction.get('status') == 'bookmarked'
            if is_bookmarked:
                bookmarked_ids.append(resource_id)
        
        logging.info(f"User {user_id} has {len(bookmarked_ids)} bookmarked resources: {bookmarked_ids}")
        
        # Fetch actual resources
        bookmarked_resources = []
        for resource_id in bookmarked_ids:
            try:
                # Try to find resource by ObjectId
                from bson import ObjectId
                try:
                    # First try as ObjectId
                    resource = Resource.objects(id=ObjectId(resource_id)).first()
                except:
                    # If that fails, try as string
                    resource = Resource.objects(id=resource_id).first()
                
                if resource:
                    resource_dict = resource.to_dict()
                    resource_dict['is_bookmarked'] = True
                    
                    # Get the interaction status
                    interaction = interactions[resource_id]
                    resource_dict['user_status'] = interaction.get('status')
                    bookmarked_resources.append(resource_dict)
                    logging.info(f"Found bookmarked resource: {resource.title} with status: {interaction.get('status')}")
                else:
                    logging.warning(f"Resource not found for ID: {resource_id}")
            except Exception as e:
                logging.error(f"Failed to fetch bookmarked resource {resource_id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'data': bookmarked_resources
        }), 200
    
    except Exception as e:
        logging.error(f"Get user bookmarks error: {e}")
        return jsonify({'error': 'Failed to fetch bookmarks'}), 500

@user_bp.route('/<user_id>/stats', methods=['GET'])
@token_required
def get_user_stats(current_user, user_id):
    """Get user learning statistics"""
    try:
        # Ensure user can only access their own stats
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Calculate stats from interactions
        interactions = current_user.interactions or {}
        
        total_resources = len(interactions)
        completed_resources = len([i for i in interactions.values() if i.get('status') == 'completed'])
        in_progress_resources = len([i for i in interactions.values() if i.get('status') == 'in-progress'])
        
        # Calculate total hours learned from completed resources
        total_hours = 0
        for resource_id, interaction in interactions.items():
            if interaction.get('status') == 'completed':
                try:
                    resource = Resource.objects(id=resource_id).first()
                    if resource and resource.duration:
                        # Extract hours from duration string (e.g., "2.5 hours" -> 2.5)
                        duration_str = resource.duration.lower().replace('hours', '').replace('hour', '').strip()
                        hours = float(duration_str)
                        total_hours += hours
                except (ValueError, AttributeError):
                    # Default to 1 hour if duration parsing fails
                    total_hours += 1.0
        
        # Calculate current streak from daily activity
        from datetime import datetime, timedelta
        import pytz
        
        current_streak = 0
        today = datetime.now(pytz.UTC).date()
        
        # Check consecutive days with activity (completed resources)
        check_date = today
        while True:
            has_activity = False
            for interaction in interactions.values():
                completed_at = interaction.get('completed_at')
                if completed_at:
                    try:
                        if isinstance(completed_at, str):
                            completed_date = datetime.fromisoformat(completed_at.replace('Z', '+00:00')).date()
                        else:
                            completed_date = completed_at.date()
                        
                        if completed_date == check_date:
                            has_activity = True
                            break
                    except (ValueError, AttributeError):
                        continue
            
            if has_activity:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
            
            # Limit streak calculation to avoid infinite loops
            if current_streak > 365:
                break
        
        stats = {
            'total_hours_learned': round(total_hours, 1),
            'modules_completed': completed_resources,
            'current_streak': current_streak,
            'total_resources': total_resources,
            'in_progress_resources': in_progress_resources,
            'weekly_activity': [
                {'day': 'Mon', 'hours': 2.5},
                {'day': 'Tue', 'hours': 3.0},
                {'day': 'Wed', 'hours': 1.5},
                {'day': 'Thu', 'hours': 4.0},
                {'day': 'Fri', 'hours': 2.0},
                {'day': 'Sat', 'hours': 0},
                {'day': 'Sun', 'hours': 1.5}
            ],
            'topic_progress': [
                {'topic': 'Python', 'progress': 80},
                {'topic': 'Machine Learning', 'progress': 65},
                {'topic': 'Data Structures', 'progress': 45}
            ]
        }
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
    
    except Exception as e:
        logging.error(f"Get user stats error: {e}")
        return jsonify({'error': 'Failed to fetch user statistics'}), 500