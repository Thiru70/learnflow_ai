from flask import Blueprint, request, jsonify
from models.feedback import Feedback
from models.resource import Resource
from utils.auth_utils import token_required, validate_json_input
import logging

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')

@feedback_bp.route('', methods=['POST'])
@token_required
@validate_json_input(['resource_id'])
def submit_feedback(current_user, data):
    """Submit feedback for a resource"""
    try:
        logging.info(f"Feedback request data: {data}")
        resource_id = data['resource_id']
        rating = data.get('rating')
        helpful = data.get('helpful')
        comment = data.get('comment', '')
        feedback_type = data.get('feedback_type', 'rating')
        
        # Validate resource exists
        resource = Resource.objects(id=resource_id).first()
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404
        
        # Validate feedback data
        if feedback_type == 'rating' and (not rating or rating < 1 or rating > 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        if feedback_type == 'like' and helpful is None:
            return jsonify({'error': 'Helpful field is required for like feedback'}), 400
        
        # Check if feedback already exists
        existing_feedback = Feedback.objects(user=current_user, resource=resource).first()
        
        if existing_feedback:
            # Update existing feedback
            if rating:
                existing_feedback.rating = rating
            if helpful is not None:
                existing_feedback.helpful = helpful
            if comment:
                existing_feedback.comment = comment
            existing_feedback.feedback_type = feedback_type
            existing_feedback.save()
            feedback = existing_feedback
        else:
            # Create new feedback
            feedback = Feedback(
                user=current_user,
                resource=resource,
                rating=rating,
                helpful=helpful,
                comment=comment,
                feedback_type=feedback_type
            )
            feedback.save()
        
        # Store interaction for ML purposes
        from models.user_interaction import UserInteraction
        from datetime import datetime
        
        interaction_type = 'rated' if rating else 'liked'
        UserInteraction(
            user=current_user,
            resource=resource,
            interaction_type=interaction_type,
            rating=rating,
            helpful=helpful,
            timestamp=datetime.utcnow()
        ).save()
        
        # Create notification for high ratings
        if rating and rating >= 5:
            create_system_notification(
                user=current_user,
                title='Thanks for the 5-star rating! ⭐',
                message=f'Your feedback helps us recommend better content.',
                notification_type='success'
            )
        
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully',
            'data': feedback.to_dict()
        }), 200
    
    except Exception as e:
        logging.error(f"Submit feedback error: {e}")
        return jsonify({'error': 'Failed to submit feedback'}), 500

@feedback_bp.route('/<user_id>', methods=['GET'])
@token_required
def get_user_feedback(current_user, user_id):
    """Get all feedback submitted by a user"""
    try:
        # Ensure user can only access their own feedback
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get query parameters
        feedback_type = request.args.get('type')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = {'user': current_user}
        if feedback_type:
            query['feedback_type'] = feedback_type
        
        # Execute query
        feedback_query = Feedback.objects(**query).order_by('-created_at')
        total_count = feedback_query.count()
        feedback_list = feedback_query.skip(offset).limit(limit)
        
        # Convert to dict and include resource information
        feedback_data = []
        for feedback in feedback_list:
            feedback_dict = feedback.to_dict()
            
            # Add resource information
            if feedback.resource:
                resource_dict = feedback.resource.to_dict()
                feedback_dict['resource'] = {
                    'id': resource_dict['id'],
                    'title': resource_dict['title'],
                    'type': resource_dict['type'],
                    'difficulty': resource_dict['difficulty']
                }
            
            feedback_data.append(feedback_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'feedback': feedback_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Get user feedback error: {e}")
        return jsonify({'error': 'Failed to fetch user feedback'}), 500

@feedback_bp.route('/resource/<resource_id>', methods=['GET'])
@token_required
def get_resource_feedback(current_user, resource_id):
    """Get all feedback for a specific resource"""
    try:
        # Validate resource exists
        resource = Resource.objects(id=resource_id).first()
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404
        
        # Get query parameters
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Get feedback
        feedback_query = Feedback.objects(resource=resource).order_by('-created_at')
        total_count = feedback_query.count()
        feedback_list = feedback_query.skip(offset).limit(limit)
        
        # Convert to dict (exclude user personal info)
        feedback_data = []
        for feedback in feedback_list:
            feedback_dict = {
                'id': str(feedback.id),
                'rating': feedback.rating,
                'helpful': feedback.helpful,
                'comment': feedback.comment,
                'feedback_type': feedback.feedback_type,
                'created_at': feedback.created_at.isoformat() if feedback.created_at else None,
                'user_name': feedback.user.name if feedback.user else 'Anonymous'
            }
            feedback_data.append(feedback_dict)
        
        # Calculate summary statistics
        ratings = [f.rating for f in Feedback.objects(resource=resource, rating__exists=True)]
        likes = Feedback.objects(resource=resource, helpful=True).count()
        
        summary = {
            'total_feedback': total_count,
            'average_rating': sum(ratings) / len(ratings) if ratings else 0,
            'total_ratings': len(ratings),
            'total_likes': likes,
            'rating_distribution': {
                '5': len([r for r in ratings if r == 5]),
                '4': len([r for r in ratings if r == 4]),
                '3': len([r for r in ratings if r == 3]),
                '2': len([r for r in ratings if r == 2]),
                '1': len([r for r in ratings if r == 1])
            }
        }
        
        return jsonify({
            'success': True,
            'data': {
                'feedback': feedback_data,
                'summary': summary,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Get resource feedback error: {e}")
        return jsonify({'error': 'Failed to fetch resource feedback'}), 500

@feedback_bp.route('/<feedback_id>', methods=['DELETE'])
@token_required
def delete_feedback(current_user, feedback_id):
    """Delete user's own feedback"""
    try:
        # Find feedback
        feedback = Feedback.objects(id=feedback_id, user=current_user).first()
        if not feedback:
            return jsonify({'error': 'Feedback not found or access denied'}), 404
        
        # Store resource reference for updating metrics
        resource = feedback.resource
        
        # Delete feedback
        feedback.delete()
        
        # Update resource metrics
        if resource:
            # Recalculate average rating
            all_ratings = Feedback.objects(resource=resource, rating__exists=True)
            if all_ratings:
                total_rating = sum([f.rating for f in all_ratings])
                avg_rating = total_rating / len(all_ratings)
                resource.rating = round(avg_rating, 2)
                resource.rating_count = len(all_ratings)
            else:
                resource.rating = 0.0
                resource.rating_count = 0
            
            # Update likes count
            likes_count = Feedback.objects(resource=resource, helpful=True).count()
            resource.likes = likes_count
            
            resource.save()
        
        return jsonify({
            'success': True,
            'message': 'Feedback deleted successfully'
        }), 200
    
    except Exception as e:
        logging.error(f"Delete feedback error: {e}")
        return jsonify({'error': 'Failed to delete feedback'}), 500

@feedback_bp.route('/stats', methods=['GET'])
@token_required
def get_feedback_stats(current_user):
    """Get user's feedback statistics"""
    try:
        # Get user's feedback counts
        total_feedback = Feedback.objects(user=current_user).count()
        ratings_given = Feedback.objects(user=current_user, rating__exists=True).count()
        likes_given = Feedback.objects(user=current_user, helpful=True).count()
        comments_given = Feedback.objects(user=current_user, comment__ne='').count()
        
        # Get feedback by type
        feedback_by_type = {}
        for feedback_type in ['rating', 'like', 'bookmark', 'comment']:
            count = Feedback.objects(user=current_user, feedback_type=feedback_type).count()
            feedback_by_type[feedback_type] = count
        
        # Get average rating given by user
        user_ratings = [f.rating for f in Feedback.objects(user=current_user, rating__exists=True)]
        avg_rating_given = sum(user_ratings) / len(user_ratings) if user_ratings else 0
        
        stats = {
            'total_feedback': total_feedback,
            'ratings_given': ratings_given,
            'likes_given': likes_given,
            'comments_given': comments_given,
            'average_rating_given': round(avg_rating_given, 2),
            'feedback_by_type': feedback_by_type
        }
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
    
    except Exception as e:
        logging.error(f"Get feedback stats error: {e}")
        return jsonify({'error': 'Failed to fetch feedback statistics'}), 500