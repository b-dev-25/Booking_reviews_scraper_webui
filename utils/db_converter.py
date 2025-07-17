"""
Enhanced utility functions to convert database tables to CSV or Excel files.
This module supports converting single or multiple tables, with Excel support
for multiple sheets named after table names.

Usage:
    from utils.db_to_csv import db_to_file, db_to_csv, db_to_excel

    # Convert a single table to CSV
    db_to_csv('path/to/database.db', 'table_name', 'output.csv')

    # Convert multiple tables to Excel
    db_to_excel('path/to/database.db', ['table1', 'table2'], 'output.xlsx')

    # Convert all tables to Excel
    db_to_file('path/to/database.db', output_path='all_tables.xlsx')
"""
import pandas as pd
import sqlalchemy as sa
from loguru import logger
from pathlib import Path
from typing import List, Optional, Union, Dict
import os


def get_all_table_names(db_path: str) -> List[str]:
    """
    Get all table names from the database.
    
    :param db_path: Path to the SQLite database file.
    :return: List of table names in the database.
    """
    try:
        engine = sa.create_engine('sqlite:///' + db_path)
        inspector = sa.inspect(engine)
        table_names = inspector.get_table_names()
        engine.dispose()
        return table_names
    except Exception as e:
        logger.error(f"Error getting table names from database '{db_path}': {e}")
        return []


def validate_inputs(db_path: str, table_names: Union[str, List[str]], output_path: str) -> tuple:
    """
    Validate input parameters.
    
    :param db_path: Path to the SQLite database file.
    :param table_names: Single table name or list of table names.
    :param output_path: Path where the output file will be saved.
    :return: Tuple of (validated_db_path, validated_table_names, output_format)
    """
    # Validate database path
    if not db_path.endswith('.db'):
        raise ValueError("The database path must point to a valid SQLite database file ending with '.db'.")
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file '{db_path}' does not exist.")
    
    # Validate table names
    if isinstance(table_names, str):
        table_names = [table_names]
    
    if not table_names or (isinstance(table_names, list) and len(table_names) == 0):
        raise ValueError("At least one table name must be provided.")
    
    # Determine output format
    output_path = Path(output_path)
    if output_path.suffix.lower() not in ['.csv', '.xlsx']:
        raise ValueError("Output file must have .csv or .xlsx extension.")
    
    output_format = output_path.suffix.lower()[1:]  # Remove the dot
    
    # For CSV, only allow single table
    if output_format == 'csv' and len(table_names) > 1:
        raise ValueError("CSV format only supports single table export. Use Excel format for multiple tables.")
    
    return db_path, table_names, output_format


def db_table_to_dataframe(engine: sa.Engine, table_name: str) -> Optional[pd.DataFrame]:
    """
    Read a single table from database into a DataFrame.
    
    :param engine: SQLAlchemy engine.
    :param table_name: Name of the table to read.
    :return: DataFrame containing the table data, or None if error.
    """
    try:
        # Check if table exists
        if not sa.inspect(engine).has_table(table_name):
            logger.error(f"Table '{table_name}' does not exist in the database.")
            return None
        
        # Read the table
        logger.debug(f"Reading table '{table_name}'...")
        df = pd.read_sql_table(table_name, engine)
        
        if df.empty:
            logger.warning(f"Table '{table_name}' is empty.")
        else:
            logger.debug(f"Table '{table_name}' has {len(df)} rows and {len(df.columns)} columns.")
        
        return df
        
    except Exception as e:
        logger.error(f"Error reading table '{table_name}': {e}")
        return None


def db_to_csv(db_path: str, table_name: str, csv_path: str) -> bool:
    """
    Convert a single database table to a CSV file.

    :param db_path: Path to the SQLite database file.
    :param table_name: Name of the table to convert.
    :param csv_path: Path where the CSV file will be saved.
    :return: True if successful, False otherwise.
    """
    try:
        db_path, table_names, _ = validate_inputs(db_path, table_name, csv_path)
        
        # Connect to database
        engine = sa.create_engine('sqlite:///' + db_path)
        logger.info(f"Connected to database '{db_path}'")
        
        # Read table
        df = db_table_to_dataframe(engine, table_names[0])
        if df is None:
            return False
        
        # Write to CSV
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"Table '{table_names[0]}' exported to '{csv_path}' successfully.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error converting table to CSV: {e}")
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()
            logger.debug("Database connection closed.")


def db_to_excel(db_path: str, 
                table_names: Union[str, List[str]], 
                excel_path: str,
                sheet_names: Optional[Dict[str, str]] = None) -> bool:
    """
    Convert one or multiple database tables to an Excel file with separate sheets.

    :param db_path: Path to the SQLite database file.
    :param table_names: Single table name or list of table names to convert.
    :param excel_path: Path where the Excel file will be saved.
    :param sheet_names: Optional dictionary mapping table names to custom sheet names.
    :return: True if successful, False otherwise.
    """
    try:
        db_path, table_names, _ = validate_inputs(db_path, table_names, excel_path)
        
        # Connect to database
        engine = sa.create_engine('sqlite:///' + db_path)
        logger.info(f"Connected to database '{db_path}'")
        
        # Prepare Excel writer
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            successful_exports = 0
            
            for table_name in table_names:
                # Read table
                df = db_table_to_dataframe(engine, table_name)
                if df is None:
                    continue
                
                # Determine sheet name
                if sheet_names and table_name in sheet_names:
                    sheet_name = sheet_names[table_name]
                else:
                    sheet_name = table_name
                
                # Excel sheet names have limitations
                sheet_name = sheet_name[:31]  # Max 31 characters
                sheet_name = sheet_name.replace('/', '_').replace('\\', '_')  # Remove invalid characters
                
                # Write to Excel sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"Table '{table_name}' exported to sheet '{sheet_name}'")
                successful_exports += 1
            
            if successful_exports > 0:
                logger.info(f"Successfully exported {successful_exports} table(s) to '{excel_path}'")
                return True
            else:
                logger.error("No tables were successfully exported.")
                return False
                
    except Exception as e:
        logger.error(f"Error converting tables to Excel: {e}")
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()
            logger.debug("Database connection closed.")


def db_to_file(db_path: str, 
               table_names: Union[str, List[str], None] = None,
               output_path: str = "output.xlsx",
               sheet_names: Optional[Dict[str, str]] = None) -> bool:
    """
    Convert database tables to CSV or Excel file based on output path extension.
    
    :param db_path: Path to the SQLite database file.
    :param table_names: Table name(s) to convert. If None, exports all tables.
    :param output_path: Path where the output file will be saved (.csv or .xlsx).
    :param sheet_names: Optional dictionary mapping table names to custom sheet names (Excel only).
    :return: True if successful, False otherwise.
    """
    try:
        # If no table names provided, get all tables
        if table_names is None:
            all_tables = get_all_table_names(db_path)
            if not all_tables:
                logger.error("No tables found in the database.")
                return False
            table_names = all_tables
            logger.info(f"No tables specified. Will export all {len(table_names)} tables: {table_names}")
        
        # Determine output format and call appropriate function
        output_format = Path(output_path).suffix.lower()[1:]
        
        if output_format == 'csv':
            if isinstance(table_names, list) and len(table_names) > 1:
                logger.error("CSV format only supports single table export.")
                return False
            single_table = table_names[0] if isinstance(table_names, list) else table_names
            return db_to_csv(db_path, single_table, output_path)
        
        elif output_format == 'xlsx':
            return db_to_excel(db_path, table_names, output_path, sheet_names)
        
        else:
            logger.error(f"Unsupported output format: {output_format}")
            return False
            
    except Exception as e:
        logger.error(f"Error in db_to_file: {e}")
        return False


# Example usage:
# if __name__ == "__main__":
    # # Example 1: Single table to CSV
    # db_to_csv('hotels_reviews.db', 'hotels', 'hotels_output.csv')
    
    # # Example 2: Single table to Excel
    # db_to_excel('hotels_reviews.db', 'hotels', 'hotels_output.xlsx')
    
    # Example 3: Multiple specific tables to Excel
    # db_to_excel('hotels_reviews.db', ['hotels', 'reviews'], 'multiple_tables.xlsx')
    
    # # Example 4: All tables to Excel
    # db_to_file('hotels_reviews.db', output_path='all_tables.xlsx')
    
    # # Example 5: Multiple tables with custom sheet names
    # custom_names = {'hotels': 'Hotel_Data', 'reviews': 'Customer_Reviews'}
    # db_to_excel('hotels_reviews.db', ['hotels', 'reviews'], 'custom_names.xlsx', custom_names)
    
    # # Example 6: Automatic format detection
    # db_to_file('hotels_reviews.db', ['hotels'], 'single_table.csv')  # CSV for single table
    # db_to_file('hotels_reviews.db', ['hotels', 'reviews'], 'multi_tables.xlsx')  # Excel for multiple