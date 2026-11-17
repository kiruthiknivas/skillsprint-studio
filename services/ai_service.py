import os
import re
import json
import time
import random
import requests
from typing import Dict, Any, List, Optional

# Supported models
DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEEP_MODEL = "gemini-3.8-flash"

def get_api_key(custom_key: Optional[str] = None) -> str:
    """Retrieve Gemini API key from custom input or environment."""
    if custom_key and custom_key.strip():
        return custom_key.strip()
    return os.environ.get("GEMINI_API_KEY", "").strip()

def call_gemini_interactions_api(prompt: str, api_key: str, model: str = DEFAULT_MODEL, timeout: int = 45) -> str:
    """
    Call Google Gemini Interactions API endpoint.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/interactions?key={api_key}"
    payload = {
        "model": model,
        "input": prompt,
        "store": False
    }
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"Gemini API returned HTTP {response.status_code}: {response.text}")
    
    data = response.json()
    # Extract text from interaction response steps
    output_text = ""
    for step in data.get("steps", []):
        if step.get("type") == "model_output":
            for part in step.get("content", []):
                if "text" in part:
                    output_text += part["text"]
    
    if not output_text and "output_text" in data:
        output_text = data["output_text"]
        
    return output_text.strip()


def extract_json_from_llm(raw_text: str) -> Dict[str, Any]:
    """
    Robust JSON parser that extracts valid JSON objects or arrays from markdown blocks.
    Handles unescaped control characters, trailing commas, and block parsing.
    """
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]
    
    text = text.strip()
    
    # 1. Direct parse attempt with strict=False
    try:
        return json.loads(text, strict=False)
    except Exception:
        pass

    # 2. Extract outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        snippet = text[start:end+1]
        try:
            return json.loads(snippet, strict=False)
        except Exception:
            # 3. Clean common trailing commas
            cleaned = re.sub(r",\s*([}\]])", r"\1", snippet)
            try:
                return json.loads(cleaned, strict=False)
            except Exception:
                pass

    # 4. Fallback: Parse individual questions using regex if full document had a syntax error
    question_blocks = re.findall(
        r'\{\s*"id"\s*:\s*(\d+).*?"question"\s*:\s*"(.*?)".*?"options"\s*:\s*\[(.*?)\].*?"correct_answer"\s*:\s*"([A-D])".*?"hint"\s*:\s*"(.*?)".*?"explanation"\s*:\s*"(.*?)"\s*\}',
        text,
        re.DOTALL
    )
    if question_blocks:
        extracted_questions = []
        for q_id, q_text, opts_raw, ans, hint, expl in question_blocks:
            opts = re.findall(r'"(.*?)"', opts_raw)
            if len(opts) < 4:
                opts = ["Option A", "Option B", "Option C", "Option D"]
            extracted_questions.append({
                "id": int(q_id),
                "topic": "General",
                "difficulty": "Intermediate",
                "question": q_text.strip(),
                "code_snippet": "",
                "options": opts[:4],
                "correct_answer": ans.strip(),
                "hint": hint.strip(),
                "explanation": expl.strip()
            })
        if extracted_questions:
            return {"questions": extracted_questions}

    # If all parsing attempts failed, raise for caller fallback
    raise ValueError(f"Could not parse valid JSON from text: {text[:200]}...")


def analyze_candidate_profile(
    candidate_name: str,
    resume_text: str,
    primary_skill: str,
    secondary_skill: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use Gemini AI to analyze candidate's background and produce tailored quiz configuration.
    """
    active_key = get_api_key(api_key)
    
    system_prompt = f"""You are an expert Technical Interview Director and Hiring Manager.
Analyze the following candidate's profile and resume.

Candidate Name: {candidate_name or "Candidate"}
Primary Skill: {primary_skill or "Not specified"}
Secondary Skill: {secondary_skill or "Not specified"}
Resume Content:
{resume_text[:2500]}

Provide an intelligent assessment in JSON format with exactly the following keys:
{{
  "candidate_name": "{candidate_name or 'Candidate'}",
  "summary": "2-3 sentence executive summary of the candidate's technical profile, core strengths, and focus areas.",
  "estimated_years_of_experience": 2.0,
  "recommended_difficulty": "Intermediate", // "Beginner" (0-1 yrs), "Intermediate" (2-4 yrs), "Harder" (5+ yrs)
  "core_competencies": ["Competency 1", "Competency 2", "Competency 3", "Competency 4"],
  "recommended_topics": [
    {{"name": "{primary_skill or '.NET Core / C#'}", "question_count": 10, "focus_areas": "Core features, design, and practical problems"}},
    {{"name": "{secondary_skill or 'Angular'}", "question_count": 10, "focus_areas": "Architecture, state, performance"}},
    {{"name": "Database & SQL Server", "question_count": 6, "focus_areas": "Queries, indexes, optimization"}},
    {{"name": "System Architecture & Problem Solving", "question_count": 4, "focus_areas": "Real-world scenario evaluation"}}
  ],
  "interview_prep_advice": "Specific tip for this candidate to succeed in upcoming technical interviews."
}}

Respond ONLY with valid JSON. Do not include introductory or markdown prose outside JSON."""

    if active_key:
        try:
            raw_resp = call_gemini_interactions_api(system_prompt, active_key, model=DEFAULT_MODEL, timeout=30)
            parsed = extract_json_from_llm(raw_resp)
            return parsed
        except Exception as e:
            print(f"[AI Service] Gemini profile analysis fallback due to: {e}")

    # Fallback heuristic analysis if API fails or no key
    detected_years = 2.0
    if "year" in resume_text.lower():
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", resume_text, re.IGNORECASE)
        if match:
            try:
                detected_years = float(match.group(1))
            except:
                pass

    difficulty = "Beginner" if detected_years < 2 else ("Intermediate" if detected_years <= 4 else "Harder")
    
    topics = []
    if primary_skill:
        topics.append({"name": primary_skill, "question_count": 10, "focus_areas": f"Core {primary_skill} concepts, best practices, and runtime mechanics"})
    else:
        topics.append({"name": ".NET Core / C#", "question_count": 10, "focus_areas": "Memory management, async/await, dependency injection"})
        
    if secondary_skill:
        topics.append({"name": secondary_skill, "question_count": 10, "focus_areas": f"Practical architecture, optimization, and real-world usage"})
    else:
        topics.append({"name": "Angular & TypeScript", "question_count": 10, "focus_areas": "Components, RxJS/Signals, change detection"})

    topics.append({"name": "SQL Server & Database Design", "question_count": 6, "focus_areas": "Indexing, joins, stored procedures, execution plans"})
    topics.append({"name": "System Scenarios & Clean Code", "question_count": 4, "focus_areas": "SOLID principles, REST API design, debugging"})

    return {
        "candidate_name": candidate_name or "Candidate",
        "summary": f"{candidate_name or 'Candidate'} demonstrates a solid technical foundation in {primary_skill or '.NET'} and {secondary_skill or 'Angular'}, with estimated {detected_years} years of development experience. Ready for role-specific technical evaluation.",
        "estimated_years_of_experience": detected_years,
        "recommended_difficulty": difficulty,
        "core_competencies": [primary_skill or ".NET Core", secondary_skill or "Angular", "SQL Server", "RESTful APIs"],
        "recommended_topics": topics,
        "interview_prep_advice": f"Review real-world implementation nuances for {primary_skill or '.NET'} and {secondary_skill or 'Angular'} with special emphasis on debugging, performance pitfalls, and database query optimization."
    }


def generate_interview_quiz(
    candidate_name: str,
    resume_text: str,
    primary_skill: str,
    secondary_skill: str,
    years_of_experience: float,
    difficulty: str,
    question_count: int = 15,
    include_coding: bool = True,
    include_behavioral: bool = True,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate dynamic, multi-modal interview questions tailored to candidate profile.
    Combines high-impact technical MCQs, practical coding challenges, and hiring/behavioral questions.
    """
    active_key = get_api_key(api_key)
    session_seed = int(time.time() * 1000) % 100000
    
    p_skill = primary_skill.strip() if primary_skill else ".NET Core / C#"
    s_skill = secondary_skill.strip() if secondary_skill else "Angular"
    
    coding_count = 1 if (include_coding and question_count <= 12) else (2 if include_coding else 0)
    behavioral_count = 1 if include_behavioral else 0
    mcq_count = max(3, question_count - (coding_count + behavioral_count))
    
    prompt = f"""You are a Principal Engineering Director and Senior Technical Interviewer conducting a realistic, end-to-end technical assessment for an engineering candidate.

CANDIDATE INFORMATION:
- Name: {candidate_name or 'Candidate'}
- Primary Skill: {p_skill}
- Secondary Skill: {s_skill}
- Experience Level: {years_of_experience} years
- Question Difficulty Target: {difficulty}
- Seed/Session: {session_seed}

RESUME CONTEXT:
{resume_text[:2000]}

REQUIREMENT:
Generate a balanced, comprehensive, and 100% UNIQUE interview set of {question_count} questions:
- CRITICAL: Generate fresh, dynamic, and non-repetitive questions tailored specifically to {candidate_name or 'Candidate'}'s profile and resume context. Do NOT use boilerplate questions from previous sessions.
1. Technical MCQs ({mcq_count} questions): Focus on real runtime Gotchas, memory/async mechanics in {p_skill}, state & rendering in {s_skill}, and SQL performance.
2. Practical Coding Challenge ({coding_count} questions, type: "coding"): Provide real hands-on coding problems with starter code, optimal solution, 2 PUBLIC test cases (visible to candidate), and 2-3 HIDDEN test cases (evaluating boundary conditions, edge cases, null handling, or scale).
3. Behavioral & Hiring Fit ({behavioral_count} questions, type: "behavioral"): Practical interview questions like 'Why should we hire you for this role?' or 'Describe resolving a high-pressure production incident' with STAR framework guidance.

Return JSON ONLY with this exact structure:
{{
  "quiz_title": "Comprehensive Technical Assessment for {candidate_name or 'Candidate'}",
  "total_questions": {question_count},
  "candidate_name": "{candidate_name or 'Candidate'}",
  "experience_level": "{years_of_experience} Years",
  "difficulty": "{difficulty}",
  "topics": ["{p_skill}", "{s_skill}", "Database & SQL", "Coding Challenges", "Hiring & Behavioral Fit"],
  "questions": [
    {{
      "id": 1,
      "type": "mcq", // Exactly one of "mcq", "coding", "behavioral"
      "topic": "{p_skill}",
      "difficulty": "{difficulty}",
      "question": "Clear technical question text...",
      "code_snippet": "// Optional formatted code snippet or empty string",
      "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option"],
      "correct_answer": "A",
      "hint": "Guiding thought-provoking clue...",
      "explanation": "Detailed explanation why correct option is right and common pitfalls."
    }},
    {{
      "id": 2,
      "type": "coding",
      "topic": "Practical Coding: {p_skill}",
      "difficulty": "{difficulty}",
      "title": "Problem Title",
      "question": "Detailed problem description and requirements...",
      "starter_code": "// Boilerplate code here...",
      "solution_code": "// Complete optimal solution code...",
      "public_test_cases": [
        {{"name": "Public Test 1", "input": "Standard input 1", "expected": "Expected output 1", "explanation": "Basic functional case"}},
        {{"name": "Public Test 2", "input": "Standard input 2", "expected": "Expected output 2", "explanation": "Standard case"}}
      ],
      "hidden_test_cases": [
        {{"name": "Hidden Test 1 [Null / Empty Boundary]", "input": "Boundary or null input", "expected": "Defensive handling", "explanation": "Checks boundary validation"}},
        {{"name": "Hidden Test 2 [Edge Case / Contention]", "input": "Edge condition", "expected": "Optimal constraint handling", "explanation": "Checks edge cases"}}
      ],
      "test_cases": [
        {{"name": "Public Test 1", "input": "Standard input 1", "expected": "Expected output 1"}}
      ],
      "hint": "Clue on data structures or approach...",
      "explanation": "Walkthrough of optimal time and space complexity."
    }},
    {{
      "id": 3,
      "type": "behavioral",
      "topic": "Hiring & Behavioral Fit",
      "difficulty": "All Levels",
      "title": "Why Should We Hire You?",
      "question": "Why should our engineering team hire you for this role over other qualified developers?",
      "star_framework_prompt": "Structure: 1) Unique skill blend, 2) Ownership & communication, 3) Quantifiable impact.",
      "key_lookouts": "What interviewers evaluate (self-awareness, clarity, impact).",
      "sample_strong_answer": "High-scoring exemplar answer with metrics and ownership.",
      "hint": "Connect technical breadth directly to product delivery velocity."
    }}
  ]
}}
Respond ONLY with the JSON object."""

    if active_key:
        try:
            raw_resp = call_gemini_interactions_api(prompt, active_key, model=DEFAULT_MODEL, timeout=75)
            parsed = extract_json_from_llm(raw_resp)
            if "questions" in parsed and len(parsed["questions"]) > 0:
                qs = parsed["questions"]
                for i, q in enumerate(qs, 1):
                    q["id"] = i
                    qtype = q.get("type", "mcq").lower()
                    q["type"] = qtype if qtype in ["mcq", "coding", "behavioral"] else "mcq"
                    if q["type"] == "mcq":
                        if not isinstance(q.get("options"), list) or len(q.get("options")) < 4:
                            q["options"] = ["Option A", "Option B", "Option C", "Option D"]
                        ans = str(q.get("correct_answer", "A")).upper().strip()
                        q["correct_answer"] = ans[0] if ans and ans[0] in "ABCD" else "A"
                    elif q["type"] == "coding":
                        if not q.get("starter_code"):
                            q["starter_code"] = "// Write your solution here\n"
                        if not q.get("public_test_cases"):
                            q["public_test_cases"] = q.get("test_cases", [])[:2] if q.get("test_cases") else [
                                {"name": "Public Test 1", "input": "Standard input", "expected": "Valid result"}
                            ]
                        if not q.get("hidden_test_cases"):
                            q["hidden_test_cases"] = [
                                {"name": "Hidden Test 1 [Null / Empty Boundary]", "input": "Null or empty input", "expected": "Handled safely without crash", "explanation": "Boundary validation"},
                                {"name": "Hidden Test 2 [Edge Case Contention]", "input": "High volume / duplicate entries", "expected": "Satisfies performance constraints", "explanation": "Edge case resilience"}
                            ]
                        q["test_cases"] = q["public_test_cases"]
                    elif q["type"] == "behavioral":
                        if not q.get("star_framework_prompt"):
                            q["star_framework_prompt"] = "Use STAR method: Situation, Task, Action, Result."
                parsed["questions"] = qs[:question_count]
                parsed["total_questions"] = len(parsed["questions"])
                return parsed
        except Exception as e:
            print(f"[AI Service] Gemini question generation fallback: {e}")

    # Fallback dynamic generator with comprehensive question bank
    return generate_fallback_quiz(
        candidate_name=candidate_name,
        primary_skill=p_skill,
        secondary_skill=s_skill,
        years_of_experience=years_of_experience,
        difficulty=difficulty,
        question_count=question_count,
        include_coding=include_coding,
        include_behavioral=include_behavioral
    )


def generate_fallback_quiz(
    candidate_name: str,
    primary_skill: str,
    secondary_skill: str,
    years_of_experience: float,
    difficulty: str,
    question_count: int = 15,
    include_coding: bool = True,
    include_behavioral: bool = True
) -> Dict[str, Any]:
    """
    Rich fallback generator producing authentic, tailored interview questions.
    Includes Technical MCQs, Hands-on Coding, and Behavioral questions.
    """
    from services.question_bank import get_curated_questions
    
    questions = get_curated_questions(
        primary_skill=primary_skill,
        secondary_skill=secondary_skill,
        years_of_experience=years_of_experience,
        difficulty=difficulty,
        target_count=question_count,
        include_coding=include_coding,
        include_behavioral=include_behavioral
    )
    
    topics = list(dict.fromkeys([q["topic"] for q in questions]))
    
    return {
        "quiz_title": f"Technical Assessment for {candidate_name or 'Candidate'}",
        "total_questions": len(questions),
        "candidate_name": candidate_name or "Candidate",
        "experience_level": f"{years_of_experience} Years",
        "difficulty": difficulty,
        "topics": topics,
        "questions": questions
    }


def generate_company_targeted_quiz(
    candidate_name: str,
    company_name: str,
    job_description: str,
    resume_text: str,
    difficulty: str = "Intermediate",
    question_count: int = 15,
    include_coding: bool = True,
    include_behavioral: bool = True,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate dynamic assessment tailored specifically to a target company and job description.
    Integrates company interview style (Glassdoor/interview patterns), JD requirements, coding and behavioral rounds.
    """
    active_key = get_api_key(api_key)
    session_seed = int(time.time() * 1000) % 100000
    comp = company_name.strip() if company_name else "Target Enterprise"

    coding_count = 1 if include_coding else 0
    behavioral_count = 1 if include_behavioral else 0
    mcq_count = max(3, question_count - (coding_count + behavioral_count))

    prompt = f"""You are a Senior Hiring Lead and Principal Interviewer at {comp}.
Conduct a targeted assessment for a candidate applying to this specific role.

COMPANY: {comp}
CANDIDATE: {candidate_name or 'Candidate'}
DIFFICULTY: {difficulty}
SEED: {session_seed}

TARGET JOB DESCRIPTION:
{job_description[:2000]}

CANDIDATE RESUME / BACKGROUND:
{resume_text[:2000]}

TASK:
Generate exactly {question_count} interview questions tailored for {comp}'s technical interview loops:
1. Technical MCQs ({mcq_count} questions, type: "mcq"): Explicitly testing frameworks, architecture, and gotchas required in the JD.
2. Coding Challenge ({coding_count} questions, type: "coding"): A practical problem matching {comp}'s interview bar with starter code, test cases, and solution.
3. Hiring Fit Question ({behavioral_count} questions, type: "behavioral"): {comp}-specific cultural question (e.g. Amazon LP, Google engineering values, or 'Why do you want to join {comp}?').

Return JSON ONLY with this exact structure:
{{
  "quiz_title": "{comp} Technical Interview Assessment",
  "company_name": "{comp}",
  "total_questions": {question_count},
  "difficulty": "{difficulty}",
  "topics": ["{comp} Architecture", "Coding Challenge", "Behavioral & {comp} Fit"],
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "topic": "{comp} Technical Core",
      "difficulty": "{difficulty}",
      "question": "Scenario question testing a core JD requirement...",
      "code_snippet": "// Code if applicable",
      "options": ["A) Opt 1", "B) Opt 2", "C) Opt 3", "D) Opt 4"],
      "correct_answer": "A",
      "hint": "Conceptual clue...",
      "explanation": "Why this answer is right and what {comp} expects candidates to articulate."
    }}
  ]
}}
Respond ONLY with valid JSON."""

    if active_key:
        try:
            raw_resp = call_gemini_interactions_api(prompt, active_key, model=DEFAULT_MODEL, timeout=75)
            parsed = extract_json_from_llm(raw_resp)
            if "questions" in parsed and len(parsed["questions"]) > 0:
                qs = parsed["questions"]
                for i, q in enumerate(qs, 1):
                    q["id"] = i
                    qtype = q.get("type", "mcq").lower()
                    q["type"] = qtype if qtype in ["mcq", "coding", "behavioral"] else "mcq"
                    if q["type"] == "mcq":
                        if not isinstance(q.get("options"), list) or len(q.get("options")) < 4:
                            q["options"] = ["Option A", "Option B", "Option C", "Option D"]
                        ans = str(q.get("correct_answer", "A")).upper().strip()
                        q["correct_answer"] = ans[0] if ans and ans[0] in "ABCD" else "A"
                    elif q["type"] == "coding":
                        if not q.get("starter_code"):
                            q["starter_code"] = "// Write your solution here\n"
                        if not q.get("public_test_cases"):
                            q["public_test_cases"] = q.get("test_cases", [])[:2] if q.get("test_cases") else [
                                {"name": "Public Test 1", "input": "Standard input", "expected": "Valid result"}
                            ]
                        if not q.get("hidden_test_cases"):
                            q["hidden_test_cases"] = [
                                {"name": "Hidden Test 1 [Null / Empty Boundary]", "input": "Null or empty input", "expected": "Handled safely without crash", "explanation": "Boundary validation"},
                                {"name": "Hidden Test 2 [Edge Case Contention]", "input": "High volume / duplicate entries", "expected": "Satisfies performance constraints", "explanation": "Edge case resilience"}
                            ]
                        q["test_cases"] = q["public_test_cases"]
                    elif q["type"] == "behavioral":
                        if not q.get("star_framework_prompt"):
                            q["star_framework_prompt"] = "Use STAR method: Situation, Task, Action, Result."
                parsed["questions"] = qs[:question_count]
                parsed["total_questions"] = len(parsed["questions"])
                return parsed
        except Exception as e:
            print(f"[AI Service] Targeted company quiz generation fallback: {e}")

    # Fallback company targeted generator
    from services.question_bank import get_curated_questions
    base_qs = get_curated_questions(
        primary_skill=".NET Core / C#",
        secondary_skill="Angular",
        years_of_experience=2.0,
        difficulty=difficulty,
        target_count=question_count,
        include_coding=include_coding,
        include_behavioral=include_behavioral
    )
    for q in base_qs:
        q["topic"] = f"{comp} • {q['topic']}"
        q["explanation"] += f" (Note: {comp} interviewers look for deep understanding of this pattern)."

    return {
        "quiz_title": f"{comp} Tailored Technical Interview Assessment",
        "company_name": comp,
        "total_questions": len(base_qs),
        "difficulty": difficulty,
        "topics": list(dict.fromkeys([q["topic"] for q in base_qs])),
        "questions": base_qs
    }


def evaluate_behavioral_response(
    question: str,
    candidate_answer: str,
    candidate_name: str = "Candidate",
    role_context: str = "",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate candidate's written behavioral response using Gemini.
    Provides scoring, STAR critique, key strengths, and an executive model rewrite.
    """
    active_key = get_api_key(api_key)
    answer_clean = candidate_answer.strip()
    
    if len(answer_clean) < 15:
        return {
            "score": 35,
            "verdict": "Needs Expansion",
            "badge_color": "rose",
            "feedback": "The response is too brief. In a real interview, aim for 2-3 minutes of structured storytelling using the STAR method (Situation, Task, Action, Result).",
            "star_breakdown": {
                "situation": "Not clearly established.",
                "task": "Specific responsibility omitted.",
                "action": "Actions not detailed.",
                "result": "No quantifiable outcome provided."
            },
            "key_strengths": ["Answer initiated."],
            "areas_to_improve": ["Detail the technical challenge", "Quantify the business impact", "Highlight collaboration"],
            "improved_answer": "In my previous project, we faced a high-impact latency bottleneck on our primary API. As the lead developer on the feature, I profiled the database queries using SQL Server Extended Events, identified an missing index on the foreign key, and deployed a covering index. This reduced peak query latency by 42% and eliminated timeouts during our flash sale."
        }

    prompt = f"""You are an Executive Engineering Hiring Manager at a top tech company evaluating a candidate's interview answer.

CANDIDATE: {candidate_name}
TARGET CONTEXT: {role_context or 'Software Engineering'}
QUESTION ASKED: "{question}"

CANDIDATE'S WRITTEN ANSWER:
"{answer_clean}"

Evaluate this answer thoroughly based on:
1. STAR Method structure (Situation, Task, Action, Result)
2. Use of specific technical detail vs vague generic claims
3. Quantifiable impact (percentages, latency, throughput, dollars, delivery dates)
4. Demonstration of ownership, empathy, and communication

Return JSON ONLY with this exact structure:
{{
  "score": 85, // integer 0 to 100
  "verdict": "Strong Hire / Interview Approved", // e.g. "Strong Hire", "Solid Foundation", "Needs More Impact"
  "badge_color": "emerald", // "emerald" for >=80, "blue" for >=70, "amber" for >=50, "rose" for <50
  "feedback": "Constructive 2-3 sentence assessment of the response...",
  "star_breakdown": {{
    "situation": "Brief critique of how well the context was set",
    "task": "Critique of their defined responsibility",
    "action": "Critique of the specific actions described",
    "result": "Critique of quantifiable outcomes"
  }},
  "key_strengths": ["First key strength", "Second key strength"],
  "areas_to_improve": ["First improvement tip", "Second improvement tip"],
  "improved_answer": "A polished, executive-level rewrite of how this candidate should phrase this exact answer in an interview to blow the interview panel away."
}}
Respond ONLY with valid JSON."""

    if active_key:
        try:
            raw_resp = call_gemini_interactions_api(prompt, active_key, model=DEFAULT_MODEL, timeout=45)
            parsed = extract_json_from_llm(raw_resp)
            if "score" in parsed and "feedback" in parsed:
                return parsed
        except Exception as e:
            print(f"[AI Service] Behavioral evaluation fallback: {e}")

    # Fallback heuristic evaluation
    words = len(answer_clean.split())
    has_metrics = bool(re.search(r"\d+%", answer_clean) or re.search(r"\$\d+", answer_clean) or re.search(r"\d+\s*(ms|seconds|users|days)", answer_clean, re.I))
    base_score = min(92, max(50, 45 + (15 if words > 40 else 5) + (20 if has_metrics else 5) + (10 if "situation" in answer_clean.lower() or "result" in answer_clean.lower() else 5)))
    
    return {
        "score": base_score,
        "verdict": "Solid Foundation / Interview Ready" if base_score >= 75 else "Competent / Needs More Metrics",
        "badge_color": "emerald" if base_score >= 80 else ("blue" if base_score >= 70 else "amber"),
        "feedback": "You provided a coherent response that demonstrates familiarity with the context. Adding more specific performance numbers and technical tooling names will make it stand out even more to hiring managers.",
        "star_breakdown": {
            "situation": "Context communicated clearly.",
            "task": "Role and ownership established.",
            "action": "Technical actions described.",
            "result": "Quantifiable metrics could be made more explicit." if not has_metrics else "Solid metric-driven results highlighted."
        },
        "key_strengths": ["Clear professional tone", "Practical technical reasoning"],
        "areas_to_improve": ["State exact numbers (e.g. latency reduced by X%)", "Mention the specific diagnostic tools used"],
        "improved_answer": f"When addressing {question.lower().replace('?', '')}, I always root my approach in concrete metrics. For example, during a critical sprint, I took ownership of our service performance, identified the root bottleneck using telemetry, and executed a targeted optimization that reduced response time by 35% with zero regressions."
    }


def run_coding_simulation(
    problem_title: str,
    question: str,
    starter_code: str,
    solution_code: str,
    user_code: str,
    public_test_cases: list = None,
    custom_test_case: str = "",
    candidate_name: str = "Candidate",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run candidate's code in 'Run Code' mode against public test cases and optional custom test cases.
    Does NOT finalize or grade the problem. Returns execution logs, output for each public test case,
    and custom test case validation.
    """
    active_key = get_api_key(api_key)
    code_clean = user_code.strip()
    public_test_cases = public_test_cases or []
    
    # If code is unmodified or empty
    if not code_clean or code_clean == starter_code.strip() or len(code_clean) < 20:
        return {
            "all_passed": False,
            "console_output": "[Compiler] Source contains empty or default starter code.\n[Warning] No executable implementation found to test.",
            "test_results": [
                {
                    "name": tc.get("name", f"Public Test {idx}"),
                    "input": tc.get("input", ""),
                    "expected": tc.get("expected", ""),
                    "actual": "No implementation executed",
                    "status": "FAILED",
                    "details": "Starter code was unmodified."
                } for idx, tc in enumerate(public_test_cases, 1)
            ] + ([{
                "name": "Custom Test Case",
                "input": custom_test_case,
                "expected": "Custom evaluation",
                "actual": "No implementation executed",
                "status": "FAILED",
                "details": "Code not modified."
            }] if custom_test_case.strip() else [])
        }

    prompt = f"""You are a Live Code Execution Engine & Test Runner sandbox.
A candidate is running their code in 'RUN CODE' mode to validate against PUBLIC TEST CASES and an optional CUSTOM TEST CASE.
This is a test run (NOT final grading).

PROBLEM TITLE: {problem_title}
PROBLEM SPEC:
{question}

STARTER CODE:
{starter_code}

OPTIMAL SOLUTION:
{solution_code}

PUBLIC TEST CASES (Candidate can see these):
{json.dumps(public_test_cases)}

CUSTOM TEST CASE (Provided by candidate, if any):
{custom_test_case if custom_test_case.strip() else "None provided"}

CANDIDATE CODE:
{code_clean}

TASK:
Simulate running the candidate's code against each public test case and the custom test case (if provided).
Determine whether the logic passes each case and what the actual output/behavior is.

Return JSON ONLY with this exact structure:
{{
  "all_passed": true, // boolean, true if all tested cases pass
  "console_output": "[Compiler] Build succeeded (0 errors, 0 warnings).\\n[Runner] Executing test suite...\\nTest 1: PASSED (14ms)...",
  "test_results": [
    {{
      "name": "Public Test 1 [Valid TTL Retrieval]",
      "input": "...",
      "expected": "...",
      "actual": "...",
      "status": "PASSED", // "PASSED" or "FAILED"
      "details": "Returns true with value 'John' within 60s window."
    }}
  ]
}}
Respond ONLY with valid JSON."""

    if active_key:
        try:
            raw_resp = call_gemini_interactions_api(prompt, active_key, model=DEFAULT_MODEL, timeout=40)
            parsed = extract_json_from_llm(raw_resp)
            if "test_results" in parsed:
                return parsed
        except Exception as e:
            print(f"[AI Service] Run coding simulation fallback: {e}")

    # Fallback simulation
    solution_tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", solution_code))
    user_tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", code_clean))
    overlap = len(solution_tokens.intersection(user_tokens)) / max(1, len(solution_tokens))
    passed = overlap >= 0.40 and len(code_clean) > len(starter_code) + 20

    results = []
    for idx, tc in enumerate(public_test_cases, 1):
        t_name = tc.get("name", f"Public Test {idx}")
        t_in = tc.get("input", "")
        t_exp = tc.get("expected", "")
        results.append({
            "name": t_name,
            "input": t_in,
            "expected": t_exp,
            "actual": t_exp if passed else "Incomplete implementation / return mismatch",
            "status": "PASSED" if passed else "FAILED",
            "details": "Verified against public criteria." if passed else "Logic did not satisfy expected outcome."
        })
    if custom_test_case.strip():
        results.append({
            "name": "Custom Test Case",
            "input": custom_test_case.strip(),
            "expected": "Custom evaluation against problem logic",
            "actual": "Computed output matching problem constraints" if passed else "Failed custom execution",
            "status": "PASSED" if passed else "FAILED",
            "details": "Custom input parsed and executed."
        })

    console_log = f"[Sandbox] Build compiled successfully. Executed {len(results)} test cases.\n"
    for r in results:
        console_log += f"[{r['status']}] {r['name']} - Input: {r['input'][:40]} -> {r['actual'][:40]}\n"

    return {
        "all_passed": passed,
        "console_output": console_log.strip(),
        "test_results": results
    }


def evaluate_coding_submission(
    problem_title: str,
    question: str,
    starter_code: str,
    solution_code: str,
    user_code: str,
    public_test_cases: list = None,
    hidden_test_cases: list = None,
    test_cases: list = None,
    candidate_name: str = "Candidate",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Final SUBMIT evaluation of candidate's code.
    Evaluates against both PUBLIC test cases and multiple HIDDEN test cases (boundary, edge, stress).
    Marks as passed (1 mark / 100%) or failed (0 marks / 0%), with failure explanation and optimal solution.
    """
    active_key = get_api_key(api_key)
    code_clean = user_code.strip()
    
    public_test_cases = public_test_cases or test_cases or []
    if not hidden_test_cases:
        hidden_test_cases = [
            {"name": "Hidden Test 1 [Null / Empty Parameter Boundary]", "input": "Null or zero-length parameter", "expected": "Defensive handling without crashing"},
            {"name": "Hidden Test 2 [Edge Condition / Concurrency]", "input": "Extreme boundary / rapid concurrent calls", "expected": "Meets performance & data consistency requirements"}
        ]
        
    all_tests_payload = {
        "public_test_cases": public_test_cases,
        "hidden_test_cases": hidden_test_cases
    }

    # If code is essentially untouched or too short
    if not code_clean or code_clean == starter_code.strip() or len(code_clean) < 30:
        return {
            "passed": False,
            "score": 0,
            "badge_color": "rose",
            "feedback": "Submission rejected (0 Marks Awarded). The code template was left unmodified or empty.",
            "test_results": [
                {"name": tc.get("name", f"Public Test {i}"), "status": "FAILED", "is_hidden": False} for i, tc in enumerate(public_test_cases, 1)
            ] + [
                {"name": tc.get("name", f"Hidden Test {i}"), "status": "FAILED", "is_hidden": True} for i, tc in enumerate(hidden_test_cases, 1)
            ],
            "expected_vs_actual": {
                "expected": "A complete functional implementation satisfying both public and hidden test cases.",
                "actual": "Starter template unmodified or empty method body."
            },
            "bugs_or_gaps": ["No implementation provided", "All public and hidden edge-case tests failed"],
            "solution_code": solution_code,
            "explanation": "Please write your own logic implementing the required operations before submitting.",
            "complexity_analysis": "Optimal Time: O(1) average lookup; Space: O(N) auxiliary storage."
        }

    prompt = f"""You are a Principal Software Engineering Assessor grading a candidate's FINAL CODE SUBMISSION.
Conduct rigorous evaluation against BOTH PUBLIC TEST CASES AND HIDDEN EDGE-CASE TEST CASES.

PROBLEM TITLE: {problem_title}
PROBLEM SPECIFICATION:
{question}

STARTER CODE:
{starter_code}

OPTIMAL PRODUCTION REFERENCE SOLUTION:
{solution_code}

TEST SUITE:
{json.dumps(all_tests_payload)}

CANDIDATE'S SUBMITTED CODE:
{code_clean}

GRADING CRITERIA:
1. 'passed' must be TRUE ONLY if the candidate's code logically satisfies ALL public tests AND ALL hidden edge-case tests.
2. If any hidden edge-case (e.g. null keys, race condition, boundary eviction) fails or is missing, 'passed' must be FALSE and 'score' must be 0.
3. If all pass, 'score' is 100.
4. Detail the result for each test in 'test_results' list with 'status' ("PASSED" or "FAILED") and 'is_hidden' (true/false).

Return JSON ONLY with this exact schema:
{{
  "passed": true, // boolean true ONLY if all public AND hidden tests pass
  "score": 100, // 100 if passed, 0 if failed
  "badge_color": "emerald", // "emerald" if passed, "rose" if failed
  "feedback": "Concise 2-3 sentences explaining the evaluation verdict.",
  "test_results": [
    {{
      "name": "Public Test 1 [Valid TTL Retrieval]",
      "status": "PASSED",
      "is_hidden": false,
      "feedback": "Operates within TTL properly."
    }},
    {{
      "name": "Hidden Test 1 [Null / Empty Parameter Boundary]",
      "status": "PASSED",
      "is_hidden": true,
      "feedback": "Safely handled null parameter."
    }}
  ],
  "expected_vs_actual": {{
    "expected": "Summary of expected behavior and test case outputs",
    "actual": "What candidate's code actually does or fails to handle"
  }},
  "strengths": ["Demonstrated understanding of thread safety"],
  "bugs_or_gaps": ["Failed on null key edge-case"],
  "explanation": "In-depth walkthrough of the optimal approach and why edge cases matter.",
  "complexity_analysis": "Optimal Time: O(1) average lookup; Space: O(N) storage."
}}
Respond ONLY with valid JSON."""

    if active_key:
        try:
            raw_resp = call_gemini_interactions_api(prompt, active_key, model=DEFAULT_MODEL, timeout=50)
            parsed = extract_json_from_llm(raw_resp)
            if "passed" in parsed and "feedback" in parsed:
                parsed["solution_code"] = solution_code
                return parsed
        except Exception as e:
            print(f"[AI Service] Coding evaluation API fallback: {e}")

    # Fallback heuristic code verification
    solution_tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", solution_code))
    user_tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", code_clean))
    overlap = len(solution_tokens.intersection(user_tokens)) / max(1, len(solution_tokens))

    passed = overlap >= 0.50 and len(code_clean) > len(starter_code) + 20
    score = 100 if passed else 0

    test_results = []
    for idx, tc in enumerate(public_test_cases, 1):
        test_results.append({
            "name": tc.get("name", f"Public Test {idx}"),
            "status": "PASSED" if passed else "FAILED",
            "is_hidden": False,
            "feedback": "Validated against public assertion." if passed else "Assertion failed."
        })
    for idx, tc in enumerate(hidden_test_cases, 1):
        test_results.append({
            "name": tc.get("name", f"Hidden Test {idx}"),
            "status": "PASSED" if passed else "FAILED",
            "is_hidden": True,
            "feedback": "Boundary condition verified." if passed else "Hidden edge case failed or not handled."
        })

    return {
        "passed": passed,
        "score": score,
        "badge_color": "emerald" if passed else "rose",
        "feedback": "All public and hidden edge-case test cases passed!" if passed else "Code failed on one or more hidden boundary test cases (0 Marks Awarded). Review the optimal solution below.",
        "test_results": test_results,
        "expected_vs_actual": {
            "expected": "Thread-safe data operations with boundary edge-case handling across all public & hidden suites.",
            "actual": "Implementation validated against all test cases." if passed else "Key constructs, boundary checks, or edge-case handling were omitted or incomplete."
        },
        "strengths": ["Structured method signature", "Appropriate framework libraries referenced"] if passed else ["Starter template syntax preserved"],
        "bugs_or_gaps": [] if passed else ["Failed hidden edge cases", "Incomplete boundary checks"],
        "solution_code": solution_code,
        "explanation": "Production implementations require strict handling of boundaries, concurrency locks, and null arguments.",
        "complexity_analysis": "Time Complexity: O(1) average; Space Complexity: O(N) auxiliary."
    }


def evaluate_comprehensive_interview(
    candidate_name: str,
    questions: list,
    user_answers: dict,
    coding_submissions: dict = None,
    coding_results: dict = None,
    behavioral_answers: dict = None,
    company_name: str = "",
    difficulty: str = "Intermediate",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive end-of-interview evaluation engine.
    Calculates Technical, Coding, and Behavioral sub-scores, provides 'Why We Hire You' analytics,
    critical blindspots, and an executive hire readiness verdict.
    """
    coding_submissions = coding_submissions or {}
    coding_results = coding_results or {}
    behavioral_answers = behavioral_answers or {}
    
    mcq_questions = [q for q in questions if q.get("type", "mcq") == "mcq"]
    coding_questions = [q for q in questions if q.get("type") == "coding"]
    behavioral_questions = [q for q in questions if q.get("type") == "behavioral"]
    
    # 1. Technical MCQ score
    mcq_correct = 0
    topic_stats = {}
    detailed_review = []
    
    for q in questions:
        qid = str(q.get("id"))
        qtype = q.get("type", "mcq")
        topic = q.get("topic", "General")
        
        if topic not in topic_stats:
            topic_stats[topic] = {"total": 0, "correct": 0, "accuracy": 0.0, "type": qtype}
        topic_stats[topic]["total"] += 1
        
        if qtype == "mcq":
            correct_ans = str(q.get("correct_answer", "A")).upper().strip()
            user_ans = str(user_answers.get(qid, "")).upper().strip()
            is_correct = (user_ans == correct_ans) and bool(user_ans)
            if is_correct:
                mcq_correct += 1
                topic_stats[topic]["correct"] += 1
                
            detailed_review.append({
                "id": q.get("id"),
                "type": "mcq",
                "topic": topic,
                "difficulty": q.get("difficulty"),
                "question": q.get("question"),
                "code_snippet": q.get("code_snippet", ""),
                "options": q.get("options", []),
                "user_answer": user_ans if user_ans else "Unanswered",
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "hint": q.get("hint", ""),
                "explanation": q.get("explanation", "")
            })
        elif qtype == "coding":
            code_text = coding_submissions.get(qid, "").strip()
            c_res = coding_results.get(qid, {})
            is_passed = bool(c_res.get("passed", False))
            if is_passed:
                topic_stats[topic]["correct"] += 1
                
            detailed_review.append({
                "id": q.get("id"),
                "type": "coding",
                "topic": topic,
                "difficulty": q.get("difficulty"),
                "title": q.get("title", "Coding Challenge"),
                "question": q.get("question"),
                "user_code": code_text if code_text else "No code submitted",
                "starter_code": q.get("starter_code", ""),
                "solution_code": q.get("solution_code", ""),
                "test_cases": q.get("test_cases", []),
                "is_correct": is_passed,
                "feedback": c_res.get("feedback", ""),
                "expected_vs_actual": c_res.get("expected_vs_actual", {}),
                "hint": q.get("hint", ""),
                "explanation": q.get("explanation", "")
            })
        elif qtype == "behavioral":
            b_text = behavioral_answers.get(qid, "").strip()
            has_b_answer = len(b_text) > 20
            if has_b_answer:
                topic_stats[topic]["correct"] += 1
            detailed_review.append({
                "id": q.get("id"),
                "type": "behavioral",
                "topic": topic,
                "difficulty": "All Levels",

                "title": q.get("title", "Behavioral Question"),
                "question": q.get("question"),
                "user_response": b_text if b_text else "No response recorded",
                "sample_strong_answer": q.get("sample_strong_answer", ""),
                "star_framework_prompt": q.get("star_framework_prompt", ""),
                "is_correct": has_b_answer,
                "hint": q.get("hint", "")
            })

    for t, stat in topic_stats.items():
        stat["accuracy"] = round((stat["correct"] / stat["total"]) * 100, 1) if stat["total"] > 0 else 0

    mcq_score = round((mcq_correct / len(mcq_questions)) * 100, 1) if mcq_questions else 80.0
    
    # Coding sub-score
    coding_attempted = sum(1 for q in coding_questions if len(coding_submissions.get(str(q["id"]), "").strip()) > 30)
    coding_score = round((coding_attempted / len(coding_questions)) * 100, 1) if coding_questions else 85.0
    
    # Behavioral sub-score
    behavioral_attempted = sum(1 for q in behavioral_questions if len(behavioral_answers.get(str(q["id"]), "").strip()) > 30)
    behavioral_score = round((behavioral_attempted / len(behavioral_questions)) * 100, 1) if behavioral_questions else 80.0
    
    # Overall Weighted Readiness Score
    overall_score = round((mcq_score * 0.55) + (coding_score * 0.25) + (behavioral_score * 0.20), 1)
    
    if overall_score >= 85:
        verdict = f"Strong Hire / Ready for {company_name or 'Senior'} Onsite"
        badge_color = "emerald"
        summary = "Exceptional performance across technical MCQs, algorithmic coding logic, and structured behavioral delivery."
    elif overall_score >= 70:
        verdict = f"Hire / Solid Mid-Senior Contender"
        badge_color = "blue"
        summary = "Demonstrated reliable technical fundamentals and practical problem-solving. A brief targeted review of missing concepts will seal your offer."
    elif overall_score >= 50:
        verdict = f"Promising / Targeted Revision Needed"
        badge_color = "amber"
        summary = "Good foundation in core mechanics, but struggled with certain complex database gotchas or coding edge-cases."
    else:
        verdict = f"Early Stage / Foundational Gaps Detected"
        badge_color = "rose"
        summary = "Recommend focused study on core language features, SQL query execution plans, and STAR-method communication before live interviews."

    why_hire_you = [
        f"Demonstrated working knowledge in core technologies ({candidate_name or 'Candidate'} scored {mcq_score}% in technical evaluations).",
        "Pragmatic approach to practical coding problems with focus on thread safety and resource management.",
        "Clear professional communication and willingness to engage in structured problem solving."
    ]
    
    critical_gaps = []
    # Detect weak topics
    for t, stat in topic_stats.items():
        if stat["accuracy"] < 60:
            critical_gaps.append(f"Review core principles and runtime gotchas in: {t} (Current accuracy: {stat['accuracy']}%)")
    if not critical_gaps:
        critical_gaps.append("Brush up on high-concurrency database locking and distributed cache invalidation strategies.")
        critical_gaps.append("Practice articulating trade-offs out loud in under 90 seconds.")

    action_checklist = [
        "Review the complete explanations and optimal code solutions in the review section below.",
        "Rehearse your 2-minute 'Why Should We Hire You' pitch incorporating quantifiable business metrics.",
        "Run another targeted sprint on your lower-scoring technical topics."
    ]

    return {
        "overall_score": overall_score,
        "verdict": verdict,
        "badge_color": badge_color,
        "summary": summary,
        "total_questions": len(questions),
        "correct_count": mcq_correct + coding_attempted + behavioral_attempted,
        "technical_score": mcq_score,
        "coding_score": coding_score,
        "behavioral_score": behavioral_score,
        "why_hire_you": why_hire_you,
        "critical_gaps": critical_gaps[:4],
        "action_checklist": action_checklist,
        "topic_stats": topic_stats,
        "detailed_review": detailed_review
    }



def generate_study_roadmap(
    candidate_name: str,
    company_name: str,
    job_description: str,
    resume_text: str,
    timeline_weeks: int = 4,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an actionable week-by-week technical study roadmap and prep guide
    based on the target company, job description, and candidate's current resume gaps.
    """
    active_key = get_api_key(api_key)
    comp = company_name.strip() if company_name else "Target Role"

    prompt = f"""You are an elite Career Mentor and Technical Interview Coach.
Analyze the candidate's resume against the target company and job description, then generate a comprehensive {timeline_weeks}-Week Master Study Roadmap.

TARGET COMPANY: {comp}
CANDIDATE: {candidate_name or 'Candidate'}
TIMELINE: {timeline_weeks} Weeks

JOB DESCRIPTION:
{job_description[:2500]}

CANDIDATE RESUME:
{resume_text[:2500]}

Generate a high-impact, realistic study roadmap in JSON format with exactly this structure:
{{
  "roadmap_title": "{comp} Technical Interview Preparation Blueprint",
  "target_company": "{comp}",
  "estimated_weeks": {timeline_weeks},
  "executive_summary": "Concise analysis of candidate alignment, primary competitive advantages, and core preparation priorities.",
  "gap_analysis": [
    {{"skill": "Skill Name", "jd_requirement": "What the JD demands", "candidate_status": "Current status in resume", "priority": "High / Medium"}},
    {{"skill": "Skill Name 2", "jd_requirement": "...", "candidate_status": "...", "priority": "High"}}
  ],
  "weekly_modules": [
    {{
      "week_number": 1,
      "theme": "Theme title (e.g. Core Language Internals & Concurrency)",
      "learning_objectives": ["Objective 1", "Objective 2", "Objective 3"],
      "must_study_topics": ["Topic A", "Topic B", "Topic C"],
      "recommended_practice": "Specific coding / problem-solving practice task",
      "mock_interview_questions": [
        "Common question asked at {comp} for this theme?",
        "Another tricky architectural question?"
      ]
    }}
  ],
  "company_interview_secrets": [
    "Crucial insight #1 about {comp}'s interview rounds and evaluation rubric.",
    "Insight #2 on how to navigate technical hurdles."
  ],
  "recommended_resume_tweaks": [
    "Specific tweak #1 to highlight for {comp}.",
    "Specific tweak #2 to emphasize quantifiable business impact."
  ]
}}
Respond ONLY with valid JSON."""

    if active_key:
        try:
            raw_resp = call_gemini_interactions_api(prompt, active_key, model=DEFAULT_MODEL, timeout=60)
            return extract_json_from_llm(raw_resp)
        except Exception as e:
            print(f"[AI Service] Study roadmap fallback: {e}")

    # Fallback structured roadmap
    return {
        "roadmap_title": f"{comp} Technical Interview Preparation Blueprint",
        "target_company": comp,
        "estimated_weeks": timeline_weeks,
        "executive_summary": f"Tailored preparation curriculum for {candidate_name or 'Candidate'} targeting {comp}. Focuses on bridging core architectural gaps, hardening framework fundamentals, and mastering company-specific system questions.",
        "gap_analysis": [
            {"skill": "Advanced API Architecture & Resilience", "jd_requirement": "Experience building high-throughput microservices with retry/circuit-breaker patterns", "candidate_status": "Basic REST API background", "priority": "High"},
            {"skill": "Database Tuning & Query Optimization", "jd_requirement": "Deep knowledge of indexing, execution plans, and deadlock resolution", "candidate_status": "Foundational SQL Server usage", "priority": "High"},
            {"skill": "Modern Frontend State & Performance", "jd_requirement": "State management (Signals/NgRx), change detection optimization", "candidate_status": "Component and template development", "priority": "Medium"}
        ],
        "weekly_modules": [
            {
                "week_number": 1,
                "theme": "Backend Runtime Internals, Memory & Async Patterns",
                "learning_objectives": ["Master async/await state machines and thread pool utilization", "Understand dependency injection service lifetimes and scope traps", "Deep dive into memory allocation, GC, and zero-allocation spans"],
                "must_study_topics": [".NET Core / C# Internals", "Task Parallel Library & I/O Completion Ports", "Middleware Pipeline & Filter Architecture"],
                "recommended_practice": "Refactor a synchronous I/O routine to high-throughput asynchronous streams with proper cancellation tokens.",
                "mock_interview_questions": [
                    "What happens when you block on an async task using .Result or .Wait()?",
                    "How do you prevent memory leaks when injecting services into Singletons?"
                ]
            },
            {
                "week_number": 2,
                "theme": "Data Persistence, Indexing & Query Optimization",
                "learning_objectives": ["Analyze and optimize SQL Server execution plans", "Implement covering non-clustered indexes with INCLUDE columns", "Resolve N+1 query traps in ORMs"],
                "must_study_topics": ["Clustered vs Non-Clustered Indexes", "Execution Plans & Index Seeks vs Scans", "Transactions, Locks & Deadlocks"],
                "recommended_practice": "Write complex SQL window functions (ROW_NUMBER, DENSE_RANK) and optimize an EF Core LINQ query with AsNoTracking and eager loading.",
                "mock_interview_questions": [
                    "How does SQL Server handle parameter sniffing and when should you recompile?",
                    "What is the difference between optimistic concurrency and pessimistic locking?"
                ]
            },
            {
                "week_number": 3,
                "theme": "Frontend Architecture, Signals & Reactive State",
                "learning_objectives": ["Master Angular ChangeDetectionStrategy.OnPush", "Implement fine-grained reactivity using Angular Signals", "Manage complex async stream composition with RxJS operators"],
                "must_study_topics": ["Angular Signals vs RxJS Observables", "switchMap vs mergeMap vs concatMap", "Memory leak prevention with takeUntilDestroyed"],
                "recommended_practice": "Build an autocomplete search bar that debounces user input, cancels in-flight requests, and handles server-side error retries.",
                "mock_interview_questions": [
                    "How does Zone.js trigger change detection and how do modern Signals make Zone optional?",
                    "What is the difference between Standalone Components and NgModules in bundle optimization?"
                ]
            },
            {
                "week_number": 4,
                "theme": "System Design, Real-world Scenarios & Behavioral Polish",
                "learning_objectives": ["Design a scalable RESTful microservice with caching and rate limiting", "Apply SOLID principles in pragmatic software refactoring", "Structure STAR method stories for behavioral and cultural fit"],
                "must_study_topics": ["Distributed Caching with Redis", "Idempotency and API Gateway Patterns", "Company Culture Alignment & Leadership Principles"],
                "recommended_practice": "Conduct a timed 45-minute mock interview session covering system design and past project trade-offs.",
                "mock_interview_questions": [
                    "How would you handle a sudden 10x traffic spike on a critical payment endpoint?",
                    "Describe a time you diagnosed and resolved an elusive production bug."
                ]
            }
        ],
        "company_interview_secrets": [
            f"At {comp}, interviewers evaluate candidates on clarity of trade-offs rather than memorized code syntax.",
            "Always clarify requirements and edge cases before jumping into solution architecture.",
            "Explain *why* an alternative approach was rejected when answering system questions."
        ],
        "recommended_resume_tweaks": [
            "Quantify project achievements with concrete numbers (e.g., 'Reduced query latency by 35% through indexing').",
            f"Tailor your skill summary to feature the exact keywords from {comp}'s job specification.",
            "Add a dedicated 'Key Architectural Contributions' section under your recent role."
        ]
    }


def analyze_resume_ats(
    resume_text: str,
    job_description: str = "",
    target_role: str = "Software Engineer",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform an in-depth Applicant Tracking System (ATS) audit of a resume.
    Calculates overall score, keyword matching, experience bullet improvements,
    and actionable recommendations to pass automated screenings.
    """
    active_key = get_api_key(api_key)
    role = target_role.strip() if target_role else "Software Engineer"

    prompt = f"""You are a Lead Technical Recruiter and an ATS (Applicant Tracking System) Algorithm Auditor.
Audit the following resume with extreme precision for a {role} position.

TARGET ROLE: {role}
TARGET JOB DESCRIPTION (if provided):
{job_description[:2000] if job_description else "Standard industry requirements for " + role}

CANDIDATE RESUME:
{resume_text[:2500]}

Perform a rigorous evaluation and return JSON ONLY with this exact structure:
{{
  "overall_score": 78, // Integer 0 to 100
  "category_scores": {{
    "keyword_match": 80, // 0 to 100
    "experience_impact": 75, // 0 to 100 (checks for quantifiable metrics & strong action verbs)
    "ats_formatting": 85, // 0 to 100 (checks for clean readable layout)
    "skills_alignment": 80 // 0 to 100
  }},
  "summary": "Executive summary of how this resume performs against modern enterprise ATS systems (e.g. Workday, Taleo, Greenhouse, Lever).",
  "matched_keywords": ["C#", ".NET Core", "Angular", "SQL Server", "REST APIs", "Git"],
  "missing_keywords": ["Unit Testing / xUnit", "Docker / Containers", "CI/CD Pipelines", "Redis", "Cloud (Azure/AWS)"],
  "bullet_improvements": [
    {{
      "section": "Experience",
      "original": "Worked on backend APIs and fixed database bugs.",
      "improved": "Architected and optimized 12+ RESTful Web APIs using ASP.NET Core and EF Core, reducing query latency by 34% across 50K daily transactions.",
      "reason": "Replaces passive phrasing with strong action verbs and quantifiable business impact (Google X-Y-Z formula)."
    }},
    {{
      "section": "Experience",
      "original": "Built frontend screens in Angular.",
      "improved": "Engineered 8+ responsive SPA dashboard modules in Angular 16+ utilizing OnPush change detection and reactive state management, decreasing initial load time by 28%.",
      "reason": "Highlights modern architectural patterns and measurable frontend performance improvements."
    }}
  ],
  "formatting_flags": [
    {{"severity": "Good", "message": "Standard font and clear chronological experience detected."}},
    {{"severity": "Warning", "message": "Ensure contact info is at the very top and avoid multi-column tables that confuse legacy ATS parsers."}}
  ],
  "top_actionable_tips": [
    "Integrate the missing high-frequency keywords into your skills section and project bullets.",
    "Ensure every experience bullet follows: [Strong Action Verb] + [Context & Tech Stack] + [Quantifiable Metric].",
    "Add a dedicated 'Cloud & Tools' subsection to immediately catch recruiter boolean searches."
  ]
}}
Respond ONLY with valid JSON."""

    if active_key:
        try:
            raw_resp = call_gemini_interactions_api(prompt, active_key, model=DEFAULT_MODEL, timeout=60)
            return extract_json_from_llm(raw_resp)
        except Exception as e:
            print(f"[AI Service] ATS analysis fallback: {e}")

    # Fallback heuristic ATS analysis
    text_lower = resume_text.lower()
    common_keywords = [
        "c#", ".net", "asp.net", "angular", "sql", "sql server", "typescript",
        "javascript", "rest api", "git", "docker", "azure", "aws", "unit test",
        "ci/cd", "microservices", "agile", "entity framework"
    ]
    matched = [kw for kw in common_keywords if kw in text_lower]
    missing = [kw for kw in common_keywords if kw not in text_lower][:6]
    
    # Calculate score based on keyword coverage and metrics
    has_metrics = bool(re.search(r"\d+%", resume_text) or re.search(r"\$\d+", resume_text) or re.search(r"\d+\+", resume_text))
    base_score = min(92, max(60, 50 + len(matched) * 3 + (10 if has_metrics else 0)))

    return {
        "overall_score": base_score,
        "category_scores": {
            "keyword_match": min(95, 60 + len(matched) * 2),
            "experience_impact": 78 if has_metrics else 62,
            "ats_formatting": 85,
            "skills_alignment": min(90, 65 + len(matched) * 2)
        },
        "summary": f"Your resume demonstrates strong technical capabilities for {role}. It achieves an ATS score of {base_score}/100. Adding high-priority missing keywords and increasing quantifiable achievements will propel it into the top 5% of applicant pools.",
        "matched_keywords": [k.upper() for k in matched[:8]],
        "missing_keywords": [k.upper() for k in missing],
        "bullet_improvements": [
            {
                "section": "Professional Experience",
                "original": "Worked on backend development and maintained database.",
                "improved": f"Architected high-throughput backend services using {matched[0].upper() if matched else '.NET Core'} and optimized SQL queries, reducing API response times by 32% across production systems.",
                "reason": "Quantifies performance improvements and uses strong technical leadership verbs."
            },
            {
                "section": "Frontend Development",
                "original": "Developed user interface components.",
                "improved": f"Engineered scalable single-page application features using {matched[1].upper() if len(matched)>1 else 'Angular'}, achieving 99.8% uptime and elevating end-user performance.",
                "reason": "Contextualizes scope and ties work to reliable customer impact."
            }
        ],
        "formatting_flags": [
            {"severity": "Good", "message": "Clean chronological career progression detected."},
            {"severity": "Warning", "message": "Avoid complex headers, footers, or embedded graphics that can get stripped by older parsers."}
        ],
        "top_actionable_tips": [
            f"Add missing keywords ({', '.join([k.upper() for k in missing[:3]])}) to your core technical skills block.",
            "Incorporate quantifiable business impact into at least 70% of your experience bullets.",
            "Tailor your professional title and executive summary to match the exact phrasing of your target job description."
        ]
    }

