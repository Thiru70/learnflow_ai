from flask import Blueprint, request, jsonify
from models.notification import Notification
from utils.auth_utils import token_required
from datetime import datetime, timedelta
import logging

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notifications_bp.route('/<user_id>', methods=['GET'])
@token_required
def get_notifications(current_user, user_id):
    """Get user notifications"""
    try:
        # Ensure user can only access their own notifications
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get query parameters
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        notification_type = request.args.get('type')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = {'user': current_user}
        
        if unread_only:
            query['read'] = False
        
        if notification_type:
            query['notification_type'] = notification_type
        
        # Execute query
        notifications_query = Notification.objects(**query).order_by('-created_at')
        total_count = notifications_query.count()
        notifications = notifications_query.skip(offset).limit(limit)
        
        # Convert to dict
        notifications_data = [notification.to_dict() for notification in notifications]
        
        # Get unread count
        unread_count = Notification.objects(user=current_user, read=False).count()
        
        return jsonify({
            'success': True,
            'data': {
                'notifications': notifications_data,
                'unread_count': unread_count,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Get notifications error: {e}")
        return jsonify({'error': 'Failed to fetch notifications'}), 500

@notifications_bp.route('/<notification_id>/read', methods=['POST', 'PUT'])
@token_required
def mark_notification_read(current_user, notification_id):
    """Mark a notification as read"""
    try:
        # Find notification
        notification = Notification.objects(id=notification_id, user=current_user).first()
        if not notification:
            return jsonify({'error': 'Notification not found or access denied'}), 404
        
        # Mark as read
        notification.mark_as_read()
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read',
            'data': notification.to_dict()
        }), 200
    
    except Exception as e:
        logging.error(f"Mark notification read error: {e}")
        return jsonify({'error': 'Failed to mark notification as read'}), 500

@notifications_bp.route('/<user_id>/mark-all-read', methods=['POST'])
@token_required
def mark_all_notifications_read(current_user, user_id):
    """Mark all notifications as read for a user"""
    try:
        # Ensure user can only mark their own notifications
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update all unread notifications
        unread_notifications = Notification.objects(user=current_user, read=False)
        count = unread_notifications.count()
        
        for notification in unread_notifications:
            notification.mark_as_read()
        
        return jsonify({
            'success': True,
            'message': f'Marked {count} notifications as read'
        }), 200
    
    except Exception as e:
        logging.error(f"Mark all notifications read error: {e}")
        return jsonify({'error': 'Failed to mark all notifications as read'}), 500

@notifications_bp.route('/<user_id>/create', methods=['POST'])
@token_required
def create_notification(current_user, user_id):
    """Create a new notification (admin or system use)"""
    try:
        # Ensure user can only create notifications for themselves (or add admin check)
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['title', 'message', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create notification
        notification = Notification(
            user=current_user,
            title=data['title'],
            message=data['message'],
            notification_type=data['type'],
            action_url=data.get('action_url'),
            action_data=data.get('action_data', {}),
            priority=data.get('priority', 'medium'),
            scheduled_for=data.get('scheduled_for')
        )
        notification.save()
        
        return jsonify({
            'success': True,
            'message': 'Notification created successfully',
            'data': notification.to_dict()
        }), 201
    
    except Exception as e:
        logging.error(f"Create notification error: {e}")
        return jsonify({'error': 'Failed to create notification'}), 500

@notifications_bp.route('/<notification_id>', methods=['DELETE'])
@token_required
def delete_notification(current_user, notification_id):
    """Delete a notification"""
    try:
        # Find notification
        notification = Notification.objects(id=notification_id, user=current_user).first()
        if not notification:
            return jsonify({'error': 'Notification not found or access denied'}), 404
        
        # Delete notification
        notification.delete()
        
        return jsonify({
            'success': True,
            'message': 'Notification deleted successfully'
        }), 200
    
    except Exception as e:
        logging.error(f"Delete notification error: {e}")
        return jsonify({'error': 'Failed to delete notification'}), 500

@notifications_bp.route('/<user_id>/stats', methods=['GET'])
@token_required
def get_notification_stats(current_user, user_id):
    """Get notification statistics for a user"""
    try:
        # Ensure user can only access their own stats
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get counts by type
        total_notifications = Notification.objects(user=current_user).count()
        unread_notifications = Notification.objects(user=current_user, read=False).count()
        
        # Get counts by notification type
        type_counts = {}
        for notif_type in ['reminder', 'success', 'warning', 'info', 'achievement']:
            count = Notification.objects(user=current_user, notification_type=notif_type).count()
            type_counts[notif_type] = count
        
        # Get recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_notifications = Notification.objects(
            user=current_user,
            created_at__gte=week_ago
        ).count()
        
        stats = {
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'read_notifications': total_notifications - unread_notifications,
            'recent_notifications': recent_notifications,
            'notifications_by_type': type_counts
        }
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
    
    except Exception as e:
        logging.error(f"Get notification stats error: {e}")
        return jsonify({'error': 'Failed to fetch notification statistics'}), 500

def create_system_notification(user, title, message, notification_type='info', action_url=None, priority='medium'):
    """Helper function to create system notifications"""
    try:
        notification = Notification(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url,
            priority=priority
        )
        notification.save()
        return notification
    except Exception as e:
        logging.error(f"Error creating system notification: {e}")
        return None

def create_learning_reminders(user):
    """Create learning reminder notifications"""
    try:
        # Check user's last activity
        interactions = user.interactions or {}
        
        if not interactions:
            # New user reminder
            create_system_notification(
                user=user,
                title="Welcome to Learning!",
                message="Start your learning journey by exploring recommended resources.",
                notification_type='info',
                action_url='/recommendations'
            )
        else:
            # Check for inactive users (no activity in 3 days)
            # This would require tracking last activity timestamp
            create_system_notification(
                user=user,
                title="Keep Learning!",
                message="You haven't practiced in a while. Quick refresher?",
                notification_type='reminder',
                action_url='/tasks'
            )
    
    except Exception as e:
        logging.error(f"Error creating learning reminders: {e}")

def create_progress_notifications(user, progress_data):
    """Create progress-based notifications"""
    try:
        if progress_data.get('status') == 'on-track':
            create_system_notification(
                user=user,
                title="Great Progress!",
                message="You're on track with your learning goals. Keep it up!",
                notification_type='success'
            )
        elif progress_data.get('status') == 'at-risk':
            create_system_notification(
                user=user,
                title="Attention Needed",
                message="You might fall behind on your goals. Consider dedicating more time this week.",
                notification_type='warning',
                action_url='/learning-path'
            )
        elif progress_data.get('status') == 'behind':
            create_system_notification(
                user=user,
                title="Let's Get Back on Track",
                message="You're behind schedule. We've prepared some easier tasks to help you catch up.",
                notification_type='warning',
                action_url='/tasks'
            )
    
    except Exception as e:
        logging.error(f"Error creating progress notifications: {e}")