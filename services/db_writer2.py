"""Async Database operations for storing hotel and review data."""
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, delete, text
from loguru import logger
from utils.reviews_photos_downloader import download_review_photos
from config import DB_PATH  # Adjust the import based on your project structure
from models.models import (
    Hotel, Review, CustomerTypeFilter, 
    LanguageFilter, RatingScore, TopicFilter,
    Base  # Make sure your Base is imported
)

class AsyncSQLiteConfig:
    """Async version of your SQLiteConfig"""
    
    def __init__(self, db_path: str = DB_PATH):
        # Create async engine with optimized SQLite settings
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            pool_size=20,
            max_overflow=30,
            pool_timeout=30,
            pool_recycle=3600,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
            },
            echo=False  # Set to True for debugging
        )
        
        # Create async session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def setup_database(self):
        """Initialize database with optimized SQLite settings"""
        async with self.engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
            # Configure SQLite for better async performance
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA synchronous=NORMAL"))
            await conn.execute(text("PRAGMA cache_size=10000"))
            await conn.execute(text("PRAGMA temp_store=memory"))
            await conn.execute(text("PRAGMA mmap_size=268435456"))
            await conn.execute(text("PRAGMA busy_timeout=30000"))
            
        logger.info("Database initialized with async optimizations")
    
    @asynccontextmanager
    async def get_session(self):
        """Async context manager for database sessions"""
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Clean shutdown of database connections"""
        await self.engine.dispose()

class AsyncDBWriter:
    """Async version of your DBWriter class"""
    
    def __init__(self, db_path: str = DB_PATH, download_images: bool = False):
        self.db_config = AsyncSQLiteConfig(db_path)
        self.download_images = download_images  # Store the flag for photo downloading
    
    async def initialize(self):
        """Initialize the database - call this once at startup"""
        await self.db_config.setup_database()
    
    async def close(self):
        """Close database connections - call this at shutdown"""
        await self.db_config.close()

    async def save_hotel_info(self, stats: dict, hotel_id: str, hotel_ufi: int, 
                            hotel_name: str, hotel_score: float, country_code: str, 
                            country_name: str, city_name: str) -> Hotel:
        """Save hotel information and related stats from the API response."""
        
        async with self.db_config.get_session() as session:
            try:
                # Calculate total reviews once
                total_reviews = stats.get('customerTypeFilter', [{}])[0].get('count', 0)
                logger.debug(f"Total reviews for hotel {hotel_id}: {total_reviews}")
                
                # Check if hotel already exists (async query)
                hotel_query = select(Hotel).where(Hotel.hotel_id == hotel_id)
                result = await session.execute(hotel_query)
                hotel = result.scalar_one_or_none()
                
                if not hotel:
                    # Create new hotel
                    hotel = Hotel(
                        hotel_id=hotel_id,
                        ufi=hotel_ufi,
                        name=hotel_name,
                        city_name=city_name,
                        country_name=country_name,
                        country_code=country_code,
                        total_reviews=total_reviews,
                        average_score=hotel_score
                    )
                    session.add(hotel)
                    await session.flush()  # Get the ID without committing
                else:
                    # Update existing hotel info
                    hotel.total_reviews = total_reviews
                    hotel.updated_at = datetime.now(timezone.utc)
                    await session.flush()

                # Clear existing related records to avoid duplicates (async delete)
                await session.execute(delete(CustomerTypeFilter).where(CustomerTypeFilter.hotel_id == hotel.id))
                await session.execute(delete(LanguageFilter).where(LanguageFilter.hotel_id == hotel.id))
                await session.execute(delete(RatingScore).where(RatingScore.hotel_id == hotel.id))
                await session.execute(delete(TopicFilter).where(TopicFilter.hotel_id == hotel.id))

                # Save related data
                await self._save_customer_type_filters(session, hotel, stats)
                await self._save_language_filters(session, hotel, stats)
                await self._save_rating_scores(session, hotel, stats)
                await self._save_topic_filters(session, hotel, stats)

                await session.commit()
                await session.refresh(hotel)
                return hotel

            except Exception as e:
                logger.error(f"Error in save_hotel_info: {e}")
                await session.rollback()
                raise

    async def save_reviews(self, reviews: List[dict], hotel_id: Optional[int] = None) -> Tuple[int, int]:
        """Save reviews and associate them with a hotel - ASYNC VERSION"""
        if not reviews:
            raise ValueError("No reviews provided to save")
        if not hotel_id:
            raise ValueError("hotel_id is required to save reviews")
        
        async with self.db_config.get_session() as session:
            added, skipped = 0, 0
            errors = []
            
            try:
                # Verify hotel exists (async query)
                hotel_query = select(Hotel).where(Hotel.id == hotel_id)
                result = await session.execute(hotel_query)
                hotel = result.scalar_one_or_none()
                
                if not hotel:
                    raise ValueError(f"No hotel found with ID {hotel_id}")

                # Process reviews in batches for better performance
                batch_size = 50  # Smaller batches for SQLite
                for i in range(0, len(reviews), batch_size):
                    batch = reviews[i:i + batch_size]
                    batch_added, batch_skipped, batch_errors = await self._process_review_batch(
                        session, batch, hotel_id
                    )
                    
                    added += batch_added
                    skipped += batch_skipped
                    errors.extend(batch_errors)

                # Commit all changes
                await session.commit()
                
                if errors:
                    for error in errors:
                        logger.error(error)

                logger.info(f"Saved {added} reviews, skipped {skipped} duplicates for hotel {hotel_id}")
                return added, skipped

            except Exception as e:
                logger.error(f"Error in save_reviews: {e}")
                await session.rollback()
                raise ValueError(f"Error in save_reviews: {str(e)}")

    async def _process_review_batch(self, session: AsyncSession, batch: List[dict], hotel_id: int) -> Tuple[int, int, List[str]]:
        """Process a batch of reviews with individual error handling"""
        added, skipped = 0, 0
        errors = []
        
        for review in batch:
            review_url = review.get('reviewUrl')
            if not review_url:
                errors.append("Missing review_url")
                continue
            
            try:
                # Check if review already exists (async query)
                existing_query = select(Review).where(Review.review_url == review_url)
                result = await session.execute(existing_query)
                existing_review = result.scalar_one_or_none()
                
                if existing_review:
                    skipped += 1
                    continue
                
                # Save new review
                await self._save_single_review(session, review, hotel_id)
                added += 1
                
                # Flush periodically to catch constraint violations early
                if added % 10 == 0:
                    await session.flush()
                    
            except IntegrityError:
                # Review already exists (race condition)
                await session.rollback()
                skipped += 1
                logger.debug(f"Duplicate review skipped: {review_url}")
            except Exception as e:
                await session.rollback()
                errors.append(f"Error saving review {review_url}: {str(e)}")
        
        return added, skipped, errors

    async def _save_single_review(self, session: AsyncSession, review: Dict[str, Any], hotel_id: int) -> None:
        """Save a single review to the database - ASYNC VERSION"""
        guest = review.get('guestDetails', {})
        text_details = review.get('textDetails', {})
        booking_details = review.get('bookingDetails', {})
        
        obj = Review(
            hotel_id=hotel_id,
            review_url=review.get('reviewUrl'),
            username=guest.get('username'),
            country_code=guest.get('countryCode'),
            country_name=guest.get('countryName'),
            reviewed_date=review.get('reviewedDate'),
            review_score=review.get('reviewScore'),
            positive_text=text_details.get('positiveText'),
            negative_text=text_details.get('negativeText'),
            checkin_date=booking_details.get('checkinDate'),
            checkout_date=booking_details.get('checkoutDate'),
            lang=text_details.get('lang'),
            raw_json=review
        )
        session.add(obj)
        await session.flush()  # Get the review ID

        # Extract photo URLs (same logic as your original)
        photo_urls = review.get('photoUrls', [])
        logger.debug(f"Extracted {len(photo_urls)} pre-extracted photo URLs for review {obj.review_url}")
        
        if not photo_urls and 'photos' in review and review['photos']:
            for photo in review['photos']:
                if isinstance(photo, dict):
                    max_url = photo.get('maxSizeUrl')
                    if max_url:
                        photo_urls.append(max_url)
                        continue
                        
                    if 'urls' in photo:                        
                      for url_obj in photo.get('urls', []):
                            if (isinstance(url_obj, dict) and 
                                url_obj.get('size') == 'max1280x900' and 
                                'url' in url_obj):
                                photo_urls.append(url_obj['url'])
                                break
                        
        obj.photo_urls = photo_urls if photo_urls else None
        
        # Download photos if URLs are available and download_images flag is enabled
        if photo_urls and self.download_images:
            from config import PHOTOS_DIR
            from pathlib import Path
            
            # Create directory based on hotel info if available
            try:
                # Get hotel info for directory naming
                hotel_result = await session.execute(select(Hotel).where(Hotel.id == hotel_id))
                hotel = hotel_result.scalar_one_or_none()
                
                if hotel:
                    # Create hotel-specific directory
                    hotel_name = hotel.name or f"hotel_{hotel.hotel_id}"
                    # Sanitize hotel name for directory
                    import re
                    hotel_name = re.sub(r'[^\w\-_\.]', '_', hotel_name)
                    hotel_photos_dir = PHOTOS_DIR / hotel_name
                    hotel_photos_dir.mkdir(parents=True, exist_ok=True)
                    download_dir = str(hotel_photos_dir)
                else:
                    download_dir = str(PHOTOS_DIR / f"hotel_{hotel_id}")
                    Path(download_dir).mkdir(parents=True, exist_ok=True)
                
                logger.debug(f"Downloading {len(photo_urls)} photos for review {obj.review_url}")
                await download_review_photos(photo_urls, obj.review_url, download_dir)
                
            except Exception as photo_error:
                logger.error(f"Error downloading photos for review {obj.review_url}: {photo_error}")
        
        logger.debug(f"Saved review {obj.review_url} with {len(photo_urls) if photo_urls else 0} photos")

    async def _save_customer_type_filters(self, session: AsyncSession, hotel: Hotel, response_data: Dict[str, Any]) -> None:
        """Save customer type filters for a hotel - ASYNC VERSION"""
        for ct_filter in response_data.get('customerTypeFilter', []):
            if not isinstance(ct_filter, dict):
                continue
                
            name = ct_filter.get('name', '')
            ctf = CustomerTypeFilter(
                hotel_id=hotel.id,
                type_name=name.split(' (')[0] if name else '',
                type_value=ct_filter.get('value', ''),
                count=ct_filter.get('count', 0)
            )
            session.add(ctf)

    async def _save_language_filters(self, session: AsyncSession, hotel: Hotel, response_data: Dict[str, Any]) -> None:
        """Save language filters for a hotel - ASYNC VERSION"""
        for lang_filter in response_data.get('languageFilter', []):
            if not isinstance(lang_filter, dict):
                continue

            name = lang_filter.get('name', '')
            lf = LanguageFilter(
                hotel_id=hotel.id,
                language_name=name.split(' (')[0] if name else '',
                language_code=lang_filter.get('value', ''),
                count=lang_filter.get('count', 0),
                country_flag=lang_filter.get('countryFlag')
            )
            session.add(lf)

    async def _save_rating_scores(self, session: AsyncSession, hotel: Hotel, response_data: Dict[str, Any]) -> None:
        """Save rating scores for a hotel - ASYNC VERSION"""
        for rating in response_data.get('ratingScores', []):
            if not isinstance(rating, dict):
                continue
                
            ufi_scores = rating.get('ufiScoresAverage', {}) or {}
            rs = RatingScore(
                hotel_id=hotel.id,
                category_name=rating.get('name', ''),
                category_translation=rating.get('translation', ''),
                score_value=rating.get('value'),
                # ufi_score_lower=ufi_scores.get('ufiScoreLowerBound'),
                # ufi_score_higher=ufi_scores.get('ufiScoreHigherBound')
            )
            session.add(rs)

    async def _save_topic_filters(self, session: AsyncSession, hotel: Hotel, response_data: Dict[str, Any]) -> None:
        """Save topic filters for a hotel - ASYNC VERSION"""
        for topic in response_data.get('topicFilters', []):
            if not isinstance(topic, dict):
                continue
                
            translation = topic.get('translation', {}) or {}
            tf = TopicFilter(
                hotel_id=hotel.id,
                topic_id=topic.get('id'),
                topic_name=topic.get('name', ''),
                translation_id=translation.get('id'),
                translation_name=translation.get('name'),
                is_selected=topic.get('isSelected', False)
            )
            session.add(tf)

    # Utility methods for concurrent operations
    async def save_multiple_hotels_concurrent(self, hotel_data_list: List[Tuple]) -> List[Hotel]:
        """Save multiple hotels concurrently"""
        import asyncio
        
        tasks = []
        for hotel_data in hotel_data_list:
            stats, hotel_id, hotel_ufi, hotel_name, hotel_score, country_code, country_name, city_name = hotel_data
            task = asyncio.create_task(
                self.save_hotel_info(stats, hotel_id, hotel_ufi, hotel_name, hotel_score, country_code, country_name, city_name)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        hotels = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Hotel save error: {result}")
            else:
                hotels.append(result)
        
        return hotels

    async def save_reviews_for_multiple_hotels(self, hotel_reviews_map: Dict[int, List[dict]]) -> Dict[int, Tuple[int, int]]:
        """Save reviews for multiple hotels concurrently"""
        import asyncio
        
        tasks = []
        for hotel_id, reviews in hotel_reviews_map.items():
            task = asyncio.create_task(self.save_reviews(reviews, hotel_id))
            tasks.append((hotel_id, task))
        
        results = {}
        for hotel_id, task in tasks:
            try:
                added, skipped = await task
                results[hotel_id] = (added, skipped)
            except Exception as e:
                logger.error(f"Error saving reviews for hotel {hotel_id}: {e}")
                results[hotel_id] = (0, 0)
        
        return results
