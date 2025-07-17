"""URL parsing functionality for booking.com URLs."""
from typing import Optional
from urllib.parse import urlparse
from loguru import logger

class URLParser:
    @staticmethod
    def extract_country_code(url: str) -> Optional[str]:
        """Extract country code from booking.com URL.
        
        Args:
            url: Booking.com hotel URL
            
        Returns:
            str: Two-letter country code or None if not found
            
        Example URL format:
        https://www.booking.com/hotel/eg/golden-scarab-pyramids.html
        """
        try:
            # Parse the URL
            parsed = urlparse(url)
            
            # Check if it's a booking.com URL
            if not parsed.netloc.endswith('booking.com'):
                logger.warning(f"Not a booking.com URL: {url}")
                return None
                
            # Extract country code from path
            path_parts = parsed.path.split('/')
            if len(path_parts) >= 3 and path_parts[1] == 'hotel':
                country_code = path_parts[2]
                if len(country_code) == 2:  # Standard country codes are 2 letters
                    return country_code.lower()
                    
            logger.warning(f"Could not extract country code from URL: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing URL {url}: {str(e)}")
            return None
          
    @staticmethod
    def clear_url_query_params(url: str) -> str:
        """Remove query parameters from a URL.
        
        Args:
            url: The URL to clear
            
        Returns:
            str: URL without query parameters
        """
        try:
            if not url:
                logger.warning("Empty URL provided")
                return url
            parsed = urlparse(url)
            # Check if the URL is already cleared
            if not parsed.query:
                logger.info("URL is already cleared of query parameters.")
                return url
            # Parse the URL and clear query parameters
            cleared_url = parsed._replace(query='').geturl()
            logger.info(f"Cleared query parameters from URL: {url} -> {cleared_url}")
            return cleared_url
        except Exception as e:
            logger.error(f"Error clearing query parameters from URL {url}: {str(e)}")
            return url