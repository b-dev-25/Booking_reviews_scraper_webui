"""Validation functions for input data."""
from typing import List, Optional, Union, Type, TypeVar
from pathlib import Path
from enum import Enum
import re
import typer

T = TypeVar('T', bound=Enum)

def validate_output_dir(value: str) -> Path:
    """Validate and create output directory if it doesn't exist."""
    path = Path(value)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        raise typer.BadParameter(f"Invalid output directory: {str(e)}")

def validate_enum(enum_class: Type[T]):
    """Validate and convert string input to enum value."""
    def callback(value: str) -> T:
        if value is None:
            raise typer.BadParameter(f"Value cannot be None")
            
        if isinstance(value, enum_class):
            return value
            
        try:
            # First try direct value lookup
            return enum_class(value)
        except ValueError:
            try:
                # Then try by name (case insensitive)
                return enum_class[value.upper()]
            except KeyError:
                valid_values = ", ".join(v.name for v in enum_class)
                raise typer.BadParameter(
                    f"Invalid value. Valid values are: {valid_values}"
                )
    return callback

def validate_languages(value: Optional[str]) -> Optional[List[str]]:
    """Validate and split language codes."""
    if value is None:
        return None
    # Split the comma-separated string into a list and convert to lowercase
    return [lang.strip().lower() for lang in value.split(',')]

def validate_urls(value: str) -> List[str]:
    """Validate booking.com URLs."""
    if not value:
        raise typer.BadParameter("URLs cannot be empty")
    
    urls = [url.strip() for url in value.split(",") if url.strip()]
    if not urls:
        raise typer.BadParameter("No valid URLs provided")

    valid_domains = [
        "booking.com",
        "www.booking.com"
    ]

    validated_urls = []
    for url in urls:
        # Basic URL format validation
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Check domain
        domain_pattern = r"^https?://(?:[\w-]+\.)*(?P<domain>[\w-]+\.\w+)/"
        match = re.match(domain_pattern, url)
        if not match or match.group("domain") not in valid_domains:
            raise typer.BadParameter(
                f"Invalid URL: {url}. Must be a booking.com URL"
            )

        # Check URL path format
        if not re.search(r"/hotel/\w+", url):
            raise typer.BadParameter(
                f"Invalid URL format: {url}. Must be a hotel URL"
            )

        validated_urls.append(url)

    return validated_urls

def validate_page_size(value: int) -> int:
    """Validate page size (1-25)."""
    if not 1 <= value <= 25:
        raise typer.BadParameter("Page size must be between 1 and 25")
    return value

def validate_concurrent_hotels(value: int) -> int:
    """Validate number of concurrent hotel processes (1-5)."""
    if not 1 <= value <= 5:
        raise typer.BadParameter("Concurrent hotels must be between 1 and 5")
    return value

def validate_languages(value: Union[str, None]) -> Union[str, None]:
    """Validate language codes."""
    if value is None:
        return None

    valid_language_pattern = r'^[a-z]{2}(?:-[A-Z]{2})?$'
    languages = [lang.strip() for lang in value.split(",") if lang.strip()]
    
    if not languages:
        return None

    invalid_langs = [
        lang for lang in languages 
        if not re.match(valid_language_pattern, lang)
    ]
    
    if invalid_langs:
        raise typer.BadParameter(
            f"Invalid language codes: {', '.join(invalid_langs)}. "
            "Use ISO 639-1 codes (e.g., 'en' or 'en-US')"
        )

    return ",".join(languages)

def validate_hotel_id(value: str) -> str:
    """Validate hotel ID format."""
    if not re.match(r'^\d+$', value):
        raise ValueError("Hotel ID must be a numeric string")
    return value    
def validate_country_code(value: str) -> str:
        """Validate country code format."""
        if not re.match(r'^[a-z]{2}$', value.lower()):
            raise ValueError("Country code must be a 2-letter ISO code")
        return value.lower()

def validate_date(value: str) -> str:
    """Validate date format (YYYY-MM-DD)."""
    if not re.match(r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$', value):
        raise ValueError("Date must be in YYYY-MM-DD format")
    return value
