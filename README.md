# Booking.com Reviews Scraper

A Python tool for fetching and analyzing hotel reviews from Booking.com. Designed for both technical and non-technical users.

---

## Features

- Fetch reviews for one or more hotels from Booking.com
- Filter by language, time of year, customer type, and review score
- Save results to a local database, JSON, and optionally Excel
- Download review photos (optional)
- Progress and error reporting with rich console output
- Easy to use from the command line

---

## Prerequisites

- Python 3.8 or newer
- Windows, macOS, or Linux
- Internet connection

---

## Installation

1. **Clone or download this repository**
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

## Output

- **Database:** All reviews are saved to `database/hotels_reviews.db`
- **JSON:** Raw API responses are saved in `output/json/`
- **Excel:** If `--save-to-excel` is used, results are saved in `output/excel/`
- **Photos:** If `--download-images` is used, photos are saved in `output/photos/`
- **Logs:** Detailed logs are in the `logs/` folder

---

## Troubleshooting & FAQ

- **Q: I get an error about invalid page size or concurrent value.**
  - A: Make sure `--page-size` is between 10 and 25, and `--concurrent` is between 1 and 5.
- **Q: The script says 'No reviews found'.**
  - A: The hotel may not have reviews, or your filters are too strict.
- **Q: How do I fetch more than one page?**
  - A: Use `--max-pages` and `--page-size` to control how many reviews you fetch.
- **Q: How do I start from a specific page?**
  - A: Use `--start-page` (first page is 1).
- **Q: Where are my results?**
  - A: See the Output section above for file locations.

---

## Development & Testing

- Run all tests:
  ```bash
  pytest
  ```
- See `test_commands.ps1` for automated test scenarios.
- Code style: [black](https://black.readthedocs.io/), [isort](https://pycqa.github.io/isort/), [pylint](https://pylint.org/), [mypy](http://mypy-lang.org/)

---

## License

MIT License

---

## Docker Usage

You can run this tool in a containerized environment using Docker:

1. **Build the Docker image:**
   ```bash
   docker build -t booking-reviews-scraper .
   ```
2. **Run the CLI inside Docker:**
   ```bash
   docker run --rm booking-reviews-scraper [CLI options]
   # Example:
   docker run --rm booking-reviews-scraper https://www.booking.com/hotel/us/pod-times-square.html --sort OLDEST_FIRST --max-pages 2
   ```
3. **Mount output directories (optional):**
   To access output files on your host machine, mount a local directory:
   ```bash
   docker run --rm -v $(pwd)/output:/app/output booking-reviews-scraper [CLI options]
   ```
