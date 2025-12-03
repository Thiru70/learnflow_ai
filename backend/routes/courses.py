from flask import Blueprint, request, jsonify
from models.course import Course, CourseCompletion
from utils.auth_utils import token_required, validate_json_input
import logging
from datetime import datetime

courses_bp = Blueprint('courses', __name__, url_prefix='/api/courses')

@courses_bp.route('', methods=['GET'])
def get_courses():
    """Get all available courses with optional filtering"""
    try:
        # Get query parameters
        category = request.args.get('category')
        difficulty = request.args.get('difficulty')
        limit = int(request.args.get('limit', 20))
        
        # Build query
        query = {'is_active': True}
        if category:
            query['category'] = category
        if difficulty:
            query['difficulty'] = difficulty
        
        courses = Course.objects(**query).limit(limit)
        courses_data = [course.to_dict() for course in courses]
        
        return jsonify({
            'success': True,
            'data': courses_data,
            'total': Course.objects(**query).count()
        }), 200
        
    except Exception as e:
        logging.error(f"Get courses error: {e}")
        return jsonify({'error': 'Failed to fetch courses'}), 500

@courses_bp.route('/<course_id>', methods=['GET'])
def get_course_details(course_id):
    """Get detailed information about a specific course"""
    try:
        course = Course.objects(course_id=course_id, is_active=True).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        return jsonify({
            'success': True,
            'data': course.to_dict()
        }), 200
        
    except Exception as e:
        logging.error(f"Get course details error: {e}")
        return jsonify({'error': 'Failed to fetch course details'}), 500

@courses_bp.route('/<user_id>/enrolled', methods=['GET'])
@token_required
def get_user_courses(current_user, user_id):
    """Get user's enrolled courses with completion status"""
    try:
        # Ensure user can only access their own courses
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get user's course completions
        completions = CourseCompletion.objects(user=user_id)
        
        courses_data = []
        for completion in completions:
            course = Course.objects(course_id=completion.course_id, is_active=True).first()
            if course:
                course_dict = course.to_dict()
                course_dict['completion'] = completion.to_dict()
                courses_data.append(course_dict)
        
        return jsonify({
            'success': True,
            'data': courses_data,
            'total': len(courses_data)
        }), 200
        
    except Exception as e:
        logging.error(f"Get user courses error: {e}")
        return jsonify({'error': 'Failed to fetch user courses'}), 500

@courses_bp.route('/<user_id>/enroll', methods=['POST'])
@token_required
@validate_json_input(['course_id'])
def enroll_course(current_user, user_id, data):
    """Enroll user in a course"""
    try:
        # Ensure user can only enroll themselves
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        course_id = data['course_id']
        
        # Check if course exists
        course = Course.objects(course_id=course_id, is_active=True).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if already enrolled
        existing_completion = CourseCompletion.objects(user=user_id, course_id=course_id).first()
        if existing_completion:
            return jsonify({'error': 'Already enrolled in this course'}), 400
        
        # Create course completion record
        completion = CourseCompletion(
            user=user_id,
            course_id=course_id,
            status='not_started',
            started_at=datetime.utcnow()
        )
        completion.save()
        
        return jsonify({
            'success': True,
            'message': 'Successfully enrolled in course',
            'data': completion.to_dict()
        }), 201
        
    except Exception as e:
        logging.error(f"Enroll course error: {e}")
        return jsonify({'error': 'Failed to enroll in course'}), 500

@courses_bp.route('/<user_id>/progress', methods=['POST'])
@token_required
@validate_json_input(['course_id', 'progress_percentage'])
def update_course_progress(current_user, user_id, data):
    """Update user's progress in a course"""
    try:
        # Ensure user can only update their own progress
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        course_id = data['course_id']
        progress = int(data['progress_percentage'])
        
        if progress < 0 or progress > 100:
            return jsonify({'error': 'Progress must be between 0 and 100'}), 400
        
        # Find course completion record
        completion = CourseCompletion.objects(user=user_id, course_id=course_id).first()
        if not completion:
            return jsonify({'error': 'Not enrolled in this course'}), 404
        
        # Update progress
        completion.progress_percentage = progress
        completion.last_accessed = datetime.utcnow()
        
        # Update status based on progress
        if progress == 0:
            completion.status = 'not_started'
        elif progress == 100:
            completion.status = 'completed'
            if not completion.completed_at:
                completion.completed_at = datetime.utcnow()
        else:
            completion.status = 'in_progress'
            if not completion.started_at:
                completion.started_at = datetime.utcnow()
        
        completion.updated_at = datetime.utcnow()
        completion.save()
        
        return jsonify({
            'success': True,
            'message': 'Progress updated successfully',
            'data': completion.to_dict()
        }), 200
        
    except Exception as e:
        logging.error(f"Update course progress error: {e}")
        return jsonify({'error': 'Failed to update progress'}), 500

@courses_bp.route('/<user_id>/complete', methods=['POST'])
@token_required
@validate_json_input(['course_id'])
def complete_course(current_user, user_id, data):
    """Mark course as completed and optionally add rating/review"""
    try:
        # Ensure user can only complete their own courses
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        course_id = data['course_id']
        rating = data.get('rating')
        review = data.get('review', '')
        
        # Find course completion record
        completion = CourseCompletion.objects(user=user_id, course_id=course_id).first()
        if not completion:
            return jsonify({'error': 'Not enrolled in this course'}), 404
        
        # Update completion
        completion.status = 'completed'
        completion.progress_percentage = 100
        completion.completed_at = datetime.utcnow()
        completion.last_accessed = datetime.utcnow()
        
        if rating and 1 <= rating <= 5:
            completion.rating = rating
        if review:
            completion.review = review
        
        completion.updated_at = datetime.utcnow()
        completion.save()
        
        return jsonify({
            'success': True,
            'message': 'Course completed successfully',
            'data': completion.to_dict()
        }), 200
        
    except Exception as e:
        logging.error(f"Complete course error: {e}")
        return jsonify({'error': 'Failed to complete course'}), 500

@courses_bp.route('/<user_id>/stats', methods=['GET'])
@token_required
def get_user_course_stats(current_user, user_id):
    """Get user's course completion statistics"""
    try:
        # Ensure user can only access their own stats
        if str(current_user.id) != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get completion statistics
        total_enrolled = CourseCompletion.objects(user=user_id).count()
        completed = CourseCompletion.objects(user=user_id, status='completed').count()
        in_progress = CourseCompletion.objects(user=user_id, status='in_progress').count()
        not_started = CourseCompletion.objects(user=user_id, status='not_started').count()
        
        # Calculate completion rate
        completion_rate = (completed / total_enrolled * 100) if total_enrolled > 0 else 0
        
        # Get recent completions
        recent_completions = CourseCompletion.objects(
            user=user_id, 
            status='completed'
        ).order_by('-completed_at').limit(5)
        
        recent_data = []
        for completion in recent_completions:
            course = Course.objects(course_id=completion.course_id).first()
            if course:
                recent_data.append({
                    'course': course.to_dict(),
                    'completed_at': completion.completed_at.isoformat() if completion.completed_at else None,
                    'rating': completion.rating
                })
        
        return jsonify({
            'success': True,
            'data': {
                'total_enrolled': total_enrolled,
                'completed': completed,
                'in_progress': in_progress,
                'not_started': not_started,
                'completion_rate': round(completion_rate, 1),
                'recent_completions': recent_data
            }
        }), 200
        
    except Exception as e:
        logging.error(f"Get user course stats error: {e}")
        return jsonify({'error': 'Failed to fetch course statistics'}), 500