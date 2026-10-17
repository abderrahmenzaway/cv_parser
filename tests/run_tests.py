"""
Test configuration and runner
"""

import unittest
import sys
import os
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "flask_app"))
sys.path.insert(0, str(project_root / "scripts"))

def run_all_tests():
    """Run all tests in the test suite."""
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('ModuleNotFoundError:')[-1].strip()}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()

def run_specific_test(test_module):
    """Run a specific test module."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_module)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_simple_tests():
    """Run only simple tests that don't require heavy dependencies."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName('test_simple')
    
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run CV Parser tests')
    parser.add_argument('--module', '-m', help='Specific test module to run')
    parser.add_argument('--coverage', '-c', action='store_true', help='Run with coverage')
    parser.add_argument('--simple', '-s', action='store_true', help='Run only simple tests (no heavy dependencies)')
    parser.add_argument('--list', '-l', action='store_true', help='List available test modules')
    
    args = parser.parse_args()
    
    if args.list:
        print("Available test modules:")
        test_files = list(Path(__file__).parent.glob('test_*.py'))
        for test_file in test_files:
            print(f"  - {test_file.stem}")
        sys.exit(0)
    
    if args.simple:
        success = run_simple_tests()
    elif args.coverage:
        try:
            import importlib
            coverage = importlib.import_module('coverage')
            cov = coverage.Coverage()
            cov.start()
            
            if args.module:
                success = run_specific_test(args.module)
            else:
                success = run_all_tests()
            
            cov.stop()
            cov.save()
            
            print("\nCoverage Report:")
            cov.report()
            
        except ImportError:
            print("❌ Coverage module not installed. Install with: pip install coverage")
            print("Running tests without coverage...")
            if args.module:
                success = run_specific_test(args.module)
            else:
                success = run_all_tests()
        except Exception as e:
            print(f"❌ Error with coverage: {e}")
            print("Running tests without coverage...")
            if args.module:
                success = run_specific_test(args.module)
            else:
                success = run_all_tests()
    else:
        if args.module:
            success = run_specific_test(args.module)
        else:
            success = run_all_tests()
    
    sys.exit(0 if success else 1)
