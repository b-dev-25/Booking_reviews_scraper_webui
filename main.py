"""Main entry point for the Booking.com reviews scraper."""
import asyncio
import typer
from typing import Optional, List
from pathlib import Path
from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.console import Console
from rich import print as rich_print
import random

from services.fetcher import APIFetcher
from services.file_saver import FileSaver
from services.db_writer2 import AsyncDBWriter
from parsers.html_parser import HTMLParser
from parsers.json_parser import JSONParser
from parsers.url_parser import URLParser
from utils.validators import (
    validate_enum, validate_languages, validate_urls,
    validate_page_size, validate_concurrent_hotels
)
from utils.converters import chunk_list
from utils.db_converter import db_to_file
from models.enums import Sorters, TimeOfYear, CustomerType, ReviewScore
from config import (
    MAX_RETRIES, RETRY_DELAY, get_log_file, LOG_FORMAT, 
    LOG_ROTATION, LOG_RETENTION, create_project_directory, JSON_DIR, EXCEL_DIR, PHOTOS_DIR
)

app = typer.Typer(help="Booking.com reviews scraping tool")
console = Console()


# Initialize log file path
log_file = get_log_file()



class BookingReviewsScraper:
    def __init__(self, download_images: bool = False):
        self.api_fetcher = APIFetcher()
        self.file_saver = FileSaver()
        self.db_writer = AsyncDBWriter(download_images=download_images)
        self.html_parser = HTMLParser()
        self.json_parser = JSONParser()
        self.url_parser = URLParser()
        
    async def process_hotel(
        self,
        url: str,
        sorter: Sorters,
        page_size: int,
        start_page: Optional[int],
        max_pages: Optional[int],
        time_of_year: str,
        languages: Optional[List[str]],
        customer_type: str,
        review_score: str,
    ):
        """Process a single hotel URL with enhanced error handling and validation."""
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL format: {url}")

            # Fetch and parse hotel page with retry
            retry_count = 0
            while retry_count < MAX_RETRIES:
                try:
                    html_content = await self.api_fetcher.fetch_hotel_page(url)
                    utag_data = self.html_parser.extract_utag_data(html_content)
                    if not utag_data:
                        raise ValueError("Could not extract hotel data from page")
                    
                    hotel_info = self.html_parser.parse_hotel_info(utag_data, url)
                    if not hotel_info or 'hotel_id' not in hotel_info or 'country_code' not in hotel_info:
                        raise ValueError("Could not parse hotel information or missing country code")
                    
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        raise ValueError(f"Failed to fetch hotel page after {MAX_RETRIES} attempts: {str(e)}")
                    logger.warning(f"Retry {retry_count}/{MAX_RETRIES} for URL {url}: {str(e)}")
                    await asyncio.sleep(RETRY_DELAY * (2 ** (retry_count - 1)))

            self.api_fetcher.update_referer(url)            
            # Fetch all reviews with pagination
            all_reviews = []
            # Convert 1-based user input to 0-based pagination, default to page 1 (index 0)
            start_page = (start_page - 1) if start_page and start_page > 0 else 0
            total_reviews = None
            errors_count = 0
            max_errors = 3  # Maximum number of consecutive errors before giving up

            for _ in range(max_pages if max_pages is not None else float('inf')):
                skip = start_page * page_size
                logger.info("Fetching page {} (skip: {}, limit: {})", start_page + 1, skip, page_size)

                # Check if we have already fetched enough reviews
                if total_reviews is not None and skip >= total_reviews:
                    logger.info("Fetched all available reviews ({}).", total_reviews)
                    break

                try:
                    response = await self.api_fetcher.make_graphql_request(
                        hotel_info=hotel_info,
                        sorter=sorter,
                        skip=skip,
                        limit=page_size,
                        time_of_year=time_of_year,
                        languages=languages,
                        customer_type=customer_type,
                        review_score=review_score
                    )
                except Exception as e:
                    logger.error(f"Error fetching reviews: {str(e)}")
                    errors_count += 1
                    if errors_count >= max_errors:
                        logger.error(f"Too many consecutive errors ({max_errors}), stopping")
                        break
                    continue
                # Use JSON_DIR for the response file
                sanitized_hotel_name = self.file_saver.sanitize_filename(hotel_info['hotel_name'])
                json_filename = JSON_DIR / f"hotel_{sanitized_hotel_name}_response.json"
                self.file_saver.export_json_response(response, filename=json_filename)
                reviews = self.json_parser.parse_reviews_response(response)
                if not reviews:
                    if skip == 0:  # No reviews at all
                        logger.info("No reviews found for hotel")
                        break
                    else:  # End of reviews reached
                        logger.info("No more reviews available")
                        break

                stats = self.json_parser.extract_hotel_stats(response)
                if total_reviews is None:
                    total_reviews = stats.get('reviewsCount', 0)
                    logger.info("Total reviews available for current configuration: {}", total_reviews)
                
                errors_count = 0  # Reset consecutive errors counter
                all_reviews.extend(reviews)
                logger.info("Fetched page {} ({} reviews)", start_page + 1, len(reviews))

                # Save reviews to database and backup file                    
                try:
                    await self.db_writer.initialize()
                    # Save hotel info first
                    hotel = await self.db_writer.save_hotel_info(stats, hotel_info['hotel_id'], hotel_info['ufi'], 
                                                          hotel_info['hotel_name'], hotel_info.get('hotel_score', 0), 
                                                          hotel_info['country_code'], hotel_info['country_name'], hotel_info['city_name'])                        
                    # Then save reviews
                    if hotel and reviews:
                        added, skipped = await self.db_writer.save_reviews(reviews, hotel.id)
                        logger.info(f"Saved {added} reviews, skipped {skipped} duplicates")
                        
                except Exception as db_error:
                    logger.error(f"Error saving data for hotel {hotel_info['hotel_id']}: {db_error}")
                    # Save to backup file even if database save fails
                    backup_file = self.file_saver.save_reviews(reviews, hotel_info['hotel_id'])
                    logger.info(f"Saved reviews backup to {backup_file}")
                    raise  # Re-raise the error after backup
                except Exception as e:
                    logger.error(f"Error fetching page {start_page + 1}: {str(e)}")
                    errors_count += 1
                    if errors_count >= max_errors:
                        logger.error(f"Too many consecutive errors ({max_errors}), stopping")
                        break
                    continue
                    
                start_page += 1
                await asyncio.sleep(random.uniform(1, 3))  # Randomized rate limiting

            return all_reviews
            
        except Exception as e:
            logger.error(f"Error processing hotel {url}: {str(e)}")
            return {"error": str(e)}
            
    async def process_urls(
        self,
        urls: List[str],
        sorter: Sorters,
        page_size: int,
        start_page: Optional[int],
        max_pages: Optional[int],
        time_of_year: str,
        languages: Optional[List[str]],
        customer_type: str,
        review_score: str,
        concurrent_hotels: int,
        download_images: bool = False
    ):
        """Process multiple hotel URLs concurrently with improved error handling."""
        logger.info("Starting to process {} URLs with {} concurrent tasks", len(urls), concurrent_hotels)
        results = {}
        
        # Process URLs in chunks to control concurrency
        for chunk in chunk_list(urls, concurrent_hotels):
            tasks = []
            for url in chunk:
                if url in results:
                    continue
                task = asyncio.create_task(
                  self.process_hotel(
                      url=url,
                      sorter=sorter,
                      page_size=page_size,
                      start_page=start_page,
                      max_pages=max_pages,
                      time_of_year=time_of_year,
                      languages=languages,
                      customer_type=customer_type,
                      review_score=review_score,
                  )
              )
            tasks.append((url, task))
            
            # Wait for current chunk to complete
            for url, task in tasks:
                try:
                    result = await task
                    results[url] = result
                except asyncio.CancelledError:
                    logger.warning(f"Task cancelled for URL: {url}")
                    results[url] = {"error": "Task cancelled"}
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {str(e)}")
                    results[url] = {"error": str(e)}
                
                # Small delay between URLs
                await asyncio.sleep(random.uniform(1, 3))
        
        return results

@app.command()
def main(
    urls: str = typer.Argument(
        ...,
        help="Comma-separated list of Booking.com hotel URLs",
        callback=validate_urls
    ),
    sorter: str = typer.Option(
        Sorters.NEWEST_FIRST.value,
        "--sort",
        "-s",
        help=f"Sort order for reviews. Options: {', '.join(s.name for s in Sorters)}",
        callback=validate_enum(Sorters)
    ),
    page_size: int = typer.Option(
        10,
        "--page-size",
        "-p",
        help="Number of reviews per page (10-100)",
        callback=validate_page_size
    ),    start_page: Optional[int] = typer.Option(
        1,
        "--start-page",
        "-sp",
        help="Starting page number for fetching reviews (1-based)"
    ),
    max_pages: Optional[int] = typer.Option(
        1,
        "--max-pages",
        "-m",
        help="Maximum number of pages to fetch per hotel"
    ),
    concurrent_hotels: int = typer.Option(
        3,
        "--concurrent",
        "-n",
        help="Number of hotels to process concurrently (1-5)",
        callback=validate_concurrent_hotels
    ),
    languages: Optional[str] = typer.Option(
        None,
        "--languages",
        "-l",
        help="Filter reviews by language(s). Use comma-separated values",
        callback=validate_languages
    ),
    time_of_year: str = typer.Option(
        TimeOfYear.ALL.value,
        "--time",
        "-t",
        help=f"Filter reviews by time of year. Options: {', '.join(t.name for t in TimeOfYear)}",
        callback=validate_enum(TimeOfYear)
    ),
    customer_type: str = typer.Option(
        CustomerType.ALL.value,
        "--customer",
        "-u",
        help=f"Filter reviews by customer type. Options: {', '.join(c.name for c in CustomerType)}",
        callback=validate_enum(CustomerType)
    ),
    review_score: str = typer.Option(
        ReviewScore.ALL.value,
        "--score",
        "-r",
        help=f"Filter reviews by score range. Options: {', '.join(r.name for r in ReviewScore)}",
        callback=validate_enum(ReviewScore)
    ),
    download_images: bool = typer.Option(
        False,
        "--download-images",
        "-di",
        help="Download images for the fetched reviews"
    ),
    save_to_excel: bool = typer.Option(
        False,
        "--save-to-excel",
        "-se",
        help="Save results to an Excel file"
    ),
    excel_name: Optional[Path] = typer.Option(
      "booking_reviews.xlsx",
      "--excel-name",
      "-en",
      help="Name of the Excel file to save results (default: booking_reviews.xlsx)"
    ),
    no_debug: bool = typer.Option(
        False,
        "--no-debug",
        "-nd",
        help="Disable debug logging"
    )
):
    """Fetch and process hotel reviews from Booking.com with progress tracking."""    
    try:
        # Configure logger with appropriate level
        logger.remove()  # Remove any existing handlers
        logger.add(
            str(log_file),  # Convert Path to string for logger
            rotation=LOG_ROTATION,
            retention=LOG_RETENTION,
            level="INFO" if no_debug else "DEBUG",
            format=LOG_FORMAT
        )
        # initialize output directory
        create_project_directory('output', subdirs=['json', 'excel', 'photos'])
        # Display configuration
        rich_print("[bold blue]Configuration:[/bold blue]")
        rich_print(f"├── Processing {len(urls)} hotels")
        if len(urls) > 1:
            rich_print(f"├── Concurrent hotels: {concurrent_hotels}")
        rich_print(f"├── Sort order: {sorter.name}")
        rich_print(f"├── Page size: {page_size}")
        rich_print(f"├── Start page: {start_page or 1}")
        rich_print(f"├── Max pages: {max_pages or 'unlimited'}")
        rich_print(f"├── Languages: {languages or 'all'}")
        rich_print(f"├── Time of year: {time_of_year.name}")
        rich_print(f"├── Customer type: {customer_type.name}")
        rich_print(f"├── Review score: {review_score.name}")
        rich_print(f"├── Download images: {'Yes' if download_images else 'No'}")
        if download_images:
            rich_print(f"│   └── Photos directory: {PHOTOS_DIR}")
        rich_print(f"├── Save to Excel: {'Yes' if save_to_excel else 'No'}")
        if save_to_excel:
            rich_print(f"│   └── Excel file: {EXCEL_DIR / excel_name.name}")

        scraper = BookingReviewsScraper(download_images=download_images)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:            
            task = progress.add_task("Processing hotels...", total=len(urls))
            results = asyncio.run(scraper.process_urls(
                urls=urls,
                sorter=sorter,
                page_size=page_size,
                start_page=start_page,
                max_pages=max_pages,
                time_of_year=time_of_year,
                languages=languages.split(",") if languages else None,
                customer_type=customer_type,
                review_score=review_score,
                concurrent_hotels=concurrent_hotels,
                download_images=download_images
            ))
            
            progress.update(task, completed=len(urls))

        # Display results summary
        rich_print("\n[bold blue]Results:[/bold blue]")
        total_reviews = 0
        failed_hotels = []
        
        for url, result in results.items():
            url = scraper.url_parser.clear_url_query_params(url)
            if isinstance(result, dict) and "error" in result:
                rich_print(f"[red]✗[/red] {url} - Error: {result['error']}")
                failed_hotels.append(url)
            else:
                review_count = len(result)
                total_reviews += review_count                
                rich_print(f"[green]✓[/green] {url} - {review_count} reviews fetched")

        rich_print(f"\n[bold]Summary:[/bold]")
        rich_print(f"├── Total reviews fetched: {total_reviews}")
        rich_print(f"├── Successful hotels: {len(urls) - len(failed_hotels)}")
        rich_print(f"├── Failed hotels: {len(failed_hotels)}")
        rich_print(f"└── Log file: [blue]{log_file}[/blue]")

        # Save results to Excel if requested
        if save_to_excel:
            excel_file = EXCEL_DIR / excel_name.name
            db_to_file(db_path='database/hotels_reviews.db', output_path=str(excel_file))
            rich_print(f"\n[green]✓[/green] Results saved to {excel_file}")
        if failed_hotels:
            logger.warning("Some hotels failed to process. Check the log file for details.")
            return 1
        return 0

    except Exception as e:
        logger.exception("Unexpected error occurred")
        rich_print(f"[red]Error:[/red] {str(e)}")
        rich_print(f"Check the log file for details: [blue]{log_file}[/blue]")
        return 1

if __name__ == "__main__":
    # Use typer to handle command line arguments
    raise SystemExit(app())
