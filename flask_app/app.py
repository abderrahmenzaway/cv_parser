import os
import json
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import mysql.connector
from mysql.connector import Error
import subprocess
from typing import Dict, Any, Optional
from werkzeug.utils import secure_filename
import logging
from pathlib import Path
import time
import docx
from docx2pdf import convert

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_change_in_production')


# Configuration
# Set BASE_DIR to the workspace root (parent of flask_app)
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
SCRIPTS_FOLDER = BASE_DIR / 'scripts'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Database configuration
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'admin'),
    'database': os.environ.get('DB_NAME', 'cv_parser'),
    'autocommit': True
}

def get_python_executable():
    """Get the Python executable path from virtual environment."""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # We're in a virtual environment
        return sys.executable
    else:
        # Fallback to system python
        return 'python'

def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_cv_with_extractor(pdf_path: str, output_json: str) -> bool:
    """Process PDF file using your cv_extractor.py script."""
    try:
        python_executable = get_python_executable()
        extractor_script = SCRIPTS_FOLDER / 'cv_extractor.py'

        if not extractor_script.exists():
            logger.error(f"CV extractor script not found at: {extractor_script}")
            return False

        logger.info(f"Calling cv_extractor.py with: {python_executable} {extractor_script} {pdf_path} {output_json}")
        logger.info(f"PDF path exists: {os.path.exists(pdf_path)} | Output dir exists: {os.path.exists(os.path.dirname(output_json))}")

        # Run your cv_extractor.py script
        result = subprocess.run(
            [python_executable, str(extractor_script), pdf_path, output_json],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,  # 5 minute timeout
            cwd=str(BASE_DIR)
        )

        logger.info(f"CV extraction successful: {result.stdout}")
        if result.stderr:
            logger.warning(f"CV extraction warnings: {result.stderr}")

        return True

    except subprocess.TimeoutExpired:
        logger.error("CV extraction timed out")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running cv_extractor.py: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error(f"CV extractor script not found: {extractor_script}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in CV extraction: {e}")
        return False

def insert_data_with_script(json_path: str, pdf_path: str) -> bool:
    """Insert data using your insert.py script."""
    try:
        python_executable = get_python_executable()
        insert_script = SCRIPTS_FOLDER / 'insert.py'
        
        if not insert_script.exists():
            logger.error(f"Insert script not found at: {insert_script}")
            return False
        
        # Run your insert.py script with both JSON and PDF file paths
        result = subprocess.run(
            [python_executable, str(insert_script), json_path, pdf_path],
            capture_output=True,
            text=True,
            timeout=60,  # 1 minute timeout
            cwd=str(BASE_DIR)
        )
        
        if result.returncode == 0:
            logger.info(f"Data insertion successful: {result.stdout}")
            if result.stderr:
                logger.warning(f"Data insertion warnings: {result.stderr}")
            return True
        else:
            logger.error(f"Insert script failed (code {result.returncode}). stdout: {result.stdout}\nstderr: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Data insertion timed out")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running insert.py: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error(f"Insert script not found: {insert_script}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in data insertion: {e}")
        return False

def get_db_connection():
    """Get database connection with error handling."""
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        logger.error(f"Database connection error: {e}")
        return None

@app.route('/')
def index():
    """Main page - redirect to upload."""
    return redirect(url_for('upload_file'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Handle file upload and processing."""
    if request.method == 'GET':
        return render_template('upload.html')
    
    # POST request handling
    try:
        # Diagnostics for debugging uploads
        logger.info(
            "Upload POST received. Content-Type=%s, Length=%s, Files=%s",
            request.headers.get('Content-Type'), request.content_length, list(request.files.keys())
        )

        # Get file safely
        file = request.files.get('pdf_file')
        if not file:
            flash('No file part in the request. Ensure the form uses multipart/form-data.', 'error')
            return render_template('upload.html')
        
        # Check if file is selected
        if not file.filename:
            flash('No file selected', 'error')
            return render_template('upload.html')
        
        # Validate extension and mimetype
        ext = file.filename.rsplit('.', 1)[1].lower()
        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload a PDF, DOC, or DOCX file.', 'error')
            return render_template('upload.html')
        
        # Secure the filename
        filename = secure_filename(file.filename)
        if not filename:
            flash('Invalid filename.', 'error')
            return render_template('upload.html')
        
        timestamp = str(int(time.time() * 1000))  # Avoid conflicts
        unique_filename = f"{timestamp}_{filename}"
        
        # Ensure uploads directory exists
        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        
        # Save and convert if needed
        if ext in ('doc', 'docx'):
            temp_doc_path = UPLOAD_FOLDER / unique_filename
            file.save(str(temp_doc_path))
            pdf_path = UPLOAD_FOLDER / f"{timestamp}_{filename}.pdf"
            try:
                convert(str(temp_doc_path), str(pdf_path))
            except Exception as conv_err:
                logger.error(f"Error converting DOC/DOCX to PDF: {conv_err}")
                flash('Failed to convert DOC/DOCX to PDF. Please upload a valid file.', 'error')
                temp_doc_path.unlink(missing_ok=True)
                return render_template('upload.html')
            temp_doc_path.unlink(missing_ok=True)
        else:
            pdf_path = UPLOAD_FOLDER / unique_filename
            file.save(str(pdf_path))
        
        # Process PDF with cv_extractor.py
        json_filename = f"{timestamp}_{filename}_results.json"
        output_json = UPLOAD_FOLDER / json_filename
        flash('Processing CV with the CV extractor...', 'info')
        
        if process_cv_with_extractor(str(pdf_path), str(output_json)):
            flash('CV processed successfully. Inserting into database...', 'info')
            if insert_data_with_script(str(output_json), str(pdf_path)):
                flash('CV successfully processed and stored in database!', 'success')
                return render_template('upload.html')
            else:
                flash('CV processed but failed to insert into database. Check insert.py script.', 'error')
                return render_template('upload.html')
        else:
            flash('Error processing the file with the CV extractor. Check cv_extractor.py script.', 'error')
            return render_template('upload.html')
    except Exception as e:
        logger.error(f"Upload processing error: {e}")
        flash(f'An error occurred while processing the file: {str(e)}', 'error')
        return render_template('upload.html')

@app.route('/search', methods=['GET', 'POST'])
def search_cv():
    """Search for candidates by skills, including skills, projects, education, and experience tables."""
    results = []
    search_term = ''
    
    if request.method == 'POST':
        search_term = request.form.get('skill', '').strip()
        
        if search_term:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    # Search in skills, projects, education, and experience
                    query = """
                        SELECT DISTINCT
                            c.candidate_id,
                            c.first_name,
                            c.last_name,
                            ct.email,
                            ct.phone,
                            c.cv_file_path,
                            GROUP_CONCAT(DISTINCT s.skill_name ORDER BY s.skill_name) as skills,
                            GROUP_CONCAT(DISTINCT p.projects ORDER BY p.project_id) as projects,
                            GROUP_CONCAT(DISTINCT e.description ORDER BY e.experience_id) as experience,
                            GROUP_CONCAT(DISTINCT ed.description ORDER BY ed.education_id) as education
                        FROM candidates c
                        LEFT JOIN contacts ct ON c.candidate_id = ct.candidate_id
                        LEFT JOIN skills s ON c.candidate_id = s.candidate_id
                        LEFT JOIN experiences e ON c.candidate_id = e.candidate_id
                        LEFT JOIN projects p ON c.candidate_id = p.candidate_id
                        LEFT JOIN educations ed ON c.candidate_id = ed.candidate_id
                        WHERE (
                            s.skill_name LIKE %s
                            OR p.projects LIKE %s
                            OR ed.description LIKE %s
                            OR e.description LIKE %s
                        )
                        GROUP BY c.candidate_id, c.first_name, c.last_name, ct.email, ct.phone, c.cv_file_path
                        ORDER BY c.last_name, c.first_name
                    """
                    like_term = f"%{search_term}%"
                    cursor.execute(query, (like_term, like_term, like_term, like_term))
                    results = cursor.fetchall()
                    
                    if not results:
                        flash(f'No candidates found with skill: {search_term}', 'info')
                    else:
                        flash(f'Found {len(results)} candidate(s) with skill: {search_term}', 'success')
                        
                except Error as e:
                    logger.error(f"Search query error: {e}")
                    flash('Error occurred while searching', 'error')
                finally:
                    cursor.close()
                    conn.close()
            else:
                flash('Database connection error', 'error')
    
    return render_template('search.html', results=results, search_term=search_term)

@app.route('/candidates')
def list_candidates():
    """List all candidates."""
    candidates = []
    conn = get_db_connection()
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    c.candidate_id,
                    c.first_name,
                    c.last_name,
                    ct.email,
                    ct.phone,
                    c.cv_file_path,
                    COUNT(s.skill_id) as skill_count
                FROM candidates c
                LEFT JOIN contacts ct ON c.candidate_id = ct.candidate_id
                LEFT JOIN skills s ON c.candidate_id = s.candidate_id
                GROUP BY c.candidate_id, c.first_name, c.last_name, ct.email, ct.phone, c.cv_file_path
                ORDER BY c.last_name, c.first_name
            """
            cursor.execute(query)
            candidates = cursor.fetchall()
        except Error as e:
            logger.error(f"Error fetching candidates: {e}")
            flash('Error fetching candidates', 'error')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Database connection error', 'error')
    
    return render_template('candidates.html', candidates=candidates)

@app.route('/status')
def system_status():
    """Check system status and script availability."""
    status = {
        'python_executable': get_python_executable(),
        'working_directory': str(BASE_DIR),
        'upload_folder': str(UPLOAD_FOLDER),
        'scripts_folder': str(SCRIPTS_FOLDER),
        'extractor_script_exists': (SCRIPTS_FOLDER / 'cv_extractor.py').exists(),
        'insert_script_exists': (SCRIPTS_FOLDER / 'insert.py').exists(),
        'upload_folder_exists': UPLOAD_FOLDER.exists(),
        'scripts_folder_exists': SCRIPTS_FOLDER.exists()
    }
    
    return render_template('status.html', status=status)

@app.route('/files')
def list_files():
    """List uploaded files and generated JSON files."""
    files = {
        'pdf_files': [],
        'json_files': []
    }
    
    if UPLOAD_FOLDER.exists():
        for file_path in UPLOAD_FOLDER.iterdir():
            if file_path.is_file():
                file_info = {
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime
                }
                
                if file_path.suffix.lower() == '.pdf':
                    files['pdf_files'].append(file_info)
                elif file_path.suffix.lower() == '.json':
                    files['json_files'].append(file_info)
    
    return render_template('files.html', files=files)

@app.route('/logs')
def view_logs():
    """Simple log viewer for debugging."""
    log_entries = []
    
    # This is a simple implementation - you might want to use proper log files
    try:
        # You can implement actual log file reading here
        log_entries = [
            f"System started at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Python executable: {get_python_executable()}",
            f"Working directory: {BASE_DIR}",
            f"CV extractor script exists: {(SCRIPTS_FOLDER / 'cv_extractor.py').exists()}",
            f"Insert script exists: {(SCRIPTS_FOLDER / 'insert.py').exists()}",
            "System ready for CV processing."
        ]
    except Exception as e:
        log_entries = [f"Error reading logs: {e}"]
    
    return render_template('logs.html', log_entries=log_entries)

@app.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        conn = get_db_connection()
        if conn:
            conn.close()
            db_status = "OK"
        else:
            db_status = "ERROR"
        
        # Check if scripts directory exists
        scripts_status = "OK" if SCRIPTS_FOLDER.exists() else "ERROR"
        
        # Check if uploads directory exists
        uploads_status = "OK" if UPLOAD_FOLDER.exists() else "ERROR"
        
        return {
            "status": "OK",
            "database": db_status,
            "scripts_folder": scripts_status,
            "uploads_folder": uploads_status,
            "python_executable": get_python_executable()
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}, 500


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    flash('File is too large. Maximum size is 16MB.', 'error')
    return render_template('upload.html'), 413

@app.route('/view_cv/<path:filename>')
def view_cv(filename):
    """View CV file."""
    try:
        # Security check: ensure filename doesn't contain path traversal
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Check in uploads folder first
        cv_path = UPLOAD_FOLDER / filename
        if cv_path.exists() and cv_path.is_file():
            return send_file(cv_path, as_attachment=False)
        
        # Check in flask_app/uploads folder
        flask_uploads = BASE_DIR / 'flask_app' / 'uploads' / filename
        if flask_uploads.exists() and flask_uploads.is_file():
            return send_file(flask_uploads, as_attachment=False)
            
        # If not found, return 404
        flash('CV file not found.', 'error')
        return redirect(url_for('list_candidates'))
        
    except Exception as e:
        logger.error(f"Error viewing CV {filename}: {e}")
        flash('Error viewing CV file.', 'error')
        return redirect(url_for('list_candidates'))

@app.route('/candidate/<int:candidate_id>')
def candidate_details(candidate_id):
    """View detailed information about a candidate."""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('list_candidates'))

        cursor = conn.cursor(dictionary=True)
        
        # Get candidate basic info
        cursor.execute("""
            SELECT c.candidate_id, c.first_name, c.last_name, ct.email, ct.phone, c.cv_file_path, c.created_at
            FROM candidates c
            LEFT JOIN contacts ct ON c.candidate_id = ct.candidate_id
            WHERE c.candidate_id = %s
        """, (candidate_id,))
        candidate = cursor.fetchone()
        
        if not candidate:
            flash('Candidate not found.', 'error')
            return redirect(url_for('list_candidates'))
        
        # Get candidate skills
        cursor.execute("""
            SELECT s.description as skill_name, NULL as proficiency_level
            FROM skills s
            WHERE s.candidate_id = %s
            ORDER BY s.description
        """, (candidate_id,))
        skills = cursor.fetchall()
        
        # Get candidate experiences
        cursor.execute("""
            SELECT description, NULL as company, NULL as position, NULL as start_date, NULL as end_date
            FROM experiences
            WHERE candidate_id = %s
            ORDER BY experience_id DESC
        """, (candidate_id,))
        experiences = cursor.fetchall()
        
        # Get candidate education
        cursor.execute("""
            SELECT description, NULL as institution, NULL as degree, NULL as field_of_study, NULL as start_date, NULL as end_date
            FROM educations
            WHERE candidate_id = %s
            ORDER BY education_id DESC
        """, (candidate_id,))
        education = cursor.fetchall()
        
        # Get candidate projects
        cursor.execute("""
            SELECT description, NULL as project_name, NULL as technologies_used, NULL as start_date, NULL as end_date
            FROM projects
            WHERE candidate_id = %s
            ORDER BY project_id DESC
        """, (candidate_id,))
        projects = cursor.fetchall()
        
        conn.close()
        
        return render_template('candidate_details.html', 
                             candidate=candidate, 
                             skills=skills,
                             experiences=experiences,
                             education=education,
                             projects=projects)
        
    except Exception as e:
        logger.error(f"Error fetching candidate details for ID {candidate_id}: {e}")
        flash('Error loading candidate details.', 'error')
        return redirect(url_for('list_candidates'))

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404

# Add template filter for timestamp conversion
@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    """Convert timestamp to readable date."""
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    except:
        return 'Unknown'

if __name__ == '__main__':
    # Create necessary directories
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    SCRIPTS_FOLDER.mkdir(exist_ok=True)
    
    # Print startup information
    print("=" * 50)
    print("CV Parser Flask Interface")
    print("=" * 50)
    print(f"Python executable: {get_python_executable()}")
    print(f"Working directory: {BASE_DIR}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Scripts folder: {SCRIPTS_FOLDER}")
    print(f"CV extractor script exists: {(SCRIPTS_FOLDER / 'cv_extractor.py').exists()}")
    print(f"Insert script exists: {(SCRIPTS_FOLDER / 'insert.py').exists()}")
    print("=" * 50)
    print("Starting server at http://127.0.0.1:5000")
    print("=" * 50)
    
    # Run the application
    app.run(
        debug=os.environ.get('FLASK_DEBUG', 'True').lower() == 'true',
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),
        port=int(os.environ.get('FLASK_PORT', 5000))
    )
