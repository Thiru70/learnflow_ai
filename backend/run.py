#!/usr/bin/env python3
"""
Learning Recommendation System Backend
Production-ready Flask application startup script
"""

import os
import sys
import logging
from app import create_app, setup_logging
from utils.db_utils import create_indexes, seed_sample_data
from services.ml_service import ml_service

def main():
    """Main application entry point"""
    
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Get environment
        env = os.environ.get('FLASK_ENV', 'development')
        logger.info(f"Starting Learning Recommendation System API in {env} mode")
        
        # Create Flask app
        app = create_app(env)
        
        # Initialize database in app context
        with app.app_context():
            logger.info("Initializing database...")
            create_indexes()
            
            # Seed sample data in development
            if app.config['DEBUG']:
                logger.info("Seeding sample data for development...")
                seed_sample_data()
                
                # Load ML data from CSV files
                logger.info("Loading ML data from CSV files...")
                from services.csv_loader import csv_loader
                ml_service.initialize(app)
                csv_loader.load_courses_from_csv()
                csv_loader.load_tasks_from_csv()
                csv_loader.generate_embeddings_for_csv_resources()
        
        # Get port from environment
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        
        logger.info(f"Starting server on {host}:{port}")
        
        # Run the application
        if env == 'production':
            # In production, use a proper WSGI server like Gunicorn
            logger.warning("Running with Flask development server. Use Gunicorn in production!")
        
        app.run(
            host=host,
            port=port,
            debug=app.config['DEBUG'],
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()