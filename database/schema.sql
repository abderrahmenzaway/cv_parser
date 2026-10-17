-- CV Parser Database Schema
-- Dialect: MySQL 8.0
-- Note: All statements are wrapped in MySQL executable comments to avoid
-- editor/linter false positives in non-MySQL parsers.

/*!80000 CREATE DATABASE IF NOT EXISTS cv_parser; */
/*!80000 USE cv_parser; */

/*!80000 DROP TABLE IF EXISTS skills; */
/*!80000 DROP TABLE IF EXISTS projects; */
/*!80000 DROP TABLE IF EXISTS experiences; */
/*!80000 DROP TABLE IF EXISTS educations; */
/*!80000 DROP TABLE IF EXISTS contacts; */
/*!80000 DROP TABLE IF EXISTS candidates; */

/*!80000 CREATE TABLE candidates (
    candidate_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL DEFAULT '',
    last_name VARCHAR(100) NOT NULL DEFAULT '',
    cv_file_path VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (first_name, last_name),
    INDEX idx_file_path (cv_file_path)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; */

/*!80000 CREATE TABLE contacts (
    contact_id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    phone VARCHAR(50) DEFAULT '',
    email VARCHAR(255) DEFAULT '',
    address TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    INDEX idx_candidate (candidate_id),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; */

/*!80000 CREATE TABLE educations (
    education_id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    INDEX idx_candidate (candidate_id),
    FULLTEXT idx_description (description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; */

/*!80000 CREATE TABLE experiences (
    experience_id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    INDEX idx_candidate (candidate_id),
    FULLTEXT idx_description (description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; */

/*!80000 CREATE TABLE projects (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    projects TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    INDEX idx_candidate (candidate_id),
    FULLTEXT idx_projects (projects)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; */

/*!80000 CREATE TABLE skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    skill_type ENUM('technical', 'language', 'extracted') DEFAULT 'extracted',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    INDEX idx_candidate (candidate_id),
    INDEX idx_skill_name (skill_name),
    INDEX idx_skill_type (skill_type),
    UNIQUE KEY unique_candidate_skill (candidate_id, skill_name, skill_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; */

/*!80000 CREATE OR REPLACE VIEW candidate_search_view AS
SELECT 
    c.candidate_id,
    c.first_name,
    c.last_name,
    c.cv_file_path,
    c.created_at,
    co.phone,
    co.email,
    co.address,
    GROUP_CONCAT(DISTINCT s.skill_name ORDER BY s.skill_name SEPARATOR ', ') as skills,
    GROUP_CONCAT(DISTINCT e.description ORDER BY e.education_id SEPARATOR ' | ') as education,
    GROUP_CONCAT(DISTINCT ex.description ORDER BY ex.experience_id SEPARATOR ' | ') as experience,
    GROUP_CONCAT(DISTINCT p.projects ORDER BY p.project_id SEPARATOR ' | ') as projects
FROM candidates c
LEFT JOIN contacts co ON c.candidate_id = co.candidate_id
LEFT JOIN skills s ON c.candidate_id = s.candidate_id
LEFT JOIN educations e ON c.candidate_id = e.candidate_id
LEFT JOIN experiences ex ON c.candidate_id = ex.candidate_id
LEFT JOIN projects p ON c.candidate_id = p.candidate_id
GROUP BY c.candidate_id, c.first_name, c.last_name, c.cv_file_path, c.created_at, co.phone, co.email, co.address; */

-- End of schema
