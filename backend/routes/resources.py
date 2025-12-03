from flask import Blueprint, request, jsonify
from models.resource import Resource
from models.feedback import Feedback
from utils.auth_utils import token_required
from services.ml_service import ml_service
import logging

resources_bp = Blueprint('resources', __name__, url_prefix='/api/resources')

@resources_bp.route('/test', methods=['GET'])
def get_resources_test():
    """Get resources without authentication for testing"""
    try:
        resources = Resource.objects().limit(10)
        resources_data = [resource.to_dict() for resource in resources]
        
        return jsonify({
            'success': True,
            'data': resources_data
        }), 200
    except Exception as e:
        logging.error(f"Get test resources error: {e}")
        return jsonify({'error': 'Failed to fetch resources'}), 500

@resources_bp.route('', methods=['GET'])
@token_required
def get_resources(current_user):
    """Get list of resources with optional filters"""
    try:
        # Get query parameters
        resource_type = request.args.getlist('type')
        difficulty = request.args.getlist('difficulty')
        tags = request.args.getlist('tags')
        category = request.args.get('category')
        sort_by = request.args.get('sort_by', 'created_at')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = {}
        
        if resource_type:
            query['type__in'] = resource_type
        
        if difficulty:
            query['difficulty__in'] = difficulty
        
        if tags:
            query['tags__in'] = tags
        
        if category:
            query['category'] = category
        
        # Execute query
        resources_query = Resource.objects(**query)
        
        # Apply sorting
        if sort_by == 'rating':
            resources_query = resources_query.order_by('-rating')
        elif sort_by == 'likes':
            resources_query = resources_query.order_by('-likes')
        elif sort_by == 'newest':
            resources_query = resources_query.order_by('-created_at')
        else:
            resources_query = resources_query.order_by('-created_at')
        
        # Apply pagination
        total_count = resources_query.count()
        resources = resources_query.skip(offset).limit(limit)
        
        # Convert to dict and add user-specific data
        resources_data = []
        user_interactions = current_user.interactions or {}
        
        for resource in resources:
            resource_dict = resource.to_dict()
            
            # Add user interaction status
            resource_id = str(resource.id)
            if resource_id in user_interactions:
                interaction = user_interactions[resource_id]
                resource_dict['user_status'] = interaction.get('status')
                resource_dict['is_bookmarked'] = interaction.get('bookmarked', False)
            else:
                resource_dict['user_status'] = None
                resource_dict['is_bookmarked'] = False
            
            resources_data.append(resource_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'resources': resources_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Get resources error: {e}")
        return jsonify({'error': 'Failed to fetch resources'}), 500

@resources_bp.route('/<resource_id>', methods=['GET'])
@token_required
def get_resource_details(current_user, resource_id):
    """Get detailed information about a specific resource"""
    try:
        resource = Resource.objects(id=resource_id).first()
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404
        
        # Increment view count
        resource.views += 1
        resource.save()
        
        # Get resource data
        resource_dict = resource.to_dict()
        
        # Add user interaction status
        user_interactions = current_user.interactions or {}
        resource_id_str = str(resource.id)
        
        if resource_id_str in user_interactions:
            interaction = user_interactions[resource_id_str]
            resource_dict['user_status'] = interaction.get('status')
            resource_dict['is_bookmarked'] = interaction.get('bookmarked', False)
        else:
            resource_dict['user_status'] = None
            resource_dict['is_bookmarked'] = False
        
        # Get user's feedback for this resource
        user_feedback = Feedback.objects(user=current_user, resource=resource).first()
        if user_feedback:
            resource_dict['user_feedback'] = user_feedback.to_dict()
        
        return jsonify({
            'success': True,
            'data': resource_dict
        }), 200
    
    except Exception as e:
        logging.error(f"Get resource details error: {e}")
        return jsonify({'error': 'Failed to fetch resource details'}), 500

@resources_bp.route('/search', methods=['POST'])
@token_required
def search_resources(current_user):
    """Semantic search for resources"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Search query is required'}), 400
        
        query = data['query']
        limit = data.get('limit', 10)
        
        # Get all resources with embeddings
        resources = Resource.objects(embedding__exists=True)
        
        print(f"Debug: Found {resources.count()} resources with embeddings")
        
        # If no resources have embeddings, fall back to text search
        if resources.count() == 0:
            # Fallback to simple text search
            all_resources = Resource.objects()
            search_results = []
            
            for resource in all_resources:
                resource_data = resource.to_dict()
                # Simple text matching
                tags_text = ''
                if resource.tags:
                    if isinstance(resource.tags, list):
                        tags_text = ' '.join(resource.tags)
                    else:
                        tags_text = str(resource.tags)
                
                text_content = f"{resource.title} {resource.description} {tags_text}".lower()
                if query.lower() in text_content:
                    search_results.append({
                        'resource': resource_data,
                        'similarity': 0.8  # Mock similarity score
                    })
            
            # Sort by title relevance and limit results
            if search_results:
                search_results = sorted(search_results, key=lambda x: query.lower() in x['resource']['title'].lower(), reverse=True)[:limit]
            else:
                # If no exact matches, return some results anyway for testing
                for resource in all_resources[:limit]:
                    resource_data = resource.to_dict()
                    search_results.append({
                        'resource': resource_data,
                        'similarity': 0.5  # Lower similarity for non-matching results
                    })
        else:
            # Prepare resource data for semantic search
            resource_embeddings = []
            for resource in resources:
                resource_data = resource.to_dict()
                resource_data['embedding'] = resource.embedding
                resource_embeddings.append(resource_data)
            
            # Perform semantic search
            search_results = ml_service.semantic_search(query, resource_embeddings, limit)
        
        # Add user interaction status
        user_interactions = current_user.interactions or {}
        
        for result in search_results:
            resource_data = result['resource']
            resource_id = resource_data['id']
            
            if resource_id in user_interactions:
                interaction = user_interactions[resource_id]
                resource_data['user_status'] = interaction.get('status')
                resource_data['is_bookmarked'] = interaction.get('bookmarked', False)
            else:
                resource_data['user_status'] = None
                resource_data['is_bookmarked'] = False
        
        return jsonify({
            'success': True,
            'data': {
                'query': query,
                'results': search_results
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Search resources error: {e}")
        return jsonify({'error': 'Search failed'}), 500

@resources_bp.route('/recommendations', methods=['GET'])
@token_required
def get_recommendations(current_user):
    """Get personalized resource recommendations"""
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 12))
        resource_type = request.args.getlist('type')
        difficulty = request.args.getlist('difficulty')
        
        # Get user interactions (don't exclude them, just track status)
        user_interactions = current_user.interactions or {}
        
        recommendations = []
        
        # Strategy 1: Interest-based recommendations (if user has interests)
        if current_user.interests and len(current_user.interests) > 0:
            # Create flexible matching for user interests
            interest_queries = []
            
            for interest in current_user.interests:
                interest_lower = interest.lower().replace(' ', '-')
                
                # Direct tag matching
                tag_query = {'tags__icontains': interest_lower}
                
                # Category matching
                category_query = {'category__icontains': interest}
                
                # Add both queries
                interest_queries.extend([tag_query, category_query])
                
                # Special mappings for common interests
                if 'web development' in interest.lower():
                    interest_queries.extend([
                        {'tags__in': ['javascript', 'html', 'css', 'react', 'node.js', 'frontend', 'backend']},
                        {'category__in': ['Web Development', 'Frontend Development', 'Backend Development']}
                    ])
                elif 'data science' in interest.lower():
                    interest_queries.extend([
                        {'tags__in': ['python', 'pandas', 'numpy', 'data-analysis', 'visualization', 'ml']},
                        {'category__in': ['Data Science', 'Machine Learning']}
                    ])
                elif 'machine learning' in interest.lower() or 'ml' in interest.lower():
                    interest_queries.extend([
                        {'tags__in': ['machine-learning', 'ml', 'ai', 'deep-learning', 'sklearn']},
                        {'category__in': ['Machine Learning', 'Artificial Intelligence', 'Deep Learning']}
                    ])
                elif 'python' in interest.lower():
                    interest_queries.extend([
                        {'tags__in': ['python', 'programming', 'scripting']},
                        {'category__in': ['Programming', 'Python']}
                    ])
            
            # Execute queries and collect resources
            interest_resources_set = set()
            for query in interest_queries:
                if difficulty:
                    query['difficulty__in'] = difficulty
                elif current_user.skill_level:
                    query['difficulty'] = current_user.skill_level
                if resource_type:
                    query['type__in'] = resource_type
                
                try:
                    resources = Resource.objects(**query).order_by('-rating', '-likes').limit(20)
                    for resource in resources:
                        if len(interest_resources_set) < limit // 2:
                            interest_resources_set.add(resource.id)
                except Exception as e:
                    logging.warning(f"Query failed: {query}, error: {e}")
                    continue
            
            # Convert to list and add to recommendations
            for resource_id in list(interest_resources_set)[:limit // 2]:
                try:
                    resource = Resource.objects(id=resource_id).first()
                    if resource:
                        resource_dict = resource.to_dict()
                        resource_dict['recommendation_reason'] = 'Matches your interests'
                        recommendations.append(resource_dict)
                except Exception as e:
                    continue
        
        # Strategy 2: Popular content for skill level
        if len(recommendations) < limit:
            remaining = limit - len(recommendations)
            query = {}
            
            # Map skill levels to difficulty
            skill_to_difficulty = {
                'Beginner': ['Beginner', 'Easy'],
                'Intermediate': ['Intermediate', 'Medium'], 
                'Advanced': ['Advanced', 'Hard']
            }
            
            if current_user.skill_level and current_user.skill_level in skill_to_difficulty:
                query['difficulty__in'] = skill_to_difficulty[current_user.skill_level]
            else:
                query['difficulty__in'] = ['Beginner', 'Easy']  # Default for new users
                
            if resource_type:
                query['type__in'] = resource_type
            
            # Exclude already recommended resources
            if recommendations:
                existing_ids = [r['id'] for r in recommendations]
                query['id__nin'] = existing_ids
            
            popular_resources = Resource.objects(**query).order_by('-rating', '-likes').limit(remaining)
            for resource in popular_resources:
                resource_dict = resource.to_dict()
                resource_dict['recommendation_reason'] = 'Popular with learners at your level'
                recommendations.append(resource_dict)
        
        # Strategy 3: Trending content (if still need more)
        if len(recommendations) < limit:
            remaining = limit - len(recommendations)
            query = {}
            if resource_type:
                query['type__in'] = resource_type
            
            # Exclude already recommended resources
            if recommendations:
                existing_ids = [r['id'] for r in recommendations]
                query['id__nin'] = existing_ids
            
            # Get highly rated content across all categories
            trending_resources = Resource.objects(**query).order_by('-rating', '-likes', '-created_at').limit(remaining)
            for resource in trending_resources:
                resource_dict = resource.to_dict()
                resource_dict['recommendation_reason'] = 'Highly rated content'
                recommendations.append(resource_dict)
        
        # Add user interaction status
        for resource_dict in recommendations:
            resource_id = resource_dict['id']
            if resource_id in user_interactions:
                interaction = user_interactions[resource_id]
                resource_dict['user_status'] = interaction.get('status')
                resource_dict['is_bookmarked'] = interaction.get('bookmarked', False)
            else:
                resource_dict['user_status'] = None
                resource_dict['is_bookmarked'] = False
        
        # Debug logging
        logging.info(f"Generated {len(recommendations)} recommendations for user {current_user.email} with interests {current_user.interests}")
        
        return jsonify({
            'success': True,
            'data': recommendations[:limit]
        }), 200
    
    except Exception as e:
        logging.error(f"Get recommendations error: {e}")
        return jsonify({'error': 'Failed to fetch recommendations'}), 500

@resources_bp.route('/<resource_id>/bookmark', methods=['POST'])
@token_required
def toggle_bookmark(current_user, resource_id):
    """Toggle bookmark status for a resource"""
    try:
        logging.info(f"Bookmark request for resource_id: {resource_id}")
        resource = Resource.objects(id=resource_id).first()
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404
        
        # Initialize interactions if not exists
        if not current_user.interactions:
            current_user.interactions = {}
        
        if resource_id not in current_user.interactions:
            current_user.interactions[resource_id] = {}
        
        interaction = current_user.interactions[resource_id]
        is_currently_bookmarked = interaction.get('bookmarked', False)
        
        # Toggle bookmark flag without affecting status
        interaction['bookmarked'] = not is_currently_bookmarked
        
        current_user.save()
        
        # Store interaction for ML purposes
        from models.user_interaction import UserInteraction
        from datetime import datetime
        from routes.notifications import create_system_notification
        
        UserInteraction(
            user=current_user,
            resource=resource,
            interaction_type='bookmarked' if interaction['bookmarked'] else 'unbookmarked',
            timestamp=datetime.utcnow()
        ).save()
        
        # Create notification for first bookmark
        if interaction['bookmarked']:
            bookmark_count = len([i for i in current_user.interactions.values() if i.get('bookmarked')])
            if bookmark_count == 1:
                create_system_notification(
                    user=current_user,
                    title='First Bookmark Added! 🔖',
                    message='Great! You can find all your bookmarked courses in your profile.',
                    notification_type='info',
                    action_url='/profile'
                )
        
        return jsonify({
            'success': True,
            'data': {
                'resource_id': resource_id,
                'is_bookmarked': interaction['bookmarked']
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Toggle bookmark error: {e}")
        return jsonify({'error': 'Failed to toggle bookmark'}), 500