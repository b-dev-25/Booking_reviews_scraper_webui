"""JSON parsing functionality for booking.com API responses."""
from typing import Dict, Any, List
from loguru import logger

class JSONParser:
    @staticmethod
    def parse_reviews_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse reviews from API response data with validation."""
        try:
            if not isinstance(response_data, dict):
                raise ValueError("Response data must be a dictionary")

            # Navigate through response structure with validation
            data = response_data.get("data")
            if not isinstance(data, dict):
                raise ValueError("Missing or invalid 'data' field in response")

            frontend_data = data.get("reviewListFrontend")
            if not isinstance(frontend_data, dict):
                raise ValueError("Missing or invalid 'reviewListFrontend' field")

            # Check for error response
            if "statusCode" in frontend_data:
                raise ValueError(f"Frontend error: {frontend_data.get('message', 'Unknown error')}")

            review_cards = frontend_data.get("reviewCard", [])
            if not isinstance(review_cards, list):
                logger.warning("Empty or invalid reviewCard field")
                return []

            # Validate individual review entries
            validated_reviews = []
            for idx, review in enumerate(review_cards):
                if not isinstance(review, dict):
                    logger.warning(f"Invalid review format at index {idx}, skipping")
                    continue

                # Validate required fields
                required_fields = {
                    'bookingDetails': dict,
                    'guestDetails': dict,
                    'textDetails': dict,
                    'reviewScore': (int, float),
                    'reviewedDate': (int, str),  # Support both int and str dates
                }

                invalid_fields = []
                for field, expected_type in required_fields.items():
                    value = review.get(field)
                    if isinstance(expected_type, tuple):
                        if not any(isinstance(value, t) for t in expected_type):
                            invalid_fields.append(field)
                            logger.warning(f"Invalid or missing field '{field}' in review at index {idx}")
                    elif not isinstance(value, expected_type):
                        invalid_fields.append(field)
                        logger.warning(f"Invalid or missing field '{field}' in review at index {idx}")

                if invalid_fields:
                    logger.warning(f"Skipping review at index {idx} due to invalid fields: {', '.join(invalid_fields)}")
                    continue

                validated_reviews.append(review)

            return validated_reviews

        except Exception as e:
            logger.error(f"Error parsing reviews response: {str(e)}")
            logger.debug(f"Raw response data: {response_data}")
            return []

    @staticmethod
    def extract_hotel_stats(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and validate hotel statistics from API response."""
        default_stats = {
            "reviewsCount": 0,
            "ratingScores": [],
            "customerTypeFilter": [],
            "languageFilter": [],
            "topicFilters": []
        }

        try:
            if not isinstance(response_data, dict):
                raise ValueError("Response data must be a dictionary")

            data = response_data.get("data", {})
            if not isinstance(data, dict):
                logger.warning("Invalid 'data' field in response")
                return default_stats

            frontend_data = data.get("reviewListFrontend", {})
            if not isinstance(frontend_data, dict):
                logger.warning("Invalid 'reviewListFrontend' field")
                return default_stats

            # Extract and validate fields
            stats = {}
            stats["reviewsCount"] = frontend_data.get("reviewsCount", 0)
            stats["ratingScores"] = frontend_data.get("ratingScores", [])
            stats["customerTypeFilter"] = frontend_data.get("customerTypeFilter", [])
            stats["languageFilter"] = frontend_data.get("languageFilter", [])
            stats["topicFilters"] = frontend_data.get("topicFilters", [])

            # Type validation
            if not isinstance(stats["reviewsCount"], int):
                logger.warning("Invalid reviewsCount type")
                stats["reviewsCount"] = 0

            for field in ["ratingScores", "customerTypeFilter", "languageFilter", "topicFilters"]:
                if not isinstance(stats[field], list):
                    logger.warning(f"Invalid {field} type")
                    stats[field] = []

            return stats

        except Exception as e:
            logger.error(f"Error extracting hotel stats: {str(e)}")
            logger.debug(f"Raw response data: {response_data}")
            return default_stats    
    
    @staticmethod
    def extract_photo_urls(photos: List[Dict[str, Any]]) -> List[str]:
        """Extract photo URLs with max1280x900 size."""
        logger.debug("Extracting photo URLs from response data: {}".format(photos))
        if not isinstance(photos, list) or not photos:
            return []
            
        photo_urls = []
        try:
            for photo in photos:
                if not isinstance(photo, dict) or 'urls' not in photo:
                    continue
                
                # Find the max1280x900 URL
                urls = photo.get('urls', [])
                if not isinstance(urls, list):
                    continue
                    
                for url_obj in urls:
                    if (isinstance(url_obj, dict) and 
                        url_obj.get('size') == 'max1280x900' and 
                        'url' in url_obj):
                        photo_urls.append(url_obj['url'])
                        break
                      
            logger.debug(f"Extracted photo URLs: {photo_urls}")
            return photo_urls
            
        except Exception as e:
            logger.error(f"Error extracting photo URLs: {str(e)}")
            return []

    @staticmethod
    def validate_review(review: Dict[str, Any]) -> bool:
        """Validate individual review data structure."""
        required_nested_fields = {
            'bookingDetails': ['customerType', 'roomType', 'checkoutDate', 'checkinDate'],
            'guestDetails': ['username', 'countryCode'],
            'textDetails': ['title', 'positiveText', 'negativeText', 'lang'],
        }

        try:
            # Validate required nested fields
            for parent_field, child_fields in required_nested_fields.items():
                if not isinstance(review.get(parent_field), dict):
                    logger.warning(f"Missing or invalid {parent_field} object")
                    return False

                parent_obj = review[parent_field]
                for child_field in child_fields:
                    if child_field not in parent_obj:
                        logger.warning(f"Missing {child_field} in {parent_field}")
                        return False

            # Handle photos field separately (it's optional but should be validated if present)
            photo_urls = []
            if 'photos' in review:
                photos = review['photos']
                if not isinstance(photos, list):
                    logger.warning("Invalid photos field type - expected list")
                    return False
                    
                # Extract and add max size URLs
                photo_urls = JSONParser.extract_photo_urls(photos)
                
                # Store URLs in both places for compatibility
                review['photoUrls'] = photo_urls
                
                # Ensure the original photos field has the URLs easily accessible
                for i, photo in enumerate(photos):
                    if isinstance(photo, dict) and 'urls' in photo:
                        for url_obj in photo['urls']:
                            if (isinstance(url_obj, dict) and 
                                url_obj.get('size') == 'max1280x900' and 
                                'url' in url_obj):
                                photos[i]['maxSizeUrl'] = url_obj['url']
                                break

            return True

        except Exception as e:
            logger.error("Error validating review: {}", str(e))
            return False
