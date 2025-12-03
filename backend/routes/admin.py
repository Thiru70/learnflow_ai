from flask import Blueprint, request, jsonify
from utils.auth_utils import token_required, admin_required
from services.ml_training_service import generate_embeddings_for_new_resources, retrain_recommendation_model
from models.resource import Resource
from models.notification import Task
from models.user import User
from models.feedback import TaskFeedback
import logging

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/ml/generate-embeddings', methods=['POST'])
@token_required
@admin_required
def trigger_embedding_generation(current_user):
    """Manually trigger embedding generation"""
    try:
        # Trigger background task
        task = generate_embeddings_for_new_resources.delay()
        
        return jsonify({
            'success': True,
            'message': 'Embedding generation started',
            'task_id': task.id
        }), 200
    
    except Exception as e:
        logging.error(f"Error triggering embedding generation: {e}")
        return jsonify({'error': 'Failed to start embedding generation'}), 500

@admin_bp.route('/ml/retrain-models', methods=['POST'])
@token_required
@admin_required
def trigger_model_retraining(current_user):
    """Manually trigger model retraining"""
    try:
        # Trigger background task
        task = retrain_recommendation_model.delay()
        
        return jsonify({
            'success': True,
            'message': 'Model retraining started',
            'task_id': task.id
        }), 200
    
    except Exception as e:
        logging.error(f"Error triggering model retraining: {e}")
        return jsonify({'error': 'Failed to start model retraining'}), 500

@admin_bp.route('/ml/status', methods=['GET'])
@token_required
@admin_required
def get_ml_status(current_user):
    """Get ML system status"""
    try:
        # Get statistics
        total_resources = Resource.objects().count()
        resources_with_embeddings = Resource.objects(embedding__exists=True).count()
        total_users = User.objects(is_active=True).count()
        total_feedback = TaskFeedback.objects().count()
        
        return jsonify({
            'success': True,
            'data': {
                'resources': {
                    'total': total_resources,
                    'with_embeddings': resources_with_embeddings,
                    'embedding_coverage': (resources_with_embeddings / total_resources * 100) if total_resources > 0 else 0
                },
                'users': {
                    'total': total_users,
                    'with_feedback': TaskFeedback.objects().distinct('user').count()
                },
                'feedback': {
                    'total': total_feedback,
                    'recent_24h': TaskFeedback.objects(created_at__gte=datetime.utcnow() - timedelta(days=1)).count()
                }
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting ML status: {e}")
        return jsonify({'error': 'Failed to get ML status'}), 500