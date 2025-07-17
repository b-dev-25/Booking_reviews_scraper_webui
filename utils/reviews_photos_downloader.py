""" Utility to download reviews photos from a given URL. """
import httpx
from pathlib import Path
from loguru import logger
from typing import List
import asyncio
from sqlalchemy import select
from config import DB_PATH, PHOTOS_DIR
import sys
import os

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent.parent  # goes up to project root


DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"


async def get_review_photos(hotel_id: int) -> List[str]:
    from services.db_writer2 import AsyncSQLiteConfig
    from models.models import Review
    """Fetch review photos from the database."""
    async with AsyncSQLiteConfig().get_session() as session:
      try:
        #lookup the reviews of the given hotel_id
        get_hotel_reviews = await session.execute(
            select(Review).where(Review.hotel_id == hotel_id)
        )
        hotel_reviews = get_hotel_reviews.scalars().all()
        logger.info(f"Fetched {len(hotel_reviews)} reviews for hotel {hotel_id}")
        # Extract photo URLs from the reviews
        if not hotel_reviews:
            logger.warning(f"No reviews found for hotel {hotel_id}")
            return []
        photos_urls: List[str] = []
        for review in hotel_reviews:
            if review.photo_urls:
                photos_urls.extend(review.photo_urls)
        logger.info(f"Found {len(photos_urls)} photos for hotel {hotel_id}")
        if not photos_urls:
            logger.warning(f"No photos found for hotel {hotel_id}")
            return []
        return photos_urls
      except Exception as e:
        logger.error(f"Error fetching review photos for hotel {hotel_id}: {e}")
        return []
          
          
async def download_review_photos(photo_urls: List[str], review_id: str, download_dir: str = None) -> None:
    """
    Download review photos from a list of URLs.
    
    Args:
        photo_urls: List of photo URLs to download
        review_id: Review ID or URL to use in the filename
        download_dir: Directory path to save the photos
        
    Returns:
        None
    """
    # Use default photos directory if none provided
    if download_dir is None:
        download_dir = str(PHOTOS_DIR)
    
    # Create directory if it doesn't exist
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    
    # Create a more efficient client with a timeout
    from config import PHOTOS_HEADERS, DEFAULT_TIMEOUT
    
    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers=PHOTOS_HEADERS
    ) as client:
        tasks = []
        for i, url in enumerate(photo_urls):
            tasks.append(client.get(url))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for i, (url, response) in enumerate(zip(photo_urls, responses)):
            try:
                if isinstance(response, httpx.Response):
                    if response.status_code == 200:
                        logger.info(f"Downloading photo from {url}")
                        # Use a unique name for each photo from the same review
                        # Sanitize review_id for filename
                        sanitized_review_id = str(review_id).replace('/', '_').replace('\\', '_').replace(':', '_')
                        photo_name = f"review_{sanitized_review_id}_photo_{i+1}.jpg"
                        photo_path = Path(download_dir) / photo_name
                        with open(photo_path, 'wb') as f:
                            f.write(response.content)
                        logger.info(f"Downloaded {photo_name} to {download_dir}")
                    else:
                        logger.warning(f"Failed to download {url}: HTTP {response.status_code}")
                elif isinstance(response, Exception):
                    logger.error(f"Failed to download {url}: {str(response)}")
            except Exception as e:
                logger.error(f"Error processing download for {url}: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Example hotel ID
    hotel_id = 1
    # Fetch review photos for the given hotel ID
    photo_urls = asyncio.run(get_review_photos(hotel_id))
    
    # # Directory to save downloaded photos
    # download_directory = "downloaded_photos"

    # # Run the download function
    # asyncio.run(download_review_photos(photo_urls, hotel_id, download_directory))
#     # Example photo URLs
#     example_urls = [
#         "https://q-xx.bstatic.com/xdata/images/xphoto/max1280x900/158633280.jpg?k=9631de7337c275a0476753f1cf1e3cb8b9dfd4c8596295dc3c34b8ef9a991de8&o=",
#     ]
    
#     # Directory to save downloaded photos
#     download_directory = "downloaded_photos"

#     # Run the download function
#     asyncio.run(download_review_photos(example_urls, download_directory))
