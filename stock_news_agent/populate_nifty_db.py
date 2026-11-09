"""
Script to populate the MySQL database with Nifty stocks from the existing JSON file.
This script reads the nse_symbols.json file and inserts the data into the nifty_stocks table.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy.exc import IntegrityError

from database import db_manager, NiftyStock, init_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_nse_symbols(json_file_path: str) -> List[Dict[str, Any]]:
    """Load NSE symbols from JSON file."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            symbols = json.load(file)
        logger.info(f"Loaded {len(symbols)} symbols from {json_file_path}")
        return symbols
    except FileNotFoundError:
        logger.error(f"JSON file not found: {json_file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {json_file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading symbols from {json_file_path}: {e}")
        return []

def get_sector_for_symbol(symbol: str) -> str:
    """
    Get sector information for a stock symbol.
    This is a simplified mapping - in a real scenario, you might want to
    fetch this from a more comprehensive data source.
    """
    # Basic sector mapping based on common patterns
    sector_mapping = {
        # Banking
        'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking', 'SBIN': 'Banking',
        'KOTAKBANK': 'Banking', 'AXISBANK': 'Banking', 'INDUSINDBK': 'Banking',
        'BANDHANBNK': 'Banking', 'FEDERALBNK': 'Banking', 'IDFCFIRSTB': 'Banking',
        
        # IT
        'TCS': 'Information Technology', 'INFY': 'Information Technology',
        'HCLTECH': 'Information Technology', 'WIPRO': 'Information Technology',
        'TECHM': 'Information Technology', 'LTIM': 'Information Technology',
        'COFORGE': 'Information Technology', 'MINDTREE': 'Information Technology',
        
        # Pharmaceuticals
        'SUNPHARMA': 'Pharmaceuticals', 'DRREDDY': 'Pharmaceuticals',
        'CIPLA': 'Pharmaceuticals', 'LUPIN': 'Pharmaceuticals',
        'AUROPHARMA': 'Pharmaceuticals', 'DIVISLAB': 'Pharmaceuticals',
        'BIOCON': 'Pharmaceuticals', 'GLENMARK': 'Pharmaceuticals',
        
        # Automobile
        'MARUTI': 'Automobile', 'TATAMOTORS': 'Automobile',
        'M&M': 'Automobile', 'BAJAJ-AUTO': 'Automobile',
        'HEROMOTOCO': 'Automobile', 'EICHERMOT': 'Automobile',
        'TVSMOTOR': 'Automobile', 'ASHOKLEY': 'Automobile',
        
        # Oil & Gas
        'RELIANCE': 'Oil & Gas', 'ONGC': 'Oil & Gas',
        'IOC': 'Oil & Gas', 'BPCL': 'Oil & Gas',
        'HINDPETRO': 'Oil & Gas', 'GAIL': 'Oil & Gas',
        
        # FMCG
        'HINDUNILVR': 'FMCG', 'ITC': 'FMCG', 'NESTLEIND': 'FMCG',
        'BRITANNIA': 'FMCG', 'DABUR': 'FMCG', 'MARICO': 'FMCG',
        'GODREJCP': 'FMCG', 'COLPAL': 'FMCG',
        
        # Metals
        'TATASTEEL': 'Metals', 'HINDALCO': 'Metals', 'JSWSTEEL': 'Metals',
        'SAIL': 'Metals', 'VEDL': 'Metals', 'JINDALSTEL': 'Metals',
        
        # Cement
        'ULTRACEMCO': 'Cement', 'SHREECEM': 'Cement', 'GRASIM': 'Cement',
        'AMBUJACEM': 'Cement', 'JKCEMENT': 'Cement', 'RAMCOCEM': 'Cement',
        
        # Power
        'NTPC': 'Power', 'POWERGRID': 'Power', 'TATAPOWER': 'Power',
        'ADANIPOWER': 'Power', 'TORNTPOWER': 'Power', 'NHPC': 'Power',
        
        # Telecom
        'BHARTIARTL': 'Telecom', 'IDEA': 'Telecom', 'RCOM': 'Telecom',
        
        # Real Estate
        'DLF': 'Real Estate', 'GODREJPROP': 'Real Estate', 'SOBHA': 'Real Estate',
        'BRIGADE': 'Real Estate', 'PRESTIGE': 'Real Estate',
    }
    
    return sector_mapping.get(symbol, 'Others')

def populate_database(symbols: List[Dict[str, Any]], batch_size: int = 100) -> bool:
    """Populate database with stock symbols."""
    session = db_manager.get_session()
    try:
        total_symbols = len(symbols)
        inserted_count = 0
        skipped_count = 0
        
        logger.info(f"Starting to populate database with {total_symbols} symbols")
        
        for i in range(0, total_symbols, batch_size):
            batch = symbols[i:i + batch_size]
            batch_inserted = 0
            batch_skipped = 0
            
            for symbol_data in batch:
                try:
                    # Create NiftyStock object
                    stock = NiftyStock(
                        symbol=symbol_data['symbol'],
                        name=symbol_data['name'],
                        sector=get_sector_for_symbol(symbol_data['symbol']),
                        market_cap=None,  # Could be populated from external API
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    session.add(stock)
                    batch_inserted += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing symbol {symbol_data.get('symbol', 'unknown')}: {e}")
                    batch_skipped += 1
                    continue
            
            try:
                # Commit batch
                session.commit()
                inserted_count += batch_inserted
                skipped_count += batch_skipped
                
                logger.info(f"Batch {i//batch_size + 1}: Inserted {batch_inserted}, Skipped {batch_skipped}")
                
            except IntegrityError as e:
                # Handle duplicate entries
                session.rollback()
                logger.warning(f"Batch {i//batch_size + 1} had integrity errors, rolling back: {e}")
                
                # Try inserting one by one to identify duplicates
                for symbol_data in batch:
                    try:
                        stock = NiftyStock(
                            symbol=symbol_data['symbol'],
                            name=symbol_data['name'],
                            sector=get_sector_for_symbol(symbol_data['symbol']),
                            market_cap=None,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        session.add(stock)
                        session.commit()
                        inserted_count += 1
                    except IntegrityError:
                        session.rollback()
                        skipped_count += 1
                        logger.debug(f"Skipped duplicate symbol: {symbol_data['symbol']}")
                    except Exception as e:
                        session.rollback()
                        skipped_count += 1
                        logger.warning(f"Error inserting {symbol_data['symbol']}: {e}")
        
        logger.info(f"Database population completed. Inserted: {inserted_count}, Skipped: {skipped_count}")
        return True
        
    except Exception as e:
        logger.error(f"Error populating database: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def clear_database() -> bool:
    """Clear all data from nifty_stocks table."""
    session = db_manager.get_session()
    try:
        session.query(NiftyStock).delete()
        session.commit()
        logger.info("Database cleared successfully")
        return True
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def main():
    """Main function to populate the database."""
    # Initialize database
    if not init_database():
        logger.error("Failed to initialize database")
        return False
    
    # Test database connection
    if not db_manager.test_connection():
        logger.error("Database connection test failed")
        return False
    
    # Get the path to the JSON file
    json_file_path = Path(__file__).parent / "static" / "nse_symbols.json"
    
    if not json_file_path.exists():
        logger.error(f"JSON file not found: {json_file_path}")
        return False
    
    # Load symbols from JSON
    symbols = load_nse_symbols(str(json_file_path))
    if not symbols:
        logger.error("No symbols loaded from JSON file")
        return False
    
    # Ask user if they want to clear existing data
    print(f"Found {len(symbols)} symbols in the JSON file.")
    response = input("Do you want to clear existing data before populating? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        if not clear_database():
            logger.error("Failed to clear database")
            return False
    
    # Populate database
    if populate_database(symbols):
        logger.info("Database populated successfully!")
        
        # Verify the data
        session = db_manager.get_session()
        try:
            count = session.query(NiftyStock).count()
            logger.info(f"Total records in database: {count}")
            
            # Show some sample records
            sample_stocks = session.query(NiftyStock).limit(5).all()
            logger.info("Sample records:")
            for stock in sample_stocks:
                logger.info(f"  {stock.symbol}: {stock.name} ({stock.sector})")
                
        finally:
            session.close()
        
        return True
    else:
        logger.error("Failed to populate database")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Database population completed successfully!")
        print("You can now use the stock_news_agent with database integration.")
    else:
        print("\n❌ Database population failed!")
        print("Please check the logs for error details.")
