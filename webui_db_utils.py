import pandas as pd
from sqlalchemy import create_engine
import os
from config import DB_PATH
import streamlit as st

@st.cache_data
def load_reviews(db_path=DB_PATH):
    if not os.path.exists(db_path):
        return pd.DataFrame()
    engine = create_engine(f'sqlite:///{db_path}')
    try:
        df = pd.read_sql('SELECT * FROM reviews', engine)
        return df
    except Exception:
        return pd.DataFrame()
      
@st.cache_data
def load_hotels(db_path=DB_PATH):
    if not os.path.exists(db_path):
        return pd.DataFrame()
    engine = create_engine(f'sqlite:///{db_path}')
    try:
        df = pd.read_sql('SELECT * FROM hotels', engine)
        return df
    except Exception:
        return pd.DataFrame()

def check_hotels_in_db(urls, db_path=DB_PATH):
    """
    Check if any hotel URLs already exist in the database
    
    Args:
        urls: List or comma-separated string of URLs to check
        db_path: Path to the database
        
    Returns:
        Dictionary with status of each URL (True if exists, False if not)
    """
    if isinstance(urls, str):
        url_list = [u.strip() for u in urls.split(',') if u.strip()]
    else:
        url_list = urls
        
    if not url_list or not os.path.exists(db_path):
        return {url: False for url in url_list}
        
    # Get the hotel dataframe
    try:
        hotels_df = load_hotels(db_path)
        if hotels_df.empty:
            return {url: False for url in url_list}
    except Exception as e:
        # If we can't load hotels, just return all False
        st.warning(f"Error loading hotels from database: {str(e)}")
        return {url: False for url in url_list}
    
    # Find all columns that might contain URLs or hotel identifiers
    url_columns = []
    name_columns = []
    
    # Determine which columns to check based on their names
    for col in hotels_df.columns:
        col_lower = col.lower()
        if 'url' in col_lower:
            url_columns.append(col)
        if 'name' in col_lower or 'hotel' in col_lower or 'title' in col_lower:
            name_columns.append(col)
    
    # If we didn't find any URL or name columns, check all string columns
    if not url_columns and not name_columns:
        for col in hotels_df.columns:
            if hotels_df[col].dtype == 'object':
                name_columns.append(col)
    
    result = {}
    
    for url in url_list:
        # Extract the hotel ID and name from the URL
        parts = url.split('/')
        if len(parts) >= 5:
            hotel_id = parts[-1].replace('.html', '')
            hotel_name = hotel_id.replace('-', ' ').lower()
            
            exists = False
            
            # First check URL columns (highest confidence match)
            for col in url_columns:
                try:
                    # Check if any URL in the database contains this hotel ID
                    exists = exists or any(
                        hotel_id.lower() in str(val).lower() 
                        for val in hotels_df[col] 
                        if val is not None and isinstance(val, str)
                    )
                    if exists:
                        break
                except Exception:
                    continue
                
            # If not found in URLs, check name columns
            if not exists:
                for col in name_columns:
                    try:
                        # Look for keywords from the hotel name
                        for keyword in hotel_name.split():
                            if len(keyword) >= 4:  # Only check meaningful words
                                exists = exists or any(
                                    keyword in str(val).lower()
                                    for val in hotels_df[col]
                                    if val is not None and isinstance(val, str)
                                )
                        if exists:
                            break
                    except Exception:
                        continue
            
            result[url] = exists
        else:
            # URL doesn't look like a hotel URL
            result[url] = False
    
    return result

def get_hotel_choices(db_path=DB_PATH):
    hotels = load_hotels(db_path)
    if hotels.empty:
        return []
    return [(row['id'], f"{row['name']} ({row['city_name']}, {row['country_name']})") for _, row in hotels.iterrows()]

def check_database_connection(db_path=DB_PATH):
    """Check if the database is accessible and return its schema"""
    if not os.path.exists(db_path):
        return False, "Database file not found", None
    
    try:
        engine = create_engine(f'sqlite:///{db_path}')
        # Get table names
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", engine)
        
        # Get schema for each table
        schema = {}
        for table in tables['name']:
            columns = pd.read_sql(f"PRAGMA table_info({table})", engine)
            schema[table] = columns['name'].tolist()
        
        return True, "Database connection successful", schema
    except Exception as e:
        return False, f"Database error: {str(e)}", None

@st.cache_data
def get_review_counts_by_hotel(db_path=DB_PATH):
    """Get the number of reviews per hotel"""
    if not os.path.exists(db_path):
        return pd.DataFrame()
    engine = create_engine(f'sqlite:///{db_path}')
    try:
        query = """
        SELECT h.name, COUNT(r.id) as review_count 
        FROM hotels h 
        LEFT JOIN reviews r ON h.id = r.hotel_id 
        GROUP BY h.id
        """
        df = pd.read_sql(query, engine)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def get_score_distribution(reviews_df):
    # Returns a DataFrame with hotel_id, review_score for boxplot/violin
    return reviews_df[['hotel_id', 'review_score']].dropna()

@st.cache_data
def get_review_timeline(reviews_df):
    # Returns a DataFrame with hotel_id, checkin_date, review_score for trend analysis
    df = reviews_df.copy()
    df['checkin_date'] = pd.to_datetime(df['checkin_date'], errors='coerce')
    return df[['hotel_id', 'checkin_date', 'review_score']].dropna()

@st.cache_data
def get_customer_type_stats(db_path=DB_PATH, hotel_id=None):
    """
    Get counts for each customer type, can be filtered by hotel
    
    Args:
        db_path: Path to the database
        hotel_id: Optional hotel ID to filter by. If None, returns aggregated stats.
    """
    if not os.path.exists(db_path):
        return pd.DataFrame()
    
    engine = create_engine(f'sqlite:///{db_path}')
    try:
        if hotel_id is None:
            # Get aggregated stats for all hotels
            query = """
            SELECT type_name, type_value, SUM(count) as total_count 
            FROM customer_type_filters 
            GROUP BY type_name, type_value
            ORDER BY total_count DESC
            """
            df = pd.read_sql(query, engine)
        else:
            # Get stats for a specific hotel
            query = """
            SELECT c.type_name, c.type_value, c.count as total_count, h.name as hotel_name
            FROM customer_type_filters c
            JOIN hotels h ON c.hotel_id = h.id
            WHERE c.hotel_id = :hotel_id
            ORDER BY c.count DESC
            """
            # Always pass parameters as a dictionary with named parameters
            params = {"hotel_id": hotel_id}
            df = pd.read_sql(query, engine, params=params)
        
        return df
    except Exception as e:
        print(f"Error getting customer type stats: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def get_language_stats(db_path=DB_PATH, hotel_id=None):
    """
    Get counts for each language, can be filtered by hotel
    
    Args:
        db_path: Path to the database
        hotel_id: Optional hotel ID to filter by. If None, returns aggregated stats.
    """
    if not os.path.exists(db_path):
        return pd.DataFrame()
    
    engine = create_engine(f'sqlite:///{db_path}')
    try:
        if hotel_id is None:
            # Get aggregated stats for all hotels
            query = """
            SELECT language_name, language_code, SUM(count) as total_count 
            FROM language_filters 
            GROUP BY language_name, language_code
            ORDER BY total_count DESC
            """
            df = pd.read_sql(query, engine)
        else:
            # Get stats for a specific hotel
            query = """
            SELECT l.language_name, l.language_code, l.count as total_count, h.name as hotel_name
            FROM language_filters l
            JOIN hotels h ON l.hotel_id = h.id
            WHERE l.hotel_id = :hotel_id
            ORDER BY l.count DESC
            """
            # Always pass parameters as a dictionary with named parameters
            params = {"hotel_id": hotel_id}
            df = pd.read_sql(query, engine, params=params)
        
        return df
    except Exception as e:
        print(f"Error getting language stats: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def get_hotels_with_stats(db_path=DB_PATH):
    """
    Get a list of hotels with customer type and language stats available
    """
    if not os.path.exists(db_path):
        return pd.DataFrame()
    
    engine = create_engine(f'sqlite:///{db_path}')
    try:
        # First try the optimized query
        query = """
        SELECT DISTINCT h.id, h.name, h.city_name, h.country_name
        FROM hotels h
        WHERE h.id IN (
            SELECT DISTINCT hotel_id FROM customer_type_filters
            UNION
            SELECT DISTINCT hotel_id FROM language_filters
        )
        ORDER BY h.name
        """
        df = pd.read_sql(query, engine)
        
        # If no results, fall back to all hotels
        if df.empty:
            print("No hotels found with filters, falling back to all hotels")
            query = """
            SELECT id, name, city_name, country_name
            FROM hotels
            ORDER BY name
            """
            df = pd.read_sql(query, engine)
        
        # Debug log
        print(f"Found {len(df)} hotels with stats")
        return df
    except Exception as e:
        print(f"Error getting hotels with stats: {str(e)}")
        return pd.DataFrame()