# SkillSprint Studio — 100% Free Public Deployment Guide

SkillSprint Studio is fully equipped to deploy publicly at **zero cost** using open-source, free-tier cloud infrastructure. All candidate authentication data, quiz history, ATS reviews, and coding submissions sync live to your **Supabase PostgreSQL database** and send real OTPs via your **Gmail SMTP server**.

---

## ⚡ Option 1: Instant Public URL via Cloudflare Tunnel (Fastest — 2 Minutes)

Cloudflare Tunnel lets you share your running SkillSprint instance with friends worldwide using a free, secure HTTPS URL (**no port forwarding, no firewall changes, no domain purchase required**).

### Step 1: Download Cloudflare Tunnel (`cloudflared`)
Download the free Windows executable:
- **Download link**: [https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe)
- Rename it to `cloudflared.exe` and place it in your `ai-interview-quiz` folder (or anywhere in your PATH).

### Step 2: Start SkillSprint
Make sure SkillSprint is running locally:
```powershell
python app.py
```
*(Runs on `http://127.0.0.1:5000`)*

### Step 3: Run Cloudflare Quick Tunnel
Open a PowerShell terminal and execute:
```powershell
.\cloudflared.exe tunnel --url http://127.0.0.1:5000
```

### Step 4: Share the Public URL!
Cloudflare will output a public HTTPS address such as:
```
https://random-phrase-abc.trycloudflare.com
```
Anyone with that link (friends, colleagues, recruiters) can immediately:
1. Open the website on desktop or mobile.
2. Register their account and receive the 6-digit verification OTP on their email.
3. Practice MCQs with on-the-spot conceptual explanations.
4. Run & Submit coding challenges with public and hidden edge-case tests.
5. All assessment data and user accounts save directly into your Supabase database!

*(Note: If you own a free domain on Cloudflare, you can bind it permanently to `quiz.yourdomain.com` for a custom branded URL).*

---

## ☁️ Option 2: 24/7 Free Cloud Hosting on Render.com

If you want the website to stay online 24/7 without keeping your computer running, you can deploy it to **Render.com** (Free Web Service tier).

### Step 1: Push Code to GitHub
1. Create a repository on GitHub (e.g., `skillsprint-studio`).
2. In your local project directory, run:
```powershell
git init
git add .
git commit -m "feat: complete skillsprint studio with separate run/submit coding and strict admin isolation"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/skillsprint-studio.git
git push -u origin main
```

### Step 2: Create a Free Web Service on Render
1. Go to [https://render.com](https://render.com) and sign in with GitHub (Free).
2. Click **New +** -> **Web Service**.
3. Select your `skillsprint-studio` repository.
4. Configure the settings:
   - **Name**: `skillsprint-studio`
   - **Region**: Singapore or Frankfurt (close to your Tokyo Supabase DB)
   - **Language**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 2 --threads 4 --timeout 120`
   - **Instance Type**: `Free` (0.1 CPU, 512 MB RAM)

### Step 3: Configure Environment Variables
Under the **Environment Variables** section on Render, add:

| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql://postgres.gnjawtunpghmrsxkvcwx:Kiruthik%402002@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres` |
| `GMAIL_SENDER` | `kiruthiknivasnkl@gmail.com` |
| `GMAIL_APP_PASSWORD` | `duqgqwnwzcvptztg` |
| `GEMINI_API_KEY` | *(Your Gemini API key)* |
| `SECRET_KEY` | `skillsprint-studio-super-secret-key-2026` |
| `PYTHONUNBUFFERED` | `1` |

### Step 4: Deploy!
Click **Create Web Service**. Render will build and deploy your app. Within 2-3 minutes, your live URL will be ready:
```
https://skillsprint-studio.onrender.com
```

---

## 🔒 Security & Admin DB Isolation Verification
- **Admin Access**: Strictly restricted to `kiruthiknivasnkl@gmail.com`.
- **Public Users / Friends**: Regular users will **never** see the Admin DB tab or receive admin privileges. Any attempts to access `/api/admin/*` will be rejected with `403 Forbidden`.
- **Database Safety**: Connects over Supabase SSL pooler on port 6543.
- **Passwords**: Hashed with cryptographic SHA-256 salt.
