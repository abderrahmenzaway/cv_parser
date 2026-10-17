"""
Tests for database operations and insert.py functionality
"""

import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from tests import TestBase

class TestDatabaseOperations(TestBase):
    """Test database insertion and operations."""
    
    def setUp(self):
        super().setUp()
        
        # Mock database connection
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_cursor.lastrowid = 1
        
    @patch('mysql.connector.connect')
    def test_database_connection(self, mock_connect):
        """Test database connection configuration."""
        mock_connect.return_value = self.mock_conn
        
        try:
            from scripts.insert import process_json_to_database
            
            # Create sample JSON file
            sample_data = self.create_sample_json()
            json_file = os.path.join(self.test_dir, "test.json")
            with open(json_file, 'w') as f:
                json.dump(sample_data, f)
            
            db_config = {
                'host': 'localhost',
                'user': 'test',
                'password': 'test',
                'database': 'test_db'
            }
            
            process_json_to_database(json_file, "test_cv.pdf", db_config)
            
            # Verify connection was attempted
            mock_connect.assert_called_once_with(**db_config)
            
        except ImportError as e:
            self.skipTest(f"Could not import insert module: {e}")
    
    @patch('mysql.connector.connect')
    def test_candidate_insertion(self, mock_connect):
        """Test candidate data insertion."""
        mock_connect.return_value = self.mock_conn
        
        try:
            from scripts.insert import validate_and_insert_data
            
            sample_data = self.create_sample_json()
            
            validate_and_insert_data(self.mock_conn, sample_data, "test_cv.pdf")
            
            # Verify candidate insertion was called
            insert_calls = self.mock_cursor.execute.call_args_list
            self.assertTrue(any("INSERT INTO cv_parser.candidates" in str(call) for call in insert_calls))
            
        except ImportError as e:
            self.skipTest(f"Could not import insert module: {e}")
    
    def test_json_validation(self):
        """Test JSON data validation."""
        try:
            from scripts.insert import validate_and_insert_data
            
            # Test missing required fields
            invalid_data = {"contact": {}}
            
            with self.assertRaises(ValueError):
                validate_and_insert_data(self.mock_conn, invalid_data, "test.pdf")
                
        except ImportError as e:
            self.skipTest(f"Could not import insert module: {e}")
    
    def test_file_not_found_handling(self):
        """Test handling of missing JSON files."""
        try:
            from scripts.insert import process_json_to_database
            
            db_config = {'host': 'localhost', 'user': 'test', 'password': 'test', 'database': 'test_db'}
            
            # This should handle the FileNotFoundError gracefully
            process_json_to_database("nonexistent.json", "test.pdf", db_config)
            
        except ImportError as e:
            self.skipTest(f"Could not import insert module: {e}")

if __name__ == "__main__":
    unittest.main()
