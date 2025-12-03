from flask import Blueprint, request, jsonify
from models.user import User
from models.learning_path import LearningPath, LearningPathStep
from utils.auth_utils import token_required
from services.ml_service import ml_service
import logging

progress_bp = Blueprint('progress', __name__, url_prefix='/api/progress')

@progress_bp.route('/prediction/<user_id>', methods=['GET'])
@token_required
def get_progress_prediction(current_user, user_id):
    """Get ML-based progress prediction for user"""
    try:
        # Ensure user can only access their own prediction
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Prepare user data for ML prediction
        user_data = {
            'user_id': str(current_user.id),
            'skill_level': current_user.skill_level,
            'interests': current_user.interests or [],
            'learning_goal': current_user.learning_goal,
            'goal_timeline': current_user.goal_timeline,
            'interactions': current_user.interactions or {},
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None
        }
        
        # Get learning path progress
        learning_path = LearningPath.objects(user=current_user).first()
        if learning_path:
            user_data['learning_path_progress'] = {
                'total_steps': learning_path.total_steps,
                'completed_steps': learning_path.completed_steps,
                'progress_percentage': learning_path.progress_percentage
            }
        
        # Get recent activity
        recent_steps = LearningPathStep.objects(user=current_user).order_by('-updated_at').limit(10)
        user_data['recent_activity'] = [
            {
                'step_id': step.step_id,
                'completed': step.completed,
                'updated_at': step.updated_at.isoformat() if step.updated_at else None
            }
            for step in recent_steps
        ]
        
        # Get prediction from ML service
        prediction = ml_service.predict_progress(user_data)
        
        return jsonify({
            'success': True,
            'data': prediction
        }), 200
    
    except Exception as e:
        logging.error(f"Get progress prediction error: {e}")
        return jsonify({'error': 'Failed to get progress prediction'}), 500

@progress_bp.route('/stats/<user_id>', methods=['GET'])
@token_required
def get_progress_stats(current_user, user_id):
    """Get detailed progress statistics"""
    try:
        # Ensure user can only access their own stats
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Calculate learning statistics
        interactions = current_user.interactions or {}
        
        # Resource interaction stats
        total_resources = len(interactions)
        completed_resources = len([i for i in interactions.values() if i.get('status') == 'completed'])
        in_progress_resources = len([i for i in interactions.values() if i.get('status') == 'in-progress'])
        bookmarked_resources = len([i for i in interactions.values() if i.get('status') == 'bookmarked'])
        
        # Learning path stats
        learning_path = LearningPath.objects(user=current_user).first()
        path_stats = {}
        if learning_path:
            path_stats = {
                'total_steps': learning_path.total_steps,
                'completed_steps': learning_path.completed_steps,
                'progress_percentage': learning_path.progress_percentage,
                'last_accessed': learning_path.last_accessed.isoformat() if learning_path.last_accessed else None
            }
        
        # Calculate streak (mock implementation - you'd track daily activity)
        current_streak = 5  # This should be calculated from actual daily activity
        
        # Weekly activity (mock data - replace with real calculations)
        weekly_activity = [
            {'day': 'Mon', 'hours': 2.5, 'resources': 3},
            {'day': 'Tue', 'hours': 3.0, 'resources': 4},
            {'day': 'Wed', 'hours': 1.5, 'resources': 2},
            {'day': 'Thu', 'hours': 4.0, 'resources': 5},
            {'day': 'Fri', 'hours': 2.0, 'resources': 3},
            {'day': 'Sat', 'hours': 0, 'resources': 0},
            {'day': 'Sun', 'hours': 1.5, 'resources': 2}
        ]
        
        # Topic progress based on user interests and completed resources
        topic_progress = []
        if current_user.interests:
            for interest in current_user.interests:
                # Calculate progress for each interest (simplified)
                progress = min(completed_resources * 10, 100)  # Mock calculation
                topic_progress.append({
                    'topic': interest,
                    'progress': progress
                })
        
        stats = {
            'total_hours_learned': sum([day['hours'] for day in weekly_activity]),
            'modules_completed': completed_resources,
            'current_streak': current_streak,
            'total_resources': total_resources,
            'completed_resources': completed_resources,
            'in_progress_resources': in_progress_resources,
            'bookmarked_resources': bookmarked_resources,
            'learning_path': path_stats,
            'weekly_activity': weekly_activity,
            'topic_progress': topic_progress,
            'completion_rate': (completed_resources / total_resources * 100) if total_resources > 0 else 0
        }
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
    
    except Exception as e:
        logging.error(f"Get progress stats error: {e}")
        return jsonify({'error': 'Failed to get progress statistics'}), 500

@progress_bp.route('/analytics/<user_id>', methods=['GET'])
@token_required
def get_learning_analytics(current_user, user_id):
    """Get advanced learning analytics"""
    try:
        # Ensure user can only access their own analytics
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Time-based analytics
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Learning velocity (resources completed per week)
        interactions = current_user.interactions or {}
        recent_completions = 0
        for interaction in interactions.values():
            if interaction.get('status') == 'completed' and interaction.get('completed_at'):
                # In a real implementation, you'd parse the date and check if it's within the week
                recent_completions += 1
        
        learning_velocity = recent_completions  # Simplified
        
        # Difficulty progression
        difficulty_progression = {
            'Beginner': 0,
            'Intermediate': 0,
            'Advanced': 0
        }
        
        # This would be calculated from actual completed resources
        # For now, using mock data
        if current_user.skill_level == 'Beginner':
            difficulty_progression = {'Beginner': 80, 'Intermediate': 15, 'Advanced': 5}
        elif current_user.skill_level == 'Intermediate':
            difficulty_progression = {'Beginner': 40, 'Intermediate': 50, 'Advanced': 10}
        else:
            difficulty_progression = {'Beginner': 20, 'Intermediate': 40, 'Advanced': 40}
        
        # Learning patterns
        learning_patterns = {
            'preferred_time': 'Evening',  # Would be calculated from activity timestamps
            'session_length': '45 minutes',  # Average session duration
            'learning_days': ['Monday', 'Tuesday', 'Thursday', 'Friday'],  # Most active days
            'content_preference': 'Video',  # Most consumed content type
        }
        
        # Goal progress
        goal_progress = {
            'goal': current_user.learning_goal,
            'timeline': current_user.goal_timeline,
            'estimated_completion': '2024-06-15',  # ML prediction
            'on_track': True,
            'days_remaining': 45
        }
        
        analytics = {
            'learning_velocity': learning_velocity,
            'difficulty_progression': difficulty_progression,
            'learning_patterns': learning_patterns,
            'goal_progress': goal_progress,
            'engagement_score': 85,  # Overall engagement score (0-100)
            'knowledge_retention': 78,  # Estimated retention rate
            'recommendation_accuracy': 92  # How often user engages with recommendations
        }
        
        return jsonify({
            'success': True,
            'data': analytics
        }), 200
    
    except Exception as e:
        logging.error(f"Get learning analytics error: {e}")
        return jsonify({'error': 'Failed to get learning analytics'}), 500