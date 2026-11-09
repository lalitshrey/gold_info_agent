"""
Setup and test script for the MySQL-integrated stock_news_agent.
This script helps set up the database and test the integration.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_mysql_installation():
    """Check if MySQL is installed and running."""
    try:
        result = subprocess.run(['mysql', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ MySQL found: {result.stdout.strip()}")
            return True
        else:
            logger.error("❌ MySQL not found in PATH")
            return False
    except FileNotFoundError:
        logger.error("❌ MySQL not installed or not in PATH")
        return False

def check_python_dependencies():
    """Check if required Python packages are installed."""
    required_packages = [
        'mysql-connector-python',
        'sqlalchemy',
        'pymysql',
        'fastapi',
        'uvicorn',
        'httpx',
        'nltk',
        'feedparser',
        'trafilatura'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✅ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"❌ {package} is not installed")
    
    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        logger.info("Install them with: pip install -r requirements.txt")
        return False
    
    return True

def setup_database_environment():
    """Set up database environment variables."""
    env_vars = {
        'DB_HOST': 'localhost',
        'DB_PORT': '3306',
        'DB_USER': 'root',
        'DB_PASSWORD': '',
        'DB_NAME': 'stock_news_db'
    }
    
    logger.info("📋 Database Configuration:")
    for key, default_value in env_vars.items():
        current_value = os.getenv(key, default_value)
        logger.info(f"  {key}: {current_value}")
        
        if not os.getenv(key):
            logger.info(f"  Setting {key}={default_value}")
            os.environ[key] = default_value
    
    return True

def test_database_connection():
    """Test database connection."""
    try:
        from database import db_manager, init_database
        
        logger.info("🔌 Testing database connection...")
        
        # Initialize database
        if init_database():
            logger.info("✅ Database initialization successful")
        else:
            logger.error("❌ Database initialization failed")
            return False
        
        # Test connection
        if db_manager.test_connection():
            logger.info("✅ Database connection test passed")
            return True
        else:
            logger.error("❌ Database connection test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return False

def populate_database():
    """Populate the database with Nifty stocks."""
    try:
        logger.info("📊 Populating database with Nifty stocks...")
        
        # Import and run the populate script
        from populate_nifty_db import main as populate_main
        
        # Run the populate script
        success = populate_main()
        
        if success:
            logger.info("✅ Database populated successfully")
            return True
        else:
            logger.error("❌ Database population failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error populating database: {e}")
        return False

def test_stock_service():
    """Test the stock service functionality."""
    try:
        logger.info("🧪 Testing stock service...")
        
        from stock_service import (
            get_nifty_stats, get_nifty_symbols, search_nifty_stocks,
            get_stocks_by_sector, validate_nifty_symbols
        )
        
        # Test basic functions
        stats = get_nifty_stats()
        logger.info(f"📈 Database stats: {stats['total_stocks']} stocks, {len(stats['sectors'])} sectors")
        
        # Test getting symbols
        symbols = get_nifty_symbols(limit=5)
        logger.info(f"📋 Sample symbols: {symbols}")
        
        # Test search
        search_results = search_nifty_stocks("TATA", limit=3)
        logger.info(f"🔍 Search results for 'TATA': {len(search_results)} found")
        
        # Test sector filtering
        if stats['sectors']:
            banking_stocks = get_stocks_by_sector("Banking", limit=3)
            logger.info(f"🏦 Banking stocks: {len(banking_stocks)} found")
        
        # Test validation
        test_symbols = ["RELIANCE", "TCS", "INVALID"]
        valid, invalid = validate_nifty_symbols(test_symbols)
        logger.info(f"✅ Validation test: {len(valid)} valid, {len(invalid)} invalid")
        
        logger.info("✅ Stock service tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Stock service test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints (basic import test)."""
    try:
        logger.info("🌐 Testing API endpoints...")
        
        from app import api
        
        # Check if API is properly configured
        if api:
            logger.info("✅ FastAPI app created successfully")
            
            # List available routes
            routes = [route.path for route in api.routes]
            logger.info(f"📋 Available routes: {len(routes)}")
            for route in routes[:10]:  # Show first 10 routes
                logger.info(f"  - {route}")
            if len(routes) > 10:
                logger.info(f"  ... and {len(routes) - 10} more")
            
            return True
        else:
            logger.error("❌ FastAPI app creation failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        return False

def test_cli_commands():
    """Test CLI commands."""
    try:
        logger.info("💻 Testing CLI commands...")
        
        # Test help command
        result = subprocess.run([
            sys.executable, 'app.py', '--help'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            logger.info("✅ CLI help command works")
        else:
            logger.warning(f"⚠️ CLI help command failed: {result.stderr}")
        
        # Test stocks command
        result = subprocess.run([
            sys.executable, 'app.py', 'stocks', '--limit', '5'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            logger.info("✅ CLI stocks command works")
        else:
            logger.warning(f"⚠️ CLI stocks command failed: {result.stderr}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ CLI test failed: {e}")
        return False

def main():
    """Main setup and test function."""
    logger.info("🚀 Starting Stock News Agent Setup and Test")
    logger.info("=" * 50)
    
    # Check prerequisites
    logger.info("📋 Checking prerequisites...")
    
    if not check_mysql_installation():
        logger.error("❌ MySQL installation check failed")
        return False
    
    if not check_python_dependencies():
        logger.error("❌ Python dependencies check failed")
        return False
    
    # Setup environment
    logger.info("\n🔧 Setting up environment...")
    setup_database_environment()
    
    # Test database
    logger.info("\n🗄️ Testing database...")
    if not test_database_connection():
        logger.error("❌ Database setup failed")
        return False
    
    # Populate database
    logger.info("\n📊 Populating database...")
    if not populate_database():
        logger.error("❌ Database population failed")
        return False
    
    # Test services
    logger.info("\n🧪 Testing services...")
    if not test_stock_service():
        logger.error("❌ Stock service test failed")
        return False
    
    # Test API
    logger.info("\n🌐 Testing API...")
    if not test_api_endpoints():
        logger.error("❌ API test failed")
        return False
    
    # Test CLI
    logger.info("\n💻 Testing CLI...")
    test_cli_commands()  # This is optional, don't fail if it doesn't work
    
    # Success summary
    logger.info("\n" + "=" * 50)
    logger.info("🎉 Setup and test completed successfully!")
    logger.info("\n📋 Next steps:")
    logger.info("1. Start the API server: uvicorn app:api --host 0.0.0.0 --port 8000")
    logger.info("2. Open browser: http://localhost:8000")
    logger.info("3. Try CLI commands:")
    logger.info("   - python app.py stocks --limit 10")
    logger.info("   - python app.py sectors")
    logger.info("   - python app.py news --tickers RELIANCE,TCS")
    logger.info("4. Test API endpoints:")
    logger.info("   - GET /stocks")
    logger.info("   - GET /stocks/sectors")
    logger.info("   - GET /news?tickers=RELIANCE,TCS")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        logger.error("\n❌ Setup failed! Please check the errors above.")
        sys.exit(1)
    else:
        logger.info("\n✅ Setup completed successfully!")
        sys.exit(0)
