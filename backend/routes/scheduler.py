from flask import Blueprint, jsonify
from services.notification_service import check_user_inactivity, check_incomplete_courses, send_progress_reminders
from utils.auth_utils import token_required
import logging

scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/api/scheduler')

@scheduler_bp.route('/check-inactivity', methods=['POST'])
def trigger_inactivity_check():
    """Manually trigger inactivity check (for testing)"""
    try:
        check_user_inactivity()
        check_incomplete_courses()
        send_progress_reminders()
        
        return jsonify({
            'success': True,
            'message': 'Inactivity check completed'
        }), 200
        
    except Exception as e:
        logging.error(f"Inactivity check error: {e}")
        return jsonify({'error': 'Failed to check inactivity'}), 500