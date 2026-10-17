# Configuration file for Multilingual CV Parser
# Copy this file to config.py and modify the values as needed

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.absolute()
UPLOAD_DIR = BASE_DIR / "uploads"
FLASK_UPLOAD_DIR = BASE_DIR / "flask_app" / "uploads"

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'admin'),
    'database': os.getenv('DB_NAME', 'cv_parser'),
    'charset': 'utf8mb4',
    'use_unicode': True,
    'autocommit': True
}

# Flask configuration
FLASK_CONFIG = {
    'SECRET_KEY': os.getenv('SECRET_KEY', 'your-secret-key-change-in-production'),
    'DEBUG': os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
    'HOST': os.getenv('FLASK_HOST', '127.0.0.1'),
    'PORT': int(os.getenv('FLASK_PORT', 5000)),
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024  # 16MB max file size
}

# File processing configuration
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE_MB = 16

# OCR and language detection settings
TESSERACT_CONFIG = {
    'tesseract_cmd': os.getenv('TESSERACT_CMD', 'tesseract'),  # Will use PATH by default
    'languages': ['eng', 'fra'],  # English and French
    'config': '--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
}

# AI Model configuration
MODEL_CONFIG = {
    'local_model_path': BASE_DIR / "local_layoutlmv3",
    'use_local_model': True,  # Set to False to use Hugging Face models
    'device': 'auto',  # 'auto', 'cpu', or 'cuda'
    'max_tokens': 4000,
    'temperature': 0.1
}

# Language detection settings
LANGUAGE_CONFIG = {
    'supported_languages': ['en', 'fr'],
    'default_language': 'en',
    'confidence_threshold': 0.8
}

# Evaluation metrics configuration
EVALUATION_CONFIG = {
    'enable_evaluation': True,
    'ground_truth_required': False,
    'metrics': ['precision', 'recall', 'f1_score'],
    'save_results': True
}

# Logging configuration
LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': BASE_DIR / 'logs' / 'cv_parser.log'
}

# Claude API configuration (if using Claude API instead of local models)
CLAUDE_CONFIG = {
    'api_key': os.getenv('CLAUDE_API_KEY', ''),
    'model': 'claude-3-sonnet-20240229',
    'max_tokens': 4000,
    'temperature': 0.1
}

# Security settings
SECURITY_CONFIG = {
    'allowed_file_types': ['.pdf'],
    'scan_uploads': True,
    'max_daily_uploads_per_ip': 100,
    'rate_limit_per_minute': 10
}

# Feature flags
FEATURES = {
    'multilingual_support': True,
    'ocr_fallback': True,
    'batch_processing': True,
    'api_endpoint': False,  # REST API endpoint
    'real_time_processing': False,
    'advanced_analytics': True
}

# Ensure required directories exist
def create_directories():
    """Create required directories if they don't exist."""
    directories = [
        UPLOAD_DIR,
        FLASK_UPLOAD_DIR,
        BASE_DIR / 'logs',
        BASE_DIR / 'temp',
        BASE_DIR / 'backup'
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    create_directories()
    print("Configuration loaded and directories created successfully.")
