#!/usr/bin/env python3
"""
Start the Flask server for testing
"""

from app import create_app

if __name__ == '__main__':
    app = create_app('development')
    print("Starting Flask server...")
    print("Available endpoints:")
    print("- GET /api/tasks/test - Test tasks endpoint")
    print("- GET /api/resources/test - Test resources endpoint") 
    print("- GET /api/learning-path/test - Test learning path endpoint")
    print("\nServer starting on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)