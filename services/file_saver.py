"""File saving and backup functionality."""
import json
import unicodedata
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Union, Optional, List, List
from loguru import logger
from config import JSON_DIR, EXCEL_DIR, PHOTOS_DIR, OUTPUT_DIR

class FileSaver:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        # First, normalize unicode characters
        filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode('ASCII')
          # Replace any non-alphanumeric characters (except periods, hyphens, and underscores) with underscore
        filename = re.sub(r'[^\w\-\.]', '_', filename)  # Replace invalid chars with underscore
        filename = re.sub(r'_+', '_', filename)  # Replace multiple underscores with single
        filename = re.sub(r'[_\.]+$', '', filename)  # Remove trailing dots and underscores
        filename = re.sub(r'^[_\.]+', '', filename)  # Remove leading dots and underscores
        
        # If the filename ends up empty (e.g., if it was all special characters), use a default
        if not filename:
            filename = 'unknown'
            
        return filename
    @staticmethod
    def save_debug_response(url: str, status_code: int, content: str) -> Path:
        """Save API response for debugging purposes."""
        # Create debug directory under OUTPUT_DIR
        debug_dir = OUTPUT_DIR / 'debug'
        debug_dir.mkdir(exist_ok=True)
        debug_file = debug_dir / f'hotel_response_{int(datetime.now().timestamp())}.txt'
        content_to_write = f"URL: {url}\nStatus: {status_code}\n\n{content}"
        
        # Check the debug directory without trying to create it
        try:
            # Quick check to avoid permission errors
            if not debug_dir.exists():
                raise OSError(f"Debug directory does not exist: {debug_dir}")
            
            if not debug_dir.is_dir():
                raise OSError(f"Debug path is not a directory: {debug_dir}")
                
            # Try to write a test file to verify permissions
            test_file = debug_dir / '.write_test'
            test_file.touch(exist_ok=True)
            test_file.unlink()  # Clean up test file
        except (OSError, PermissionError) as e:
            logger.error(f"Debug directory not writable: {str(e)}")
            raise OSError(f"Debug directory not writable: {str(e)}")
        
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(content_to_write)
            logger.debug(f"Debug response saved to {debug_file}")
            return debug_file
        except OSError as e:
            logger.error(f"Failed to save debug response: {str(e)}")
            raise

    def save_reviews(self, reviews: Dict[str, Any], hotel_id: Union[str, int]) -> Path:
        """Save reviews to a JSON file with backup functionality."""
        base_filename = f"hotel_{hotel_id}_reviews.json"
        sanitized_name = self.sanitize_filename(base_filename)
        filename = JSON_DIR / sanitized_name
        
        try:
            # Ensure the directory exists
            JSON_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(reviews, f, ensure_ascii=False, indent=2)
            logger.info(f"Reviews saved to {filename}")
            return filename
        except OSError as e:
            logger.error(f"Failed to save reviews to {filename}: {str(e)}")
            
            # Try to save to a backup file
            backup_filename = JSON_DIR / self.sanitize_filename(
                f"hotel_reviews_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            try:
                with open(backup_filename, 'w', encoding='utf-8') as f:
                    json.dump(reviews, f, ensure_ascii=False, indent=2)
                logger.info(f"Reviews saved to backup file: {backup_filename}")
                return backup_filename
            except OSError as backup_error:
                logger.error(f"Failed to save backup file {backup_filename}: {str(backup_error)}")
                raise

    def export_json_response(self, response_data: Dict[str, Any], filename: Path) -> Path:
        """
        Export JSON response to a file.
        
        Args:
            response_data: The data to export
            filename: The path where to save the data
            
        Returns:
            The path to the saved file
            
        Raises:
            Exception: If the file cannot be written
        """
        try:
            # Ensure the parent directory exists
            filename.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Response saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving response: {str(e)}")
            raise

