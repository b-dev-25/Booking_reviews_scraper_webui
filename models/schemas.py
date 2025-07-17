"""Data validation schemas using Pydantic."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator
import re
from models.enums import CustomerType, TimeOfYear, ReviewScore

class ReviewText(BaseModel):
    """Review text content."""
    title: str = Field(..., min_length=1)
    positiveText: Optional[str] = None
    negativeText: Optional[str] = None
    lang: str = Field(..., pattern=r'^[a-z]{2}(?:-[A-Z]{2})?$')
    textTrivialFlag: Optional[bool] = None

class GuestDetails(BaseModel):
    """Guest information."""
    username: str
    countryCode: Optional[str] = Field(None, pattern=r'^[A-Z]{2}$')
    countryName: Optional[str] = None
    guestTypeTranslation: Optional[str] = None

class BookingDetails(BaseModel):
    """Booking information."""
    customerType: Optional[str] = None
    roomType: Optional[dict] = None
    checkoutDate: datetime
    checkinDate: datetime
    numNights: Optional[int] = Field(None, ge=1)
    stayStatus: Optional[str] = None

    @field_validator('checkoutDate', 'checkinDate', pre=True)
    def parse_datetime(cls, v):
        """Parse datetime from string."""
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError as e:
                raise ValueError(f"Invalid datetime format: {e}")
        return v

    @field_validator('numNights')
    def validate_nights(cls, v, values):
        """Validate number of nights matches dates."""
        if v is not None and 'checkoutDate' in values and 'checkinDate' in values:
            nights = (values['checkoutDate'] - values['checkinDate']).days
            if v != nights:
                raise ValueError(f"Number of nights ({v}) doesn't match dates ({nights})")
        return v

class ReviewCard(BaseModel):
    """Review card data."""
    reviewUrl: Optional[HttpUrl] = None
    guestDetails: GuestDetails
    bookingDetails: BookingDetails
    reviewedDate: datetime
    isTranslatable: Optional[bool] = None
    helpfulVotesCount: Optional[int] = Field(None, ge=0)
    reviewScore: float = Field(..., ge=0, le=10)
    textDetails: ReviewText
    isApproved: bool

class HotelStats(BaseModel):
    """Hotel statistics."""
    reviewsCount: int = Field(..., ge=0)
    ratingScores: List[dict] = []
    customerTypeFilter: List[dict] = []
    languageFilter: List[dict] = []
    topicFilters: List[dict] = []

class ReviewFilters(BaseModel):
    """Review filters."""
    text: str = ""
    customerType: Optional[CustomerType] = None
    timeOfYear: Optional[TimeOfYear] = None
    languages: List[str] = Field(default_factory=list)
    scoreRange: Optional[ReviewScore] = None

    @field_validator('languages')
    def validate_languages(cls, v):
        """Validate language codes."""
        pattern = r'^[a-z]{2}(?:-[A-Z]{2})?$'
        invalid = [lang for lang in v if not re.match(pattern, lang)]
        if invalid:
            raise ValueError(f"Invalid language codes: {', '.join(invalid)}")
        return v

class ReviewListResponse(BaseModel):
    """Full review list response."""
    reviewCard: List[ReviewCard]
    reviewsCount: int = Field(..., ge=0)
    stats: Optional[HotelStats] = None
    filters: Optional[ReviewFilters] = None
