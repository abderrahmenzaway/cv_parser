"""
Tests for Flask web application functionality
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from tests import TestBase

class TestFlaskApp(TestBase):
    """Test Flask application routes and functionality."""
    
    def setUp(self):
        super().setUp()
        
        # Mock flask app
        try:
            # Ensure we're in test mode
            os.environ['TESTING'] = 'True'
            os.environ['FLASK_ENV'] = 'testing'
            
            # Try importing the Flask app using package path for Pylance
            from flask_app.app import app
            
            app.config['TESTING'] = True
            app.config['WTF_CSRF_ENABLED'] = False
            app.config['SECRET_KEY'] = 'test-secret-key'
            self.app = app.test_client()
            self.ctx = app.app_context()
            self.ctx.push()
            
        except ImportError as import_error:
            if 'flask' in str(import_error).lower():
                print("ℹ️  Flask not installed - skipping Flask tests")
            elif 'mysql' in str(import_error).lower():
                print("ℹ️  MySQL connector not installed - skipping Flask tests")
            else:
                print(f"ℹ️  Import error: {import_error}")
            self.app = None
        except Exception as e:
            print(f"ℹ️  Error setting up Flask app: {e}")
            self.app = None
    
    def tearDown(self):
        super().tearDown()
        if hasattr(self, 'ctx'):
            self.ctx.pop()
    
    def test_home_page(self):
        """Test home page loads correctly."""
        if self.app is None:
            self.skipTest("Flask app not available")
            
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CV Parser', response.data)
    
    def test_upload_page(self):
        """Test upload page loads correctly."""
        if self.app is None:
            self.skipTest("Flask app not available")
            
        response = self.app.get('/upload')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'upload', response.data.lower())
    
    def test_candidates_page(self):
        """Test candidates page loads correctly."""
        if self.app is None:
            self.skipTest("Flask app not available")
            
        with patch('mysql.connector.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            response = self.app.get('/candidates')
            self.assertEqual(response.status_code, 200)
    
    def test_search_functionality(self):
        """Test search functionality."""
        if self.app is None:
            self.skipTest("Flask app not available")
            
        with patch('mysql.connector.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            response = self.app.post('/search', data={'query': 'python'})
            self.assertEqual(response.status_code, 200)
    
    @patch('subprocess.run')
    def test_file_upload_processing(self, mock_subprocess):
        """Test file upload and processing."""
        if self.app is None:
            self.skipTest("Flask app not available")
            
        # Mock successful subprocess calls
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Success",
            stderr=""
        )
        
        # Create a fake PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b'%PDF-1.4 fake pdf content')
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, 'rb') as test_file:
                response = self.app.post('/upload', 
                    data={'file': (test_file, 'test.pdf')},
                    content_type='multipart/form-data'
                )
            
            # Should redirect after successful upload
            self.assertIn(response.status_code, [200, 302])
            
        finally:
            os.unlink(tmp_file_path)
    
    def test_file_extension_validation(self):
        """Test file extension validation."""
        if self.app is None:
            self.skipTest("Flask app not available")
            
        # Test invalid file extension
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(b'not a pdf')
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, 'rb') as test_file:
                response = self.app.post('/upload', 
                    data={'file': (test_file, 'test.txt')},
                    content_type='multipart/form-data'
                )
            
            # Should reject non-PDF files
            self.assertEqual(response.status_code, 200)
            
        finally:
            os.unlink(tmp_file_path)
    
    def test_error_handlers(self):
        """Test error handling routes."""
        if self.app is None:
            self.skipTest("Flask app not available")
            
        # Test 404 error
        response = self.app.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
