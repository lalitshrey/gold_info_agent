"""
Database configuration and connection module for stock_news_agent.
Handles MySQL database connections and provides database utilities.
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, DateTime, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import mysql.connector
from mysql.connector import Error

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'stock_news_db'),
    'charset': 'utf8mb4',
    'autocommit': True
}

# SQLAlchemy Base
Base = declarative_base()

class NiftyStock(Base):
    """SQLAlchemy model for Nifty stocks table."""
    __tablename__ = 'nifty_stocks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

class DatabaseManager:
    """Database connection and management class."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DB_CONFIG
        self.engine = None
        self.SessionLocal = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection."""
        try:
            # Create connection string
            connection_string = (
                f"mysql+pymysql://{self.config['user']}:{self.config['password']}"
                f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
                f"?charset={self.config['charset']}"
            )
            
            # Create engine
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            logger.info(f"Database connection initialized for {self.config['database']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def get_session(self):
        """Get database session."""
        if not self.SessionLocal:
            self._initialize_connection()
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                return result.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def create_database_if_not_exists(self):
        """Create database if it doesn't exist."""
        try:
            # Connect without specifying database
            temp_config = self.config.copy()
            temp_config.pop('database', None)
            
            connection_string = (
                f"mysql+pymysql://{temp_config['user']}:{temp_config['password']}"
                f"@{temp_config['host']}:{temp_config['port']}"
                f"?charset={temp_config['charset']}"
            )
            
            temp_engine = create_engine(connection_string)
            
            with temp_engine.connect() as connection:
                # Create database if not exists
                connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}"))
                connection.commit()
            
            temp_engine.dispose()
            logger.info(f"Database {self.config['database']} created or verified")
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise
    
    def create_tables(self):
        """Create all tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("All tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all tables."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("All tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

# Global database manager instance
db_manager = DatabaseManager()

def get_db_session():
    """Get database session for dependency injection."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

def init_database():
    """Initialize database with tables."""
    try:
        db_manager.create_database_if_not_exists()
        db_manager.create_tables()
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

def get_nifty_stocks_from_db(limit: Optional[int] = None, sector: Optional[str] = None) -> list:
    """Fetch Nifty stocks from database."""
    session = db_manager.get_session()
    try:
        query = session.query(NiftyStock)
        
        if sector:
            query = query.filter(NiftyStock.sector == sector)
        
        if limit:
            query = query.limit(limit)
        
        stocks = query.all()
        return [
            {
                'symbol': stock.symbol,
                'name': stock.name,
                'sector': stock.sector,
                'market_cap': stock.market_cap
            }
            for stock in stocks
        ]
    except Exception as e:
        logger.error(f"Failed to fetch stocks from database: {e}")
        return []
    finally:
        session.close()

def get_stock_symbols_from_db(limit: Optional[int] = None) -> list:
    """Get list of stock symbols from database."""
    session = db_manager.get_session()
    try:
        query = session.query(NiftyStock.symbol)
        
        if limit:
            query = query.limit(limit)
        
        symbols = query.all()
        return [symbol[0] for symbol in symbols]
    except Exception as e:
        logger.error(f"Failed to fetch stock symbols from database: {e}")
        return []
    finally:
        session.close()

if __name__ == "__main__":
    # Test database connection
    if init_database():
        print("Database initialized successfully")
        if db_manager.test_connection():
            print("Database connection test passed")
        else:
            print("Database connection test failed")
    else:
        print("Database initialization failed")
