from models.resource import Resource
from services.ml_service import ml_service
import logging
from typing import List, Dict, Any

class SearchService:
    """Service for handling search functionality"""
    
    @staticmethod
    def semantic_search(query: str, user_id: str = None, limit: int = 10) -> List[Dict]:
        """Perform semantic search using ML embeddings"""
        try:
            # Get all resources with embeddings
            resources = Resource.objects(embedding__exists=True)
            
            if not resources:
                # Fallback to keyword search if no embeddings
                return SearchService.keyword_search(query, limit)
            
            # Prepare resource data for ML service
            resource_embeddings = []
            for resource in resources:
                resource_data = resource.to_dict()
                resource_data['embedding'] = resource.embedding
                resource_embeddings.append(resource_data)
            
            # Perform semantic search using ML service
            search_results = ml_service.semantic_search(query, resource_embeddings, limit)
            
            # Format results
            formatted_results = []
            for result in search_results:
                resource_data = result['resource']
                resource_data['similarity_score'] = result['similarity']
                resource_data['search_reason'] = f"Semantic match (score: {result['similarity']:.2f})"
                formatted_results.append(resource_data)
            
            return formatted_results
        
        except Exception as e:
            logging.error(f"Error in semantic search: {e}")
            # Fallback to keyword search
            return SearchService.keyword_search(query, limit)
    
    @staticmethod
    def keyword_search(query: str, limit: int = 10) -> List[Dict]:
        """Perform keyword-based search"""
        try:
            query_lower = query.lower()
            keywords = query_lower.split()
            
            # Search in title, description, and tags
            resources = Resource.objects()
            
            scored_resources = []
            for resource in resources:
                score = 0
                reasons = []
                
                # Check title matches
                title_lower = resource.title.lower()
                title_matches = sum(1 for keyword in keywords if keyword in title_lower)
                if title_matches > 0:
                    score += title_matches * 3  # Title matches are weighted higher
                    reasons.append(f"Title matches: {title_matches}")
                
                # Check description matches
                desc_lower = resource.description.lower()
                desc_matches = sum(1 for keyword in keywords if keyword in desc_lower)
                if desc_matches > 0:
                    score += desc_matches * 2
                    reasons.append(f"Description matches: {desc_matches}")
                
                # Check tag matches
                tags_lower = [tag.lower() for tag in resource.tags]
                tag_matches = sum(1 for keyword in keywords for tag in tags_lower if keyword in tag)
                if tag_matches > 0:
                    score += tag_matches * 2
                    reasons.append(f"Tag matches: {tag_matches}")
                
                # Check category match
                if resource.category and query_lower in resource.category.lower():
                    score += 2
                    reasons.append("Category match")
                
                if score > 0:
                    resource_dict = resource.to_dict()
                    resource_dict['search_score'] = score
                    resource_dict['search_reason'] = '; '.join(reasons)
                    scored_resources.append(resource_dict)
            
            # Sort by score and return top results
            scored_resources.sort(key=lambda x: x['search_score'], reverse=True)
            return scored_resources[:limit]
        
        except Exception as e:
            logging.error(f"Error in keyword search: {e}")
            return []
    
    @staticmethod
    def filter_resources(filters: Dict) -> List[Dict]:
        """Filter resources based on criteria"""
        try:
            query = {}
            
            # Type filter
            if filters.get('type'):
                query['type__in'] = filters['type']
            
            # Difficulty filter
            if filters.get('difficulty'):
                query['difficulty__in'] = filters['difficulty']
            
            # Tags filter
            if filters.get('tags'):
                query['tags__in'] = filters['tags']
            
            # Category filter
            if filters.get('category'):
                query['category'] = filters['category']
            
            # Rating filter
            if filters.get('min_rating'):
                query['rating__gte'] = float(filters['min_rating'])
            
            # Duration filter (this would need parsing)
            # if filters.get('max_duration'):
            #     # Parse duration and filter
            #     pass
            
            # Execute query
            resources = Resource.objects(**query)
            
            # Apply sorting
            sort_by = filters.get('sort_by', 'rating')
            if sort_by == 'rating':
                resources = resources.order_by('-rating')
            elif sort_by == 'likes':
                resources = resources.order_by('-likes')
            elif sort_by == 'newest':
                resources = resources.order_by('-created_at')
            elif sort_by == 'title':
                resources = resources.order_by('title')
            
            # Apply pagination
            limit = int(filters.get('limit', 20))
            offset = int(filters.get('offset', 0))
            
            total_count = resources.count()
            resources = resources.skip(offset).limit(limit)
            
            # Convert to dict
            results = [resource.to_dict() for resource in resources]
            
            return {
                'resources': results,
                'total_count': total_count,
                'has_more': offset + limit < total_count
            }
        
        except Exception as e:
            logging.error(f"Error filtering resources: {e}")
            return {'resources': [], 'total_count': 0, 'has_more': False}
    
    @staticmethod
    def get_search_suggestions(query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query"""
        try:
            query_lower = query.lower()
            suggestions = set()
            
            # Get suggestions from resource titles
            resources = Resource.objects()
            for resource in resources:
                title_words = resource.title.lower().split()
                for word in title_words:
                    if word.startswith(query_lower) and len(word) > len(query):
                        suggestions.add(word.capitalize())
            
            # Get suggestions from tags
            all_tags = Resource.objects().distinct('tags')
            for tag in all_tags:
                if tag and tag.lower().startswith(query_lower):
                    suggestions.add(tag.capitalize())
            
            # Get suggestions from categories
            all_categories = Resource.objects().distinct('category')
            for category in all_categories:
                if category and category.lower().startswith(query_lower):
                    suggestions.add(category)
            
            return list(suggestions)[:limit]
        
        except Exception as e:
            logging.error(f"Error getting search suggestions: {e}")
            return []
    
    @staticmethod
    def get_popular_searches() -> List[str]:
        """Get popular search terms (mock implementation)"""
        try:
            # In a real implementation, you would track search queries
            # and return the most popular ones
            popular_terms = [
                "Python",
                "Machine Learning",
                "JavaScript",
                "Data Science",
                "Web Development",
                "Algorithms",
                "React",
                "SQL",
                "Deep Learning",
                "API Development"
            ]
            return popular_terms
        
        except Exception as e:
            logging.error(f"Error getting popular searches: {e}")
            return []
    
    @staticmethod
    def search_by_category(category: str, limit: int = 20) -> List[Dict]:
        """Search resources by category"""
        try:
            resources = Resource.objects(category=category).order_by('-rating').limit(limit)
            return [resource.to_dict() for resource in resources]
        
        except Exception as e:
            logging.error(f"Error searching by category: {e}")
            return []
    
    @staticmethod
    def search_by_tags(tags: List[str], limit: int = 20) -> List[Dict]:
        """Search resources by tags"""
        try:
            resources = Resource.objects(tags__in=tags).order_by('-rating').limit(limit)
            return [resource.to_dict() for resource in resources]
        
        except Exception as e:
            logging.error(f"Error searching by tags: {e}")
            return []

# Global search service instance
search_service = SearchService()