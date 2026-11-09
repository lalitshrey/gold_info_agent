"""
Stock service module for fetching Nifty stocks from MySQL database.
Provides high-level functions for the stock_news_agent to interact with the database.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from database import db_manager, NiftyStock, get_nifty_stocks_from_db, get_stock_symbols_from_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockService:
    """Service class for stock-related database operations."""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def get_all_stocks(self, limit: Optional[int] = None) -> List[Dict[str, any]]:
        """Get all Nifty stocks from database."""
        try:
            return get_nifty_stocks_from_db(limit=limit)
        except Exception as e:
            logger.error(f"Error fetching all stocks: {e}")
            return []
    
    def get_stock_symbols(self, limit: Optional[int] = None) -> List[str]:
        """Get list of stock symbols from database."""
        try:
            return get_stock_symbols_from_db(limit=limit)
        except Exception as e:
            logger.error(f"Error fetching stock symbols: {e}")
            return []
    
    def get_stocks_by_sector(self, sector: str, limit: Optional[int] = None) -> List[Dict[str, any]]:
        """Get stocks filtered by sector."""
        try:
            return get_nifty_stocks_from_db(limit=limit, sector=sector)
        except Exception as e:
            logger.error(f"Error fetching stocks by sector {sector}: {e}")
            return []
    
    def get_stock_by_symbol(self, symbol: str) -> Optional[Dict[str, any]]:
        """Get a specific stock by its symbol."""
        session = self.db_manager.get_session()
        try:
            stock = session.query(NiftyStock).filter(NiftyStock.symbol == symbol.upper()).first()
            if stock:
                return {
                    'symbol': stock.symbol,
                    'name': stock.name,
                    'sector': stock.sector,
                    'market_cap': stock.market_cap
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching stock by symbol {symbol}: {e}")
            return None
        finally:
            session.close()
    
    def search_stocks(self, query: str, limit: Optional[int] = None) -> List[Dict[str, any]]:
        """Search stocks by name or symbol."""
        session = self.db_manager.get_session()
        try:
            search_term = f"%{query.upper()}%"
            stocks = session.query(NiftyStock).filter(
                (NiftyStock.symbol.like(search_term)) | 
                (NiftyStock.name.like(f"%{query}%"))
            )
            
            if limit:
                stocks = stocks.limit(limit)
            
            return [
                {
                    'symbol': stock.symbol,
                    'name': stock.name,
                    'sector': stock.sector,
                    'market_cap': stock.market_cap
                }
                for stock in stocks.all()
            ]
        except Exception as e:
            logger.error(f"Error searching stocks with query {query}: {e}")
            return []
        finally:
            session.close()
    
    def get_top_stocks_by_market_cap(self, limit: int = 50) -> List[Dict[str, any]]:
        """Get top stocks by market cap (if available)."""
        session = self.db_manager.get_session()
        try:
            stocks = session.query(NiftyStock).filter(
                NiftyStock.market_cap.isnot(None)
            ).order_by(NiftyStock.market_cap.desc()).limit(limit)
            
            return [
                {
                    'symbol': stock.symbol,
                    'name': stock.name,
                    'sector': stock.sector,
                    'market_cap': stock.market_cap
                }
                for stock in stocks.all()
            ]
        except Exception as e:
            logger.error(f"Error fetching top stocks by market cap: {e}")
            return []
        finally:
            session.close()
    
    def get_stocks_by_sectors(self, sectors: List[str], limit: Optional[int] = None) -> Dict[str, List[Dict[str, any]]]:
        """Get stocks grouped by sectors."""
        result = {}
        for sector in sectors:
            result[sector] = self.get_stocks_by_sector(sector, limit)
        return result
    
    def get_available_sectors(self) -> List[str]:
        """Get list of available sectors."""
        session = self.db_manager.get_session()
        try:
            sectors = session.query(NiftyStock.sector).filter(
                NiftyStock.sector.isnot(None)
            ).distinct().all()
            return [sector[0] for sector in sectors if sector[0]]
        except Exception as e:
            logger.error(f"Error fetching available sectors: {e}")
            return []
        finally:
            session.close()
    
    def get_stock_count(self) -> int:
        """Get total number of stocks in database."""
        session = self.db_manager.get_session()
        try:
            return session.query(NiftyStock).count()
        except Exception as e:
            logger.error(f"Error getting stock count: {e}")
            return 0
        finally:
            session.close()
    
    def get_stock_count_by_sector(self) -> Dict[str, int]:
        """Get count of stocks by sector."""
        session = self.db_manager.get_session()
        try:
            from sqlalchemy import func
            result = session.query(
                NiftyStock.sector, 
                func.count(NiftyStock.id)
            ).group_by(NiftyStock.sector).all()
            
            return {sector: count for sector, count in result if sector}
        except Exception as e:
            logger.error(f"Error getting stock count by sector: {e}")
            return {}
        finally:
            session.close()
    
    def validate_symbols(self, symbols: List[str]) -> Tuple[List[str], List[str]]:
        """Validate list of symbols and return valid and invalid ones."""
        session = self.db_manager.get_session()
        try:
            valid_symbols = []
            invalid_symbols = []
            
            for symbol in symbols:
                stock = session.query(NiftyStock).filter(
                    NiftyStock.symbol == symbol.upper()
                ).first()
                
                if stock:
                    valid_symbols.append(symbol.upper())
                else:
                    invalid_symbols.append(symbol)
            
            return valid_symbols, invalid_symbols
        except Exception as e:
            logger.error(f"Error validating symbols: {e}")
            return [], symbols
        finally:
            session.close()

# Global stock service instance
stock_service = StockService()

# Convenience functions for easy access
def get_nifty_stocks(limit: Optional[int] = None) -> List[Dict[str, any]]:
    """Get all Nifty stocks."""
    return stock_service.get_all_stocks(limit)

def get_nifty_symbols(limit: Optional[int] = None) -> List[str]:
    """Get list of Nifty stock symbols."""
    return stock_service.get_stock_symbols(limit)

def get_stocks_by_sector(sector: str, limit: Optional[int] = None) -> List[Dict[str, any]]:
    """Get stocks by sector."""
    return stock_service.get_stocks_by_sector(sector, limit)

def search_nifty_stocks(query: str, limit: Optional[int] = None) -> List[Dict[str, any]]:
    """Search Nifty stocks."""
    return stock_service.search_stocks(query, limit)

def validate_nifty_symbols(symbols: List[str]) -> Tuple[List[str], List[str]]:
    """Validate Nifty stock symbols."""
    return stock_service.validate_symbols(symbols)

def get_nifty_sectors() -> List[str]:
    """Get available sectors."""
    return stock_service.get_available_sectors()

def get_nifty_stats() -> Dict[str, any]:
    """Get Nifty database statistics."""
    return {
        'total_stocks': stock_service.get_stock_count(),
        'sectors': stock_service.get_available_sectors(),
        'stocks_by_sector': stock_service.get_stock_count_by_sector()
    }

if __name__ == "__main__":
    # Test the stock service
    print("Testing Stock Service...")
    
    # Test database connection
    if not db_manager.test_connection():
        print("❌ Database connection failed")
        exit(1)
    
    print("✅ Database connection successful")
    
    # Test basic functions
    stats = get_nifty_stats()
    print(f"📊 Database Stats: {stats}")
    
    # Test getting symbols
    symbols = get_nifty_symbols(limit=10)
    print(f"📈 Sample symbols: {symbols}")
    
    # Test searching
    search_results = search_nifty_stocks("TATA", limit=5)
    print(f"🔍 Search results for 'TATA': {len(search_results)} found")
    for stock in search_results:
        print(f"  - {stock['symbol']}: {stock['name']}")
    
    # Test sector filtering
    sectors = get_nifty_sectors()
    print(f"🏢 Available sectors: {sectors[:5]}...")  # Show first 5
    
    if sectors:
        banking_stocks = get_stocks_by_sector("Banking", limit=3)
        print(f"🏦 Banking stocks: {len(banking_stocks)} found")
        for stock in banking_stocks:
            print(f"  - {stock['symbol']}: {stock['name']}")
    
    print("✅ Stock service test completed successfully!")
