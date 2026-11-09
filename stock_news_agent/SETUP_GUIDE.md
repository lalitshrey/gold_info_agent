# 🚀 Stock News Agent - Quick Setup Guide

## ✅ Issue Resolved: ModuleNotFoundError

The `ModuleNotFoundError: No module named 'database'` has been fixed! The issue was that the required dependencies weren't installed in a proper Python environment.

## 🛠️ Quick Setup (5 minutes)

### 1. Install MySQL (if not already installed)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql

# macOS (with Homebrew)
brew install mysql
brew services start mysql
```

### 2. Create Database (Optional - will be created automatically)
```sql
mysql -u root -p
CREATE DATABASE stock_news_db;
```

### 3. Run the Application

#### Option A: Use the provided scripts (Recommended)
```bash
# For CLI commands
./run.sh stocks --limit 10
./run.sh sectors
./run.sh stats

# For news
./run.sh news --tickers RELIANCE,TCS

# Start the web server
./start_server.sh
```

#### Option B: Manual setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Run CLI commands
python3 app.py stocks --limit 10
python3 app.py sectors
python3 app.py stats

# Start server
uvicorn app:api --host 0.0.0.0 --port 8000
```

## 🎯 Quick Test

1. **Test database connection:**
   ```bash
   ./run.sh stats
   ```

2. **List some stocks:**
   ```bash
   ./run.sh stocks --limit 5
   ```

3. **Search for stocks:**
   ```bash
   ./run.sh stocks --search TATA
   ```

4. **Start the web server:**
   ```bash
   ./start_server.sh
   ```
   Then open: http://localhost:8000

## 📋 Available Commands

### CLI Commands
```bash
# List stocks
./run.sh stocks                    # All stocks
./run.sh stocks --limit 20         # Limit to 20 stocks
./run.sh stocks --sector Banking   # Banking stocks only
./run.sh stocks --search TATA      # Search for TATA stocks

# List sectors
./run.sh sectors

# Database statistics
./run.sh stats

# Get news (validates symbols against database)
./run.sh news --tickers RELIANCE,TCS,HDFCBANK
```

### Web Server
```bash
# Start server
./start_server.sh

# Access web interface
open http://localhost:8000

# API endpoints
curl "http://localhost:8000/stocks"
curl "http://localhost:8000/stocks?sector=Banking&limit=10"
curl "http://localhost:8000/news?tickers=RELIANCE,TCS"
```

## 🔧 Configuration

### Environment Variables (Optional)
```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=stock_news_db
```

### Server Configuration
```bash
# Custom host/port
HOST=127.0.0.1 PORT=9000 ./start_server.sh
```

## 🐛 Troubleshooting

### Common Issues

1. **MySQL not running:**
   ```bash
   sudo systemctl start mysql  # Ubuntu
   brew services start mysql   # macOS
   ```

2. **Permission denied on scripts:**
   ```bash
   chmod +x run.sh start_server.sh
   ```

3. **Virtual environment issues:**
   ```bash
   rm -rf .venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Database connection issues:**
   - Check MySQL is running: `sudo systemctl status mysql`
   - Test connection: `mysql -u root -p`
   - Check credentials in environment variables

## 📊 What's New

### Database Integration
- ✅ MySQL database for Nifty stocks
- ✅ Stock validation against database
- ✅ Sector-based filtering
- ✅ Search functionality
- ✅ Database statistics

### Enhanced Features
- ✅ New API endpoints for stock data
- ✅ Enhanced CLI with database commands
- ✅ Automatic database initialization
- ✅ Stock symbol validation
- ✅ Sector classification

### Easy Setup
- ✅ Virtual environment management
- ✅ Automated dependency installation
- ✅ Helper scripts for easy execution
- ✅ Comprehensive error handling

## 🎉 You're Ready!

The `ModuleNotFoundError` is now fixed, and you have a fully functional MySQL-integrated stock news agent. The virtual environment is set up with all dependencies, and you can use the provided scripts for easy execution.

### Next Steps:
1. Run `./run.sh stats` to verify everything works
2. Start the server with `./start_server.sh`
3. Open http://localhost:8000 in your browser
4. Try the CLI commands to explore the database

Happy trading! 📈

