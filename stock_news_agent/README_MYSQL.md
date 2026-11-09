# Stock News Agent with MySQL Integration

This enhanced version of the Stock News Agent now includes MySQL database integration for managing Nifty stocks data. The system fetches stock information from a MySQL database instead of using hardcoded tickers.

## 🚀 Features

- **MySQL Database Integration**: Store and manage Nifty stocks in a MySQL database
- **Stock Validation**: Validate ticker symbols against the database
- **Sector-based Filtering**: Filter stocks by sectors (Banking, IT, Pharmaceuticals, etc.)
- **Search Functionality**: Search stocks by name or symbol
- **Enhanced API**: New endpoints for database operations
- **Improved CLI**: Extended command-line interface with database commands
- **Automatic Database Setup**: Scripts to initialize and populate the database

## 📋 Prerequisites

### System Requirements
- Python 3.8+
- MySQL Server 5.7+ or MySQL 8.0+
- Internet connection for fetching news

### Python Dependencies
All dependencies are listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

## 🗄️ Database Setup

### 1. Install MySQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server

# macOS (with Homebrew)
brew install mysql

# Start MySQL service
sudo systemctl start mysql  # Linux
brew services start mysql   # macOS
```

### 2. Create Database User (Optional)
```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create database and user
CREATE DATABASE stock_news_db;
CREATE USER 'stock_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON stock_news_db.* TO 'stock_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Environment Configuration
Set environment variables (optional, defaults provided):
```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=stock_news_db
```

## 🛠️ Installation and Setup

### 1. Clone and Install Dependencies
```bash
cd stock_news_agent
pip install -r requirements.txt
```

### 2. Run Setup Script
```bash
python setup_and_test.py
```

This script will:
- Check MySQL installation
- Verify Python dependencies
- Initialize the database
- Populate with Nifty stocks
- Run comprehensive tests

### 3. Manual Database Population (Alternative)
```bash
python populate_nifty_db.py
```

## 🎯 Usage

### API Server
Start the FastAPI server:
```bash
uvicorn app:api --host 0.0.0.0 --port 8000
```

Access the web interface at: http://localhost:8000

### CLI Commands

#### Get News for Stocks
```bash
# Get news for specific stocks
python app.py news --tickers RELIANCE,TCS,HDFCBANK

# With custom parameters
python app.py news --tickers RELIANCE,TCS --limit 10 --days 3 --json
```

#### List Stocks from Database
```bash
# List all stocks
python app.py stocks

# List with limit
python app.py stocks --limit 20

# Filter by sector
python app.py stocks --sector Banking

# Search stocks
python app.py stocks --search TATA

# Output as JSON
python app.py stocks --limit 10 --json
```

#### List Sectors
```bash
# List all sectors
python app.py sectors

# Output as JSON
python app.py sectors --json
```

#### Database Statistics
```bash
# Show database stats
python app.py stats

# Output as JSON
python app.py stats --json
```

### API Endpoints

#### News Endpoints
- `GET /news?tickers=RELIANCE,TCS&limit=20&days=7` - Get news for specific stocks
- `GET /` - Web interface for news search

#### Stock Database Endpoints
- `GET /stocks` - Get all stocks (with optional limit and sector filter)
- `GET /stocks/symbols` - Get list of stock symbols
- `GET /stocks/search?query=TATA` - Search stocks by name or symbol
- `GET /stocks/sectors` - Get available sectors
- `GET /stocks/sector/{sector}` - Get stocks by specific sector
- `GET /stocks/stats` - Get database statistics
- `GET /stocks/validate?symbols=RELIANCE,TCS` - Validate ticker symbols
- `GET /stocks/{symbol}` - Get specific stock by symbol

#### Example API Calls
```bash
# Get all stocks
curl "http://localhost:8000/stocks"

# Get banking stocks
curl "http://localhost:8000/stocks?sector=Banking&limit=10"

# Search for TATA stocks
curl "http://localhost:8000/stocks/search?query=TATA"

# Get available sectors
curl "http://localhost:8000/stocks/sectors"

# Validate symbols
curl "http://localhost:8000/stocks/validate?symbols=RELIANCE,TCS,INVALID"

# Get news for stocks
curl "http://localhost:8000/news?tickers=RELIANCE,TCS&limit=5"
```

## 📊 Database Schema

### nifty_stocks Table
```sql
CREATE TABLE nifty_stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    market_cap FLOAT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_symbol (symbol)
);
```

## 🔧 Configuration

### Database Configuration
The database configuration is managed in `database.py`:
```python
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'stock_news_db'),
    'charset': 'utf8mb4',
    'autocommit': True
}
```

### Available Sectors
The system includes sector classification for stocks:
- Banking
- Information Technology
- Pharmaceuticals
- Automobile
- Oil & Gas
- FMCG
- Metals
- Cement
- Power
- Telecom
- Real Estate
- And more...

## 🧪 Testing

### Run Comprehensive Tests
```bash
python setup_and_test.py
```

### Test Individual Components
```bash
# Test database connection
python database.py

# Test stock service
python stock_service.py

# Test database population
python populate_nifty_db.py
```

## 🐛 Troubleshooting

### Common Issues

#### 1. MySQL Connection Error
```
Error: Can't connect to MySQL server
```
**Solution**: Ensure MySQL is running and credentials are correct
```bash
sudo systemctl status mysql  # Check MySQL status
mysql -u root -p  # Test connection
```

#### 2. Database Not Found
```
Error: Unknown database 'stock_news_db'
```
**Solution**: Create the database
```sql
CREATE DATABASE stock_news_db;
```

#### 3. Permission Denied
```
Error: Access denied for user
```
**Solution**: Check user permissions
```sql
GRANT ALL PRIVILEGES ON stock_news_db.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 4. Import Errors
```
ModuleNotFoundError: No module named 'mysql'
```
**Solution**: Install missing dependencies
```bash
pip install -r requirements.txt
```

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export PYTHONPATH=.
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
```

## 📈 Performance Considerations

- **Connection Pooling**: The system uses SQLAlchemy connection pooling
- **Indexing**: Database indexes on frequently queried columns
- **Batch Operations**: Bulk operations for database population
- **Caching**: Consider implementing Redis for frequently accessed data

## 🔒 Security Notes

- Change default MySQL root password
- Use environment variables for sensitive configuration
- Implement proper user permissions
- Consider SSL connections for production

## 📝 Development

### Adding New Features
1. Modify `database.py` for schema changes
2. Update `stock_service.py` for business logic
3. Add new endpoints in `app.py`
4. Update CLI commands as needed
5. Add tests in `setup_and_test.py`

### Code Structure
```
stock_news_agent/
├── app.py                 # Main FastAPI application
├── database.py            # Database configuration and models
├── stock_service.py       # Stock service layer
├── populate_nifty_db.py   # Database population script
├── setup_and_test.py      # Setup and testing script
├── requirements.txt       # Python dependencies
├── static/
│   └── nse_symbols.json  # Source data for stocks
└── templates/
    └── index.html        # Web interface template
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is open source. Please check the main project license.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Run the setup and test script
3. Check MySQL logs
4. Verify environment configuration
5. Create an issue with detailed error information
