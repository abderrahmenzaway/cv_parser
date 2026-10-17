# Installation Guide - Multilingual CV Parser

## System Requirements
- Python 3.8 or higher
- MySQL 8.0 or higher
- Windows 10/11 (or Linux/macOS with appropriate adjustments)

## Pre-requisites Installation

### 1. Install Tesseract OCR
**Windows:**
1. Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location: `C:\Program Files\Tesseract-OCR\`
3. Add to PATH: `C:\Program Files\Tesseract-OCR\`

**Linux:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng
```

### 2. Install Poppler for PDF processing
**Windows:**
1. Download from: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract to `C:\poppler`
3. Add `C:\poppler\Library\bin` to PATH

**Linux:**
```bash
sudo apt-get install poppler-utils
```

### 3. Install MySQL
1. Download MySQL 8.0 from: https://dev.mysql.com/downloads/installer/
2. Install with default settings
3. Set root password to `admin` (or update in `flask_app/app.py`)
4. Start MySQL service

## Project Setup

### 1. Clone and Setup Python Environment
```bash
# Navigate to project directory
cd cv_parser

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Start MySQL service (Windows)
net start MySQL80

# Connect to MySQL and create database
mysql -u root -p
```

```sql
CREATE DATABASE cv_parser;
USE cv_parser;

-- Run the schema creation script
SOURCE database/schema.sql;
```

### 3. Configure Application
1. Update database credentials in `flask_app/app.py` if needed
2. Ensure upload directories exist:
   ```bash
   mkdir uploads
   mkdir flask_app/uploads
   ```

### 4. Test Installation
```bash
# Test Tesseract
tesseract --version

# Test Python dependencies
python -c "import torch, transformers, pdfplumber, pytesseract; print('All dependencies loaded successfully')"

# Start the application
cd flask_app
python app.py
```

## Troubleshooting

### Common Issues:

1. **Tesseract not found:**
   - Ensure Tesseract is in PATH
   - Set environment variable: `TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata`

2. **PDF2Image errors:**
   - Ensure Poppler is in PATH
   - Test with: `python -c "from pdf2image import convert_from_path; print('PDF2Image working')"`

3. **MySQL connection errors:**
   - Verify MySQL service is running
   - Check credentials in `flask_app/app.py`
   - Ensure database `cv_parser` exists

4. **CUDA/GPU issues:**
   - For CPU-only: Models will automatically fall back to CPU
   - For GPU: Install appropriate CUDA version matching PyTorch

### Environment Variables (Optional)
Create a `.env` file in the root directory:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=admin
DB_NAME=cv_parser
TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
```

## Verification
After installation, test the system by:
1. Accessing http://127.0.0.1:5000
2. Uploading a sample CV
3. Checking the database for extracted data
4. Testing search functionality
