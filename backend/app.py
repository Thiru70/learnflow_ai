from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config
from utils.db_utils import init_db, create_indexes, seed_sample_data
from services.ml_service import ml_service
import logging
import os

# Import route blueprints
from routes.auth import auth_bp
from routes.user import user_bp
from routes.resources import resources_bp
from routes.learning_path import learning_path_bp
from routes.tasks import tasks_bp
from routes.feedback import feedback_bp
from routes.notifications import notifications_bp
from routes.progress import progress_bp
from routes.data_management import data_bp
from routes.scheduler import scheduler_bp
from routes.courses import courses_bp

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    CORS(app, origins=app.config['CORS_ORIGINS'])
    jwt = JWTManager(app)
    
    # Initialize database
    init_db(app)
    
    # Initialize ML service
    ml_service.initialize(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(learning_path_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(courses_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token is required'}), 401
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'Learning Recommendation System API',
            'version': '1.0.0'
        }), 200
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            'message': 'Learning Recommendation System API',
            'version': '1.0.0',
            'endpoints': {
                'auth': '/api/auth',
                'users': '/api/user',
                'resources': '/api/resources',
                'learning_paths': '/api/learning-path',
                'tasks': '/api/tasks',
                'feedback': '/api/feedback',
                'notifications': '/api/notifications',
                'progress': '/api/progress',
                'data': '/api/data',
                'health': '/api/health'
            }
        }), 200
    
    return app

def setup_logging():
    """Setup application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

if __name__ == '__main__':
    # Setup logging
    setup_logging()
    
    # Create app
    app = create_app()
    
    # Create database indexes and seed data in development
    with app.app_context():
        try:
            create_indexes()
            # Temporarily disabled to use tasks from CSV
            # if app.config['DEBUG']:
            #     seed_sample_data()
            #     logging.info("Sample data seeded for development")
        except Exception as e:
            logging.error(f"Error during startup: {e}")
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=app.config['DEBUG']
    )