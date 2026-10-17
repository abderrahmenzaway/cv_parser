"""
Test suite for CV Parser application
Run with: python -m pytest tests/
"""

import unittest
import os
import sys
import tempfile
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "flask_app"))
sys.path.insert(0, str(project_root / "scripts"))

# Set test environment variables
os.environ['TESTING'] = 'True'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USER'] = 'test_user'
os.environ['DB_PASSWORD'] = 'test_password'
os.environ['DB_NAME'] = 'test_cv_parser'

class TestBase(unittest.TestCase):
    """Base test class with common setup and teardown."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.project_root = project_root
        self.sample_pdf_path = project_root / "cv_teste.pdf"
        
    def tearDown(self):
        """Clean up after each test method."""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def create_sample_json(self):
        """Create a sample JSON output for testing."""
        return {
            "contact": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890"
            },
            "sections": {
                "education": [
                    {"text": "Master of Computer Science"}
                ],
                "experience": [
                    {"id": 1, "text": "Software Engineer at Tech Corp"}
                ],
                "skills": [
                    {"text": "Python, JavaScript, SQL"}
                ]
            },
            "skills": {
                "technical": ["Python", "JavaScript", "SQL"],
                "languages": ["English", "French"],
                "extracted": ["Programming", "Web Development"]
            }
        }

if __name__ == "__main__":
    unittest.main()
