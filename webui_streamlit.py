import streamlit as st
import sys
import subprocess
import os
import json
import webui_db_utils
import time
import pandas as pd
import datetime


# Set page configuration with a more modern look
st.set_page_config(
    page_title="Booking.com Reviews Scraper",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
# Define callback function to synchronize input state with session state
def sync_input_with_state(key):
    """Sync the session state with input widget values"""
    if f"{key}_input" in st.session_state:
        st.session_state[key] = st.session_state[f"{key}_input"]

def init_session_state():
    """Initialize all session state variables with defaults if they don't exist"""
    # App navigation
    if 'app_view' not in st.session_state:
        st.session_state['app_view'] = 'scraper'  # Default view: scraper or results

    # Scraper configuration
    if 'urls' not in st.session_state:
        st.session_state['urls'] = "https://www.booking.com/hotel/us/pod-times-square.html"
    if 'sort' not in st.session_state:
        st.session_state['sort'] = "MOST_RELEVANT"
    if 'page_size' not in st.session_state:
        st.session_state['page_size'] = 10
    if 'start_page' not in st.session_state:
        st.session_state['start_page'] = 1
    if 'max_pages' not in st.session_state:
        st.session_state['max_pages'] = 1
    if 'concurrent' not in st.session_state:
        st.session_state['concurrent'] = 3
    if 'languages' not in st.session_state:
        st.session_state['languages'] = ""
    if 'time_of_year' not in st.session_state:
        st.session_state['time_of_year'] = "ALL"
    if 'customer_type' not in st.session_state:
        st.session_state['customer_type'] = "ALL"
    if 'review_score' not in st.session_state:
        st.session_state['review_score'] = "ALL"
    if 'download_images' not in st.session_state:
        st.session_state['download_images'] = False
    if 'save_to_excel' not in st.session_state:
        st.session_state['save_to_excel'] = True
    if 'excel_name' not in st.session_state:
        st.session_state['excel_name'] = "booking_reviews.xlsx"
    if 'no_debug' not in st.session_state:
        st.session_state['no_debug'] = False
    
    # Initialize input keys with current session state values
    for key in ['urls', 'sort', 'page_size', 'start_page', 'max_pages', 'concurrent',
               'languages', 'time_of_year', 'customer_type', 'review_score',
               'download_images', 'save_to_excel', 'excel_name', 'no_debug',
               'override_duplicate']:
        input_key = f"{key}_input"
        if input_key not in st.session_state:
            st.session_state[input_key] = st.session_state.get(key)

# Run initialization
init_session_state()

# Functions to handle configuration history persistence
def load_config_history():
    """Load previously run configurations from a JSON file"""
    
    history_file = os.path.join('output', 'scraper_history.json')
    details_file = os.path.join('output', 'scraper_details.json')
    
    if not os.path.exists(os.path.join('output')):
        os.makedirs(os.path.join('output'))
    
    configs = []
    config_details = {}
    
    # Load hash list
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                configs = json.load(f)
        except (json.JSONDecodeError, IOError):
            configs = []
    
    # Load detailed info
    if os.path.exists(details_file):
        try:
            with open(details_file, 'r') as f:
                config_details = json.load(f)
        except (json.JSONDecodeError, IOError):
            config_details = {}
    
    # Store the details in session state
    st.session_state['config_details'] = config_details
    
    return configs

def save_config_history(configs):
    """Save configuration history to a JSON file"""
    import json
    
    history_file = os.path.join('output', 'scraper_history.json')
    details_file = os.path.join('output', 'scraper_details.json')
    
    try:
        # Save hash list
        with open(history_file, 'w') as f:
            json.dump(configs, f)
        
        # Save detailed info
        with open(details_file, 'w') as f:
            json.dump(st.session_state.get('config_details', {}), f)
    except IOError:
        st.warning("Could not save configuration history to file.")

def extract_scraper_results(output_lines):
    """Extract scraped stats from the scraper output lines"""
    import re
    
    results = {}
    
    # Look for common patterns in the scraper output
    hotel_match = re.search(r'Scraped\s+(\d+)\s+hotels', "".join(output_lines))
    if hotel_match:
        results['hotels'] = int(hotel_match.group(1))
    
    review_match = re.search(r'Scraped\s+(\d+)\s+reviews', "".join(output_lines))
    if review_match:
        results['reviews'] = int(review_match.group(1))
        
    # Extract any errors
    error_lines = [line for line in output_lines if 'error' in line.lower() or 'exception' in line.lower()]
    if error_lines:
        results['errors'] = error_lines
        
    return results

# Track previous configurations to prevent duplicate runs
if 'previous_configs' not in st.session_state:
    st.session_state['previous_configs'] = load_config_history()
    
# Flag to allow override of duplicate warning
if 'override_duplicate' not in st.session_state:
    st.session_state['override_duplicate'] = False

# Track configurations with additional details
if 'config_details' not in st.session_state:
    st.session_state['config_details'] = {}

# Function to generate a config hash for tracking
def generate_config_hash(config):
    """Generate a unique hash for a configuration to track duplicates"""
    import hashlib
    
    # Parse URLs to better identify duplicates (focusing on hotel IDs)
    urls = config.get('urls', '')
    url_list = [u.strip() for u in urls.split(',') if u.strip()]
    
    # Create a sorted, simplified representation of the config
    # Focus on the most important parameters that determine unique data
    simplified = {
        'urls': sorted(url_list),  # Sort URLs to ensure consistent hashing
        'sort': config.get('sort', ''),
        'page_size': config.get('page_size', 0),
        'start_page': config.get('start_page', 0),
        'max_pages': config.get('max_pages', 0),
        'languages': config.get('languages', ''),
        'time_of_year': config.get('time_of_year', ''),
        'customer_type': config.get('customer_type', ''),
        'review_score': config.get('review_score', '')
    }
    
    # Convert to JSON string and hash it
    config_str = json.dumps(simplified, sort_keys=True)
    return hashlib.md5(config_str.encode()).hexdigest()

# Function to check if config has been run before
def is_duplicate_config(config):
    """Check if this exact configuration has been run before"""
    config_hash = generate_config_hash(config)
    return config_hash in st.session_state['previous_configs']

# Function to get details about a previous run
def get_config_details(config):
    """Get details about a previous run of this configuration"""
    config_hash = generate_config_hash(config)
    return st.session_state['config_details'].get(config_hash, None)

# Function to save config as run
def mark_config_as_run(config, results=None):
    """
    Add this configuration to the list of previously run configs
    
    Args:
        config: The configuration that was run
        results: Optional dictionary with results info (hotels count, reviews count, etc.)
    """
    import datetime
    
    config_hash = generate_config_hash(config)
    
    # Only add if it's new
    if config_hash not in st.session_state['previous_configs']:
        st.session_state['previous_configs'].append(config_hash)
    
    # Always update the details with the latest run info
    url_list = [u.strip() for u in config.get('urls', '').split(',') if u.strip()]
    hotel_names = []
    
    # Try to extract hotel names from URLs for better display
    for url in url_list:
        parts = url.split('/')
        if len(parts) >= 5:
            hotel_part = parts[-1].replace('.html', '').replace('-', ' ')
            hotel_names.append(hotel_part)
    
    # Store detailed information about this run
    st.session_state['config_details'][config_hash] = {
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'hotels': hotel_names,
        'url_count': len(url_list),
        'results': results or {}
    }
    
    # Save to persistent storage
    save_config_history(st.session_state['previous_configs'])

# Add custom CSS for better styling
st.markdown("""
<style>
    .main .block-container {padding-top: 1rem;}
    div[data-testid="stMetricValue"] {font-size: 1.5rem; font-weight: bold;}
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-weight: 500;
    }
    .output-container {
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 10px;
        background-color: #f9f9f9;
    }
    .header-container {
        background-color: #f0f7ff;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Load data from database
def refresh_data():
    """Reload data from the database and update session state"""
    # Clear the cache to force fresh data load
    webui_db_utils.load_hotels.clear()
    webui_db_utils.load_reviews.clear()
    webui_db_utils.get_customer_type_stats.clear()
    webui_db_utils.get_language_stats.clear()
    webui_db_utils.get_hotels_with_stats.clear()
    
    # Load fresh data
    st.session_state['hotels_df'] = webui_db_utils.load_hotels()
    st.session_state['reviews_df'] = webui_db_utils.load_reviews()
    st.session_state['customer_types_df'] = webui_db_utils.get_customer_type_stats()
    st.session_state['languages_df'] = webui_db_utils.get_language_stats()
    st.session_state['hotels_with_stats'] = webui_db_utils.get_hotels_with_stats()

# Initialize data if not already loaded
if 'hotels_df' not in st.session_state or 'customer_types_df' not in st.session_state:
    refresh_data()

# Always use the session state variables directly
hotels_df = st.session_state['hotels_df']
reviews_df = st.session_state['reviews_df']
customer_types_df = st.session_state.get('customer_types_df', pd.DataFrame())
languages_df = st.session_state.get('languages_df', pd.DataFrame())

# Header with app title and description
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏨 Booking.com Reviews Scraper")
        st.write("Scrape and analyze hotel reviews from Booking.com")
    with col2:
        # Display stats if we have data - always access directly from session state for latest counts
        hotels_count = len(st.session_state['hotels_df']) if not st.session_state['hotels_df'].empty else 0
        reviews_count = len(st.session_state['reviews_df']) if not st.session_state['reviews_df'].empty else 0
        
        if hotels_count > 0:
            st.metric("Hotels", f"{hotels_count}")
        if reviews_count > 0:
            st.metric("Reviews", f"{reviews_count}")

# Navigation in sidebar
with st.sidebar:
    st.title("Navigation")
    
    # View selector
    view_options = ["Scraper", "Results"] if not hotels_df.empty else ["Scraper"]
    selected_view = st.radio("Select View", view_options, label_visibility="collapsed")
    st.session_state['app_view'] = selected_view.lower()
    
    st.divider()
    
    # Only show scraper options in scraper view
    if st.session_state['app_view'] == 'scraper':
        st.header("Scraper Configuration")
        
        with st.expander("URLs & Pagination", expanded=True):
            st.text_area(
                "Hotel URLs (comma-separated)", 
                value=st.session_state['urls'],
                key="urls_input", 
                on_change=sync_input_with_state,
                args=("urls",)
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.slider(
                    "Reviews per page", 
                    10, 25, 
                    value=st.session_state['page_size'],
                    key="page_size_input",
                    on_change=sync_input_with_state,
                    args=("page_size",)
                )
                st.number_input(
                    "Start page", 
                    min_value=1, 
                    value=st.session_state['start_page'],
                    key="start_page_input",
                    on_change=sync_input_with_state,
                    args=("start_page",)
                )
            with col2:
                st.number_input(
                    "Max pages", 
                    min_value=1, 
                    value=st.session_state['max_pages'],
                    key="max_pages_input",
                    on_change=sync_input_with_state,
                    args=("max_pages",)
                )
                st.slider(
                    "Concurrent hotels", 
                    1, 5, 
                    value=st.session_state['concurrent'],
                    key="concurrent_input",
                    on_change=sync_input_with_state,
                    args=("concurrent",)
                )
        
        with st.expander("Filters", expanded=True):
            st.selectbox(
                "Sort order", 
                ["MOST_RELEVANT", "NEWEST_FIRST", "OLDEST_FIRST", "HIGHEST_SCORE", "LOWEST_SCORE"], 
                index=["MOST_RELEVANT", "NEWEST_FIRST", "OLDEST_FIRST", "HIGHEST_SCORE", "LOWEST_SCORE"].index(st.session_state['sort']),
                key="sort_input",
                on_change=sync_input_with_state,
                args=("sort",)
            )
            
            st.text_input(
                "Languages (comma-separated, e.g. en,fr)", 
                value=st.session_state['languages'],
                key="languages_input",
                on_change=sync_input_with_state,
                args=("languages",)
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.selectbox(
                    "Time of year", 
                    ["ALL", "MAR_MAY", "JUN_AUG", "SEP_NOV", "DEC_FEB"], 
                    index=["ALL", "MAR_MAY", "JUN_AUG", "SEP_NOV", "DEC_FEB"].index(st.session_state['time_of_year']),
                    key="time_of_year_input",
                    on_change=sync_input_with_state,
                    args=("time_of_year",)
                )
                
                st.selectbox(
                    "Customer type", 
                    ["ALL", "FAMILIES", "COUPLES", "GROUP_OF_FRIENDS", "SOLO_TRAVELLERS", "BUSINESS_TRAVELLERS"], 
                    index=["ALL", "FAMILIES", "COUPLES", "GROUP_OF_FRIENDS", "SOLO_TRAVELLERS", "BUSINESS_TRAVELLERS"].index(st.session_state['customer_type']),
                    key="customer_type_input",
                    on_change=sync_input_with_state,
                    args=("customer_type",)
                )
                
            with col2:
                st.selectbox(
                    "Review score", 
                    ["ALL", "WONDERFUL", "GOOD", "FAIR", "POOR", "VERY_POOR"], 
                    index=["ALL", "WONDERFUL", "GOOD", "FAIR", "POOR", "VERY_POOR"].index(st.session_state['review_score']),
                    key="review_score_input",
                    on_change=sync_input_with_state,
                    args=("review_score",)
                )
        
        with st.expander("Output Options", expanded=True):
            st.checkbox(
                "Download images", 
                value=st.session_state['download_images'],
                key="download_images_input",
                on_change=sync_input_with_state,
                args=("download_images",)
            )
            
            st.checkbox(
                "Save to Excel", 
                value=st.session_state['save_to_excel'],
                key="save_to_excel_input",
                on_change=sync_input_with_state,
                args=("save_to_excel",)
            )
            
            if st.session_state['save_to_excel']:
                st.text_input(
                    "Excel file name", 
                    value=st.session_state['excel_name'],
                    key="excel_name_input",
                    on_change=sync_input_with_state,
                    args=("excel_name",)
                )
                
            st.checkbox(
                "Disable debug logging", 
                value=st.session_state['no_debug'],
                key="no_debug_input",
                on_change=sync_input_with_state,
                args=("no_debug",)
            )
        
        # Advanced options
        with st.expander("Advanced Options", expanded=False):
            # Get current configuration
            current_config = {k: st.session_state[k] for k in [
                'urls', 'sort', 'page_size', 'start_page', 'max_pages', 
                'languages', 'time_of_year', 'customer_type', 'review_score'
            ]}
            
            # Check if URLs are in the database
            if current_config['urls'].strip():
                db_check = webui_db_utils.check_hotels_in_db(current_config['urls'])
                if any(db_check.values()):
                    st.warning("⚠️ Some hotels are already in the database:")
                    for url, exists in db_check.items():
                        if exists:
                            parts = url.split('/')
                            hotel_name = parts[-1].replace('.html', '').replace('-', ' ').title() if len(parts) >= 5 else url
                            st.info(f"🏨 **{hotel_name}** already exists in the database")
                            
                    # Add a check to see how many reviews are already in the database for these hotels
                    review_counts = webui_db_utils.get_review_counts_by_hotel()
                    if not review_counts.empty:
                        # Extract hotel names from URLs
                        existing_hotels = []
                        for url, exists in db_check.items():
                            if exists:
                                parts = url.split('/')
                                if len(parts) >= 5:
                                    hotel_name = parts[-1].replace('.html', '').replace('-', ' ').title()
                                    existing_hotels.append(hotel_name)
                        
                        for hotel in existing_hotels:
                            try:
                                # Find closest match in the database
                                if 'name' in review_counts.columns:
                                    # Convert to lowercase and handle potential NaN values
                                    matches = review_counts[
                                        review_counts['name'].fillna('').str.lower().str.contains(
                                            hotel.lower(), regex=False)
                                    ]
                                    
                                    if not matches.empty:
                                        for _, row in matches.iterrows():
                                            st.caption(f"📊 {row['name']} has {row['review_count']} reviews already in the database")
                            except Exception as e:
                                st.caption(f"Could not check review count: {str(e)}")
            
            # Check if it's a duplicate configuration
            is_duplicate = is_duplicate_config(current_config)
            
            if is_duplicate:
                # Get details about the previous run
                run_details = get_config_details(current_config)
                if run_details:
                    st.warning("⚠️ **DUPLICATE CONFIGURATION DETECTED**")
                    st.info(f"⏱️ Previously run on: **{run_details['timestamp']}**")
                    
                    if run_details.get('hotels'):
                        st.write("**Hotels included:**")
                        for hotel in run_details['hotels']:
                            st.write(f"- {hotel}")
                    
                    # Show results if available
                    if run_details.get('results'):
                        res = run_details['results']
                        st.write("**Previous results:**")
                        st.write(f"- Hotels scraped: {res.get('hotels', 'unknown')}")
                        st.write(f"- Reviews collected: {res.get('reviews', 'unknown')}")
                
                st.checkbox(
                    "Override duplicate prevention", 
                    value=st.session_state.get('override_duplicate', False),
                    key="override_duplicate_input",
                    on_change=sync_input_with_state,
                    args=("override_duplicate",),
                    help="Check this to force run the scraper even though this exact configuration has already been run before."
                )
                
                st.markdown("""
                <div style="background-color: #fff3cd; padding: 10px; border-radius: 5px;">
                <b>Why is this blocked?</b><br>
                Running the same configuration again may:
                <ul>
                <li>Waste processing time</li>
                <li>Create duplicate data in the database</li>
                <li>Potentially trigger rate limiting on Booking.com</li>
                </ul>
                </div>
                """, unsafe_allow_html=True)
            
            if st.session_state['previous_configs']:
                st.divider()
                st.write(f"**Run History: {len(st.session_state['previous_configs'])} configurations**")
                
                # Add a way to view all run history in a table
                if st.button(
                    label="📋 View All Run History",
                    use_container_width=True,
                    help="Show a table with details of all previous scraper runs"
                ):
                    # Collect history data for display
                    history_data = []
                    for config_hash in st.session_state['previous_configs']:
                        if config_hash in st.session_state['config_details']:
                            details = st.session_state['config_details'][config_hash]
                            history_data.append({
                                "Timestamp": details.get('timestamp', 'Unknown'),
                                "Hotels": ', '.join(details.get('hotels', [])) or 'Unknown',
                                "Reviews": details.get('results', {}).get('reviews', 'N/A'),
                                "Success": "✅" if not details.get('results', {}).get('failed', False) else "❌",
                                "Time": details.get('results', {}).get('elapsed_time', 'Unknown')
                            })
                    
                    if history_data:
                        st.dataframe(
                            history_data,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No detailed history available")
                
                if st.button(
                    label="🗑️ Clear Configuration History",
                    use_container_width=True,
                    help="Delete all saved configuration history"
                ):
                    st.session_state['previous_configs'] = []
                    st.session_state['config_details'] = {}
                    # Clear the persistent history files too
                    save_config_history([])
                    st.success("Configuration history cleared!")
                    st.rerun()
        
        # Create the run button with appropriate state based on duplicate detection
        if is_duplicate and not st.session_state['override_duplicate']:
            st.error("⛔ This configuration is blocked because it has already been run.")
            run_btn = st.button(
                label="🚀 Start Scraper",
                disabled=True,
                use_container_width=True,
                help="This button is disabled because this configuration has already been run"
            )
            
            st.warning("""
            **To run this configuration again, you need to:**
            1. Open 'Advanced Options' above
            2. Check the 'Override duplicate prevention' option
            3. Confirm you want to run a duplicate configuration
            """)
        else:
            if is_duplicate:
                run_btn = st.button(
                    label="🚀 Start Scraper (DUPLICATE RUN)",
                    type="primary",
                    use_container_width=True,
                    help="This will run the scraper even though this configuration has already been run before"
                )
                st.caption("⚠️ Running a duplicate configuration. This may create redundant data.")
            else:
                run_btn = st.button(
                    label="🚀 Start Scraper",
                    type="primary", 
                    use_container_width=True,
                    help="Start the scraper with the current configuration"
                )
    else:
        # Results view navigation options
        st.header("Results View")
        st.info("Showing previously scraped data from the database.")
        refresh_btn = st.button(
            label="🔄 Refresh Data",
            use_container_width=True,
            help="Reload the latest data from the database"
        )
        if refresh_btn:
            refresh_data()
            st.rerun()

# --- Main content area ---

# --- Main content area ---
# Function to display a clean scraper interface and build the command
def display_scraper_interface():
    st.subheader("🛠️ Scraper Configuration Summary")
    
    # Display the scraper configuration in a clean format
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Basic Settings**")
        st.info(f"🔢 Reviews per page: **{st.session_state['page_size']}**")
        st.info(f"📄 Pages: **{st.session_state['start_page']}** to **{st.session_state['start_page'] + st.session_state['max_pages'] - 1}**")
        st.info(f"🔄 Concurrent: **{st.session_state['concurrent']}** hotels")
    
    with col2:
        st.write("**Filters**")
        st.info(f"🔤 Sort: **{st.session_state['sort']}**")
        st.info(f"📅 Time: **{st.session_state['time_of_year']}**")
        st.info(f"👥 Customer: **{st.session_state['customer_type']}**")
        st.info(f"⭐ Score: **{st.session_state['review_score']}**")
    
    with col3:
        st.write("**Output**")
        st.info("💾 Save to DB: **Yes**")
        if st.session_state['save_to_excel']:
            st.info(f"📊 Excel: **{st.session_state['excel_name']}**")
        if st.session_state['download_images']:
            st.info("🖼️ Download images: **Yes**")
    
    # URL count display
    url_list = [u.strip() for u in st.session_state['urls'].split(",") if u.strip()]
    st.subheader(f"🏨 Hotels to scrape: {len(url_list)}")
    
    if url_list:
        for i, url in enumerate(url_list):
            st.code(url, language=None)
    
    # Check for duplicate configuration
    current_config = {k: st.session_state[k] for k in [
        'urls', 'sort', 'page_size', 'start_page', 'max_pages', 
        'languages', 'time_of_year', 'customer_type', 'review_score'
    ]}
    is_duplicate = is_duplicate_config(current_config)
    
    if is_duplicate:
        st.warning("⚠️ Note: You've already run this exact configuration before.")
        if not st.session_state['override_duplicate']:
            st.info("To re-run the same configuration, enable 'Override duplicate check' in Advanced Options.")
        else:
            st.info("You've chosen to override the duplicate check. The scraper will run normally.")
    
    # Build the command for the scraper
    cmd = [
        sys.executable, "main.py",
        st.session_state['urls'],
        "--sort", st.session_state['sort'],
        "--page-size", str(st.session_state['page_size']),
        "--start-page", str(st.session_state['start_page']),
        "--max-pages", str(st.session_state['max_pages']),
        "--concurrent", str(st.session_state['concurrent']),
        "--time", st.session_state['time_of_year'],
        "--customer", st.session_state['customer_type'],
        "--score", st.session_state['review_score']
    ]
    
    if st.session_state['languages']:
        cmd += ["--languages", st.session_state['languages']]
    if st.session_state['download_images']:
        cmd += ["--download-images"]
    if st.session_state['save_to_excel']:
        cmd += ["--save-to-excel", "--excel-name", st.session_state['excel_name']]
    if st.session_state['no_debug']:
        cmd += ["--no-debug"]
    
    return cmd

# Function to display a clean results overview
def display_results_overview():
    # Always use the latest data from session state
    hotels_df_latest = st.session_state['hotels_df']
    reviews_df_latest = st.session_state['reviews_df']
    
    if hotels_df_latest.empty:
        st.info("No hotels data found in the database. Run the scraper first.")
        return
    
    # Option to view run history
    with st.expander("🔍 View Previous Run History", expanded=False):
        if not st.session_state['previous_configs']:
            st.info("No previous runs recorded in this session.")
        else:
            st.info(f"You have run {len(st.session_state['previous_configs'])} unique configurations in this session.")
            st.warning("Note: Run history is reset when you restart the app.")
            
            if st.button(
                label="🗑️ Clear Run History", 
                use_container_width=True,
                help="Delete all saved run history information"
            ):
                st.session_state['previous_configs'] = []
                st.session_state['config_details'] = {}
                # Clear the persistent history file too
                save_config_history([])
                st.success("Run history cleared!")
                st.rerun()
        
    st.subheader("📊 Scraped Hotels Overview")
    
    # Show overall metrics - always access from session state for latest values
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    # Use session state directly to always get the latest data
    hotels_df_current = st.session_state['hotels_df']
    reviews_df_current = st.session_state['reviews_df']
    
    with col1:
        st.metric("Total Hotels", len(hotels_df_current))
    with col2:
        st.metric("Total Reviews", len(reviews_df_current) if not reviews_df_current.empty else 0)
    with col3:
        avg_score = hotels_df_current['average_score'].mean() if 'average_score' in hotels_df_current.columns and not hotels_df_current.empty else 0
        st.metric("Avg. Score", f"{avg_score:.2f}")
    with col4:
        countries = len(hotels_df_current['country_name'].unique()) if 'country_name' in hotels_df_current.columns and not hotels_df_current.empty else 0
        st.metric("Countries", countries)
    with col5:
        # Count customer types
        customer_types = len(st.session_state['customer_types_df']) if 'customer_types_df' in st.session_state and not st.session_state['customer_types_df'].empty else 0
        st.metric("Customer Types", customer_types)
    with col6:
        # Count languages
        languages = len(st.session_state['languages_df']) if 'languages_df' in st.session_state and not st.session_state['languages_df'].empty else 0
        st.metric("Languages", languages)
    
    # Simple hotel data table
    st.subheader("Hotels Data")
    if 'total_reviews' in hotels_df_latest.columns and 'average_score' in hotels_df_latest.columns:
        display_cols = ['name', 'city_name', 'country_name', 'total_reviews', 'average_score']
        display_cols = [col for col in display_cols if col in hotels_df_latest.columns]
        
        st.dataframe(
            hotels_df_latest[display_cols].sort_values('average_score', ascending=False),
            use_container_width=True,
            column_config={
                "name": "Hotel Name",
                "city_name": "City",
                "country_name": "Country",
                "total_reviews": st.column_config.NumberColumn("Reviews", format="%d"),
                "average_score": st.column_config.NumberColumn("Avg. Score", format="%.2f")
            },
            hide_index=True
        )
    
    # Customer type and language statistics
    st.subheader("Review Statistics")
    
    # Import Plotly to create charts
    import plotly.express as px
    
    # First show aggregated statistics
    st.write("### Overall Statistics")
    tab1, tab2 = st.tabs(["All Customer Types", "All Languages"])
    
    with tab1:
        if 'customer_types_df' in st.session_state and not st.session_state['customer_types_df'].empty:
            customer_types_df = st.session_state['customer_types_df']
            
            # Create a bar chart for customer types
            st.write("#### Overall Customer Types Distribution")
            
            fig = px.bar(
                customer_types_df,
                x='type_name',
                y='total_count',
                text='total_count',
                title="Number of Reviews by Customer Type (All Hotels)",
                labels={'type_name': 'Customer Type', 'total_count': 'Number of Reviews'},
                color='total_count',
                color_continuous_scale=px.colors.sequential.Blues
            )
            
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig.update_layout(
                xaxis_title="Customer Type",
                yaxis_title="Number of Reviews",
                xaxis={'categoryorder':'total descending'},
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display the data table as well
            with st.expander("Show Overall Customer Type Data"):
                st.dataframe(
                    customer_types_df, 
                    column_config={
                        "type_name": "Customer Type",
                        "type_value": "Type Value",
                        "total_count": st.column_config.NumberColumn("Total Reviews", format="%d")
                    },
                    hide_index=True,
                    use_container_width=True
                )
        else:
            st.info("No customer type data available. This may be because the database doesn't contain this information yet.")
            
    with tab2:
        if 'languages_df' in st.session_state and not st.session_state['languages_df'].empty:
            languages_df = st.session_state['languages_df']
            
            # Show only top 10 languages for better visualization
            top_languages = languages_df.head(10)
            
            # Create a bar chart for languages
            st.write("#### Overall Languages Distribution")
            
            fig = px.bar(
                top_languages,
                x='language_name',
                y='total_count',
                text='total_count',
                title="Top 10 Languages by Number of Reviews (All Hotels)",
                labels={'language_name': 'Language', 'total_count': 'Number of Reviews'},
                color='total_count',
                color_continuous_scale=px.colors.sequential.Greens
            )
            
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig.update_layout(
                xaxis_title="Language",
                yaxis_title="Number of Reviews",
                xaxis={'categoryorder':'total descending'},
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display the data table as well
            with st.expander("Show All Languages Data"):
                st.dataframe(
                    languages_df, 
                    column_config={
                        "language_name": "Language",
                        "language_code": "Code",
                        "total_count": st.column_config.NumberColumn("Total Reviews", format="%d")
                    },
                    hide_index=True,
                    use_container_width=True
                )
        else:
            st.info("No language data available. This may be because the database doesn't contain this information yet.")
            
    # Now show hotel-specific statistics
    st.write("### Hotel-Specific Statistics")
    
    if 'hotels_with_stats' in st.session_state and not st.session_state['hotels_with_stats'].empty:
        hotels_with_stats = st.session_state['hotels_with_stats']
        
        # Create a hotel selector
        hotel_options = [f"{row['name']} ({row['city_name'] if 'city_name' in row and pd.notna(row['city_name']) else 'Unknown'}, {row['country_name'] if 'country_name' in row and pd.notna(row['country_name']) else 'Unknown'})" for _, row in hotels_with_stats.iterrows()]
        hotel_ids = hotels_with_stats['id'].tolist()
        
        selected_hotel_index = st.selectbox(
            "Select a hotel to view statistics",
            options=range(len(hotel_options)),
            format_func=lambda x: hotel_options[x]
        )
        
        if selected_hotel_index is not None:
            selected_hotel_id = hotel_ids[selected_hotel_index]
            selected_hotel_name = hotel_options[selected_hotel_index]
            
            try:
                # Get hotel-specific data - ensuring we pass hotel_id in the correct format
                st.info(f"Loading statistics for hotel ID: {selected_hotel_id}")
                hotel_customer_types = webui_db_utils.get_customer_type_stats(hotel_id=selected_hotel_id)
                hotel_languages = webui_db_utils.get_language_stats(hotel_id=selected_hotel_id)
                
                # Create tabs for the hotel-specific data
                hotel_tab1, hotel_tab2 = st.tabs([f"Customer Types - {selected_hotel_name}", f"Languages - {selected_hotel_name}"])
            except Exception as e:
                st.error(f"Error loading hotel statistics: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
            
            with hotel_tab1:
                if not hotel_customer_types.empty:
                    st.write(f"#### Customer Types for {selected_hotel_name}")
                    
                    fig = px.bar(
                        hotel_customer_types,
                        x='type_name',
                        y='total_count',
                        text='total_count',
                        title=f"Number of Reviews by Customer Type for {selected_hotel_name}",
                        labels={'type_name': 'Customer Type', 'total_count': 'Number of Reviews'},
                        color='total_count',
                        color_continuous_scale=px.colors.sequential.Blues
                    )
                    
                    fig.update_traces(texttemplate='%{text}', textposition='outside')
                    fig.update_layout(
                        xaxis_title="Customer Type",
                        yaxis_title="Number of Reviews",
                        xaxis={'categoryorder':'total descending'},
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander(f"Show Customer Type Data for {selected_hotel_name}"):
                        st.dataframe(
                            hotel_customer_types, 
                            column_config={
                                "type_name": "Customer Type",
                                "type_value": "Type Value",
                                "total_count": st.column_config.NumberColumn("Reviews", format="%d")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                else:
                    st.info(f"No customer type data available for {selected_hotel_name}.")
                
            with hotel_tab2:
                if not hotel_languages.empty:
                    st.write(f"#### Languages for {selected_hotel_name}")
                    
                    # Show only top 10 languages for better visualization
                    top_hotel_languages = hotel_languages
                    
                    fig = px.bar(
                        top_hotel_languages,
                        x='language_name',
                        y='total_count',
                        text='total_count',
                        title=f"Top Languages by Number of Reviews for {selected_hotel_name}",
                        labels={'language_name': 'Language', 'total_count': 'Number of Reviews'},
                        color='total_count',
                        color_continuous_scale=px.colors.sequential.Greens
                    )
                    
                    fig.update_traces(texttemplate='%{text}', textposition='outside')
                    fig.update_layout(
                        xaxis_title="Language",
                        yaxis_title="Number of Reviews",
                        xaxis={'categoryorder':'total descending'},
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander(f"Show All Languages Data for {selected_hotel_name}"):
                        st.dataframe(
                            hotel_languages, 
                            column_config={
                                "language_name": "Language",
                                "language_code": "Code",
                                "total_count": st.column_config.NumberColumn("Reviews", format="%d")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                else:
                    st.info(f"No language data available for {selected_hotel_name}.")
    else:
        st.info("No hotels with detailed statistics found. Run the scraper to collect more data.")
    
    # Review samples with filtering
    if not reviews_df_latest.empty:
        st.subheader("Reviews Explorer")
        
        # Create tabbed interface for filters
        filter_tab1, filter_tab2 = st.tabs(["Basic Filters", "Advanced Filters"])
        
        with filter_tab1:
            # Basic filters
            col1, col2 = st.columns(2)
            with col1:
                if 'hotel_id' in reviews_df_latest.columns and not hotels_df_latest.empty:
                    hotel_names = hotels_df_latest.set_index('id')['name'].to_dict()
                    hotel_options = ['All Hotels'] + list(hotel_names.values())
                    selected_hotel = st.selectbox("Filter by Hotel", hotel_options)
            
            with col2:
                if 'review_score' in reviews_df_latest.columns:
                    min_score, max_score = float(reviews_df_latest['review_score'].min()), float(reviews_df_latest['review_score'].max())
                    score_range = st.slider("Score Range", min_score, max_score, (min_score, max_score))
        
        with filter_tab2:
            # Advanced filters - language, date, country
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Language filter
                if 'language_code' in reviews_df_latest.columns:
                    available_languages = ['All Languages'] + sorted(reviews_df_latest['language_code'].dropna().unique().tolist())
                    selected_language = st.selectbox("Filter by Language", available_languages)
                else:
                    selected_language = 'All Languages'
            
            with col2:
                # Date filter
                if 'checkin_date' in reviews_df_latest.columns:
                    reviews_df_latest['checkin_date'] = pd.to_datetime(reviews_df_latest['checkin_date'], errors='coerce')
                    min_date = reviews_df_latest['checkin_date'].min()
                    max_date = reviews_df_latest['checkin_date'].max()
                    
                    if pd.notna(min_date) and pd.notna(max_date):
                        date_range = st.date_input(
                            "Date Range",
                            value=(min_date.date(), max_date.date()),
                            min_value=min_date.date(),
                            max_value=max_date.date()
                        )
                        
                        # Handle case where a single date is selected
                        if isinstance(date_range, tuple) and len(date_range) == 2:
                            start_date, end_date = date_range
                        else:
                            start_date = end_date = date_range
                    else:
                        start_date = end_date = None
                        st.info("No valid dates available in the data.")
                else:
                    start_date = end_date = None
                    st.info("No date information available.")
            
            with col3:
                # Country filter
                if 'country_name' in reviews_df_latest.columns:
                    available_countries = ['All Countries'] + sorted(reviews_df_latest['country_name'].dropna().unique().tolist())
                    selected_country = st.selectbox("Filter by Country", available_countries)
                else:
                    selected_country = 'All Countries'
        
        # Apply filters
        filtered_df = reviews_df_latest.copy()
        
        # Hotel filter
        if 'hotel_id' in filtered_df.columns and selected_hotel != 'All Hotels':
            try:
                hotel_id = [k for k, v in hotel_names.items() if v == selected_hotel][0]
                filtered_df = filtered_df[filtered_df['hotel_id'] == hotel_id]
            except IndexError:
                st.error(f"Could not find hotel ID for '{selected_hotel}'. Please refresh the data.")
        
        # Score filter
        if 'review_score' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['review_score'] >= score_range[0]) & 
                (filtered_df['review_score'] <= score_range[1])
            ]
        
        # Language filter
        if 'language_code' in filtered_df.columns and selected_language != 'All Languages':
            filtered_df = filtered_df[filtered_df['language_code'] == selected_language]
        
        # Date filter
        if 'checkin_date' in filtered_df.columns and start_date and end_date:
            start_datetime = pd.Timestamp(start_date)
            end_datetime = pd.Timestamp(end_date)
            filtered_df = filtered_df[
                (filtered_df['checkin_date'] >= start_datetime) & 
                (filtered_df['checkin_date'] <= end_datetime)
            ]
        
        # Country filter
        if 'country_name' in filtered_df.columns and selected_country != 'All Countries':
            filtered_df = filtered_df[filtered_df['country_name'] == selected_country]
        
        # Pagination
        total_reviews = len(filtered_df)
        page_size = 10  # Number of reviews per page
        
        st.write(f"Found {total_reviews} reviews matching your criteria.")
        
        # Calculate total pages
        total_pages = max(1, (total_reviews + page_size - 1) // page_size)
        
        # Page selector
        col1, col2 = st.columns([3, 1])
        with col1:
            # Only show pagination if we have multiple pages
            if total_pages > 1:
                page_number = st.slider("Page", 1, total_pages, 1)
            else:
                page_number = 1
        
        with col2:
            page_size = st.selectbox("Reviews per page", [10, 20, 50, 100], index=0)
        
        # Display reviews
        excluded_cols = ['raw_json', 'hotel_id', 'id', 'review_url', 'photo_urls', 'created_at']
        
        # Select columns that are most useful for display
        preferred_cols = ['reviewer_name', 'review_title', 'review_text', 'review_score', 
                         'checkin_date', 'language_code', 'country_name', 'customer_type']
        
        # Filter to available columns
        display_cols = [col for col in preferred_cols if col in filtered_df.columns]
        
        # Add any other columns not in excluded_cols
        display_cols += [col for col in filtered_df.columns if col not in excluded_cols and col not in display_cols]
        
        # Calculate slice indices
        start_idx = (page_number - 1) * page_size
        end_idx = min(start_idx + page_size, total_reviews)
        
        # Handle the case when there are no reviews after filtering
        if filtered_df.empty:
            st.warning("No reviews match your filter criteria.")
        else:
            # Format for better display
            display_df = filtered_df.iloc[start_idx:end_idx].copy()
            
            # Format date columns
            if 'checkin_date' in display_df.columns:
                display_df['checkin_date'] = pd.to_datetime(display_df['checkin_date']).dt.strftime('%Y-%m-%d')
            
            # Show dataframe with pagination
            st.dataframe(
                display_df[display_cols],
                use_container_width=True,
                column_config={
                    "reviewer_name": "Reviewer",
                    "review_title": "Title",
                    "review_text": st.column_config.TextColumn("Review Text", width="large"),
                    "review_score": st.column_config.NumberColumn("Score", format="%.1f"),
                    "checkin_date": "Date",
                    "language_code": "Language",
                    "country_name": "Country",
                    "customer_type": "Customer Type"
                },
                hide_index=True
            )
            
            # Pagination info
            st.caption(f"Showing reviews {start_idx+1} to {end_idx} of {total_reviews}")
            
            # Export button
            if st.button("Export Filtered Reviews to Excel"):
                # Create Excel file with the filtered data
                excel_filename = f"filtered_reviews_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                excel_path = os.path.join("output", "excel", excel_filename)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(excel_path), exist_ok=True)
                
                # Write to Excel
                filtered_df.to_excel(excel_path, index=False)
                
                # Create download button
                with open(excel_path, "rb") as f:
                    excel_bytes = f.read()
                
                st.download_button(
                    label="📥 Download Excel File",
                    data=excel_bytes,
                    file_name=excel_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download the filtered reviews as an Excel file"
                )
# --- Main app layout ---
# Based on selected view in navigation, show different content
if st.session_state['app_view'] == 'scraper':
    # Display scraper interface and get the command
    cmd = display_scraper_interface()
    
    # Run the scraper when the button is clicked
    if run_btn:
        # Create expandable section for command output
        with st.expander("Command Execution", expanded=True):
            st.code(f"Running: {' '.join(cmd)}", language="bash")
            
            # Progress indicators
            progress_container = st.container()
            
            # Animated progress bar (indeterminate)
            progress_bar = progress_container.progress(0)
            
            # Live output display with auto-scroll
            st.markdown("### Live Output")
            output_container = st.empty()
            output_lines = []
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            # Start the process
            with st.spinner("Scraper is running..."):
                start_time = time.time()
                proc = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    encoding="utf-8", 
                    env=env
                )
                
                # Read output and update display
                for line in proc.stdout:
                    # Add line to buffer
                    output_lines.append(line)
                    
                    # Update output display (last 20 lines only to prevent slowdown)
                    output_container.code("".join(output_lines[-20:]), language="bash")
                    
                    # Update progress bar animation
                    progress_value = (time.time() - start_time) % 1
                    progress_bar.progress(progress_value)
                
                # Wait for process completion
                return_code = proc.wait()
            
            # Final progress update
            progress_bar.progress(100)
            
            # Show final status
            elapsed_time = time.time() - start_time
            
            # Extract results from output
            results = extract_scraper_results(output_lines)
            results['elapsed_time'] = f"{elapsed_time:.1f} seconds"
            results['return_code'] = return_code
            
            if return_code == 0:
                st.success(f"✅ Scraper completed successfully in {elapsed_time:.1f} seconds!")
                
                if 'reviews' in results:
                    st.info(f"📊 Scraped {results.get('reviews', 0)} reviews from {results.get('hotels', 0)} hotels")
                
                # Record this successful configuration to prevent duplicates
                current_config = {k: st.session_state[k] for k in [
                    'urls', 'sort', 'page_size', 'start_page', 'max_pages', 
                    'languages', 'time_of_year', 'customer_type', 'review_score'
                ]}
                mark_config_as_run(current_config, results)
                
                # Force refresh of metrics in the UI - need to do this as metrics won't auto-update otherwise
                refresh_data()
                
                # Rerun the app to ensure everything is refreshed
                st.rerun()
            else:
                st.error(f"❌ Scraper failed with return code {return_code}")
                
                # Still record the failed run to prevent duplicate attempts
                current_config = {k: st.session_state[k] for k in [
                    'urls', 'sort', 'page_size', 'start_page', 'max_pages', 
                    'languages', 'time_of_year', 'customer_type', 'review_score'
                ]}
                results['failed'] = True
                mark_config_as_run(current_config, results)
                
                # Force refresh of data
                refresh_data()
            
            # Show full output in collapsible
            with st.expander("Full Process Output", expanded=False):
                st.code("".join(output_lines), language="bash")
        
        # Reload data after scraping
        refresh_data()
        # Update our local variables to match the refreshed session state
        hotels_df = st.session_state['hotels_df']
        reviews_df = st.session_state['reviews_df']
        
        # Show a summary of what was scraped
        st.subheader("📊 Scraping Results")
        col1, col2 = st.columns(2)
        
        with col1:
            # Always access directly from session state for latest counts
            hotels_count = len(st.session_state['hotels_df']) if not st.session_state['hotels_df'].empty else 0
            reviews_count = len(st.session_state['reviews_df']) if not st.session_state['reviews_df'].empty else 0
            
            if hotels_count > 0:
                st.metric("Hotels Scraped", hotels_count)
            if reviews_count > 0:
                st.metric("Reviews Collected", reviews_count)
        
        with col2:
            if st.session_state['save_to_excel'] and os.path.exists(os.path.join("output", "excel", st.session_state['excel_name'])):
                st.success(f"✅ Excel file saved: {st.session_state['excel_name']}")
                excel_path = os.path.join("output", "excel", st.session_state['excel_name'])
                try:
                    with open(excel_path, "rb") as file:
                        excel_data = file.read()
                    st.download_button(
                        label="📥 Download Excel File",
                        data=excel_data,
                        file_name=st.session_state['excel_name'],
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Download the generated Excel file with all the scraped data"
                    )
                except Exception as e:
                    st.error(f"Error reading Excel file: {str(e)}")
            
            if st.session_state['download_images']:
                st.success("✅ Images downloaded to output/photos folder")
        
        # Show button to view results
        if not hotels_df.empty:
            if st.button(
                label="📊 View Results",
                use_container_width=True,
                help="Switch to the Results view to see detailed analysis of the scraped data"
            ):
                st.session_state['app_view'] = 'results'
                st.rerun()

else:
    # Results view
    display_results_overview()

