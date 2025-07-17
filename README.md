# Booking.com Reviews Scraper

A Python tool for fetching and analyzing hotel reviews from Booking.com with an intuitive Streamlit web interface and command-line support. Designed for both technical and non-technical users.

![Streamlit UI Screenshot](https://via.placeholder.com/800x400?text=Booking+Reviews+Scraper+Screenshot)

---

## Features

### Web User Interface

- **Streamlit Dashboard**: Easy-to-use interactive web interface
- **Hotel Statistics**: View detailed statistics for each hotel including:
  - Customer type distribution
  - Language distribution
  - Review score analysis
- **Advanced Review Explorer**:
  - Filter reviews by hotel, score, language, date range, and country
  - Pagination support for browsing large numbers of reviews
  - Export filtered results to Excel

### Scraper Capabilities

- Fetch reviews for one or more hotels from Booking.com
- Filter by language, time of year, customer type, and review score
- Save results to a local database, JSON, and optionally Excel
- Download review photos (optional)
- Progress and error reporting with rich console output
- Easy to use from the command line or web interface

---

## Prerequisites

- Python 3.8 or newer (Python 3.12 recommended)
- Windows, macOS, or Linux
- Internet connection

---

## Installation

1. **Clone or download this repository**

   ```bash
   git clone https://github.com/b-dev-25/Booking_reviews_scraper_webui.git
   cd Booking_reviews_scraper_webui
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   Or, for development and testing:

   ```bash
   pip install -e '.[test]'
   pip install -e '.[dev]'
   ```

---

## Quick Start

### Using the Web Interface (Recommended)

1. **Launch the Streamlit web app**:

   ```bash
   streamlit run webui_streamlit.py
   ```

2. **Access the app** in your web browser at `http://localhost:8501`

3. **Configure your scrape**:

   - Enter Booking.com hotel URLs (comma-separated)
   - Set filters, sort order, and other options
   - Click "Start Scraping" to begin

4. **View and analyze results**:
   - Click "View Results" after scraping completes
   - Explore hotel statistics, review distributions, and individual reviews
   - Use the filtering and pagination features in the "Reviews Explorer"
   - Export filtered reviews to Excel for further analysis

### Using the Command Line

Fetch reviews for a single hotel (first page, default options):

```bash
python main.py https://www.booking.com/hotel/us/pod-times-square.html
```

Fetch reviews for multiple hotels (comma-separated URLs):

```bash
python main.py "https://www.booking.com/hotel/us/pod-times-square.html,https://www.booking.com/hotel/id/suma.html"
```

---

## Common Options

| Option              | Short | Default              | Description                                                                                        |
| ------------------- | ----- | -------------------- | -------------------------------------------------------------------------------------------------- |
| `--sort`            | `-s`  | NEWEST_FIRST         | Sort order: NEWEST_FIRST, OLDEST_FIRST, HIGHEST_SCORE, LOWEST_SCORE                                |
| `--page-size`       | `-p`  | 10                   | Number of reviews per page (10-25)                                                                 |
| `--start-page`      | `-sp` | 1                    | Starting page number (1-based)                                                                     |
| `--max-pages`       | `-m`  | 1                    | Maximum number of pages to fetch per hotel                                                         |
| `--concurrent`      | `-n`  | 3                    | Number of hotels to process at once (1-5)                                                          |
| `--languages`       | `-l`  | all                  | Comma-separated language codes (e.g. en,fr,it)                                                     |
| `--time`            | `-t`  | ALL                  | Time of year: ALL, MAR_MAY, JUN_AUG, SEP_NOV, DEC_FEB                                              |
| `--customer`        | `-u`  | ALL                  | Customer type: ALL, FAMILIES, COUPLES, GROUP_OF_FRIENDS, SOLO_TRAVELLERS,BUSINESS_TRAVELLERS, etc. |
| `--score`           | `-r`  | ALL                  | Review score: ALL, WONDERFUL, GOOD, FAIR, POOR, VERY_POOR.                                         |
| `--download-images` | `-di` | False                | Download review photos                                                                             |
| `--save-to-excel`   | `-se` | False                | Save results to Excel file                                                                         |
| `--excel-name`      | `-en` | booking_reviews.xlsx | Name of Excel file (if saving to Excel)                                                            |
| `--no-debug`        | `-nd` | False                | Disable debug logging                                                                              |

---

## Example: Fetching Reviews with Filters

Fetch the first 2 pages of reviews (25 per page), sorted by oldest, for a specific hotel:

```bash
python main.py https://www.booking.com/hotel/us/pod-times-square.html --sort OLDEST_FIRST --page-size 25 --max-pages 2
```

Fetch reviews in English and French for multiple hotels, save to Excel:

```bash
python main.py "https://www.booking.com/hotel/us/pod-times-square.html,https://www.booking.com/hotel/id/suma.html" --languages en,fr --save-to-excel
```

---

## Output & Data Storage

- **Database:** All reviews are saved to `database/hotels_reviews.db` (SQLite)
- **JSON:** Raw API responses are saved in `output/json/`
- **Excel:** If `--save-to-excel` is used, results are saved in `output/excel/`
- **Photos:** If `--download-images` is used, photos are saved in `output/photos/`
- **Logs:** Detailed logs are in the `logs/` folder

---

## Streamlit UI Features

### Results Overview Dashboard

The "Results" view provides comprehensive analysis of your scraped data:

- **Summary Metrics**: View total hotels, reviews, average scores, customer types, and languages
- **Hotels Table**: See all hotels with their locations and review counts
- **Overall Statistics**:
  - Customer type distribution across all hotels
  - Language distribution across all hotels
- **Hotel-Specific Statistics**:
  - Select individual hotels to view their specific statistics
  - Customer type breakdown for each hotel
  - Language distribution for each hotel

### Reviews Explorer

Advanced review browsing and filtering capabilities:

- **Basic Filters**:
  - Filter by hotel
  - Filter by review score (slider range)
- **Advanced Filters**:
  - Filter by language
  - Filter by check-in date range
  - Filter by reviewer country
- **Pagination**: Browse through large sets of reviews with configurable page size
- **Export**: Download filtered results as Excel files for further analysis

---

## Troubleshooting & FAQ

- **Q: The Streamlit interface isn't loading.**
  - A: Make sure you've installed all requirements with `pip install -r requirements.txt` and that port 8501 isn't in use.
- **Q: I get an error about invalid page size or concurrent value.**
  - A: Make sure `--page-size` is between 10 and 25, and `--concurrent` is between 1 and 5.
- **Q: The script says 'No reviews found'.**
  - A: The hotel may not have reviews, or your filters are too strict.
- **Q: How do I fetch more than one page?**
  - A: In the UI, set "Max Pages" to your desired value. In CLI, use `--max-pages`.
- **Q: Where are my results?**
  - A: In the UI, click "View Results" after scraping. For CLI, see the Output section above.

---

## Database Schema

The application uses SQLite for data storage with the following key tables:

- **hotels**: Information about each hotel (name, location, average score)
- **reviews**: Individual reviews with scores, text content, and metadata
- **customer_type_filters**: Statistics on customer types per hotel
- **language_filters**: Statistics on languages used in reviews per hotel

You can query the database directly using any SQLite client, or explore it through the UI.

---

## Development & Testing

- **Run all tests**:

  ```bash
  pytest
  ```

- **Run the Streamlit UI in development mode**:

  ```bash
  streamlit run webui_streamlit.py
  ```

- See `test_commands.ps1` for automated test scenarios
- Code style: [black](https://black.readthedocs.io/), [isort](https://pycqa.github.io/isort/), [pylint](https://pylint.org/), [mypy](http://mypy-lang.org/)

---

## Docker Usage

### CLI Mode

You can run this tool in a containerized environment using Docker:

1. **Build the Docker image**:

   ```bash
   docker build -t booking-reviews-scraper .
   ```

2. **Run the CLI inside Docker**:

   ```bash
   docker run --rm booking-reviews-scraper [CLI options]
   # Example:
   docker run --rm booking-reviews-scraper https://www.booking.com/hotel/us/pod-times-square.html --sort OLDEST_FIRST --max-pages 2
   ```

3. **Mount output directories (optional)**:
   To access output files on your host machine, mount a local directory:

   ```bash
   docker run --rm -v $(pwd)/output:/app/output booking-reviews-scraper [CLI options]
   ```

### Streamlit UI Mode

Run the Streamlit UI in Docker with persistent storage:

```bash
docker build -t booking-reviews-ui .
docker run --rm -p 8501:8501 -v $(pwd)/database:/app/database -v $(pwd)/output:/app/output booking-reviews-ui streamlit run webui_streamlit.py
```

Then access the UI at `http://localhost:8501` in your browser.

---

## Support the Project

If you find this tool useful, consider supporting its continued development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/b-dev25)

[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/bdev25)

Your support helps keep this project maintained and improved!

---

## License

MIT License

---

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues to improve the tool.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
