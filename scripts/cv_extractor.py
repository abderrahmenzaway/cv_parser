import re
import json
import torch
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from PIL import Image
import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
import pdfplumber
from dataclasses import dataclass
import sys  # Added for command-line arguments

# Language detection
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0

@dataclass
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float

@dataclass
class TextElement:
    text: str
    bbox: BoundingBox
    confidence: float
    label: str = None

class LayoutLM3CVExtractor:
    def __init__(self, model_name: str = "microsoft/layoutlmv3-base", use_layoutlm3: bool = False):
        self.detected_language = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")

        self.use_layoutlm3 = use_layoutlm3

        if self.use_layoutlm3:
            try:
                self.processor = LayoutLMv3Processor.from_pretrained(model_name)
                self.model = LayoutLMv3ForTokenClassification.from_pretrained(model_name)
                self.model.to(self.device)
                print("LayoutLM3 model loaded successfully")
            except Exception as e:
                print(f"Warning: Could not load LayoutLM3 model: {e}")
                print("Falling back to rule-based extraction")
                self.use_layoutlm3 = False
        else:
            print("Using rule-based extraction (LayoutLM3 disabled)")
            self.processor = None
            self.model = None

        self.setup_label_mappings()
        self.setup_keywords()

    def setup_label_mappings(self):
        self.section_labels = {
            'B-HEADER': 'header', 'I-HEADER': 'header',
            'B-EDUCATION': 'education', 'I-EDUCATION': 'education',
            'B-EXPERIENCE': 'experience', 'I-EXPERIENCE': 'experience',
            'B-SKILLS': 'skills', 'I-SKILLS': 'skills',
            'B-CONTACT': 'contact', 'I-CONTACT': 'contact',
            'O': 'other'
        }
        self.section_keywords = {
            'education': ['education', 'academic', 'qualification', 'degree', 'university', 'college'],
            'skills': ['skills', 'technical', 'competencies', 'technologies', 'expertise', 'proficiencies'],
            'experience': ['experience', 'employment', 'work', 'career', 'professional'],
            'contact': ['contact', 'personal', 'phone', 'email', 'address']
        }

    def setup_keywords(self):
        # Default: English
        self.technical_skills = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'kotlin', 'swift', 'typescript', 'sql', 'r', 'matlab', 'vhdl', 'c'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'nodejs', 'django', 'flask', 'express', 'bootstrap', 'jquery', 'graphql', 'rest'],
            'databases': ['mysql', 'postgresql', 'mongodb', 'redis', 'sqlite', 'oracle', 'cassandra', 'dynamodb', 'sql server'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible', 'jenkins', 'cloudformation'],
            'ml_ai': ['tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'opencv', 'keras', 'matplotlib', 'seaborn', 'nltk'],
            'tools': ['git', 'jira', 'confluence', 'linux', 'windows', 'macos', 'vim', 'vscode', 'docker', 'jenkins', 'bash', 'redhat'],
            'soft_skills': ['communication', 'teamwork', 'problem solving', 'leadership', 'time management', 'adaptability', 'project management'],
            'languages': ['french', 'english', 'spanish', 'arabic']
        }
        self.education_patterns = [
            r'(?i)\b(Bachelor|B\.?S\.?|B\.?A\.?|Master|M\.?S\.?|M\.?A\.?|MBA|PhD|Ph\.?D\.?|Doctorate|Diploma|Certificate|Associate)\b\s+(?:of\s+Science|of\s+Arts|in)?\s+([\w\s-]{3,}?)(?:\s+(?:at|from)\s+([\w\s-]{4,}?))?(?:\s*[,-]?\s*(\d{4}(?:[-–]\d{4})?))?',
            r'(?i)\b(?:Graduated|Degree|Studied)\s+(?:in|with)\s+([\w\s-]{3,})',
            r'(?i)(?:University|College|Institute|School)\s+of\s+([\w\s-]{4,})',
            r'(?i)\b(GPA|Grade)[\s:]+(\d+\.\d+)\b'
        ]
        self.contact_patterns = {
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'phone': r'\+?\d{1,4}[-.\s]?\d{2,3}[-.\s]?\d{2,4}[-.\s]?\d{2,4}|\d{8,12}',
            'name': r'^[A-Za-zÀ-ÿ\s-]+$'
        }
        # Adapt for French if detected
        if hasattr(self, 'detected_language') and self.detected_language == 'fr':
            self.technical_skills['soft_skills'] = ['communication', 'travail d\'équipe', 'résolution de problèmes', 'leadership', 'gestion du temps', 'adaptabilité', 'gestion de projet']
            self.technical_skills['languages'] = ['français', 'anglais', 'espagnol', 'arabe']
            self.section_keywords = {
                'education': ['éducation', 'formation', 'diplôme', 'université', 'école', 'collège'],
                'skills': ['compétences', 'techniques', 'technologies', 'expertise', 'savoir-faire'],
                'experience': ['expérience', 'emploi', 'travail', 'carrière', 'professionnel'],
                'contact': ['contact', 'personnel', 'téléphone', 'email', 'adresse']
            }
            self.education_patterns = [
                r'(?i)\b(Licence|Master|Doctorat|Diplôme|Certificat|BTS|DUT|Ingénieur)\b\s+([\w\s-]{3,}?)(?:\s+(?:à|de|en)\s+([\w\s-]{4,}?))?(?:\s*[,-]?\s*(\d{4}(?:[-–]\d{4})?))?',
                r'(?i)\b(?:Diplômé|Étudié|Formation)\s+(?:en|avec)\s+([\w\s-]{3,})',
                r'(?i)(?:Université|École|Institut|Collège)\s+de\s+([\w\s-]{4,})',
                r'(?i)\b(Mention|Note)[\s:]+(\d+\.\d+)\b'
            ]
            self.contact_patterns['name'] = r'^[A-Za-zÀ-ÿ\s-]+$'

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
                text = text.strip()
                # If no text, try OCR
                if not text:
                    print("[INFO] No text found with pdfplumber, switching to OCR...")
                    from pdf2image import convert_from_path
                    import pytesseract
                    images = convert_from_path(pdf_path, dpi=300)
                    ocr_text = ""
                    for img in images:
                        ocr_text += pytesseract.image_to_string(img, lang='eng+fra') + "\n"
                    text = ocr_text.strip()
                # Language detection
                try:
                    lang = detect(text)
                except Exception:
                    lang = "unknown"
                print(f"[INFO] Detected language: {lang}")
                self.detected_language = lang
                # Re-setup keywords and patterns for detected language
                self.setup_keywords()
                return text
        except Exception as e:
            print(f"Erreur lors de l'extraction du texte avec pdfplumber: {e}")
            return ""

    def extract_text_and_layout(self, image_path: str) -> Tuple[List[TextElement], np.ndarray]:
        if image_path.lower().endswith('.pdf'):
            print(f"PDF detected: {image_path}")
            return self.extract_from_pdf(image_path)

        image = cv2.imread(image_path)
        if image is None:
            try:
                pil_image = Image.open(image_path)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            except Exception as e:
                raise ValueError(f"Could not load image from {image_path}. Error: {e}")

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        try:
            ocr_data = pytesseract.image_to_data(image_rgb, output_type=pytesseract.Output.DICT)
        except Exception as e:
            raise ValueError(f"OCR failed on {image_path}. Make sure Tesseract is installed. Error: {e}")

        text_elements = []
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            if text and int(ocr_data['conf'][i]) > 30:
                bbox = BoundingBox(
                    x0=ocr_data['left'][i],
                    y0=ocr_data['top'][i],
                    x1=ocr_data['left'][i] + ocr_data['width'][i],
                    y1=ocr_data['top'][i] + ocr_data['height'][i]
                )
                text_elements.append(TextElement(
                    text=text,
                    bbox=bbox,
                    confidence=int(ocr_data['conf'][i]) / 100.0
                ))

        return text_elements, image_rgb

    def extract_from_pdf(self, pdf_path: str) -> Tuple[List[TextElement], np.ndarray]:
        try:
            images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
            if not images:
                raise ValueError("No pages found in PDF")

            image_array = np.array(images[0])
            ocr_data = pytesseract.image_to_data(image_array, output_type=pytesseract.Output.DICT)

            text_elements = []
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                if text and int(ocr_data['conf'][i]) > 30:
                    bbox = BoundingBox(
                        x0=ocr_data['left'][i],
                        y0=ocr_data['top'][i],
                        x1=ocr_data['left'][i] + ocr_data['width'][i],
                        y1=ocr_data['top'][i] + ocr_data['height'][i]
                    )
                    text_elements.append(TextElement(
                        text=text,
                        bbox=bbox,
                        confidence=int(ocr_data['conf'][i]) / 100.0
                    ))

            return text_elements, image_array

        except Exception as e:
            raise ValueError(f"Could not process PDF {pdf_path}. Error: {e}")

    def process_with_layoutlm3(self, image: np.ndarray, text_elements: List[TextElement]) -> Dict[str, Any]:
        if not self.use_layoutlm3:
            return self.process_with_rules(text_elements)

        try:
            pil_image = Image.fromarray(image)
            words = [elem.text for elem in text_elements]
            boxes = [[int(elem.bbox.x0), int(elem.bbox.y0), int(elem.bbox.x1), int(elem.bbox.y1)]
                    for elem in text_elements]

            height, width = image.shape[:2]
            normalized_boxes = []
            for box in boxes:
                normalized_box = [
                    int(1000 * box[0] / width),
                    int(1000 * box[1] / height),
                    int(1000 * box[2] / width),
                    int(1000 * box[3] / height)
                ]
                normalized_boxes.append(normalized_box)

            encoding = self.processor(
                pil_image,
                words,
                boxes=normalized_boxes,
                return_tensors="pt",
                truncation=True,
                padding=True
            )

            encoding = {k: v.to(self.device) for k, v in encoding.items()}

            with torch.no_grad():
                outputs = self.model(**encoding)
                predictions = torch.argmax(outputs.logits, dim=-1)

            predicted_labels = predictions[0].cpu().numpy()
            sections = defaultdict(list)
            for i, (text_elem, pred_label) in enumerate(zip(text_elements, predicted_labels)):
                section_name = self.classify_section_by_content(text_elem.text)
                text_elem.label = section_name
                sections[section_name].append(text_elem)

            return {
                'sections': sections,
                'predictions': predicted_labels,
                'text_elements': text_elements
            }

        except Exception as e:
            print(f"LayoutLM3 processing failed: {e}")
            print("Falling back to rule-based classification")
            return self.process_with_rules(text_elements)

    def process_with_rules(self, text_elements: List[TextElement]) -> Dict[str, Any]:
        sections = defaultdict(list)
        current_section = 'other'

        for text_elem in text_elements:
            section_name = self.classify_section_by_content(text_elem.text)
            if self.is_section_header(text_elem.text):
                current_section = section_name
            else:
                if section_name != 'other':
                    current_section = section_name

            text_elem.label = current_section
            sections[current_section].append(text_elem)

        return {
            'sections': sections,
            'predictions': [],
            'text_elements': text_elements
        }

    def is_section_header(self, text: str) -> bool:
        text_lower = text.lower().strip()
        headers = [
            'education', 'academic background', 'qualifications',
            'skills', 'technical skills', 'competencies', 'expertise',
            'experience', 'work experience', 'employment', 'career',
            'contact', 'personal information', 'contact information'
        ]
        return (text_lower in headers or
                any(header in text_lower for header in headers) and len(text) < 50)

    def classify_section_by_content(self, text: str) -> str:
        text_lower = text.lower()
        for section, keywords in self.section_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return section
        if re.search(r'\b(bachelor|master|phd|university|college)\b', text_lower):
            return 'education'
        elif re.search(r'\b(python|java|javascript|programming|development)\b', text_lower):
            return 'skills'
        elif re.search(r'\b(experience|work|employment|company)\b', text_lower):
            return 'experience'
        elif re.search(r'\b(phone|email|address|contact)\b', text_lower):
            return 'contact'
        return 'other'

    def extract_skills_from_sections(self, sections: Dict[str, List[TextElement]]) -> Dict[str, List[str]]:
        skills = defaultdict(list)

        skills_elements = sections.get('skills', []) + sections.get('other', []) + sections.get('experience', [])
        skills_text = ' '.join([elem.text for elem in skills_elements]).lower()

        skills_text = re.sub(r'[^\w\s,;-]', ' ', skills_text)
        skills_text = re.sub(r'\s+', ' ', skills_text).strip()

        for category, skill_list in self.technical_skills.items():
            for skill in skill_list:
                if re.search(r'\b' + re.escape(skill) + r'\b', skills_text):
                    skills[category].append(skill)

        skill_patterns = [
            r'(?:proficient in|experienced with|skilled in|familiar with|knowledge of)[\s:]+([\w\s,;-]+?)(?=\.|,|\n|$)',
            r'(?:technologies|tools|languages|skills)[\s:]+([\w\s,;-]+?)(?=\.|,|\n|$)',
            r'•\s*([\w\s,;-]+?)(?=\.|,|\n|$)',
            r'-\s*([\w\s,;-]+?)(?=\.|,|\n|$)'
        ]

        for pattern in skill_patterns:
            matches = re.findall(pattern, skills_text, re.IGNORECASE)
            for match in matches:
                skill_items = [item.strip() for item in re.split(r'[,;]', match) if item.strip()]
                for item in skill_items:
                    if (len(item) > 2 and len(item) < 50 and
                        not re.match(r'^\d+$', item) and
                        item.lower() not in ['and', 'or', 'with', 'in', 'at']):
                        skills['extracted'].append(item)

        for category in skills:
            skills[category] = sorted(list(set(skills[category])))

        return dict(skills)

    def extract_education_from_sections(self, sections: Dict[str, List[TextElement]]) -> List[Dict[str, str]]:
        education_list = []

        education_elements = sections.get('education', []) + sections.get('other', [])
        education_text = ' '.join([elem.text for elem in education_elements])

        education_text = re.sub(r'[^\w\s,;-]', ' ', education_text)
        education_text = re.sub(r'\s+', ' ', education_text).strip()

        for pattern in self.education_patterns:
            matches = re.findall(pattern, education_text, re.IGNORECASE)
            for match in matches:
                education_entry = {
                    'degree': match[0].strip() if match[0] else '',
                    'field': match[1].strip() if len(match) > 1 and match[1] and len(match[1].strip()) > 2 else '',
                    'institution': match[2].strip() if len(match) > 2 and match[2] and len(match[2].strip()) > 4 else '',
                    'year': match[3].strip() if len(match) > 3 and match[3] else ''
                }
                if (education_entry['degree'] and len(education_entry['degree']) > 1) or (education_entry['institution'] and len(education_entry['institution']) > 4):
                    if education_entry['field']:
                        education_entry['field'] = education_entry['field'].title()
                    if education_entry['institution']:
                        education_entry['institution'] = education_entry['institution'].title()
                    education_list.append(education_entry)

        seen = set()
        unique_education_list = []
        for entry in education_list:
            entry_tuple = (entry['degree'].lower(), entry['field'].lower(), entry['institution'].lower(), entry['year'])
            if entry_tuple not in seen and (entry['degree'] or entry['institution']):
                seen.add(entry_tuple)
                unique_education_list.append(entry)

        return unique_education_list

    def extract_contact_info(self, pdf_path: str) -> Dict[str, str]:
        contact_info = {
            'first_name': '',
            'last_name': '',
            'email': '',
            'phone': ''
        }

        texte = self.extract_text_from_pdf(pdf_path)
        if not texte:
            print("No text extracted for contact info")
            return contact_info

        lines = texte.split("\n")[:5]
        print("Texte analysé pour le nom :")
        print("\n".join(lines))

        # Helpers
        def clean_tokens(s: str) -> list:
            # Remove separators and common noise words
            s = re.sub(r'[|•–—\u2022\u2013\u2014]', ' ', s)
            s = re.sub(r'\b(cv|resume|curriculum|vitae)\b', ' ', s, flags=re.IGNORECASE)
            s = re.sub(r'[^A-Za-zÀ-ÿ\s\'-]', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return [t for t in s.split(' ') if t]

        def looks_like_name_tokens(tokens: list) -> bool:
            if len(tokens) < 2:
                return False
            # Accept 2 or 3 tokens, all alphabetic/hyphen/apostrophe
            if len(tokens) > 3:
                return False
            for t in tokens:
                if not re.match(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\'-]*$", t):
                    return False
            return True

        found_name = False
        # Try to extract name from the first 5 lines
        for line in lines:
            line = line.strip()
            if not line or any(x in line.lower() for x in ["contact", "phone", "email", "address", "curriculum", "vitae"]):
                continue
            tokens = clean_tokens(line)
            if looks_like_name_tokens(tokens):
                # Prefer first two tokens for first/last
                first, last = tokens[0], tokens[1]
                contact_info['first_name'] = first.title()
                contact_info['last_name'] = last.title()
                found_name = True
                break

        # Fallback: try from email local part
        if not found_name:
            email_match = re.search(self.contact_patterns['email'], texte)
            if email_match:
                local = email_match.group(0).split('@')[0]
                parts = [p for p in re.split(r"[._+\-]", local) if p and not p.isdigit()]
                if len(parts) >= 2:
                    contact_info['first_name'] = parts[0].title()
                    contact_info['last_name'] = parts[1].title()
                    found_name = True

        # Fallback: try from PDF filename
        if not found_name:
            import os
            base = os.path.splitext(os.path.basename(pdf_path))[0]
            parts = [p for p in re.split(r"[\s_\-\.]+", base) if p and p.lower() not in {'cv','resume','curriculum','vitae'}]
            # Keep only alphabetic tokens
            parts = [p for p in parts if re.match(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\'-]*$", p)]
            if len(parts) >= 2:
                contact_info['first_name'] = parts[0].title()
                contact_info['last_name'] = parts[1].title()
                found_name = True

        # Email and phone (keep existing logic)
        email_match = re.search(self.contact_patterns['email'], texte)
        if email_match:
            contact_info['email'] = email_match.group(0)

        phone_matches = re.findall(self.contact_patterns['phone'], texte)
        valid_phones = []
        for phone in phone_matches:
            digits = re.sub(r'\D', '', phone)
            if len(digits) >= 10 and not (len(digits) == 4 and 1900 <= int(digits) <= 2100):
                valid_phones.append(phone)
        preferred_phones = [p for p in valid_phones if re.search(r'[-\s]', p)]
        if preferred_phones:
            phone = preferred_phones[0]
        elif valid_phones:
            phone = valid_phones[0]
        else:
            phone = ''
        if phone:
            phone = re.sub(r'[\n\s]+', ' ', phone).strip()
            contact_info['phone'] = phone

        print(f"Extracted contact info: {contact_info}")
        return contact_info

    def process_cv_image(self, image_path: str) -> Dict[str, Any]:
        try:
            text_elements, image_array = self.extract_text_and_layout(image_path)
            print(f"Extracted {len(text_elements)} text elements")

            layout_results = self.process_with_layoutlm3(image_array, text_elements)

            skills = self.extract_skills_from_sections(layout_results['sections'])
            education = self.extract_education_from_sections(layout_results['sections'])
            contact = {'first_name': '', 'last_name': '', 'email': '', 'phone': ''} if not image_path.lower().endswith('.pdf') else {}

            results = {
                'skills': skills,
                'education': education,
                'contact': contact,
                'sections': {k: [elem.text for elem in v] for k, v in layout_results['sections'].items()},
                'text_elements': [(elem.text, elem.bbox.__dict__, elem.confidence) for elem in text_elements]
            }

            return results

        except Exception as e:
            print(f"Error in CV processing pipeline: {e}")
            raise

    def process_cv_pdf(self, pdf_path: str) -> Dict[str, Any]:
        images = convert_from_path(pdf_path, dpi=300)

        contact = self.extract_contact_info(pdf_path)

        all_results = []
        for i, image in enumerate(images):
            temp_path = f"temp_page_{i}.png"
            image.save(temp_path)

            print(f"Processing page {i + 1}")
            page_results = self.process_cv_image(temp_path)
            all_results.append(page_results)

            import os
            os.remove(temp_path)

        combined_results = self.combine_page_results(all_results, contact)
        print(f"Combined contact info: {combined_results['contact']}")
        return combined_results

    def combine_page_results(self, page_results: List[Dict], contact: Dict[str, str]) -> Dict[str, Any]:
        combined = {
            'skills': defaultdict(list),
            'education': [],
            'contact': contact,
            'sections': defaultdict(list),
            'text_elements': []
        }

        for result in page_results:
            for category, skills in result['skills'].items():
                combined['skills'][category].extend(skills)

            combined['education'].extend(result['education'])

            for section, content in result['sections'].items():
                combined['sections'][section].extend(content)

            combined['text_elements'].extend(result['text_elements'])

        for category in combined['skills']:
            combined['skills'][category] = list(set(combined['skills'][category]))

        return dict(combined)

    def save_results(self, results: Dict, output_path: str):
        filtered_results = {
            'skills': results['skills'],
            'education': results['education'],
            'contact': results['contact'],
            'sections': results['sections']
        }
        print(f"Saving contact info to JSON: {filtered_results['contact']}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_path}")

    def evaluate_extraction(ground_truth: dict, extracted: dict, fields=None):
        """
        Evaluate extraction results against ground truth for given fields.
        Returns a dict with precision, recall, and F1 for each field.
        """
        if fields is None:
            fields = ['first_name', 'last_name', 'email', 'phone', 'skills', 'education']
        from collections import Counter
        def score(gt, ex):
            if isinstance(gt, list) and isinstance(ex, list):
                gt_set, ex_set = set(gt), set(ex)
                tp = len(gt_set & ex_set)
                fp = len(ex_set - gt_set)
                fn = len(gt_set - ex_set)
            else:
                tp = int(gt == ex and gt)
                fp = int(ex and gt != ex)
                fn = int(gt and gt != ex)
            precision = tp / (tp + fp) if (tp + fp) else 0.0
            recall = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
            return {'precision': precision, 'recall': recall, 'f1': f1}
        results = {}
        for field in fields:
            gt = ground_truth.get(field, [])
            ex = extracted.get(field, [])
            results[field] = score(gt, ex)
        return results

# Modified main to handle command-line arguments
def main(pdf_path: str = None, output_json: str = None):
    if not pdf_path or not output_json:
        print("Usage: python cv_extractor.py <pdf_path> <output_json>")
        return

    extractor = LayoutLM3CVExtractor(use_layoutlm3=False)
    try:
        print(f"Processing CV: {pdf_path}")
        results = extractor.process_cv_pdf(pdf_path)
        
        print("\n=== EXTRACTED SKILLS ===")
        for category, skills in results['skills'].items():
            if skills:
                print(f"{category.upper()}: {', '.join(skills)}")

        print("\n=== ALL SKILLS SECTION CONTENT ===")
        skills_content = results['sections'].get('skills', [])
        if skills_content:
            print(f"SKILLS SECTION ({len(skills_content)} elements):")
            for i, item in enumerate(skills_content, 1):
                print(f"  {i}. {item}")
        else:
            print("No skills section found.")

        print("\n=== EXTRACTED EDUCATION ===")
        for edu in results['education']:
            print(f"Degree: {edu['degree']}")
            print(f"Field: {edu['field']}")
            print(f"Institution: {edu['institution']}")
            print(f"Year: {edu['year']}")
            print("---")

        extractor.save_results(results, output_json)

    except Exception as e:
        print(f"Error processing CV: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Tesseract and pdfplumber are installed")
        print("2. Make sure poppler is installed for PDF processing")
        print("3. Check that the file path is correct")
        print("4. Try with use_layoutlm3=True if you have a fine-tuned model")

if __name__ == "__main__":
    # Get command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python cv_extractor.py <pdf_path> <output_json>")
        sys.exit(1)
    pdf_path = sys.argv[1]
    output_json = sys.argv[2]
    main(pdf_path, output_json)