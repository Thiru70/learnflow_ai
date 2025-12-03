from flask import Blueprint, request, jsonify, send_file
from utils.auth_utils import token_required
from services.csv_loader import csv_loader
import logging
import os

data_bp = Blueprint('data', __name__, url_prefix='/api/data')

@data_bp.route('/load-csv', methods=['POST'])
@token_required
def load_data_from_csv(current_user):
    """Load courses and tasks from CSV files"""
    try:
        data = request.get_json() or {}
        load_courses = data.get('load_courses', True)
        load_tasks = data.get('load_tasks', True)
        generate_embeddings = data.get('generate_embeddings', True)
        
        results = {}
        
        # Load courses
        if load_courses:
            courses_loaded = csv_loader.load_courses_from_csv()
            results['courses_loaded'] = courses_loaded
        
        # Load tasks
        if load_tasks:
            tasks_loaded = csv_loader.load_tasks_from_csv()
            results['tasks_loaded'] = tasks_loaded
        
        # Generate embeddings
        if generate_embeddings:
            embeddings_generated = csv_loader.generate_embeddings_for_csv_resources()
            results['embeddings_generated'] = embeddings_generated
        
        return jsonify({
            'success': True,
            'message': 'Data loaded successfully from CSV files',
            'data': results
        }), 200
    
    except Exception as e:
        logging.error(f"Load CSV data error: {e}")
        return jsonify({'error': 'Failed to load data from CSV'}), 500

@data_bp.route('/export-training-data', methods=['POST'])
@token_required
def export_training_data(current_user):
    """Export current data for ML model training"""
    try:
        success = csv_loader.export_training_data()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Training data exported successfully',
                'data': {
                    'export_path': '/api/data/download-exports'
                }
            }), 200
        else:
            return jsonify({'error': 'Failed to export training data'}), 500
    
    except Exception as e:
        logging.error(f"Export training data error: {e}")
        return jsonify({'error': 'Failed to export training data'}), 500

@data_bp.route('/upload-csv', methods=['POST'])
@token_required
def upload_csv_file(current_user):
    """Upload and process CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        file_type = request.form.get('type', 'courses')  # courses, tasks, interactions
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Save uploaded file
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads')
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = os.path.join(data_dir, f"{file_type}_{file.filename}")
        file.save(file_path)
        
        # Process based on file type
        results = {}
        
        if file_type == 'courses':
            results['courses_loaded'] = csv_loader.load_courses_from_csv(file_path)
            results['embeddings_generated'] = csv_loader.generate_embeddings_for_csv_resources()
        elif file_type == 'tasks':
            results['tasks_loaded'] = csv_loader.load_tasks_from_csv(file_path)
        elif file_type == 'interactions':
            results['interactions_loaded'] = len(csv_loader.load_user_interactions_from_csv(file_path))
        
        return jsonify({
            'success': True,
            'message': f'{file_type.capitalize()} CSV uploaded and processed successfully',
            'data': results
        }), 200
    
    except Exception as e:
        logging.error(f"Upload CSV error: {e}")
        return jsonify({'error': 'Failed to upload and process CSV'}), 500

@data_bp.route('/stats', methods=['GET'])
@token_required
def get_data_stats(current_user):
    """Get statistics about loaded data"""
    try:
        from models.resource import Resource
        from models.notification import Task
        from models.user import User
        
        stats = {
            'resources': {
                'total': Resource.objects().count(),
                'with_embeddings': Resource.objects(embedding__exists=True).count(),
                'by_difficulty': {
                    'Beginner': Resource.objects(difficulty='Beginner').count(),
                    'Intermediate': Resource.objects(difficulty='Intermediate').count(),
                    'Advanced': Resource.objects(difficulty='Advanced').count()
                },
                'by_type': {}
            },
            'tasks': {
                'total': Task.objects().count(),
                'by_difficulty': {
                    'Easy': Task.objects(difficulty='Easy').count(),
                    'Medium': Task.objects(difficulty='Medium').count(),
                    'Hard': Task.objects(difficulty='Hard').count()
                }
            },
            'users': {
                'total': User.objects().count(),
                'onboarded': User.objects(is_onboarded=True).count()
            }
        }
        
        # Get resource types
        resource_types = Resource.objects().distinct('type')
        for rtype in resource_types:
            stats['resources']['by_type'][rtype] = Resource.objects(type=rtype).count()
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
    
    except Exception as e:
        logging.error(f"Get data stats error: {e}")
        return jsonify({'error': 'Failed to get data statistics'}), 500

@data_bp.route('/sample-csv/<file_type>', methods=['GET'])
def download_sample_csv(file_type):
    """Download sample CSV templates"""
    try:
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        
        file_mapping = {
            'courses': 'courses.csv',
            'tasks': 'tasks.csv',
            'interactions': 'user_interactions.csv'
        }
        
        if file_type not in file_mapping:
            return jsonify({'error': 'Invalid file type'}), 400
        
        file_path = os.path.join(data_dir, file_mapping[file_type])
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Sample file not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"sample_{file_mapping[file_type]}"
        )
    
    except Exception as e:
        logging.error(f"Download sample CSV error: {e}")
        return jsonify({'error': 'Failed to download sample CSV'}), 500