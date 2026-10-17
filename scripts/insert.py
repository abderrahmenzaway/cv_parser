import mysql.connector
import json
import os
from typing import Dict, Any, List
from collections import defaultdict
import sys

def reset_auto_increment(conn: mysql.connector.connection.MySQLConnection, table: str) -> None:
    """Reset the auto-increment value for a given table to the next available ID."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT MAX(candidate_id) INTO @max_id FROM cv_parser.{table}")
    cursor.execute("SELECT IFNULL(@max_id, 0) + 1 INTO @next_id")  # Ensure @next_id is set
    cursor.execute("SELECT @next_id INTO @next_id_value")  # Fetch the value into a variable
    cursor.execute("SET @sql = CONCAT('ALTER TABLE cv_parser.', %s, ' AUTO_INCREMENT = ', @next_id_value)", (table,))
    cursor.execute("PREPARE stmt FROM @sql")
    cursor.execute("EXECUTE stmt")
    cursor.execute("DEALLOCATE PREPARE stmt")
    conn.commit()
    cursor.close()

def validate_and_insert_data(conn: mysql.connector.connection.MySQLConnection, data: Dict[str, Any], cv_file_path: str) -> None:
    """Validate JSON data and insert into candidates, contacts, educations, experiences, and skills tables."""
    cursor = conn.cursor()

    # Validate required fields
    if not data.get('contact', {}).get('first_name') and not data.get('contact', {}).get('last_name'):
        raise ValueError("Missing required field: first_name or last_name")

    # Insert into candidates
    cursor.execute('''
        INSERT INTO cv_parser.candidates (first_name, last_name, cv_file_path)
        VALUES (%s, %s, %s)
    ''', (
        data['contact'].get('first_name', ''),
        data['contact'].get('last_name', ''),
        cv_file_path
    ))
    candidate_id = cursor.lastrowid

    # Insert into contacts
    cursor.execute('''
        INSERT INTO cv_parser.contacts (candidate_id, phone, email, address)
        VALUES (%s, %s, %s, %s)''', (
        candidate_id,
        data['contact'].get('phone', ''),
        data['contact'].get('email', ''),
        None  # Address not provided in JSON
    ))

    # Combine all education texts into a single description
    education_texts = []
    for edu in data.get('sections', {}).get('education', []):
        if isinstance(edu, dict) and 'text' in edu:
            education_texts.append(edu['text'])
        elif isinstance(edu, str):
            education_texts.append(edu)
    education_description = ' '.join(education_texts).strip()
    if education_description:
        cursor.execute('''
            INSERT INTO cv_parser.educations (candidate_id, description)
            VALUES (%s, %s)
        ''', (
            candidate_id,
            education_description
        ))

    # Combine all experience texts into a single description
    experience_texts = defaultdict(list)
    for exp in data.get('sections', {}).get('experience', []):
        if isinstance(exp, dict) and 'id' in exp and 'text' in exp:
            experience_texts[exp['id']].append(exp['text'])
        elif isinstance(exp, str):
            experience_texts[0].append(exp)  # Default id for simple string list
    for exp_id, texts in experience_texts.items():
        experience_description = ' '.join(texts).strip()
        if experience_description:
            cursor.execute('''
                INSERT INTO cv_parser.experiences (candidate_id, description)
                VALUES (%s, %s)
            ''', (
                candidate_id,
                experience_description
            ))

    # Combine all skills texts under sections and insert into projects table
    skills_texts = []
    for skill in data.get('sections', {}).get('skills', []):
        if isinstance(skill, dict) and 'text' in skill:
            skills_texts.append(skill['text'])
        elif isinstance(skill, str):
            skills_texts.append(skill)
    projects_text = ' '.join(skills_texts).strip()
    if projects_text:
        cursor.execute('''
            INSERT INTO cv_parser.projects (candidate_id, projects)
            VALUES (%s, %s)
        ''', (
            candidate_id,
            projects_text
        ))

    # Insert into skills (deduplicate and ignore duplicates)
    seen = set()
    for category, skills in (data.get('skills', {}) or {}).items():
        if not isinstance(skills, (list, tuple)):
            continue
        skill_type = 'language' if category == 'languages' else 'extracted' if category == 'extracted' else 'technical'
        for skill in skills:
            s = str(skill).strip()
            if not s:
                continue
            key = (s.lower(), skill_type)
            if key in seen:
                continue
            seen.add(key)
            cursor.execute('''
                INSERT INTO cv_parser.skills (candidate_id, skill_name, skill_type)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE skill_name = VALUES(skill_name)
            ''', (
                candidate_id,
                s,
                skill_type
            ))

    conn.commit()
    print(f"Inserted candidate: {data['contact'].get('first_name')} {data['contact'].get('last_name')}")

def process_json_to_database(json_file_path: str, cv_file_path: str, db_config: dict) -> bool:
    """Process JSON file and insert into candidates, contacts, educations, experiences, and skills tables."""
    try:
        # Check if JSON file exists
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        # Read JSON file
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Connect to database
        conn = mysql.connector.connect(**db_config)

        # Process single candidate (JSON is not a list)
        validate_and_insert_data(conn, data, cv_file_path)

        # Reset auto-increment for candidates (optional, after insertion)
        reset_auto_increment(conn, 'candidates')

        # Close connection
        conn.close()
        print("Data insertion completed successfully.")
        
        return True
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return False
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

# Example usage with real file
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python insert.py <json_file_path> <cv_file_path>")
        sys.exit(1)
    json_file_path = sys.argv[1]
    cv_file_path = sys.argv[2]
    db_config = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', 'admin'),
        'database': os.environ.get('DB_NAME', 'cv_parser')
    }

    # Process JSON and insert into database
    success = process_json_to_database(json_file_path, cv_file_path, db_config)
    sys.exit(0 if success else 1)