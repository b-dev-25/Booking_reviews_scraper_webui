"""Data conversion and transformation utilities."""
from typing import Optional
from urllib.parse import urlparse, parse_qs

def extract_hotel_id_from_url(url: str) -> Optional[str]:
    """Extract hotel ID from booking.com URL."""
    try:
        # First try to get from highlighted_hotels parameter
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        hotel_id = query_params.get('highlighted_hotels', [None])[0]
        
        if hotel_id:
            return hotel_id
            
        # Try alternate methods here if needed
        return None
    except (ValueError, IndexError):
        return None

def chunk_list(items: list, chunk_size: int) -> list:
    """Split a list into chunks of specified size."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
