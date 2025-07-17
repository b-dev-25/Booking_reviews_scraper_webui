"""Network request handling for booking.com API."""
import httpx
import asyncio
import random
from typing import Dict, Any, Optional
from loguru import logger
from config import API_URL, API_HEADERS, MAX_RETRIES, RETRY_DELAY, DEFAULT_TIMEOUT
from models.models import GraphQLRequest, Variables, InputData, Filters
from models.enums import Sorters, TimeOfYear, CustomerType, ReviewScore

REVIEW_LIST_QUERY = '''
query ReviewList($input: ReviewListFrontendInput!, $shouldShowReviewListPhotoAltText: Boolean = false) {
  reviewListFrontend(input: $input) {
    ... on ReviewListFrontendResult {
      ratingScores {
        name
        translation
        value
        ufiScoresAverage {
          ufiScoreLowerBound
          ufiScoreHigherBound
          __typename
        }
        __typename
      }
      topicFilters {
        id
        name
        isSelected
        translation {
          id
          name
          __typename
        }
        __typename
      }
      reviewScoreFilter {
        name
        value
        count
        __typename
      }
      languageFilter {
        name
        value
        count
        countryFlag
        __typename
      }
      timeOfYearFilter {
        name
        value
        count
        __typename
      }
      customerTypeFilter {
        count
        name
        value
        __typename
      }
      reviewCard {
        reviewUrl
        guestDetails {
          username
          avatarUrl
          countryCode
          countryName
          avatarColor
          showCountryFlag
          anonymous
          guestTypeTranslation
          __typename
        }
        bookingDetails {
          customerType
          roomId
          roomType {
            id
            name
            __typename
          }
          checkoutDate
          checkinDate
          numNights
          stayStatus
          __typename
        }
        reviewedDate
        isTranslatable
        helpfulVotesCount
        reviewScore
        textDetails {
          title
          positiveText
          negativeText
          textTrivialFlag
          lang
          __typename
        }
        isApproved
        partnerReply {
          reply
          __typename
        }
        positiveHighlights {
          start
          end
          __typename
        }
        negativeHighlights {
          start
          end
          __typename
        }
        editUrl
        photos {
          id
          urls {
            size
            url
            __typename
          }
          kind
          mlTagHighestProbability @include(if: $shouldShowReviewListPhotoAltText)
          __typename
        }
        __typename
      }
      reviewsCount
      sorters {
        name
        value
        __typename
      }
      __typename
    }
    ... on ReviewsFrontendError {
      statusCode
      message
      __typename
    }
    __typename
  }
}
'''

class BookingAPIError(Exception):
    """Base exception for Booking API errors."""
    pass

class RequestError(BookingAPIError):
    """Exception for request-related errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)

class APIFetcher:
    def __init__(self):
        self.api_headers = API_HEADERS.copy()

    def update_referer(self, url: str) -> None:
        """Update the referer header."""
        self.api_headers['referer'] = url

    async def fetch_hotel_page(self, url: str) -> str:
        """Fetch the hotel's HTML page."""
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(url, headers={'User-Agent': API_HEADERS['user-agent']}, follow_redirects=True)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as e:
            raise RequestError(f"Failed to fetch hotel page: {str(e)}", 
                            getattr(e, 'response', None) and e.response.status_code,
                            getattr(e, 'response', None) and e.response.text)      
    async def make_graphql_request(
        self,
        hotel_info: dict,
        sorter: Optional[Sorters] = None,
        skip: int = 0,
        limit: int = 10,
        time_of_year: Optional[TimeOfYear] = None,
        languages: Optional[list[str]] = None,
        customer_type: Optional[CustomerType] = None,
        review_score: Optional[ReviewScore] = None,
    ) -> Dict[str, Any]:
        """Make a GraphQL request to the Booking.com API."""
        # Validate required hotel info fields
        required_fields = ['hotel_id', 'ufi', 'country_code']
        missing_fields = [field for field in required_fields if field not in hotel_info]
        if missing_fields:
            raise ValueError(f"Missing required hotel info fields: {', '.join(missing_fields)}")

        # Log request details with sensitive data masked
        masked_headers = {k: v if k.lower() not in ['authorization', 'cookie'] else '[MASKED]' 
                       for k, v in self.api_headers.items()}
        logger.debug("Making GraphQL request for hotel_id: {}", hotel_info.get('hotel_id'))
        logger.debug("Request headers: {}", masked_headers)
        
        # Create filters with input validation
        try:
            filters = Filters(
                text='',
                customerType=customer_type.value if customer_type and customer_type != CustomerType.ALL else None,
                timeOfYear=time_of_year.value if time_of_year and time_of_year != TimeOfYear.ALL else None,
                languages=languages if languages else [],
                scoreRange=review_score.value if review_score and review_score != ReviewScore.ALL else None
            )
            logger.debug("Created filters object: {}", filters.model_dump())
        except Exception as e:
            raise RequestError(f"Failed to create filters: {str(e)}")

        # Create input data with validation
        try:
            input_data = InputData(
                hotelId=int(hotel_info['hotel_id']),
                ufi=int(hotel_info['ufi']),
                hotelCountryCode=hotel_info['country_code'],
                sorter=sorter.value if sorter else "MOST_RELEVANT",
                filters=filters,
                skip=skip,
                limit=limit,
                upsortReviewUrl=""
            )
            logger.debug("Created input data object: {}", input_data.model_dump())
        except Exception as e:
            raise RequestError(f"Failed to create input data: {str(e)}")

        # Create request variables
        try:
            variables = Variables(
                input=input_data,
                shouldShowReviewListPhotoAltText=True
            )
            logger.debug("Created variables object: {}", variables.model_dump())
        except Exception as e:
            raise RequestError(f"Failed to create variables: {str(e)}")

        # Create final request
        try:
            request = GraphQLRequest(
                operationName='ReviewList',
                variables=variables,
                query=REVIEW_LIST_QUERY,
                extensions={}
            )
            logger.debug("Created final GraphQL request object: {}", request.model_dump())
        except Exception as e:
            raise RequestError(f"Failed to create GraphQL request: {str(e)}")

        retry_count = 0
        last_error = None
        while retry_count < MAX_RETRIES:
            try:
                async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                    # Log request payload with sensitive data masked
                    json_payload = request.model_dump()
                    logger.debug("Request payload: {}", json_payload)
                    
                    response = await client.post(
                        API_URL,
                        headers=self.api_headers,
                        json=json_payload
                    )
                    
                    # Log response details
                    logger.debug("Response status code: {}", response.status_code)
                    logger.debug("Response headers: {}", response.headers)
                    
                    # Log response content (truncated if too long)
                    content = response.text
                    logger.debug("Response content (first 1000 chars): {}", 
                               content[:1000] if content else "Empty response")
                    
                    # Validate response status
                    response.raise_for_status()
                    data = response.json()
                    #logger.debug("Response JSON data: {}", data)

                    # Validate response structure
                    if not isinstance(data, dict):
                        raise RequestError("Invalid response format: expected dictionary")

                    # Check for GraphQL errors
                    if "errors" in data:
                        error_messages = [error.get("message", "Unknown error") 
                                      for error in data.get("errors", [])]
                        raise RequestError(
                            f"GraphQL errors: {', '.join(error_messages)}",
                            response.status_code,
                            response.text
                        )

                    # Validate response data structure
                    reviews_data = data.get("data", {}).get("reviewListFrontend", {})
                    if not reviews_data:
                        raise RequestError("Missing reviewListFrontend data in response")

                    if isinstance(reviews_data, dict) and "statusCode" in reviews_data:
                        # Handle frontend error response
                        raise RequestError(
                            f"Frontend error: {reviews_data.get('message', 'Unknown error')}",
                            reviews_data.get('statusCode'),
                            content
                        )

                    return data

            except httpx.RequestError as e:
                last_error = e
                retry_count += 1
                logger.error("Request error on attempt {}/{}: {}", retry_count, MAX_RETRIES, str(e))
                
                # Log detailed error information
                if isinstance(e, httpx.RequestError):
                    logger.error("HTTP Request Error details:")
                    if hasattr(e, 'request'):
                        logger.error("Request URL: {}", e.request.url)
                        logger.error("Request method: {}", e.request.method)
                        logger.error("Request headers: {}", {
                            k: v if k.lower() not in ['authorization', 'cookie'] else '[MASKED]'
                            for k, v in e.request.headers.items()
                        })
                    if hasattr(e, 'response'):
                        logger.error("Response status: {}", e.response.status_code)
                        logger.error("Response headers: {}", e.response.headers)
                        logger.error("Response content: {}", e.response.text[:1000])

                # Implement exponential backoff
                if retry_count < MAX_RETRIES:
                    wait_time = RETRY_DELAY * (2 ** (retry_count - 1))  # Exponential backoff
                    jitter = random.uniform(0, 0.1 * wait_time)  # Add jitter
                    total_wait = wait_time + jitter
                    logger.info("Retrying in {:.2f} seconds...", total_wait)
                    await asyncio.sleep(total_wait)
                    continue

                logger.error("Max retries reached for request")
                break

            except Exception as e:
                logger.error("Unexpected error: {}", str(e))
                logger.error("Error type: {}", type(e).__name__)
                import traceback
                logger.error("Traceback: {}", traceback.format_exc())
                raise RequestError(f"Unexpected error: {str(e)}")

        final_error_msg = f"Request failed after {MAX_RETRIES} attempts"
        logger.error(final_error_msg)
        
        if last_error:
            logger.error("Last error: {}", str(last_error))
            if hasattr(last_error, 'response_text'):
                logger.error("Last error response: {}", last_error.response_text)
                
        raise RequestError(
            final_error_msg,
            getattr(last_error, 'status_code', None),
            getattr(last_error, 'response_text', None)
        )
