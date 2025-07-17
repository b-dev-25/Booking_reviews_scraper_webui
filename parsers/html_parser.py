"""HTML parsing functionality for booking.com pages."""
import re
from loguru import logger
from typing import Optional, Dict, Any
from .url_parser import URLParser
import demjson3 as demjson

class HTMLParser:
    def __init__(self):
        self.url_parser = URLParser()    
    
    
    @staticmethod
    def extract_utag_data(script_text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse utag_data from script text using Node.js"""
        try:
            import ast
            # Extract the utag_data object literal
            # Try different patterns to match utag_data assignment
            patterns = [
                r'window\.utag_data\s*=\s*({[^}]*(?:{[^}]*})*[^}]*})',  # With window prefix, handles nested objects
                r'utag_data\s*=\s*({[^}]*(?:{[^}]*})*[^}]*})',          # Without window prefix
                r'window\.utag_data\s*=\s*({.*?})',                      # Simple fallback with window
                r'utag_data\s*=\s*({.*?})'                              # Simple fallback without window
            ]
            
            match = None
            for pattern in patterns:
                try:
                    match = re.search(pattern, script_text, re.DOTALL)
                    if match:
                        break
                except re.error:
                    continue
                    
            if not match:
                logger.error("Could not find utag_data in script")
                return None
            
            # Get the raw object literal
            object_literal = match.group(1).strip()
            if not object_literal:
                logger.error("Found empty utag_data object")
                return None
            logger.debug(f"Extracted utag_data: {object_literal}")
            
            # Add quotes around unquoted keys
            # python_dict_str = re.sub(r'(\w+):', r'"\1":', object_literal)
            # logger.debug(f"Converted utag_data to Python dict format: {python_dict_str}")

            # Convert to Python dict
            data =demjson.decode(object_literal, encoding='utf-8', strict=False)
            logger.debug(f"Parsed utag_data: {data}")
                
            if not isinstance(data, dict):
                logger.error("Parsed data is not a dictionary")
                return None
            return data
        except (SyntaxError, ValueError) as e:
            logger.error(f"Error parsing utag_data: {str(e)}")
            return None
    
    @staticmethod
    def parse_hotel_info(utag_data: Dict[str, Any], url: str = None) -> Dict[str, Any]:
        """Parse hotel information from utag_data"""        
        def safe_int(value: Any) -> int:
            """Safely convert a value to int"""
            if value is None:
                return 0
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                # Remove any non-numeric characters
                clean_value = ''.join(c for c in value if c.isdigit())
                try:
                    return int(clean_value) if clean_value else 0
                except ValueError:
                    return 0
            return 0
        
        try:
            if utag_data is None:
                raise ValueError("utag_data cannot be None")

            hotel_info = {
                'hotel_id': safe_int(utag_data.get('hotel_id')),
                'ufi': safe_int(utag_data.get('dest_ufi', utag_data.get('ufi', 0))),
                'dest_cc': str(utag_data.get('dest_cc', '')).strip() or 'unknown',
                'hotel_name': str(utag_data.get('hotel_name', '')).strip() or 'unknown',
                'hotel_score': float(utag_data.get('utrs', 0)),
                'city_name': str(utag_data.get('city_name', '')).strip() or 'unknown',
                'country_name': str(utag_data.get('country_name', '')).strip() or 'unknown'
            }
            logger.debug(f"Parsed hotel info: {hotel_info}")
            # Extract country code from URL if provided
            if url:
                country_code = URLParser.extract_country_code(url)
                if country_code:
                    hotel_info['country_code'] = country_code

            # Validate critical fields - hotel_id must be present and > 0
            if hotel_info['hotel_id'] == 0:
                raise ValueError(f"Invalid hotel_id: {utag_data.get('hotel_id')}")
                
            return hotel_info
            
        except Exception as e:
            logger.error(f"Error parsing hotel info: {str(e)}")
            raise ValueError(f"Failed to parse hotel info: {str(e)}")
          
          
# if __name__ == "__main__":
#     # Example usage
#     parser = HTMLParser()
#     def load_example_script():
#         """Load an example script for testing purposes."""
#         with open('e:/personal_projects/booking_reviews_api/scraper_project/test_page.html', 'r', encoding='utf-8') as f:
#             content = f.read()
#             logger.debug(f"Read {len(content)} characters from test_page.html")
#             return content
#     script_text = load_example_script()

#     utag_data = parser.extract_utag_data(script_text)
#     if utag_data:
#         hotel_info = parser.parse_hotel_info(utag_data, "https://www.booking.com/hotel/us/example-hotel.html")
#         print(hotel_info)
