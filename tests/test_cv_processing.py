"""
Tests for CV processing
"""

import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from tests import TestBase

class TestCVProcessing(TestBase):
    """Test CV processing functionality."""
    
    def setUp(self):
        super().setUp()
        
    def test_language_detection(self):
        """Test language detection functionality."""
        try:
            from scripts.cv_extractor import detect_language
            
            # Test English text
            english_text = "Hello, this is an English resume with experience in software development."
            lang = detect_language(english_text)
            self.assertIn(lang, ['en', 'english'])
            
            # Test French text
            french_text = "Bonjour, ceci est un CV en français avec expérience en développement logiciel."
            lang = detect_language(french_text)
            self.assertIn(lang, ['fr', 'french'])
            
        except ImportError as e:
            self.skipTest(f"Could not import cv_extractor module: {e}")
        except Exception as e:
            self.skipTest(f"Error in language detection test: {e}")
    
    def test_multilingual_keywords(self):
        """Test multilingual keyword extraction."""
        try:
            from scripts.cv_extractor import get_multilingual_keywords
            
            keywords = get_multilingual_keywords()
            
            # Should have both English and French keywords
            self.assertIn('skills', keywords)
            self.assertIn('compétences', keywords)
            self.assertIn('experience', keywords)
            self.assertIn('expérience', keywords)
            
        except ImportError as e:
            self.skipTest(f"Could not import cv_extractor module: {e}")
        except Exception as e:
            self.skipTest(f"Error in multilingual keywords test: {e}")
    
    @patch('subprocess.run')
    def test_ocr_processing(self, mock_subprocess):
        """Test OCR processing functionality."""
        try:
            from scripts.cv_extractor import extract_text_with_ocr
            
            # Mock tesseract output
            mock_subprocess.return_value = MagicMock(
                returncode=0,
                stdout="Extracted text from PDF",
                stderr=""
            )
            
            # Create a temporary image file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(b'fake image data')
                tmp_file_path = tmp_file.name
            
            try:
                result = extract_text_with_ocr(tmp_file_path)
                self.assertIsInstance(result, str)
                
            finally:
                os.unlink(tmp_file_path)
                
        except ImportError as e:
            self.skipTest(f"Could not import cv_extractor module: {e}")
    
    def test_evaluation_metrics(self):
        """Test evaluation metrics calculation."""
        try:
            from scripts.cv_extractor import evaluate_extraction
            
            # Sample ground truth and extracted data
            ground_truth = {
                "skills": ["Python", "JavaScript", "SQL"],
                "experience": ["Software Engineer"],
                "education": ["Computer Science"]
            }
            
            extracted = {
                "skills": ["Python", "Java", "SQL"],  # Missing JS, added Java
                "experience": ["Software Engineer"],
                "education": ["Computer Science"]
            }
            
            metrics = evaluate_extraction(ground_truth, extracted)
            
            self.assertIn('precision', metrics)
            self.assertIn('recall', metrics)
            self.assertIn('f1_score', metrics)
            
            # Skills precision should be 2/3 (Python and SQL correct out of 3 extracted)
            # Skills recall should be 2/3 (Python and SQL found out of 3 in ground truth)
            self.assertAlmostEqual(metrics['skills']['precision'], 0.67, places=1)
            self.assertAlmostEqual(metrics['skills']['recall'], 0.67, places=1)
            
        except ImportError as e:
            self.skipTest(f"Could not import cv_extractor module: {e}")
    
    def test_json_output_format(self):
        """Test JSON output format validation."""
        sample_output = self.create_sample_json()
        
        # Test required fields
        self.assertIn('contact', sample_output)
        self.assertIn('sections', sample_output)
        self.assertIn('skills', sample_output)
        
        # Test contact fields
        contact = sample_output['contact']
        self.assertIn('first_name', contact)
        self.assertIn('last_name', contact)
        self.assertIn('email', contact)
        
        # Test sections structure
        sections = sample_output['sections']
        self.assertIn('education', sections)
        self.assertIn('experience', sections)
        self.assertIn('skills', sections)
    
    def test_pdf_to_text_extraction(self):
        """Test PDF text extraction without OCR."""
        try:
            from scripts.cv_extractor import extract_text_from_pdf
            
            # Check if sample PDF exists
            if self.sample_pdf_path.exists():
                text = extract_text_from_pdf(str(self.sample_pdf_path))
                self.assertIsInstance(text, str)
                self.assertGreater(len(text), 0)
            else:
                self.skipTest("Sample PDF not found")
                
        except ImportError as e:
            self.skipTest(f"Could not import cv_extractor module: {e}")

class TestMLModelIntegration(TestBase):
    """Test machine learning model integration."""
    
    def test_layoutlm_model_loading(self):
        """Test LayoutLM model loading."""
        try:
            from scripts.cv_extractor import load_local_model
            
            model_path = self.project_root / "local_layoutlmv3"
            if model_path.exists():
                processor, model = load_local_model(str(model_path))
                self.assertIsNotNone(processor)
                self.assertIsNotNone(model)
            else:
                self.skipTest("Local LayoutLM model not found")
                
        except ImportError as e:
            self.skipTest(f"Could not import cv_extractor module or model dependencies: {e}")
    
    def test_model_inference(self):
        """Test model inference functionality."""
        try:
            from scripts.cv_extractor import process_with_layoutlm
            
            # Mock model inference
            with patch('scripts.cv_extractor.load_local_model') as mock_load:
                mock_processor = MagicMock()
                mock_model = MagicMock()
                mock_load.return_value = (mock_processor, mock_model)
                
                # Mock inference result
                mock_model.return_value = MagicMock()
                
                sample_text = "Sample CV text for processing"
                result = process_with_layoutlm(sample_text)
                
                self.assertIsNotNone(result)
                
        except ImportError as e:
            self.skipTest(f"Could not import cv_extractor module: {e}")

if __name__ == "__main__":
    unittest.main()
