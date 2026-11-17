import os
import sys
import json
import traceback
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from services.db import init_db, SessionLocal, User, QuizHistory, ATSReview, StudyPlan, get_database_url
from services.email_service import generate_otp, send_otp_email
from services.resume_parser import extract_text_from_file, analyze_resume_text
from services.ai_service import (
    analyze_candidate_profile,
    generate_interview_quiz,
    generate_company_targeted_quiz,
    generate_study_roadmap,
    analyze_resume_ats,
    evaluate_behavioral_response,
    run_coding_simulation,
    evaluate_coding_submission,
    evaluate_comprehensive_interview
)

# Reconfigure stdout for Windows console UTF-8 safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Administrator Authorization Configuration
ADMIN_EMAILS = {"kiruthiknivasnkl@gmail.com"}

def is_admin_user() -> bool:
    """Check if the currently authenticated session belongs to the verified administrator."""
    email = session.get("user_email", "").strip().lower()
    return bool(email and email in ADMIN_EMAILS)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "skillsprint-secret-super-key-2026")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize Database tables
init_db()


# ==========================================
# AUTHENTICATION & USER MANAGEMENT
# ==========================================
@app.route("/api/auth/register", methods=["POST"])
def register():
    """Register a new user, create OTP, and send verification email."""
    db = SessionLocal()
    try:
        data = request.get_json(force=True) or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not name or not email or not password:
            return jsonify({"error": "Name, email, and password are required."}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long."}), 400

        existing_user = db.query(User).filter(User.email == email).first()
        otp = generate_otp()
        now = datetime.now(timezone.utc)

        if existing_user:
            if existing_user.is_verified:
                return jsonify({"error": "An account with this email already exists. Please log in."}), 400
            # User exists but not verified yet - update password and send new OTP
            existing_user.name = name
            existing_user.password_hash = generate_password_hash(password)
            existing_user.otp_code = otp
            existing_user.otp_created_at = now
            db.commit()
            user = existing_user
        else:
            new_user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                is_verified=False,
                otp_code=otp,
                otp_created_at=now
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user

        # Send OTP
        success, msg, extra = send_otp_email(email, name, otp)

        return jsonify({
            "success": True,
            "message": msg,
            "email": email,
            "extra": extra
        })

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    """Verify user account with 6-digit OTP."""
    db = SessionLocal()
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email", "").strip().lower()
        otp = data.get("otp", "").strip()

        if not email or not otp:
            return jsonify({"error": "Email and OTP code are required."}), 400

        user = db.query(User).filter(User.email == email).first()
        if not user:
            return jsonify({"error": "User account not found."}), 404

        if user.otp_code != otp:
            return jsonify({"error": "Invalid verification code. Please check and try again."}), 400

        # Mark verified
        user.is_verified = True
        user.otp_code = None
        db.commit()

        # Log user into session
        session.permanent = True
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_name"] = user.name

        return jsonify({
            "success": True,
            "message": "Account verified successfully!",
            "user": user.to_dict()
        })

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Verification failed: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/auth/resend-otp", methods=["POST"])
def resend_otp():
    """Resend OTP to email."""
    db = SessionLocal()
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email", "").strip().lower()

        user = db.query(User).filter(User.email == email).first()
        if not user:
            return jsonify({"error": "User not found."}), 404

        otp = generate_otp()
        user.otp_code = otp
        user.otp_created_at = datetime.now(timezone.utc)
        db.commit()

        success, msg, extra = send_otp_email(email, user.name, otp)
        return jsonify({
            "success": True,
            "message": msg,
            "extra": extra
        })

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Resend OTP failed: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Log in user with email and password."""
    db = SessionLocal()
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        user = db.query(User).filter(User.email == email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid email or password."}), 401

        if not user.is_verified:
            otp = generate_otp()
            user.otp_code = otp
            user.otp_created_at = datetime.now(timezone.utc)
            db.commit()
            send_otp_email(user.email, user.name, otp)
            return jsonify({
                "error": "Account not verified yet. A new verification OTP was sent to your email.",
                "requires_verification": True,
                "email": user.email
            }), 403

        # Set session
        session.permanent = True
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_name"] = user.name

        return jsonify({
            "success": True,
            "message": f"Welcome back, {user.name}!",
            "user": user.to_dict()
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Login failed: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    """Send a password reset OTP to the user's email."""
    db = SessionLocal()
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email", "").strip().lower()

        if not email:
            return jsonify({"error": "Email address is required."}), 400

        user = db.query(User).filter(User.email == email).first()
        if not user:
            return jsonify({"error": "No account found with this email address."}), 404

        otp = generate_otp()
        user.otp_code = otp
        user.otp_created_at = datetime.now(timezone.utc)
        db.commit()

        success, msg, extra = send_otp_email(email, user.name, otp, purpose="Password Reset")
        return jsonify({
            "success": True,
            "message": f"A 6-digit password reset code has been sent to {email}.",
            "email": email,
            "extra": extra
        })
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Password reset request failed: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    """Verify OTP and update user's password."""
    db = SessionLocal()
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email", "").strip().lower()
        otp = data.get("otp", "").strip()
        new_password = data.get("new_password", "").strip()

        if not email or not otp or not new_password:
            return jsonify({"error": "Email, verification code, and new password are required."}), 400

        if len(new_password) < 6:
            return jsonify({"error": "New password must be at least 6 characters long."}), 400

        user = db.query(User).filter(User.email == email).first()
        if not user:
            return jsonify({"error": "User account not found."}), 404

        if user.otp_code != otp:
            return jsonify({"error": "Invalid verification code. Please check your email and try again."}), 400

        # Update password
        user.password_hash = generate_password_hash(new_password)
        user.is_verified = True
        user.otp_code = None
        db.commit()

        # Log into session
        session.permanent = True
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_name"] = user.name

        return jsonify({
            "success": True,
            "message": "Password updated successfully! You are now signed in.",
            "user": user.to_dict()
        })
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Password reset failed: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/auth/me", methods=["GET"])
def get_current_user():
    """Retrieve logged-in user details."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"logged_in": False})

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            session.clear()
            return jsonify({"logged_in": False})
        return jsonify({
            "logged_in": True,
            "user": user.to_dict(),
            "is_admin": is_admin_user()
        })
    finally:
        db.close()


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Clear session."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/auth/update-profile", methods=["POST"])
def update_profile():
    """Save or update candidate's default profile in database."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    db = SessionLocal()
    try:
        data = request.get_json(force=True) or {}
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({"error": "User not found."}), 404

        if "primary_skill" in data:
            user.primary_skill = data["primary_skill"].strip()
        if "secondary_skill" in data:
            user.secondary_skill = data["secondary_skill"].strip()
        if "years_experience" in data:
            try:
                user.years_experience = float(data["years_experience"])
            except:
                pass
        if "resume_text" in data and data["resume_text"].strip():
            user.resume_text = data["resume_text"].strip()

        db.commit()
        return jsonify({"success": True, "user": user.to_dict()})
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Profile update failed: {str(e)}"}), 500
    finally:
        db.close()


# ==========================================
# RESUME PARSING & PROFILE ANALYSIS
# ==========================================
@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    """Handle resume file upload (PDF, DOCX, TXT) or raw pasted text."""
    try:
        resume_text = ""
        file_name = ""

        if "file" in request.files:
            file = request.files["file"]
            if file and file.filename and allowed_file(file.filename):
                safe_name = secure_filename(file.filename)
                saved_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
                file.save(saved_path)
                resume_text = extract_text_from_file(saved_path)
                file_name = safe_name

        pasted_text = request.form.get("resume_text", "").strip()
        if not resume_text and pasted_text:
            resume_text = pasted_text
            file_name = "Pasted Resume"

        if not resume_text:
            return jsonify({"error": "No resume text or valid file received."}), 400

        candidate_name = request.form.get("name", "").strip()
        primary_skill = request.form.get("primary_skill", "").strip()
        secondary_skill = request.form.get("secondary_skill", "").strip()

        analysis = analyze_resume_text(
            text=resume_text,
            candidate_name=candidate_name,
            primary_skill=primary_skill,
            secondary_skill=secondary_skill
        )

        # If user is logged in, optionally cache resume to user profile
        user_id = session.get("user_id")
        if user_id:
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and not user.resume_text:
                    user.resume_text = resume_text
                    if primary_skill: user.primary_skill = primary_skill
                    if secondary_skill: user.secondary_skill = secondary_skill
                    db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

        return jsonify({
            "success": True,
            "filename": file_name,
            "text_length": len(resume_text),
            "resume_text": resume_text,
            "analysis": analysis
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to process resume: {str(e)}"}), 500


@app.route("/api/analyze-profile", methods=["POST"])
def analyze_profile():
    """AI analyzes candidate profile and returns custom assessment configuration."""
    try:
        data = request.get_json(force=True) or {}
        candidate_name = data.get("name", "").strip()
        resume_text = data.get("resume_text", "").strip()
        primary_skill = data.get("primary_skill", "").strip()
        secondary_skill = data.get("secondary_skill", "").strip()
        custom_api_key = data.get("api_key", "").strip()

        profile_analysis = analyze_candidate_profile(
            candidate_name=candidate_name,
            resume_text=resume_text,
            primary_skill=primary_skill,
            secondary_skill=secondary_skill,
            api_key=custom_api_key
        )

        return jsonify({
            "success": True,
            "profile": profile_analysis
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Profile analysis failed: {str(e)}"}), 500


# ==========================================
# QUIZ GENERATION & EVALUATION
# ==========================================
@app.route("/api/generate-quiz", methods=["POST"])
def generate_quiz():
    """Generate dynamic, multi-modal technical assessment (MCQs, Coding, Behavioral)."""
    try:
        data = request.get_json(force=True) or {}
        candidate_name = data.get("name", "Candidate").strip()
        resume_text = data.get("resume_text", "").strip()
        primary_skill = data.get("primary_skill", ".NET Core / C#").strip()
        secondary_skill = data.get("secondary_skill", "Angular").strip()
        
        try:
            years_exp = float(data.get("years_of_experience", 2.0))
        except (ValueError, TypeError):
            years_exp = 2.0

        difficulty = data.get("difficulty", "Intermediate").strip()
        if difficulty not in ["Beginner", "Intermediate", "Harder"]:
            difficulty = "Intermediate"

        try:
            question_count = int(data.get("question_count", 15))
        except (ValueError, TypeError):
            question_count = 15
        question_count = max(5, min(question_count, 40))

        include_coding = bool(data.get("include_coding", True))
        include_behavioral = bool(data.get("include_behavioral", True))
        custom_api_key = data.get("api_key", "").strip()

        quiz_data = generate_interview_quiz(
            candidate_name=candidate_name,
            resume_text=resume_text,
            primary_skill=primary_skill,
            secondary_skill=secondary_skill,
            years_of_experience=years_exp,
            difficulty=difficulty,
            question_count=question_count,
            include_coding=include_coding,
            include_behavioral=include_behavioral,
            api_key=custom_api_key
        )

        return jsonify({
            "success": True,
            "quiz": quiz_data
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Quiz generation failed: {str(e)}"}), 500


@app.route("/api/company-quiz/generate", methods=["POST"])
def generate_company_quiz():
    """Generate company-targeted interview assessment tailored to specific JD."""
    try:
        data = request.get_json(force=True) or {}
        candidate_name = data.get("name", "Candidate").strip()
        company_name = data.get("company_name", "Target Company").strip()
        job_description = data.get("job_description", "").strip()
        resume_text = data.get("resume_text", "").strip()
        difficulty = data.get("difficulty", "Intermediate").strip()
        custom_api_key = data.get("api_key", "").strip()

        try:
            question_count = int(data.get("question_count", 15))
        except:
            question_count = 15
        question_count = max(5, min(question_count, 40))

        include_coding = bool(data.get("include_coding", True))
        include_behavioral = bool(data.get("include_behavioral", True))

        if not job_description:
            return jsonify({"error": "Job description is required to generate company-targeted questions."}), 400

        quiz_data = generate_company_targeted_quiz(
            candidate_name=candidate_name,
            company_name=company_name,
            job_description=job_description,
            resume_text=resume_text,
            difficulty=difficulty,
            question_count=question_count,
            include_coding=include_coding,
            include_behavioral=include_behavioral,
            api_key=custom_api_key
        )

        return jsonify({
            "success": True,
            "quiz": quiz_data
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Company quiz generation failed: {str(e)}"}), 500


@app.route("/api/evaluate-behavioral", methods=["POST"])
def evaluate_behavioral():
    """Evaluate candidate's behavioral answer in real time using STAR analysis."""
    try:
        data = request.get_json(force=True) or {}
        question = data.get("question", "").strip()
        answer = data.get("answer", "").strip()
        candidate_name = data.get("name", "Candidate").strip()
        role_context = data.get("role_context", "").strip()
        custom_api_key = data.get("api_key", "").strip()

        if not question or not answer:
            return jsonify({"error": "Question and answer text are required."}), 400

        result = evaluate_behavioral_response(
            question=question,
            candidate_answer=answer,
            candidate_name=candidate_name,
            role_context=role_context,
            api_key=custom_api_key
        )
        return jsonify({"success": True, "evaluation": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Behavioral evaluation failed: {str(e)}"}), 500


@app.route("/api/run-coding", methods=["POST"])
def run_coding():
    """Run candidate's code in test sandbox against public test cases and optional custom test case."""
    try:
        data = request.get_json(force=True) or {}
        problem_title = data.get("problem_title", "Coding Challenge").strip()
        question = data.get("question", "").strip()
        starter_code = data.get("starter_code", "").strip()
        solution_code = data.get("solution_code", "").strip()
        user_code = data.get("user_code", "").strip()
        public_test_cases = data.get("public_test_cases", []) or data.get("test_cases", [])
        custom_test_case = data.get("custom_test_case", "").strip()
        candidate_name = data.get("name", "Candidate").strip()
        custom_api_key = data.get("api_key", "").strip()

        if not question:
            return jsonify({"error": "Question is required."}), 400

        result = run_coding_simulation(
            problem_title=problem_title,
            question=question,
            starter_code=starter_code,
            solution_code=solution_code,
            user_code=user_code,
            public_test_cases=public_test_cases,
            custom_test_case=custom_test_case,
            candidate_name=candidate_name,
            api_key=custom_api_key
        )
        return jsonify({"success": True, "result": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Coding run failed: {str(e)}"}), 500


@app.route("/api/evaluate-coding", methods=["POST"])
def evaluate_coding():
    """Evaluate candidate's final code submission against public and hidden edge-case test cases."""
    try:
        data = request.get_json(force=True) or {}
        problem_title = data.get("problem_title", "Coding Challenge").strip()
        question = data.get("question", "").strip()
        starter_code = data.get("starter_code", "").strip()
        solution_code = data.get("solution_code", "").strip()
        user_code = data.get("user_code", "").strip()
        public_test_cases = data.get("public_test_cases", []) or data.get("test_cases", [])
        hidden_test_cases = data.get("hidden_test_cases", [])
        test_cases = data.get("test_cases", [])
        candidate_name = data.get("name", "Candidate").strip()
        custom_api_key = data.get("api_key", "").strip()

        if not question or not user_code:
            return jsonify({"error": "Question and user code are required."}), 400

        result = evaluate_coding_submission(
            problem_title=problem_title,
            question=question,
            starter_code=starter_code,
            solution_code=solution_code,
            user_code=user_code,
            public_test_cases=public_test_cases,
            hidden_test_cases=hidden_test_cases,
            test_cases=test_cases,
            candidate_name=candidate_name,
            api_key=custom_api_key
        )
        return jsonify({"success": True, "result": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Coding evaluation failed: {str(e)}"}), 500


@app.route("/api/evaluate-quiz", methods=["POST"])
def evaluate_quiz():
    """Evaluate complete multi-modal interview (MCQs + Coding + Behavioral) with full readiness analytics."""
    try:
        data = request.get_json(force=True) or {}
        questions = data.get("questions", [])
        user_answers = data.get("answers", {})
        coding_submissions = data.get("coding_submissions", {})
        coding_results = data.get("coding_results", {})
        behavioral_answers = data.get("behavioral_answers", {})
        candidate_name = data.get("name", "Candidate")
        quiz_type = data.get("quiz_type", "skill_quiz")
        company_name = data.get("company_name", "")
        quiz_title = data.get("quiz_title", "Interview Assessment")
        difficulty = data.get("difficulty", "Intermediate")
        custom_api_key = data.get("api_key", "").strip()

        if not questions:
            return jsonify({"error": "No questions provided for evaluation."}), 400

        eval_res = evaluate_comprehensive_interview(
            candidate_name=candidate_name,
            questions=questions,
            user_answers=user_answers,
            coding_submissions=coding_submissions,
            coding_results=coding_results,
            behavioral_answers=behavioral_answers,
            company_name=company_name,
            difficulty=difficulty,
            api_key=custom_api_key
        )

        # Record to database if user is authenticated
        user_id = session.get("user_id")
        if user_id:
            db = SessionLocal()
            try:
                hist = QuizHistory(
                    user_id=user_id,
                    quiz_title=quiz_title,
                    quiz_type=quiz_type,
                    company_name=company_name,
                    difficulty=difficulty,
                    total_questions=eval_res["total_questions"],
                    correct_count=eval_res["correct_count"],
                    percentage=eval_res["overall_score"],
                    verdict=eval_res["verdict"],
                    topic_stats_json=json.dumps(eval_res["topic_stats"])
                )
                db.add(hist)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[DB Error] Failed to record quiz history: {e}")
            finally:
                db.close()

        return jsonify({
            "success": True,
            **eval_res
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Quiz evaluation failed: {str(e)}"}), 500


# ==========================================
# STUDY ROADMAP & ATS RESUME AUDIT
# ==========================================
@app.route("/api/study-roadmap/generate", methods=["POST"])
def study_roadmap():
    """Generate tailored study roadmap based on company, JD, and resume."""
    try:
        data = request.get_json(force=True) or {}
        candidate_name = data.get("name", "Candidate").strip()
        company_name = data.get("company_name", "Target Company").strip()
        job_description = data.get("job_description", "").strip()
        resume_text = data.get("resume_text", "").strip()
        timeline_weeks = int(data.get("timeline_weeks", 4))
        custom_api_key = data.get("api_key", "").strip()

        if not job_description and not resume_text:
            return jsonify({"error": "Please provide either a Job Description or Resume to build a roadmap."}), 400

        roadmap_data = generate_study_roadmap(
            candidate_name=candidate_name,
            company_name=company_name,
            job_description=job_description,
            resume_text=resume_text,
            timeline_weeks=timeline_weeks,
            api_key=custom_api_key
        )

        # Save to DB if logged in
        user_id = session.get("user_id")
        if user_id:
            db = SessionLocal()
            try:
                plan = StudyPlan(
                    user_id=user_id,
                    target_role=data.get("target_role", "Software Engineer"),
                    company_name=company_name,
                    plan_title=roadmap_data.get("roadmap_title", f"{company_name} Prep Plan"),
                    plan_json=json.dumps(roadmap_data)
                )
                db.add(plan)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[DB Error] Failed to save study plan: {e}")
            finally:
                db.close()

        return jsonify({
            "success": True,
            "roadmap": roadmap_data
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Roadmap generation failed: {str(e)}"}), 500


@app.route("/api/ats-audit", methods=["POST"])
def ats_audit():
    """Perform comprehensive ATS scoring and resume optimization audit."""
    try:
        data = request.get_json(force=True) or {}
        resume_text = data.get("resume_text", "").strip()
        job_description = data.get("job_description", "").strip()
        target_role = data.get("target_role", "Software Engineer").strip()
        company_name = data.get("company_name", "").strip()
        custom_api_key = data.get("api_key", "").strip()

        if not resume_text:
            return jsonify({"error": "Resume text is required for ATS audit."}), 400

        ats_data = analyze_resume_ats(
            resume_text=resume_text,
            job_description=job_description,
            target_role=target_role,
            api_key=custom_api_key
        )

        # Save to DB if user is logged in
        user_id = session.get("user_id")
        if user_id:
            db = SessionLocal()
            try:
                review = ATSReview(
                    user_id=user_id,
                    target_role=target_role,
                    company_name=company_name,
                    overall_score=ats_data.get("overall_score", 75),
                    analysis_json=json.dumps(ats_data)
                )
                db.add(review)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[DB Error] Failed to save ATS review: {e}")
            finally:
                db.close()

        return jsonify({
            "success": True,
            "audit": ats_data
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"ATS audit failed: {str(e)}"}), 500


# ==========================================
# USER DASHBOARD & HISTORY
# ==========================================
@app.route("/api/user/dashboard-stats", methods=["GET"])
def user_dashboard_stats():
    """Retrieve statistics for the candidate's dashboard."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"logged_in": False})

    db = SessionLocal()
    try:
        quizzes = db.query(QuizHistory).filter(QuizHistory.user_id == user_id).order_by(QuizHistory.id.desc()).all()
        ats_reviews = db.query(ATSReview).filter(ATSReview.user_id == user_id).order_by(ATSReview.id.desc()).all()
        plans = db.query(StudyPlan).filter(StudyPlan.user_id == user_id).order_by(StudyPlan.id.desc()).all()

        total_tests = len(quizzes)
        avg_score = round(sum(q.percentage for q in quizzes) / total_tests, 1) if total_tests > 0 else 0.0
        latest_ats = ats_reviews[0].overall_score if ats_reviews else None

        return jsonify({
            "logged_in": True,
            "total_tests": total_tests,
            "average_score": avg_score,
            "latest_ats": latest_ats,
            "total_plans": len(plans),
            "recent_quizzes": [q.to_dict() for q in quizzes[:5]],
            "recent_ats": [a.to_dict() for a in ats_reviews[:3]],
            "recent_plans": [p.to_dict() for p in plans[:3]]
        })
    finally:
        db.close()


@app.route("/api/user/history", methods=["GET"])
def user_history():
    """Retrieve complete history for the user."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"logged_in": False, "quizzes": [], "ats_reviews": [], "study_plans": []})

    db = SessionLocal()
    try:
        quizzes = db.query(QuizHistory).filter(QuizHistory.user_id == user_id).order_by(QuizHistory.id.desc()).all()
        ats_reviews = db.query(ATSReview).filter(ATSReview.user_id == user_id).order_by(ATSReview.id.desc()).all()
        plans = db.query(StudyPlan).filter(StudyPlan.user_id == user_id).order_by(StudyPlan.id.desc()).all()

        return jsonify({
            "logged_in": True,
            "quizzes": [q.to_dict() for q in quizzes],
            "ats_reviews": [a.to_dict() for a in ats_reviews],
            "study_plans": [p.to_dict() for p in plans]
        })
    finally:
        db.close()


# ==========================================
# STATUS & UTILITIES
# ==========================================
@app.route("/api/status", methods=["GET"])
def api_status():
    has_gemini = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    has_openai = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    db_url = get_database_url()
    db_type = "Online PostgreSQL (Supabase / Neon)" if "postgres" in db_url else "Open-Source SQLite"
    
    return jsonify({
        "status": "online",
        "has_gemini_key": has_gemini,
        "has_openai_key": has_openai,
        "database_type": db_type,
        "default_model": "gemini-3.5-flash-lite / gemini-3.8-flash"
    })


@app.route("/api/sample-resume", methods=["GET"])
def get_sample_resume():
    """Return a sample 2-year .NET, Angular, SQL Server resume."""
    sample = {
        "name": "Alex Mercer",
        "primary_skill": ".NET Core / C#",
        "secondary_skill": "Angular",
        "resume_text": """ALEX MERCER
Software Developer | 2 Years of Experience
Email: alex.mercer@email.com | LinkedIn: linkedin.com/in/alexmercer-dev

SUMMARY:
Results-driven Full Stack Software Developer with 2 years of professional experience designing, building, and deploying scalable enterprise web applications using .NET Core, C#, Angular, and Microsoft SQL Server. Passionate about clean architecture, SOLID principles, and RESTful API performance.

CORE TECHNICAL SKILLS:
- Backend: .NET 8, ASP.NET Core Web API, C#, Entity Framework Core, LINQ, Dependency Injection, MediatR, xUnit.
- Frontend: Angular (v16/v17), TypeScript, RxJS, NgRx, HTML5, CSS3, SCSS, Bootstrap, Tailwind CSS.
- Databases: Microsoft SQL Server, T-SQL, Stored Procedures, Indexing, Query Optimization, Redis Caching.
- Cloud & DevOps: Azure App Services, Docker containers, Azure DevOps, Git, CI/CD pipelines.

PROFESSIONAL EXPERIENCE:
Junior Full Stack Developer | FinTech Solutions Inc.
July 2024 - Present (approx. 2 years total experience)
- Developed and maintained microservices-based REST APIs using ASP.NET Core and Entity Framework Core, processing over 50,000 daily financial transactions.
- Built dynamic, responsive single-page application (SPA) modules in Angular 16+ utilizing Standalone Components, Reactive Forms, and NgRx state management.
- Optimized complex SQL Server queries, stored procedures, and created covering non-clustered indexes, reducing average API response times by 38%.
- Implemented JWT token-based authentication and role-based authorization using ASP.NET Core Identity.
- Wrote unit and integration tests using xUnit and Moq, achieving 82% code coverage.

EDUCATION:
Bachelor of Science in Computer Science & Engineering | 2024
"""
    }
    return jsonify(sample)


# ==========================================
# ADMIN DATABASE PORTAL & CLOUD CONFIG
# ==========================================
@app.route("/api/admin/overview", methods=["GET"])
def admin_overview():
    """Retrieve full database view across all users, quizzes, ATS reviews, and plans."""
    if not is_admin_user():
        return jsonify({"error": "Access denied. Administrative access is strictly restricted to kiruthiknivasnkl@gmail.com."}), 403

    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id.desc()).all()
        quizzes = db.query(QuizHistory).order_by(QuizHistory.id.desc()).all()
        ats_reviews = db.query(ATSReview).order_by(ATSReview.id.desc()).all()
        plans = db.query(StudyPlan).order_by(StudyPlan.id.desc()).all()

        user_map = {u.id: u for u in users}

        user_list = []
        for u in users:
            user_list.append({
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "is_verified": u.is_verified,
                "primary_skill": u.primary_skill or "",
                "secondary_skill": u.secondary_skill or "",
                "years_experience": u.years_experience or 2.0,
                "has_resume": bool(u.resume_text and len(u.resume_text.strip()) > 20),
                "resume_snippet": (u.resume_text[:120] + "...") if u.resume_text else "No resume uploaded",
                "created_at": u.created_at.strftime("%b %d, %Y - %I:%M %p") if u.created_at else ""
            })

        quiz_list = []
        for q in quizzes:
            user_obj = user_map.get(q.user_id)
            quiz_list.append({
                "id": q.id,
                "user_name": user_obj.name if user_obj else "Guest/Deleted",
                "user_email": user_obj.email if user_obj else "N/A",
                "quiz_title": q.quiz_title,
                "quiz_type": q.quiz_type,
                "company_name": q.company_name or "General",
                "difficulty": q.difficulty,
                "score": f"{q.correct_count} / {q.total_questions}",
                "percentage": q.percentage,
                "verdict": q.verdict,
                "created_at": q.created_at.strftime("%b %d, %Y - %I:%M %p") if q.created_at else ""
            })

        ats_list = []
        for a in ats_reviews:
            user_obj = user_map.get(a.user_id)
            ats_list.append({
                "id": a.id,
                "user_name": user_obj.name if user_obj else "Guest/Deleted",
                "user_email": user_obj.email if user_obj else "N/A",
                "target_role": a.target_role,
                "company_name": a.company_name or "General",
                "overall_score": a.overall_score,
                "created_at": a.created_at.strftime("%b %d, %Y - %I:%M %p") if a.created_at else ""
            })

        plan_list = []
        for p in plans:
            user_obj = user_map.get(p.user_id)
            plan_list.append({
                "id": p.id,
                "user_name": user_obj.name if user_obj else "Guest/Deleted",
                "user_email": user_obj.email if user_obj else "N/A",
                "plan_title": p.plan_title,
                "company_name": p.company_name or "General",
                "target_role": p.target_role,
                "created_at": p.created_at.strftime("%b %d, %Y - %I:%M %p") if p.created_at else ""
            })

        db_url = get_database_url()
        db_provider = "Online PostgreSQL (Supabase / Neon / Render)" if "postgres" in db_url else "Open-Source Local SQLite"

        return jsonify({
            "success": True,
            "db_provider": db_provider,
            "db_url_masked": db_url.split("@")[-1] if "@" in db_url else "interview_hub.db",
            "stats": {
                "total_users": len(users),
                "verified_users": sum(1 for u in users if u.is_verified),
                "total_quizzes": len(quizzes),
                "total_ats_checks": len(ats_reviews),
                "total_plans": len(plans),
                "avg_quiz_score": round(sum(q.percentage for q in quizzes) / len(quizzes), 1) if quizzes else 0.0
            },
            "users": user_list,
            "quizzes": quiz_list,
            "ats_reviews": ats_list,
            "plans": plan_list
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to retrieve admin overview: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/admin/save-config", methods=["POST"])
def admin_save_config():
    """Update runtime database URL or SMTP configuration."""
    if not is_admin_user():
        return jsonify({"error": "Access denied. Administrative access is strictly restricted to kiruthiknivasnkl@gmail.com."}), 403

    try:
        data = request.get_json(force=True) or {}
        db_url = data.get("database_url", "").strip()
        smtp_server = data.get("smtp_server", "").strip()
        smtp_port = data.get("smtp_port", "587").strip()
        smtp_email = data.get("smtp_email", "").strip()
        smtp_pass = data.get("smtp_password", "").strip()
        gemini_key = data.get("gemini_key", "").strip()

        env_lines = []
        if db_url:
            os.environ["DATABASE_URL"] = db_url
            env_lines.append(f"DATABASE_URL={db_url}")
        if smtp_server:
            os.environ["SMTP_SERVER"] = smtp_server
            env_lines.append(f"SMTP_SERVER={smtp_server}")
        if smtp_port:
            os.environ["SMTP_PORT"] = smtp_port
            env_lines.append(f"SMTP_PORT={smtp_port}")
        if smtp_email:
            os.environ["SMTP_EMAIL"] = smtp_email
            env_lines.append(f"SMTP_EMAIL={smtp_email}")
        if smtp_pass:
            os.environ["SMTP_PASSWORD"] = smtp_pass
            env_lines.append(f"SMTP_PASSWORD={smtp_pass}")
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key
            env_lines.append(f"GEMINI_API_KEY={gemini_key}")

        # Save to .env file for persistence across server restarts
        env_file_path = os.path.join(os.path.dirname(__file__), ".env")
        try:
            with open(env_file_path, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(env_lines) + "\n")
        except Exception as e:
            print(f"[Config] Note: Could not write .env file: {e}")

        return jsonify({
            "success": True,
            "message": "Configuration updated successfully!"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to save configuration: {str(e)}"}), 500


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[SkillSprint AI] Server starting on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
