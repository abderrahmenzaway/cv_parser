"""
Performance monitoring and system health check for CV Parser
"""

import os
import sys
import time
import psutil
import mysql.connector
from pathlib import Path
from datetime import datetime
import json
import logging
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitor system resources and application health."""
    
    def __init__(self, config_file: str = None):
        self.start_time = time.time()
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'admin'),
            'database': os.getenv('DB_NAME', 'cv_parser')
        }
        
        # Project paths
        self.base_dir = Path(__file__).parent.absolute()
        self.upload_dir = self.base_dir / "uploads"
        self.flask_upload_dir = self.base_dir / "flask_app" / "uploads"
        
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system CPU, memory, and disk usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                }
            }
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            return {'error': str(e)}
    
    def check_database_connection(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Check table counts
            cursor.execute("SELECT COUNT(*) FROM candidates")
            candidate_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM skills")
            skills_count = cursor.fetchone()[0]
            
            connection_time = time.time() - start_time
            
            cursor.close()
            conn.close()
            
            return {
                'status': 'connected',
                'connection_time': connection_time,
                'candidate_count': candidate_count,
                'skills_count': skills_count
            }
            
        except mysql.connector.Error as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Unexpected error: {e}"
            }
    
    def check_file_system(self) -> Dict[str, Any]:
        """Check upload directories and file system health."""
        results = {}
        
        for name, path in [('upload_dir', self.upload_dir), 
                          ('flask_upload_dir', self.flask_upload_dir)]:
            try:
                if path.exists():
                    files = list(path.glob('*'))
                    total_size = sum(f.stat().st_size for f in files if f.is_file())
                    
                    results[name] = {
                        'exists': True,
                        'file_count': len([f for f in files if f.is_file()]),
                        'total_size': total_size,
                        'writable': os.access(path, os.W_OK)
                    }
                else:
                    results[name] = {
                        'exists': False,
                        'error': 'Directory does not exist'
                    }
            except Exception as e:
                results[name] = {
                    'error': str(e)
                }
        
        return results
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check if required dependencies are available."""
        dependencies = {}
        
        # Python packages
        required_packages = [
            'flask', 'mysql-connector-python', 'pdfplumber', 
            'pdf2image', 'pytesseract', 'torch', 'transformers',
            'langdetect', 'pillow'
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                dependencies[package] = {'status': 'installed'}
            except ImportError:
                dependencies[package] = {'status': 'missing'}
        
        # External tools
        external_tools = {
            'tesseract': 'tesseract --version',
            'poppler': 'pdftoppm -h'  # Part of poppler-utils
        }
        
        for tool, command in external_tools.items():
            try:
                import subprocess
                result = subprocess.run(
                    command.split(), 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                dependencies[tool] = {
                    'status': 'available' if result.returncode == 0 else 'error',
                    'version': result.stdout.split('\n')[0] if result.returncode == 0 else None
                }
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                dependencies[tool] = {
                    'status': 'not_found',
                    'error': str(e)
                }
        
        return dependencies
    
    def check_model_availability(self) -> Dict[str, Any]:
        """Check if AI models are available."""
        model_status = {}
        
        # Local LayoutLM model
        local_model_path = self.base_dir / "local_layoutlmv3"
        if local_model_path.exists():
            model_files = ['config.json', 'model.safetensors']
            processor_files = ['tokenizer.json', 'preprocessor_config.json']
            
            model_status['local_layoutlmv3'] = {
                'available': all((local_model_path / 'model' / f).exists() for f in model_files),
                'processor_available': all((local_model_path / 'processor' / f).exists() for f in processor_files),
                'path': str(local_model_path)
            }
        else:
            model_status['local_layoutlmv3'] = {
                'available': False,
                'error': 'Model directory not found'
            }
        
        # Check if CUDA is available
        try:
            import torch
            model_status['cuda'] = {
                'available': torch.cuda.is_available(),
                'device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0
            }
        except ImportError:
            model_status['cuda'] = {
                'available': False,
                'error': 'PyTorch not installed'
            }
        
        return model_status
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check."""
        logger.info("Starting health check...")
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'uptime': time.time() - self.start_time,
            'system_resources': self.check_system_resources(),
            'database': self.check_database_connection(),
            'file_system': self.check_file_system(),
            'dependencies': self.check_dependencies(),
            'models': self.check_model_availability()
        }
        
        # Overall health assessment
        critical_issues = []
        warnings = []
        
        # Check for critical issues
        if health_report['database'].get('status') != 'connected':
            critical_issues.append('Database connection failed')
        
        if health_report['system_resources'].get('memory', {}).get('percent', 0) > 90:
            critical_issues.append('High memory usage')
        
        if health_report['system_resources'].get('disk', {}).get('percent', 0) > 95:
            critical_issues.append('Low disk space')
        
        # Check for warnings
        if health_report['system_resources'].get('cpu_usage', 0) > 80:
            warnings.append('High CPU usage')
        
        missing_deps = [k for k, v in health_report['dependencies'].items() 
                       if v.get('status') in ['missing', 'not_found']]
        if missing_deps:
            warnings.append(f"Missing dependencies: {', '.join(missing_deps)}")
        
        health_report['health_status'] = {
            'overall': 'critical' if critical_issues else 'warning' if warnings else 'healthy',
            'critical_issues': critical_issues,
            'warnings': warnings
        }
        
        return health_report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save health report to file."""
        if filename is None:
            filename = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        reports_dir = self.base_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / filename
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Health report saved to: {report_file}")
        return report_file

def main():
    """Main monitoring function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='CV Parser System Monitor')
    parser.add_argument('--save', '-s', action='store_true', 
                       help='Save report to file')
    parser.add_argument('--continuous', '-c', type=int, default=0,
                       help='Run continuously with specified interval (seconds)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Quiet mode - minimal output')
    
    args = parser.parse_args()
    
    monitor = SystemMonitor()
    
    def run_check():
        report = monitor.run_health_check()
        
        if not args.quiet:
            print(f"\n=== CV Parser Health Check - {report['timestamp']} ===")
            print(f"Overall Status: {report['health_status']['overall'].upper()}")
            
            if report['health_status']['critical_issues']:
                print(f"🔴 Critical Issues: {', '.join(report['health_status']['critical_issues'])}")
            
            if report['health_status']['warnings']:
                print(f"🟡 Warnings: {', '.join(report['health_status']['warnings'])}")
            
            if report['health_status']['overall'] == 'healthy':
                print("✅ All systems healthy")
            
            # System resources
            resources = report['system_resources']
            if 'error' not in resources:
                print(f"CPU: {resources['cpu_usage']:.1f}%")
                print(f"Memory: {resources['memory']['percent']:.1f}%")
                print(f"Disk: {resources['disk']['percent']:.1f}%")
            
            # Database
            db_status = report['database']
            if db_status['status'] == 'connected':
                print(f"Database: ✅ Connected ({db_status['candidate_count']} candidates)")
            else:
                print(f"Database: ❌ {db_status.get('error', 'Connection failed')}")
        
        if args.save:
            monitor.save_report(report)
        
        return report
    
    if args.continuous > 0:
        logger.info(f"Starting continuous monitoring (interval: {args.continuous}s)")
        try:
            while True:
                run_check()
                time.sleep(args.continuous)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
    else:
        run_check()

if __name__ == "__main__":
    main()
