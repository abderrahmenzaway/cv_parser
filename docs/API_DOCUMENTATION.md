# CV Parser API Documentation

## Overview
The CV Parser is a multilingual web application that extracts structured information from PDF resumes using AI and OCR technologies.

## Features
- **Multilingual Support**: English and French CV processing
- **OCR Fallback**: Handles scanned PDFs with Tesseract OCR
- **AI Processing**: Uses LayoutLMv3, OCR and rule-based parsing for extraction
- **Evaluation Metrics**: Precision, recall, and F1-score calculations
- **Web Interface**: Modern responsive web interface
- **Database Storage**: MySQL backend for candidate data

## Web Interface Endpoints

### Main Routes

#### `GET /`
**Description**: Home page with application overview
**Response**: HTML template with navigation and features

#### `GET /upload`
**Description**: File upload page
**Response**: HTML form for PDF upload
**Form Fields**:
- `file`: PDF file input (required)

#### `POST /upload`
**Description**: Process uploaded CV file
**Content-Type**: `multipart/form-data`
**Parameters**:
- `file`: PDF file (max 16MB)

**Response**:
- **Success**: Redirect to candidates page with success message
- **Error**: Error page with specific error message

**Error Codes**:
- `400`: No file provided or invalid file type
- `413`: File too large
- `500`: Processing error

#### `GET /candidates`
**Description**: View all candidates with pagination and filtering
**Query Parameters**:
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)

**Response**: HTML template with candidate grid/list view

#### `GET /search`
**Description**: Search form page
**Response**: HTML template with search interface

#### `POST /search`
**Description**: Search candidates
**Content-Type**: `application/x-www-form-urlencoded`
**Parameters**:
- `query`: Search term (string)

**Response**: HTML template with filtered results

#### `GET /files`
**Description**: File management page
**Response**: HTML template with uploaded files list

#### `GET /logs`
**Description**: Application logs viewer
**Response**: HTML template with system logs

#### `GET /status`
**Description**: System status and health check
**Response**: HTML template with system information

### Error Handlers

#### `404 Not Found`
**Description**: Page not found
**Response**: Custom 404 error page

#### `413 Request Entity Too Large`
**Description**: File too large
**Response**: Custom error page with file size information

#### `500 Internal Server Error`
**Description**: Server error
**Response**: Custom 500 error page

## Database Schema

### Tables

#### `candidates`
```sql
candidate_id INT PRIMARY KEY AUTO_INCREMENT
first_name VARCHAR(100)
last_name VARCHAR(100)
cv_file_path VARCHAR(500)
created_at TIMESTAMP
updated_at TIMESTAMP
```

#### `contacts`
```sql
contact_id INT PRIMARY KEY AUTO_INCREMENT
candidate_id INT FOREIGN KEY
phone VARCHAR(50)
email VARCHAR(255)
address TEXT
created_at TIMESTAMP
```

#### `educations`
```sql
education_id INT PRIMARY KEY AUTO_INCREMENT
candidate_id INT FOREIGN KEY
description TEXT
created_at TIMESTAMP
```

#### `experiences`
```sql
experience_id INT PRIMARY KEY AUTO_INCREMENT
candidate_id INT FOREIGN KEY
description TEXT
created_at TIMESTAMP
```

#### `projects`
```sql
project_id INT PRIMARY KEY AUTO_INCREMENT
candidate_id INT FOREIGN KEY
projects TEXT
created_at TIMESTAMP
```

#### `skills`
```sql
skill_id INT PRIMARY KEY AUTO_INCREMENT
candidate_id INT FOREIGN KEY
skill_name VARCHAR(255)
skill_type ENUM('technical', 'language', 'extracted')
created_at TIMESTAMP
```

## Processing Pipeline

### 1. File Upload
1. Validate file type (PDF only)
2. Check file size (max 16MB)
3. Generate unique filename
4. Save to uploads directory

### 2. Text Extraction
1. Try direct PDF text extraction using pdfplumber
2. If fails or low quality, fall back to OCR:
   - Convert PDF to images using pdf2image
   - Apply OCR using Tesseract
   - Detect language for appropriate processing

### 3. AI Processing
1. Process extracted text with the local LayoutLMv3 model and rules
2. Extract structured information:
   - Contact details (name, email, phone)
   - Education history
   - Work experience
   - Skills (technical, languages)
   - Projects

### 4. Data Storage
1. Parse JSON output from AI processing
2. Insert into MySQL database using insert.py
3. Handle data validation and error recovery

### 5. Evaluation (Optional)
1. Calculate precision, recall, F1-score
2. Compare with ground truth if available
3. Save evaluation metrics

## Configuration

### Environment Variables
```bash
# Database
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=admin
DB_NAME=cv_parser

# Flask
SECRET_KEY=your-secret-key
FLASK_DEBUG=False
FLASK_HOST=127.0.0.1
FLASK_PORT=5000

# OCR
TESSERACT_CMD=tesseract
TESSDATA_PREFIX=/path/to/tessdata

# AI Models
USE_LOCAL_MODEL=True
MODEL_DEVICE=auto
```

### File Structure
```
cv_parser/
├── flask_app/
│   ├── app.py              # Main Flask application
│   ├── templates/          # HTML templates
│   ├── static/            # CSS, JS, images
│   └── uploads/           # Uploaded files
├── scripts/
│   ├── cv_extractor.py          # AI processing
│   └── insert.py          # Database operations
├── database/
│   └── schema.sql         # Database schema
├── local_layoutlmv3/      # Local AI model
├── tests/                 # Test suite
└── uploads/               # Global upload directory
```

## Usage Examples

### Upload a CV
```bash
curl -X POST http://127.0.0.1:5000/upload \
  -F "file=@resume.pdf"
```

### Search Candidates
```bash
curl -X POST http://127.0.0.1:5000/search \
  -d "query=python developer"
```

### Database Query Example
```sql
-- Find all candidates with Python skills
SELECT c.first_name, c.last_name, s.skill_name
FROM candidates c
JOIN skills s ON c.candidate_id = s.candidate_id
WHERE s.skill_name LIKE '%python%';
```

## Error Handling

### Common Error Scenarios
1. **File Upload Errors**
   - Invalid file type → 400 Bad Request
   - File too large → 413 Request Entity Too Large
   - No file provided → 400 Bad Request

2. **Processing Errors**
   - PDF corruption → OCR fallback attempted
   - AI processing timeout → Error logged, user notified
   - Database connection failure → Error page displayed

3. **OCR Errors**
   - Tesseract not found → Clear error message
   - Language detection failure → Default to English
   - Image conversion failure → Logged and reported

## Performance Considerations

### Optimization Tips
1. **File Size**: Keep PDF files under 16MB for optimal processing
2. **Concurrent Uploads**: System handles one file at a time
3. **Database**: Use indexes for frequent search queries
4. **OCR**: Scanned PDFs take longer to process
5. **Memory**: LayoutLM3 model requires significant RAM

### Monitoring
- Check `/status` endpoint for system health
- Monitor `/logs` for processing errors
- Database connection status
- File system usage in uploads directory

## Development

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test module
python tests/run_tests.py -m test_database

# Run with coverage
python tests/run_tests.py --coverage
```

### Development Server
```bash
cd flask_app
python app.py
```

### Database Setup
```bash
mysql -u root -p < database/schema.sql
```
