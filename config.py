"""Configuration settings for the booking reviews scraper."""
import os
from pathlib import Path
from typing import Optional, List

# API Configuration
API_URL = 'https://www.booking.com/dml/graphql'
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36')

BASE_DIR = Path(__file__).resolve().parent  # goes up to project root
DB_PATH = BASE_DIR / 'database' / 'hotels_reviews.db'
# Directory Configuration
def create_project_directory(dir_name: str, subdirs: Optional[List[str]] = None) -> Path:
    """
    Create a writable directory and optionally create subdirectories within it.
    
    Args:
        dir_name: Name of the main directory to create
        subdirs: Optional list of subdirectory names to create within the main directory
        
    Returns:
        Path object of the created main directory
        
    Raises:
        OSError: If directory creation fails or permissions are insufficient
    """
    project_root = Path(__file__).parent
    target_dir = project_root / dir_name
    
    # Check if directory exists and is writable
    if target_dir.exists() and not target_dir.is_dir():
        raise OSError(f"{dir_name} path exists but is not a directory: {target_dir}")
    
    # Try to create or access the main directory
    try:
        target_dir.mkdir(exist_ok=True)
        
        # Test write permissions on main directory
        test_file = target_dir / '.write_test'
        test_file.touch(exist_ok=True)
        test_file.unlink()
        
        # Create subdirectories if specified
        if subdirs:
            for subdir in subdirs:
                subdir_path = target_dir / subdir
                subdir_path.mkdir(exist_ok=True)
                
    except (OSError, PermissionError) as e:
        raise OSError(f"Failed to create {dir_name} directory or subdirectories: {e}")
    
    return target_dir

# Create directories with subdirectories
LOGS_DIR = create_project_directory('logs')
OUTPUT_DIR = create_project_directory('output', ['json', 'excel', 'photos'])
#subdirectories pathes
JSON_DIR = OUTPUT_DIR / 'json'
EXCEL_DIR = OUTPUT_DIR / 'excel'
PHOTOS_DIR = OUTPUT_DIR / 'photos'

# Request Configuration
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAY = 1.0

# API Headers
API_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    'x-booking-context': 'web',
    'x-booking-language-code': 'en-us',
    'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="136", "Chromium";v="136"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'accept-language': 'en-US,en;q=0.7',
    'origin': 'https://www.booking.com',
    'priority': 'u=1, i',
    'sec-fetch-dest': 'empty',
    'sec-gpc': '1',
    'user-agent': USER_AGENT,
}

PHOTOS_HEADERS = {
  'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
  'accept-language': 'en-US,en;q=0.5',
  'user-agent': USER_AGENT,
}

# Database Configuration
DATABASE_URL = 'sqlite:///booking_reviews.db'

# Logging Configuration
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
LOG_ROTATION = "1 day"
LOG_RETENTION = "7 days"

def get_log_file() -> Path:
    """Get the log file path with timestamp."""
    from datetime import datetime
    return LOGS_DIR / f"booking_api_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')}.log"
