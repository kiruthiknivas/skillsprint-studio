# SkillSprint AI - Career & Technical Interview Intelligence Platform

SkillSprint AI is an end-to-end job seeker web application designed to help software engineers and technical candidates prepare for interviews, master targeted company requirements, and optimize their resumes for Applicant Tracking Systems (ATS).

---

## What's New in This Version

### 1. User Authentication & Email OTP Verification
- **User Registration**: Sign up with Name, Email ID, and Password.
- **Email OTP Verification**: Dispatches a 6-digit one-time passcode to verify email ownership before granting workspace access.
- **Smart Development Mode**: If SMTP is not yet configured, the platform displays an instant Dev OTP banner so you and your friends can test and create accounts immediately with zero friction.
- **Configurable SMTP**: Easily connect your personal or organization's email (Gmail, Outlook, SendGrid, Amazon SES) in Settings.

### 2. Open-Source Online Database Integration
- **Zero-Cost Storage**: Connects out of the box to open-source databases with no paid servers required:
  - **Local Open-Source Database**: Pre-configured SQLite engine (`interview_hub.db`).
  - **Cloud Open-Source Databases**: Native support for **Supabase**, **Neon.tech**, **Render**, or **Railway** PostgreSQL by simply pasting your connection string (`postgresql+psycopg://...`) in Settings or setting `DATABASE_URL`.
- **User Isolation**: All test attempts, quiz scores, ATS reviews, and study plans are permanently saved and indexed per user.

### 3. Company & Job Description Targeted Interview Simulator
- Enter your **Target Company Name** (e.g. *Google*, *Microsoft*, *Amazon*, *Infosys*, *TCS*, *Cognizant*, *Accenture*, *Deloitte*, or *Startups*) and paste the **Job Description (JD)** from LinkedIn or company careers portals.
- The AI cross-references the candidate's resume, the JD requirements, and Glassdoor/industry interview patterns to formulate a targeted technical interview assessment.
- Topics mirror the role's production responsibilities, testing real-world architectural trade-offs, defensive coding, and performance optimization.

### 4. Personalized Technical Study Roadmap
- Performs automated **Gap Analysis** comparing what the JD requires versus what the candidate currently has on their resume.
- Generates a **multi-week curriculum** (2, 4, or 6 weeks) with:
  - Week-by-week learning themes and core objectives.
  - Must-study topics and hands-on practice projects.
  - Common interview questions and traps for that specific company.
  - Company-specific interview secrets and evaluation rubrics.

### 5. ATS Resume Optimizer & Auditor
- Comprehensive ATS Scoring (0 to 100) with sub-category scores:
  - Keyword Optimization
  - Experience Impact & Quantifiable Metrics
  - ATS Formatting & Layout Readability
  - Skills Relevance
- **Matched vs Missing Keywords**: Highlights high-frequency keywords found in the JD that are absent from the resume.
- **Before vs After Bullet Point Rewrites**: Uses the **Google X-Y-Z formula** (*"Accomplished [X] as measured by [Y], by doing [Z]"*) to transform passive bullets into high-impact accomplishments.

### 6. Interactive 30-MCQ Arena with Side Learning Hub
- Arranged topic-wise (e.g. .NET Core, Angular, SQL Server, System Design).
- Features code snippets with syntax highlighting, live timer, and a 1-to-30 question navigation palette.
- **Side Learning Hub**:
  - 💡 **Clue / Hint Tab**: Offers a conceptual clue without giving away the answer.
  - 📖 **Full Answer & Deep Dive Tab**: In-depth explanation of the underlying mechanics, common interview pitfalls, and pro-tips.

---

## How to Run

1. Open PowerShell or Command Prompt:
   ```powershell
   cd C:\Users\nivas\.gemini\antigravity\scratch\ai-interview-quiz
   ```
2. Start the application:
   ```powershell
   python app.py
   ```
   *(Or double-click `run.bat`)*
3. Open your browser at:
   ```
   http://127.0.0.1:5000
   ```

---

## Connecting an Online Database (Supabase / Neon)

1. Create a free project on [Supabase](https://supabase.com) or [Neon](https://neon.tech).
2. Copy your PostgreSQL connection URI.
3. Open the app, click **Database & AI** in the top bar, paste the URL into **Open-Source Online Database URL**, and save!
