# Multilingual CV Parser

A tool that reads CVs in any format (digital PDFs, scanned PDFs, Word files), extracts the candidate's details, stores them in a searchable MySQL database, and lets recruiters find candidates by skill or field from a web interface instead of reading every CV.

Built during my software engineering internship at IF Begin Agency (summer 2025).

## Results

Tested on **50 CVs** with different layouts:

| Field | Accuracy |
|---|---|
| Name, contact details, skills | 100% |
| Work experience | about 50% (correct on standard layouts) |

Experience sections are the hardest part: their layout varies a lot from one CV to another (columns, tables, free text), which is where a layout-aware model helps.

## How it works

```
 upload (PDF / DOC / DOCX)
        │   Word files are converted to PDF
        ▼
 scripts/cv_extractor.py
   1. text extraction with pdfplumber
   2. no text layer (scanned CV)? → render pages (pdf2image, 300 dpi) + Tesseract OCR (English + French)
   3. language detection (langdetect) → English or French keyword sets
   4. split into sections (contact, education, experience, skills, languages, projects)
      with rules and keywords; optional LayoutLMv3 token classification
   5. output: structured JSON
        │
        ▼
 scripts/insert.py ──► MySQL (candidates, contacts, educations, experiences, projects, skills)
        │
        ▼
 Flask web app: upload, search by skill or field, candidate pages, system status, logs
```

- **Multilingual**: the language is detected automatically and the extraction keywords adapt (English and French; new languages are added in `setup_keywords`).
- **Scanned CVs**: if a PDF has no text layer, the pages are rendered and read with OCR.
- **Layout model (optional)**: `LayoutLM3CVExtractor(use_layoutlm3=True)` adds token classification with LayoutLMv3 on top of the rule-based extraction. The default is rules only, which needs no GPU.
- **Evaluation**: `evaluate_extraction()` compares the output with a hand-labelled ground truth and computes precision, recall and F1-score per field.

## Web interface

| Page | Purpose |
|---|---|
| `/upload` | Upload a CV; it is parsed and stored automatically |
| `/search` | Find candidates by skill, field or keyword |
| `/candidates`, `/candidate/<id>` | List of candidates and full extracted profile |
| `/status`, `/health` | Checks the database, the scripts and the upload folder |
| `/files`, `/logs` | Uploaded files and processing logs |

## Repository layout

```
flask_app/              web app (app.py, HTML templates, CSS)
scripts/cv_extractor.py CV extraction: PDF text, OCR, language detection, sections, LayoutLMv3 option, evaluation
scripts/insert.py       inserts the extracted JSON into MySQL
database/schema.sql     database schema (6 tables)
tests/                  unit tests (extraction, database, web app)
monitor.py              system monitoring
config_template.py      configuration template (database, OCR, model paths)
.env.template           environment variables template
docs/                   install guide, API documentation, project summary, test analysis
```

## Run it

1. Install the system tools: **Tesseract OCR** (with the English and French languages), **Poppler** (for `pdf2image`) and **MySQL**. See [docs/INSTALL.md](docs/INSTALL.md).
2. Install the Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Create the database:
   ```bash
   mysql -u root -p < database/schema.sql
   ```
4. Copy `.env.template` to `.env` and fill in your MySQL credentials and tool paths.
5. Start the web app:
   ```bash
   cd flask_app
   python app.py
   ```
6. Parse a single CV from the command line:
   ```bash
   python scripts/cv_extractor.py path/to/cv.pdf output.json
   ```

The LayoutLMv3 option downloads `microsoft/layoutlmv3-base` from Hugging Face the first time it is used.

## Privacy

No real CVs or extracted candidate data are included in this repository. Uploaded files and results are excluded by `.gitignore`, because they contain personal data.

## Tech

Python, Flask, MySQL, pdfplumber, Tesseract OCR, pdf2image, OpenCV, langdetect, Hugging Face Transformers (LayoutLMv3), PyTorch
