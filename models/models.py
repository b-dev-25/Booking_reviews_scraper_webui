from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, UniqueConstraint, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Optional, Dict, List
from pydantic import BaseModel

class Filters(BaseModel):
    text: str = ''
    customerType: Optional[str] = None
    timeOfYear: Optional[str] = None
    languages: List[str] = []
    scoreRange: Optional[str] = None

class InputData(BaseModel):
    hotelId: int
    ufi: int
    hotelCountryCode: str
    sorter: str = "MOST_RELEVANT"
    filters: Filters = Filters()
    skip: int = 0
    limit: int = 10
    upsortReviewUrl: str = ""

class Variables(BaseModel):
    input: InputData
    shouldShowReviewListPhotoAltText: bool = True

class GraphQLRequest(BaseModel):
    operationName: str
    variables: Variables
    query: str
    extensions: Optional[Dict] = None

Base = declarative_base()

class Hotel(Base):
    __tablename__ = 'hotels'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(String, unique=True, nullable=False)
    name = Column(String)
    country_code = Column(String)
    country_name = Column(String)
    city_name = Column(String)
    ufi = Column(Integer)  # Booking.com unique facility identifier
    total_reviews = Column(Integer)
    average_score = Column(Float)    
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    reviews = relationship("Review", back_populates="hotel")
    customer_type_stats = relationship("CustomerTypeFilter", back_populates="hotel")
    language_stats = relationship("LanguageFilter", back_populates="hotel")
    rating_scores = relationship("RatingScore", back_populates="hotel")
    topic_filters = relationship("TopicFilter", back_populates="hotel")

class CustomerTypeFilter(Base):
    __tablename__ = 'customer_type_filters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey('hotels.id'))
    type_name = Column(String, nullable=False)  # e.g., "Families", "Business travelers"
    type_value = Column(String, nullable=False)  # e.g., "FAMILIES", "BUSINESS_TRAVELLERS"
    count = Column(Integer)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    hotel = relationship("Hotel", back_populates="customer_type_stats")

class LanguageFilter(Base):
    __tablename__ = 'language_filters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey('hotels.id'))
    language_name = Column(String, nullable=False)  # e.g., "English", "Arabic"
    language_code = Column(String)  # e.g., "en", "ar"
    count = Column(Integer)
    country_flag = Column(String)  # e.g., "gb", "sa"
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    hotel = relationship("Hotel", back_populates="language_stats")

class RatingScore(Base):
    __tablename__ = 'rating_scores'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey('hotels.id'))
    category_name = Column(String, nullable=False)  # e.g., "Cleanliness", "Location"
    category_translation = Column(String)    
    score_value = Column(Float)
    # ufi_score_lower = Column(Float)
    # ufi_score_higher = Column(Float)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    hotel = relationship("Hotel", back_populates="rating_scores")

class TopicFilter(Base):
    __tablename__ = 'topic_filters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey('hotels.id'))
    topic_id = Column(Integer)  # Booking.com's topic ID
    topic_name = Column(String, nullable=False)  # e.g., "Location", "Breakfast"
    translation_id = Column(String)  # e.g., "topic_location"
    translation_name = Column(String)
    is_selected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    hotel = relationship("Hotel", back_populates="topic_filters")

class Review(Base):
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey('hotels.id'))
    review_url = Column(String, unique=True, nullable=False)
    username = Column(String)
    country_code = Column(String)
    country_name = Column(String)
    reviewed_date = Column(String)
    review_score = Column(Float)
    positive_text = Column(String)
    negative_text = Column(String)
    checkin_date = Column(String)  # Date format: "YYYY-MM-DD"
    checkout_date = Column(String)  # Date format: "YYYY-MM-DD"
    lang = Column(String)      
    photo_urls = Column(JSON)  # List of photo URLs stored as JSON
    raw_json = Column(JSON)  # Store the full review as JSON for future extensibility
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    hotel = relationship("Hotel", back_populates="reviews")

    __table_args__ = (
        UniqueConstraint('review_url', name='uix_review_url'),
    )