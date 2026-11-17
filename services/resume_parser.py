import os
import re
from typing import Dict, Any, List

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import docx
except ImportError:
    docx = None


def extract_text_from_pdf(file_path: str) -> str:
    """Extract clean text from a PDF file using PyMuPDF."""
    text_parts = []
    if fitz is not None:
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_parts.append(page.get_text("text"))
        except Exception as e:
            text_parts.append(f"[Error reading PDF: {e}]")
    else:
        text_parts.append("[PyMuPDF not installed]")
    return "\n".join(text_parts).strip()


def extract_text_from_docx(file_path: str) -> str:
    """Extract clean text from a DOCX file using python-docx."""
    text_parts = []
    if docx is not None:
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        text_parts.append(" | ".join(row_cells))
        except Exception as e:
            text_parts.append(f"[Error reading DOCX: {e}]")
    else:
        text_parts.append("[python-docx not installed]")
    return "\n".join(text_parts).strip()


def extract_text_from_file(file_path: str) -> str:
    """Extract text based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(file_path)
    else:
        # Default text read
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
        except Exception as e:
            return f"[Error reading file: {e}]"


def analyze_resume_text(text: str, candidate_name: str = "", primary_skill: str = "", secondary_skill: str = "") -> Dict[str, Any]:
    """
    Parse resume text to infer candidate skills, experience level, and topic recommendations.
    """
    cleaned = text.strip()
    
    # 1. Experience detection heuristic
    exp_years = None
    exp_patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience",
        r"experience\s*:\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        r"total\s+experience\s*:\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+as\s+a",
    ]
    for pattern in exp_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            try:
                exp_years = float(match.group(1))
                break
            except ValueError:
                pass
    
    # Fallback default if not detected
    if exp_years is None:
        # Check date intervals (e.g., 2022 - 2024 or 2022 - Present)
        date_matches = re.findall(r"(20\d\d)\s*[-–to]+\s*(20\d\d|present|current)", cleaned, re.IGNORECASE)
        if date_matches:
            first_year = min(int(m[0]) for m in date_matches)
            current_year = 2026
            diff = max(1, current_year - first_year)
            exp_years = min(diff, 10)
        else:
            exp_years = 2.0  # default reasonable mid-junior baseline

    # 2. Extract technical keywords found
    tech_catalog = [
        ".NET", "C#", "ASP.NET Core", "Entity Framework", "LINQ", "Web API", "SQL Server",
        "Angular", "React", "TypeScript", "JavaScript", "HTML5", "CSS3", "Tailwind CSS",
        "Python", "Django", "FastAPI", "Flask", "Java", "Spring Boot", "Node.js", "Express",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes", "Azure", "AWS",
        "Microservices", "RESTful APIs", "GraphQL", "Git", "CI/CD", "Unit Testing", "NUnit"
    ]
    found_skills = []
    for tech in tech_catalog:
        # Match word boundaries or special handling for .NET / C#
        pattern = r"\b" + re.escape(tech) + r"\b" if not tech.startswith(".") else re.escape(tech)
        if re.search(pattern, cleaned, re.IGNORECASE):
            found_skills.append(tech)

    # Ensure primary and secondary are highlighted
    if primary_skill and primary_skill not in found_skills:
        found_skills.insert(0, primary_skill)
    if secondary_skill and secondary_skill not in found_skills:
        found_skills.append(secondary_skill)

    # 3. Formulate recommended topics
    topics = []
    if primary_skill:
        topics.append(primary_skill)
    if secondary_skill:
        topics.append(secondary_skill)
    
    # Add 1-2 complementary topics from found skills
    for s in found_skills:
        if s not in topics and len(topics) < 4:
            topics.append(s)

    if not topics:
        topics = [".NET Core / C#", "Angular", "SQL Server", "System Design & Problem Solving"]

    # 4. Difficulty suggestion based on experience
    if exp_years < 2:
        recommended_difficulty = "Beginner"
    elif exp_years <= 4:
        recommended_difficulty = "Intermediate"
    else:
        recommended_difficulty = "Harder"

    return {
        "candidate_name": candidate_name or "Candidate",
        "detected_experience_years": round(exp_years, 1),
        "recommended_difficulty": recommended_difficulty,
        "extracted_skills": found_skills[:12],
        "suggested_topics": topics,
        "resume_word_count": len(cleaned.split()),
        "resume_snippet": cleaned[:500] + ("..." if len(cleaned) > 500 else "")
    }
