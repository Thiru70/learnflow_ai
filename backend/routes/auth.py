from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models.user import User
from utils.auth_utils import validate_json_input
import logging

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/signup', methods=['POST'])
@validate_json_input(['email', 'password', 'name'])
def signup(data):
    """Register a new user"""
    try:
        email = data['email'].lower().strip()
        password = data['password']
        name = data['name'].strip()
        
        # Validation
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        if len(name) < 2:
            return jsonify({'error': 'Name must be at least 2 characters'}), 400
        
        # Check if user already exists
        if User.objects(email=email).first():
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Create new user
        user = User(email=email, name=name)
        user.set_password(password)
        user.save()
        
        # Generate initial recommendations for new user
        try:
            from services.recommendation_service import RecommendationService
            initial_recommendations = RecommendationService.get_cold_start_recommendations(user)
            logging.info(f"Generated {len(initial_recommendations)} initial recommendations for new user")
        except Exception as e:
            logging.error(f"Failed to generate initial recommendations: {e}")
        
        # Generate tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'data': {
                'user': user.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 201
    
    except Exception as e:
        logging.error(f"Signup error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
@validate_json_input(['email', 'password'])
def login(data):
    """Authenticate user and return JWT tokens"""
    try:
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = User.objects(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Generate tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'data': {
                'user': user.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token"""
    try:
        current_user_id = get_jwt_identity()
        user = User.objects(id=current_user_id).first()
        
        if not user or not user.is_active:
            return jsonify({'error': 'Invalid user'}), 401
        
        # Generate new access token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'data': {
                'access_token': access_token
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Token refresh error: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500

@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if the current token is valid"""
    try:
        current_user_id = get_jwt_identity()
        user = User.objects(id=current_user_id).first()
        
        if not user or not user.is_active:
            return jsonify({'error': 'Invalid user'}), 401
        
        return jsonify({
            'success': True,
            'data': {
                'user': user.to_dict()
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Token verification error: {e}")
        return jsonify({'error': 'Token verification failed'}), 500