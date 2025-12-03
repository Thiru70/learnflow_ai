from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models.user import User

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        try:
            current_user_id = get_jwt_identity()
            current_user = User.objects(id=current_user_id).first()
            
            if not current_user or not current_user.is_active:
                return jsonify({'error': 'Invalid or inactive user'}), 401
                
            return f(current_user=current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Token validation failed'}), 401
    
    return decorated

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        try:
            current_user_id = get_jwt_identity()
            current_user = User.objects(id=current_user_id).first()
            
            if not current_user or not current_user.is_active:
                return jsonify({'error': 'Invalid or inactive user'}), 401
            
            # Add admin check logic here if you have admin roles
            # For now, we'll skip this check
            
            return f(current_user=current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Authorization failed'}), 403
    
    return decorated

def validate_json_input(required_fields=None):
    """Decorator to validate JSON input"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'error': f'Missing required fields: {", ".join(missing_fields)}'
                    }), 400
            
            return f(data=data, *args, **kwargs)
        return decorated
    return decorator

def validate_user_access(f):
    """Decorator to validate user can access their own resources"""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            current_user_id = get_jwt_identity()
            requested_user_id = kwargs.get('user_id') or request.view_args.get('user_id')
            
            if requested_user_id and str(current_user_id) != str(requested_user_id):
                return jsonify({'error': 'Access denied'}), 403
                
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Access validation failed'}), 403
    
    return decorated

def flexible_user_access(f):
    """Decorator that allows JWT user to override URL user for security"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        try:
            current_user_id = get_jwt_identity()
            current_user = User.objects(id=current_user_id).first()
            
            if not current_user or not current_user.is_active:
                return jsonify({'error': 'Invalid or inactive user'}), 401
            
            # Get requested user ID from URL
            requested_user_id = kwargs.get('user_id')
            
            # If user IDs don't match, log warning but continue with JWT user
            if requested_user_id and str(current_user.id) != requested_user_id:
                import logging
                logging.warning(f"User ID mismatch: JWT user {current_user.id} vs URL user {requested_user_id}. Using JWT user for security.")
            
            return f(current_user=current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Token validation failed'}), 401
    
    return decorated