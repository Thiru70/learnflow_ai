from models.user import User
from models.resource import Resource
from models.feedback import Feedback
from models.learning_path import LearningPathStep
from services.ml_service import ml_service
import logging
from typing import List, Dict, Any

class RecommendationService:
    """Service for generating personalized recommendations"""
    
    @staticmethod
    def get_personalized_recommendations(user: User, limit: int = 12, filters: Dict = None) -> List[Dict]:
        """Generate personalized resource recommendations for a user"""
        try:
            # Get user preferences and history
            user_interests = user.interests or []
            user_skill_level = user.skill_level or 'Beginner'
            user_interactions = user.interactions or {}
            
            # Get resources user has already interacted with
            interacted_resource_ids = list(user_interactions.keys())
            
            # Build base query
            query = {}
            
            # Apply filters if provided
            if filters:
                if filters.get('type'):
                    query['type__in'] = filters['type']
                if filters.get('difficulty'):
                    query['difficulty__in'] = filters['difficulty']
                if filters.get('topics'):
                    query['tags__in'] = filters['topics']
            
            # Default to user's skill level if no difficulty filter
            if not filters or not filters.get('difficulty'):
                query['difficulty'] = user_skill_level
            
            # Filter by user interests if available
            if user_interests and (not filters or not filters.get('topics')):
                query['tags__in'] = user_interests
            
            # Exclude already interacted resources
            if interacted_resource_ids:
                query['id__nin'] = interacted_resource_ids
            
            # Get candidate resources
            resources = Resource.objects(**query).order_by('-rating', '-likes')
            
            # Apply collaborative filtering if we have enough data
            recommendations = RecommendationService._apply_collaborative_filtering(
                user, resources, limit
            )
            
            # If not enough recommendations, fall back to content-based
            if len(recommendations) < limit:
                content_based = RecommendationService._apply_content_based_filtering(
                    user, resources, limit - len(recommendations)
                )
                recommendations.extend(content_based)
            
            # Apply sorting based on filters
            if filters and filters.get('sortBy'):
                recommendations = RecommendationService._sort_recommendations(
                    recommendations, filters['sortBy']
                )
            
            return recommendations[:limit]
        
        except Exception as e:
            logging.error(f"Error generating personalized recommendations: {e}")
            return []
    
    @staticmethod
    def _apply_collaborative_filtering(user: User, resources, limit: int) -> List[Dict]:
        """Apply collaborative filtering based on similar users"""
        try:
            # Find users with similar interests
            similar_users = User.objects(
                interests__in=user.interests or [],
                skill_level=user.skill_level
            ).limit(50)
            
            # Get resources liked by similar users
            similar_user_ids = [str(u.id) for u in similar_users if str(u.id) != str(user.id)]
            
            if not similar_user_ids:
                return []
            
            # Get highly rated resources by similar users
            liked_feedback = Feedback.objects(
                user__in=similar_user_ids,
                helpful=True
            ).order_by('-created_at')
            
            # Score resources based on similar user preferences
            resource_scores = {}
            for feedback in liked_feedback:
                resource_id = str(feedback.resource.id)
                if resource_id not in resource_scores:
                    resource_scores[resource_id] = 0
                resource_scores[resource_id] += 1
            
            # Get top scored resources
            sorted_resources = sorted(
                resource_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            recommendations = []
            for resource_id, score in sorted_resources[:limit]:
                resource = Resource.objects(id=resource_id).first()
                if resource:
                    resource_dict = resource.to_dict()
                    resource_dict['recommendation_score'] = score
                    resource_dict['recommendation_reason'] = 'Users with similar interests liked this'
                    recommendations.append(resource_dict)
            
            return recommendations
        
        except Exception as e:
            logging.error(f"Error in collaborative filtering: {e}")
            return []
    
    @staticmethod
    def _apply_content_based_filtering(user: User, resources, limit: int) -> List[Dict]:
        """Apply content-based filtering based on user profile"""
        try:
            recommendations = []
            user_interests = user.interests or []
            
            for resource in resources[:limit * 2]:  # Get more candidates
                resource_dict = resource.to_dict()
                score = 0
                reasons = []
                
                # Score based on interest overlap
                interest_overlap = len(set(resource.tags) & set(user_interests))
                if interest_overlap > 0:
                    score += interest_overlap * 2
                    reasons.append(f"Matches {interest_overlap} of your interests")
                
                # Score based on difficulty match
                if resource.difficulty == user.skill_level:
                    score += 3
                    reasons.append("Matches your skill level")
                
                # Score based on rating and popularity
                score += resource.rating
                score += min(resource.likes / 10, 2)  # Cap likes bonus at 2
                
                if score > 0:
                    resource_dict['recommendation_score'] = score
                    resource_dict['recommendation_reason'] = '; '.join(reasons) or 'Popular content'
                    recommendations.append(resource_dict)
            
            # Sort by score and return top results
            recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
            return recommendations[:limit]
        
        except Exception as e:
            logging.error(f"Error in content-based filtering: {e}")
            return []
    
    @staticmethod
    def _sort_recommendations(recommendations: List[Dict], sort_by: str) -> List[Dict]:
        """Sort recommendations based on criteria"""
        try:
            if sort_by == 'rating':
                return sorted(recommendations, key=lambda x: x.get('rating', 0), reverse=True)
            elif sort_by == 'likes':
                return sorted(recommendations, key=lambda x: x.get('likes', 0), reverse=True)
            elif sort_by == 'newest':
                return sorted(recommendations, key=lambda x: x.get('created_at', ''), reverse=True)
            elif sort_by == 'relevance':
                return sorted(recommendations, key=lambda x: x.get('recommendation_score', 0), reverse=True)
            else:
                return recommendations
        except Exception as e:
            logging.error(f"Error sorting recommendations: {e}")
            return recommendations
    
    @staticmethod
    def get_next_learning_step(user: User) -> Dict:
        """Get the next recommended learning step for the user"""
        try:
            # Get user's current learning path
            current_step = LearningPathStep.objects(
                user=user,
                completed=False
            ).order_by('order').first()
            
            if current_step:
                step_dict = current_step.to_dict()
                step_dict['recommendation_reason'] = 'Next step in your learning path'
                return step_dict
            
            # If no learning path, recommend based on user profile
            recommendations = RecommendationService.get_personalized_recommendations(user, limit=1)
            if recommendations:
                return recommendations[0]
            
            return {}
        
        except Exception as e:
            logging.error(f"Error getting next learning step: {e}")
            return {}
    
    @staticmethod
    def get_cold_start_recommendations(user: User, limit: int = 12) -> List[Dict]:
        """Get recommendations for new users without profile data"""
        try:
            recommendations = []
            
            # Strategy 1: Popular beginner courses (40%)
            beginner_limit = max(1, limit // 3)
            beginner_courses = Resource.objects(
                difficulty='Beginner'
            ).order_by('-rating', '-likes').limit(beginner_limit)
            
            for course in beginner_courses:
                course_dict = course.to_dict()
                course_dict['recommendation_reason'] = 'Great for beginners'
                course_dict['recommendation_score'] = 5.0
                recommendations.append(course_dict)
            
            # Strategy 2: Highly rated courses across all levels (40%)
            popular_limit = max(1, limit // 3)
            popular_courses = Resource.objects().order_by('-rating', '-likes').limit(popular_limit * 2)
            
            added_count = 0
            for course in popular_courses:
                if added_count >= popular_limit:
                    break
                # Skip if already added
                if not any(r['id'] == str(course.id) for r in recommendations):
                    course_dict = course.to_dict()
                    course_dict['recommendation_reason'] = 'Highly rated by learners'
                    course_dict['recommendation_score'] = 4.0
                    recommendations.append(course_dict)
                    added_count += 1
            
            # Strategy 3: Recent popular content (20%)
            remaining = limit - len(recommendations)
            if remaining > 0:
                recent_courses = Resource.objects().order_by('-created_at', '-likes').limit(remaining * 2)
                
                added_count = 0
                for course in recent_courses:
                    if added_count >= remaining:
                        break
                    # Skip if already added
                    if not any(r['id'] == str(course.id) for r in recommendations):
                        course_dict = course.to_dict()
                        course_dict['recommendation_reason'] = 'Trending content'
                        course_dict['recommendation_score'] = 3.0
                        recommendations.append(course_dict)
                        added_count += 1
            
            return recommendations[:limit]
        
        except Exception as e:
            logging.error(f"Error generating cold start recommendations: {e}")
            return []
    
    @staticmethod
    def get_trending_resources(limit: int = 10) -> List[Dict]:
        """Get trending resources based on recent activity"""
        try:
            # Get resources with high recent engagement
            resources = Resource.objects().order_by('-likes', '-rating', '-views').limit(limit)
            
            trending = []
            for resource in resources:
                resource_dict = resource.to_dict()
                resource_dict['recommendation_reason'] = 'Trending now'
                trending.append(resource_dict)
            
            return trending
        
        except Exception as e:
            logging.error(f"Error getting trending resources: {e}")
            return []
    
    @staticmethod
    def get_bookmarked_resources(user: User) -> List[Dict]:
        """Get user's bookmarked resources"""
        try:
            user_interactions = user.interactions or {}
            bookmarked_ids = [
                resource_id for resource_id, interaction in user_interactions.items()
                if interaction.get('status') == 'bookmarked'
            ]
            
            if not bookmarked_ids:
                return []
            
            resources = Resource.objects(id__in=bookmarked_ids)
            bookmarked = []
            
            for resource in resources:
                resource_dict = resource.to_dict()
                resource_dict['is_bookmarked'] = True
                resource_dict['user_status'] = 'bookmarked'
                bookmarked.append(resource_dict)
            
            return bookmarked
        
        except Exception as e:
            logging.error(f"Error getting bookmarked resources: {e}")
            return []

# Global recommendation service instance
recommendation_service = RecommendationService()