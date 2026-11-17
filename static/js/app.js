/**
 * SkillSprint Studio - Core Application Logic
 * Studio Obsidian Engine // Precision Interview & Career Suite
 */

const app = {
    activeTab: 'resume-learning',
    user: null,
    isAdmin: false,

    // Shared Resume State
    resume: {
        text: '',
        filename: '',
        wordCount: 0,
        skills: []
    },

    // Active Assessment Session
    session: {
        quizTitle: '',
        companyName: '',
        difficulty: 'Intermediate',
        questionCount: 10,
        includeCoding: true,
        includeBehavioral: true,
        questions: [],
        answers: {}, // for MCQs { [qid]: "A" }
        verifiedQuestions: {}, // { [qid]: { isVerified: bool, wasCorrect: bool, feedback: str } }
        codingSubmissions: {}, // { [qid]: "code..." }
        codingResults: {}, // { [qid]: { passed: bool, score: int, feedback: str, expected_vs_actual: obj } }
        behavioralAnswers: {}, // { [qid]: "answer..." }
        behavioralEvaluations: {}, // { [qid]: evalObj }
        currentIndex: 0,
        flaggedQuestions: new Set(),
        timerInterval: null,
        secondsElapsed: 0,
        evaluation: null
    },

    // Admin Cache
    adminData: null
};

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    checkCurrentUser();
    setupDropZones();
    setupKeyboardNav();
});

// Toast Notification Utility (Non-blocking modern UI)
function showToast(message, type = 'info') {
    const container = document.getElementById('studioToastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `studio-toast ${type === 'success' ? 'success' : (type === 'error' ? 'error' : '')}`;

    let icon = 'fa-solid fa-circle-info text-blue-400';
    if (type === 'success') icon = 'fa-solid fa-circle-check text-emerald-400';
    if (type === 'error') icon = 'fa-solid fa-triangle-exclamation text-rose-400';

    toast.innerHTML = `<i class="${icon}"></i><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 250);
    }, 4000);
}

// ==========================================
// AUTHENTICATION & HEADER PROFILE / LOGOUT
// ==========================================
async function checkCurrentUser() {
    try {
        const res = await fetch('/api/auth/me');
        const data = await res.json();
        const adminBtn = document.getElementById('admin-nav-btn');

        if (data.logged_in && data.user) {
            app.user = data.user;
            app.isAdmin = Boolean(data.is_admin);

            // Admin Button STRICT ISOLATION: Show ONLY if email is kiruthiknivasnkl@gmail.com
            if (adminBtn) {
                adminBtn.style.display = app.isAdmin ? 'inline-flex' : 'none';
            }

            renderAuthHeader();

            // Autofill user details in forms
            if (data.user.name) {
                const uName = document.getElementById('resumeUserName');
                if (uName && !uName.value) uName.value = data.user.name;
            }
            if (data.user.primary_skill) {
                const pSkill = document.getElementById('resumePrimarySkill');
                if (pSkill && !pSkill.value) pSkill.value = data.user.primary_skill;
            }
            if (data.user.secondary_skill) {
                const sSkill = document.getElementById('resumeSecondarySkill');
                if (sSkill && !sSkill.value) sSkill.value = data.user.secondary_skill;
            }
            if (data.user.resume_text && !app.resume.text) {
                setSharedResume(data.user.resume_text, 'Saved Account Resume', Math.round(data.user.resume_text.length / 5));
            }
        } else {
            app.user = null;
            app.isAdmin = false;
            if (adminBtn) adminBtn.style.display = 'none';
            renderAuthHeader();
        }
    } catch (e) {
        console.warn('Auth status check encountered network error:', e);
        renderAuthHeader();
    }
}

function renderAuthHeader() {
    const container = document.getElementById('authHeaderControl');
    if (!container) return;

    if (app.user) {
        const initial = (app.user.name || 'U').charAt(0).toUpperCase();
        const firstName = (app.user.name || 'User').split(' ')[0];

        container.innerHTML = `
            <div class="flex items-center gap-2">
                <!-- User Profile Pill -->
                <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs">
                    <div class="w-5 h-5 rounded-md bg-emerald-500/20 text-emerald-300 font-bold font-mono flex items-center justify-center text-[10px]">
                        ${initial}
                    </div>
                    <span class="text-white font-medium max-w-[100px] truncate">${escapeHtml(firstName)}</span>
                </div>

                <!-- Distinct Log Out Button -->
                <button type="button" onclick="handleLogout()" 
                    class="text-xs px-2.5 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/25 text-rose-300 font-medium transition flex items-center gap-1.5 shadow-sm" title="Log Out">
                    <i class="fa-solid fa-arrow-right-from-bracket text-[10px]"></i>
                    <span class="hidden sm:inline">Log Out</span>
                </button>
            </div>
        `;
    } else {
        container.innerHTML = `
            <button type="button" onclick="openAuthModal('login')" 
                class="text-xs px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition shadow-sm shadow-emerald-500/20 flex items-center gap-1.5">
                <i class="fa-solid fa-right-to-bracket text-[11px]"></i>
                <span>Sign In</span>
            </button>
        `;
    }
}

async function handleLogout() {
    try {
        const res = await fetch('/api/auth/logout', { method: 'POST' });
        const data = await res.json();
        
        app.user = null;
        app.isAdmin = false;

        // Hide admin button immediately
        const adminBtn = document.getElementById('admin-nav-btn');
        if (adminBtn) adminBtn.style.display = 'none';

        renderAuthHeader();
        showToast('You have been logged out successfully.', 'info');
    } catch (e) {
        console.error('Logout error:', e);
        showToast('Logout failed due to network error.', 'error');
    }
}

// ==========================================
// NAVIGATION CONTROLLER
// ==========================================
function switchMajorTab(tabId) {
    app.activeTab = tabId;

    ['resume', 'jd', 'ats'].forEach(t => {
        const dBtn = document.getElementById(`mainTabBtn-${t}`);
        const mBtn = document.getElementById(`mobTabBtn-${t}`);
        const view = document.getElementById(t === 'resume' ? 'tab-resume-learning' : (t === 'jd' ? 'tab-jd-learning' : 'tab-ats-score'));

        const isMatch = (t === 'resume' && tabId === 'resume-learning') ||
                        (t === 'jd' && tabId === 'jd-learning') ||
                        (t === 'ats' && tabId === 'ats-score');

        if (dBtn) {
            if (isMatch) dBtn.classList.add('active');
            else dBtn.classList.remove('active');
        }
        if (mBtn) {
            if (isMatch) {
                mBtn.className = 'flex-1 py-1.5 px-3 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-semibold text-center whitespace-nowrap';
            } else {
                mBtn.className = 'flex-1 py-1.5 px-3 rounded-lg text-slate-400 hover:text-white font-medium text-center whitespace-nowrap';
            }
        }
        if (view) {
            if (isMatch) view.classList.remove('hidden');
            else view.classList.add('hidden');
        }
    });

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// RESUME DROPZONE & UPLOAD HANDLER
// ==========================================
function setupDropZones() {
    ['tab1', 'tab3'].forEach(tid => {
        const drop = document.getElementById(`dropZone-${tid}`);
        if (!drop) return;

        ['dragenter', 'dragover'].forEach(eName => {
            drop.addEventListener(eName, e => {
                e.preventDefault();
                drop.classList.add('drag-active');
            });
        });

        ['dragleave', 'drop'].forEach(eName => {
            drop.addEventListener(eName, e => {
                e.preventDefault();
                drop.classList.remove('drag-active');
            });
        });

        drop.addEventListener('drop', e => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                uploadResumeFile(tid, files[0]);
            }
        });
    });
}

function handleFileSelect(tabId, event) {
    const file = event.target.files[0];
    if (file) {
        uploadResumeFile(tabId, file);
    }
}

async function uploadResumeFile(tabId, file) {
    const titleEl = document.getElementById(`fileTitle-${tabId}`);
    const badgeEl = document.getElementById(`fileBadge-${tabId}`);
    const nameEl = document.getElementById(`fileNameDisplay-${tabId}`);

    if (titleEl) titleEl.textContent = `Analyzing ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', document.getElementById('resumeUserName')?.value || '');
    formData.append('primary_skill', document.getElementById('resumePrimarySkill')?.value || '');
    formData.append('secondary_skill', document.getElementById('resumeSecondarySkill')?.value || '');

    try {
        const res = await fetch('/api/upload-resume', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (res.ok && data.success) {
            setSharedResume(data.resume_text, data.filename, data.analysis?.resume_word_count || 100);

            // Update UI
            if (titleEl) titleEl.textContent = 'Resume Loaded & Analyzed';
            if (badgeEl) badgeEl.classList.remove('hidden');
            if (nameEl) nameEl.textContent = `${data.filename} (${data.analysis?.resume_word_count || 0} words)`;

            // Auto-populate skills if detected
            if (data.analysis) {
                const a = data.analysis;
                if (a.candidate_name && a.candidate_name !== 'Candidate') {
                    const uName = document.getElementById('resumeUserName');
                    if (uName && !uName.value) uName.value = a.candidate_name;
                }
                if (a.extracted_skills && a.extracted_skills.length > 0) {
                    renderExtractedSkills(tabId, a.extracted_skills);
                }
                if (a.recommended_difficulty) {
                    setResumeDiff(a.recommended_difficulty);
                }
            }
            showToast('Resume uploaded & analyzed successfully!', 'success');
        } else {
            showToast(data.error || 'Failed to parse resume.', 'error');
            if (titleEl) titleEl.textContent = 'Upload failed. Click to try again.';
        }
    } catch (e) {
        console.error('Upload error:', e);
        showToast('Network error while uploading resume.', 'error');
        if (titleEl) titleEl.textContent = 'Upload error. Click to try again.';
    }
}

function renderExtractedSkills(tabId, skills) {
    const container = document.getElementById(`extractedSkillsContainer-${tabId}`);
    const badges = document.getElementById(`extractedSkillsBadges-${tabId}`);
    if (!container || !badges) return;

    badges.innerHTML = '';
    skills.forEach(s => {
        const span = document.createElement('span');
        span.className = 'px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono text-[11px]';
        span.textContent = s;
        badges.appendChild(span);
    });
    container.classList.remove('hidden');
}

function setSharedResume(text, filename, wordCount) {
    app.resume.text = text;
    app.resume.filename = filename;
    app.resume.wordCount = wordCount;

    // Update Banner in Tab 2
    const jdText = document.getElementById('jdResumeStatusText');
    if (jdText) {
        jdText.textContent = `Linked Resume: ${filename} (${wordCount} words)`;
    }
}

function loadSampleResume(tabId) {
    fetch('/api/sample-resume')
        .then(r => r.json())
        .then(data => {
            setSharedResume(data.text, data.filename, data.word_count);

            const titleEl = document.getElementById(`fileTitle-${tabId}`);
            const badgeEl = document.getElementById(`fileBadge-${tabId}`);
            const nameEl = document.getElementById(`fileNameDisplay-${tabId}`);

            if (titleEl) titleEl.textContent = 'Sample 2-Yr .NET + Angular Resume Loaded';
            if (badgeEl) badgeEl.classList.remove('hidden');
            if (nameEl) nameEl.textContent = data.filename;

            document.getElementById('resumeUserName').value = data.candidate_name;
            document.getElementById('resumePrimarySkill').value = data.primary_skill;
            document.getElementById('resumeSecondarySkill').value = data.secondary_skill;
            setResumeDiff('Intermediate');

            renderExtractedSkills(tabId, ['.NET 8', 'ASP.NET Core', 'C#', 'Angular 17', 'SQL Server', 'EF Core', 'REST APIs']);
            showToast('Loaded 2-Year Full Stack sample resume.', 'success');
        })
        .catch(e => {
            showToast('Failed to load sample resume.', 'error');
        });
}

function loadSampleJD() {
    const sample = `Job Title: Senior Full Stack Software Engineer (.NET & Angular)
Company: Enterprise FinTech Cloud Systems
Location: Remote / Hybrid

About The Role:
We are looking for a Senior Full Stack Engineer with strong mastery of ASP.NET Core, C#, Entity Framework Core, Microsoft SQL Server, and Angular (v16+). You will build distributed, high-throughput financial transaction processing microservices and dynamic client dashboards.

Key Responsibilities:
- Design and implement scalable RESTful Web APIs using ASP.NET Core and Clean Architecture.
- Engineer stateful single-page applications in Angular using RxJS observables, reactive forms, and signals.
- Optimize database performance in SQL Server: writing stored procedures, covering indexes, and analyzing execution plans.
- Diagnose concurrency bottlenecks, distributed caching with Redis, and enforce security best practices (JWT / OAuth2).

Qualifications:
- 3+ years experience with C# / .NET Core and relational SQL databases.
- Hands-on proficiency in Angular & TypeScript.
- Strong problem-solving mindset, algorithmic thinking, and clear cross-functional communication.`;

    document.getElementById('targetCompanyName').value = 'Enterprise FinTech Cloud';
    document.getElementById('targetJobTitle').value = 'Senior Full Stack .NET & Angular Engineer';
    document.getElementById('targetJobDescription').value = sample;
    showToast('Loaded sample job description.', 'info');
}

function setCompanyQuick(comp) {
    document.getElementById('targetCompanyName').value = comp;
}

// ==========================================
// SESSION CONFIGURATION CONTROLS
// ==========================================
function setQuestionCount(count) {
    app.session.questionCount = count;
    document.querySelectorAll('[data-qcount]').forEach(btn => {
        if (parseInt(btn.getAttribute('data-qcount')) === count) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

function setResumeDiff(diff) {
    app.session.difficulty = diff;
    document.querySelectorAll('[data-diff]').forEach(btn => {
        if (btn.getAttribute('data-diff') === diff) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// ==========================================
// TAB 1: RESUME ASSESSMENT LAUNCHER
// ==========================================
async function handleResumeQuizStart(event) {
    if (event) event.preventDefault();

    const name = document.getElementById('resumeUserName').value.trim() || 'Candidate';
    const primarySkill = document.getElementById('resumePrimarySkill').value.trim() || '.NET Core / C#';
    const secondarySkill = document.getElementById('resumeSecondarySkill').value.trim() || 'Angular';
    const difficulty = app.session.difficulty || 'Intermediate';
    const count = app.session.questionCount || 10;
    const includeCoding = document.getElementById('modToggleCoding').checked;
    const includeBehavioral = document.getElementById('modToggleBehavioral').checked;

    const btn = document.getElementById('startResumeQuizBtn');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i><span>Generating Dynamic Set...</span>`;

    try {
        const res = await fetch('/api/generate-quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                primary_skill: primarySkill,
                secondary_skill: secondarySkill,
                resume_text: app.resume.text || '',
                difficulty: difficulty,
                question_count: count,
                include_coding: includeCoding,
                include_behavioral: includeBehavioral
            })
        });

        const data = await res.json();
        if (res.ok && data.success && data.quiz && data.quiz.questions) {
            initAssessmentSession(data.quiz);
        } else {
            showToast(data.error || 'Failed to generate assessment.', 'error');
        }
    } catch (e) {
        console.error('Generation failure:', e);
        showToast('Server connection error. Please try again.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Launch Interview Session</span><i class="fa-solid fa-arrow-right text-xs"></i>`;
    }
}

// ==========================================
// TAB 2: COMPANY-TARGETED QUIZ LAUNCHER
// ==========================================
async function handleCompanyQuizStart() {
    const comp = document.getElementById('targetCompanyName').value.trim() || 'Target Enterprise';
    const jd = document.getElementById('targetJobDescription').value.trim();

    if (!jd) {
        showToast('Please paste or load a Job Description first.', 'error');
        return;
    }

    const btn = document.getElementById('companyQuizStartBtn');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i><span>Simulating ${comp} Interview...</span>`;

    try {
        const res = await fetch('/api/company-quiz/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: document.getElementById('resumeUserName')?.value || 'Candidate',
                company_name: comp,
                job_description: jd,
                resume_text: app.resume.text || '',
                difficulty: app.session.difficulty || 'Intermediate',
                question_count: app.session.questionCount || 10,
                include_coding: true,
                include_behavioral: true
            })
        });

        const data = await res.json();
        if (res.ok && data.success && data.quiz && data.quiz.questions) {
            initAssessmentSession(data.quiz);
            switchMajorTab('resume-learning');
        } else {
            showToast(data.error || 'Failed to simulate company interview.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Connection error while generating company interview.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-play text-[11px]"></i><span>Simulate Company Interview</span>`;
    }
}

// ==========================================
// MULTI-MODAL ASSESSMENT ARENA ENGINE
// ==========================================
function initAssessmentSession(quizData) {
    app.session.quizTitle = quizData.quiz_title || 'Technical Assessment';
    app.session.companyName = quizData.company_name || '';
    app.session.difficulty = quizData.difficulty || 'Intermediate';
    app.session.questions = quizData.questions;
    app.session.answers = {};
    app.session.verifiedQuestions = {};
    app.session.codingSubmissions = {};
    app.session.codingResults = {};
    app.session.codingRunResults = {};
    app.session.customTestCases = {};
    app.session.activeCodingTab = {};
    app.session.behavioralAnswers = {};
    app.session.behavioralEvaluations = {};
    app.session.currentIndex = 0;
    app.session.flaggedQuestions = new Set();
    app.session.secondsElapsed = 0;

    // Hide Setup Card, Show Arena
    document.getElementById('resumeQuizSetupCard').classList.add('hidden');
    document.getElementById('quizResultsContainer').classList.add('hidden');

    const arena = document.getElementById('quizArenaContainer');
    arena.classList.remove('hidden');

    // Start Timer
    if (app.session.timerInterval) clearInterval(app.session.timerInterval);
    app.session.timerInterval = setInterval(() => {
        app.session.secondsElapsed++;
        updateArenaTimer();
    }, 1000);

    renderCurrentArenaQuestion();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateArenaTimer() {
    const el = document.getElementById('arenaTimerDisplay');
    if (!el) return;
    const m = Math.floor(app.session.secondsElapsed / 60);
    const s = app.session.secondsElapsed % 60;
    el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function renderCurrentArenaQuestion() {
    const arena = document.getElementById('quizArenaContainer');
    if (!arena || !app.session.questions.length) return;

    const q = app.session.questions[app.session.currentIndex];
    const total = app.session.questions.length;
    const qid = String(q.id);
    const qtype = q.type || 'mcq';

    // Verification state for this question
    const vState = app.session.verifiedQuestions[qid] || { isVerified: false };

    // Type Badge & Colors
    let typeBadgeHtml = '';
    if (qtype === 'coding') {
        typeBadgeHtml = `<span class="px-2.5 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/25 text-cyan-400 font-mono text-[11px] font-bold"><i class="fa-solid fa-code mr-1"></i> PRACTICAL CODING CHALLENGE</span>`;
    } else if (qtype === 'behavioral') {
        typeBadgeHtml = `<span class="px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/25 text-amber-400 font-mono text-[11px] font-bold"><i class="fa-solid fa-user-tie mr-1"></i> HIRING & BEHAVIORAL FIT</span>`;
    } else {
        typeBadgeHtml = `<span class="px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 font-mono text-[11px] font-bold"><i class="fa-solid fa-circle-check mr-1"></i> TECHNICAL MCQ // ${escapeHtml(q.topic)}</span>`;
    }

    // Build Question Stepper Pills with Immediate Verification Icons (✓ or ✗)
    let stepperHtml = '';
    app.session.questions.forEach((item, idx) => {
        const itemQid = String(item.id);
        const isActive = idx === app.session.currentIndex;
        const itemV = app.session.verifiedQuestions[itemQid];
        const isFlagged = app.session.flaggedQuestions.has(itemQid);

        let pillClass = '';
        let pillText = String(idx + 1);

        if (itemV && itemV.isVerified) {
            if (itemV.wasCorrect) {
                pillClass = 'is-correct';
                pillText = `<i class="fa-solid fa-check text-[10px]"></i>`;
            } else {
                pillClass = 'is-wrong';
                pillText = `<i class="fa-solid fa-xmark text-[10px]"></i>`;
            }
        } else if (isActive) {
            pillClass = 'active';
        }

        stepperHtml += `
            <button type="button" onclick="jumpToArenaQuestion(${idx})" 
                class="question-nav-pill ${isActive ? 'active' : ''} ${pillClass} ${isFlagged ? 'flagged' : ''}">
                ${pillText}
            </button>
        `;
    });

    // Build Question Body based on type
    let questionBodyHtml = '';
    if (qtype === 'mcq') {
        const selectedOpt = app.session.answers[qid] || '';
        const correctOpt = strUpper(q.correct_answer || 'A');

        let optionsHtml = '';
        (q.options || []).forEach(opt => {
            const letter = opt.substring(0, 1).toUpperCase();
            const isSelected = selectedOpt === letter;

            let optClass = '';
            let optStatusBadge = '';

            if (vState.isVerified) {
                if (letter === correctOpt) {
                    optClass = 'mcq-correct';
                    optStatusBadge = `<span class="text-[11px] font-mono text-emerald-300 font-bold ml-auto"><i class="fa-solid fa-check mr-1"></i> Correct Answer</span>`;
                } else if (isSelected && letter !== correctOpt) {
                    optClass = 'mcq-wrong';
                    optStatusBadge = `<span class="text-[11px] font-mono text-rose-300 font-bold ml-auto"><i class="fa-solid fa-xmark mr-1"></i> Your Choice (Incorrect)</span>`;
                }
            } else if (isSelected) {
                optClass = 'selected';
            }

            optionsHtml += `
                <div onclick="selectArenaMcqOption('${qid}', '${letter}')" class="mcq-option-card ${optClass}">
                    <div class="option-letter-badge">${letter}</div>
                    <div class="text-xs text-slate-200 leading-relaxed font-sans pt-0.5">${opt.replace(/^[A-D]\)\s*/, '')}</div>
                    ${optStatusBadge}
                </div>
            `;
        });

        let codeSnippetHtml = '';
        if (q.code_snippet && q.code_snippet.trim()) {
            codeSnippetHtml = `
                <div class="code-editor-wrapper my-3.5">
                    <div class="code-editor-header text-[11px] font-mono text-slate-400">
                        <span><i class="fa-solid fa-file-code mr-1"></i> Code Context</span>
                    </div>
                    <pre class="p-4 text-xs font-mono text-slate-200 overflow-x-auto"><code>${escapeHtml(q.code_snippet)}</code></pre>
                </div>
            `;
        }

        // Immediate Learning Card (Rendered if user verified the question)
        let immediateLearningHtml = '';
        if (vState.isVerified) {
            if (vState.wasCorrect) {
                immediateLearningHtml = `
                    <div class="immediate-feedback-card p-4 rounded-xl bg-emerald-500/[0.05] border border-emerald-500/30 space-y-2 text-xs">
                        <div class="flex items-center gap-2 text-emerald-400 font-bold font-mono">
                            <i class="fa-solid fa-circle-check"></i>
                            <span>Correct! (+1 Mark Awarded)</span>
                        </div>
                        <div class="text-slate-300 leading-relaxed">${escapeHtml(q.explanation || '')}</div>
                    </div>
                `;
            } else {
                immediateLearningHtml = `
                    <div class="immediate-feedback-card p-4 rounded-xl bg-rose-500/[0.05] border border-rose-500/30 space-y-2 text-xs">
                        <div class="flex items-center gap-2 text-rose-400 font-bold font-mono">
                            <i class="fa-solid fa-circle-xmark"></i>
                            <span>Incorrect Answer (0 Marks Awarded). Learn the concept below before continuing:</span>
                        </div>
                        <div class="p-3 rounded-lg bg-black/40 border border-white/[0.06] text-slate-200 space-y-1.5 leading-relaxed">
                            <div class="text-[11px] font-mono text-emerald-400 font-semibold uppercase">Correct Answer: Option ${correctOpt}</div>
                            <p>${escapeHtml(q.explanation || '')}</p>
                        </div>
                        <div class="text-[11px] font-mono text-amber-300 pt-1">
                            <i class="fa-solid fa-lightbulb text-amber-400 mr-1"></i> Interview Pro-Tip: Explain runtime behavior and memory implications rather than just quoting textbook definitions.
                        </div>
                    </div>
                `;
            }
        }

        questionBodyHtml = `
            <div class="space-y-4">
                <h2 class="text-sm sm:text-base font-semibold text-white leading-snug">${escapeHtml(q.question)}</h2>
                ${codeSnippetHtml}
                <div class="space-y-2.5 pt-1">${optionsHtml}</div>
                ${immediateLearningHtml}
                ${!vState.isVerified ? renderHintAccordion(q.hint) : ''}
            </div>
        `;
    } else if (qtype === 'coding') {
        const savedCode = app.session.codingSubmissions[qid] || q.starter_code || '// Write your solution here\n';
        const runRes = app.session.codingRunResults ? app.session.codingRunResults[qid] : null;
        const cResult = app.session.codingResults ? app.session.codingResults[qid] : null;

        // 1. Run Output Console (Sandbox Test Execution - Not Graded)
        let runConsoleHtml = '';
        if (runRes) {
            let runRows = '';
            (runRes.test_results || []).forEach((tr, i) => {
                const isPass = tr.status === 'PASSED';
                runRows += `
                    <div class="p-2.5 rounded-lg ${isPass ? 'bg-emerald-500/[0.06] border border-emerald-500/20' : 'bg-rose-500/[0.06] border border-rose-500/20'} space-y-1">
                        <div class="flex items-center justify-between">
                            <span class="font-mono font-bold text-[11px] ${isPass ? 'text-emerald-300' : 'text-rose-300'}">
                                <i class="fa-solid ${isPass ? 'fa-circle-check' : 'fa-circle-xmark'} mr-1"></i>
                                ${escapeHtml(tr.name || `Test Case ${i+1}`)}
                            </span>
                            <span class="text-[10px] font-mono px-2 py-0.5 rounded ${isPass ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'} uppercase font-bold">${escapeHtml(tr.status || 'FAILED')}</span>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[10px] font-mono pt-0.5">
                            <div class="text-slate-400"><strong>Input:</strong> <span class="text-slate-200">${escapeHtml(tr.input || '')}</span></div>
                            <div class="text-slate-400"><strong>Output:</strong> <span class="${isPass ? 'text-emerald-300' : 'text-rose-300'}">${escapeHtml(tr.actual || '')}</span></div>
                        </div>
                        ${tr.details ? `<div class="text-[10px] text-slate-400 pt-0.5"><i class="fa-solid fa-circle-info mr-1 text-slate-500"></i>${escapeHtml(tr.details)}</div>` : ''}
                    </div>
                `;
            });

            runConsoleHtml = `
                <div class="p-3.5 rounded-xl bg-black/60 border border-cyan-500/30 space-y-2.5 text-xs">
                    <div class="flex items-center justify-between border-b border-white/[0.06] pb-2">
                        <div class="flex items-center gap-2 font-mono text-xs text-cyan-300 font-bold">
                            <i class="fa-solid fa-terminal text-cyan-400"></i>
                            <span>Run Console Output (Validation Sandbox - Not Graded)</span>
                        </div>
                        <span class="text-[10px] font-mono ${runRes.all_passed ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}">
                            ${runRes.all_passed ? '✓ All Tests Passed' : '⚠ Validation Gaps Detected'}
                        </span>
                    </div>
                    <div class="space-y-1.5">${runRows}</div>
                    ${runRes.console_output ? `
                        <div class="pt-1">
                            <div class="text-[10px] font-mono text-slate-400 uppercase mb-1">Compiler / Sandbox Log:</div>
                            <pre class="p-2.5 rounded bg-black/80 font-mono text-[10px] text-slate-300 border border-white/[0.04] overflow-x-auto whitespace-pre-wrap">${escapeHtml(runRes.console_output)}</pre>
                        </div>
                    ` : ''}
                    <div class="pt-1 text-[11px] font-mono text-slate-400 flex items-center justify-between">
                        <span><i class="fa-solid fa-arrow-right mr-1 text-cyan-400"></i> Ready to submit? Click <strong>'Submit Solution'</strong> to test all hidden edge cases and finalize your grade.</span>
                    </div>
                </div>
            `;
        }

        // 2. Graded Final Submission Result (Evaluated against Hidden + Public Test Cases)
        let codingFeedbackHtml = '';
        if (cResult) {
            let testsBreakdownHtml = '';
            if (cResult.test_results && cResult.test_results.length) {
                testsBreakdownHtml = `
                    <div class="space-y-1.5 pt-1">
                        <div class="text-[10px] font-mono uppercase text-slate-400 font-bold">Test Suite & Hidden Boundary Audit:</div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                            ${cResult.test_results.map(t => {
                                const pass = t.status === 'PASSED';
                                return `
                                    <div class="p-2 rounded bg-black/40 border ${pass ? 'border-emerald-500/25' : 'border-rose-500/25'} flex items-center justify-between text-[11px] font-mono">
                                        <div class="truncate mr-2">
                                            <span class="${t.is_hidden ? 'text-amber-300' : 'text-cyan-300'} font-semibold mr-1">${t.is_hidden ? '[Hidden]' : '[Public]'}</span>
                                            <span class="text-slate-300">${escapeHtml(t.name || 'Test Case')}</span>
                                        </div>
                                        <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${pass ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}">${t.status}</span>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `;
            }

            if (cResult.passed) {
                codingFeedbackHtml = `
                    <div class="immediate-feedback-card p-4 rounded-xl bg-emerald-500/[0.05] border border-emerald-500/30 space-y-3 text-xs">
                        <div class="flex items-center justify-between border-b border-emerald-500/20 pb-2">
                            <div class="flex items-center gap-2 text-emerald-400 font-bold font-mono">
                                <i class="fa-solid fa-circle-check text-sm"></i>
                                <span>All Public & Hidden Edge Cases Passed (+1 Mark Awarded)</span>
                            </div>
                            <span class="text-[10px] font-mono text-emerald-300 bg-emerald-500/20 px-2 py-0.5 rounded font-bold">100% Score</span>
                        </div>
                        <p class="text-slate-300 leading-relaxed">${escapeHtml(cResult.feedback || 'Code successfully handled all boundary conditions and concurrency requirements.')}</p>
                        ${testsBreakdownHtml}
                        <div class="text-[11px] font-mono text-cyan-400 pt-1">
                            ${escapeHtml(cResult.complexity_analysis || 'Complexity: O(1) Time, O(N) Space.')}
                        </div>
                    </div>
                `;
            } else {
                codingFeedbackHtml = `
                    <div class="immediate-feedback-card p-4 rounded-xl bg-rose-500/[0.05] border border-rose-500/30 space-y-3 text-xs">
                        <div class="flex items-center justify-between border-b border-rose-500/20 pb-2">
                            <div class="flex items-center gap-2 text-rose-400 font-bold font-mono">
                                <i class="fa-solid fa-circle-xmark text-sm"></i>
                                <span>Failed Hidden Edge Cases (0 Marks Awarded)</span>
                            </div>
                            <span class="text-[10px] font-mono text-rose-300 bg-rose-500/20 px-2 py-0.5 rounded font-bold">0 Marks</span>
                        </div>
                        
                        <p class="text-slate-300 leading-relaxed">${escapeHtml(cResult.feedback || 'The submission failed on one or more hidden boundary conditions. Review the breakdown and optimal solution below:')}</p>
                        ${testsBreakdownHtml}

                        <!-- Expected vs Actual Breakdown -->
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] pt-1">
                            <div class="p-2.5 rounded bg-black/40 border border-white/[0.06]">
                                <strong class="text-emerald-400 font-mono block mb-1">Expected Outcome:</strong>
                                <span class="text-slate-300">${escapeHtml(cResult.expected_vs_actual?.expected || 'Valid thread-safe implementation with boundary edge case compliance.')}</span>
                            </div>
                            <div class="p-2.5 rounded bg-black/40 border border-rose-500/25">
                                <strong class="text-rose-400 font-mono block mb-1">Actual Code Result:</strong>
                                <span class="text-slate-300">${escapeHtml(cResult.expected_vs_actual?.actual || cResult.feedback || 'Failed boundary cases or unhandled edge parameters.')}</span>
                            </div>
                        </div>

                        <!-- Optimal Solution Walkthrough -->
                        <div class="p-3.5 rounded-lg bg-black/50 border border-emerald-500/25 space-y-2">
                            <div class="flex items-center justify-between">
                                <div class="text-[11px] font-mono text-emerald-400 font-bold uppercase">Optimal Production Reference Solution:</div>
                                <span class="text-[10px] font-mono text-slate-400">Learn Immediately</span>
                            </div>
                            <pre class="p-3 rounded bg-black/60 text-[11px] font-mono text-slate-200 overflow-x-auto border border-white/[0.06]"><code>${escapeHtml(q.solution_code || cResult.solution_code || '')}</code></pre>
                            <p class="text-slate-300 text-[11px] leading-relaxed pt-1">${escapeHtml(q.explanation || cResult.explanation || '')}</p>
                        </div>
                    </div>
                `;
            }
        }

        questionBodyHtml = `
            <div class="space-y-4">
                <div>
                    <h2 class="text-sm sm:text-base font-semibold text-white">${escapeHtml(q.title || 'Practical Coding Challenge')}</h2>
                    <p class="text-xs text-slate-300 mt-1.5 leading-relaxed">${escapeHtml(q.question)}</p>
                </div>

                <!-- Test Cases Panel (Public & Custom Tabs) -->
                ${renderCodingTestPanel(q, qid)}

                <!-- Code Workspace -->
                <div class="code-editor-wrapper">
                    <div class="code-editor-header flex items-center justify-between px-3 py-2 bg-[#0c101c] border-b border-white/[0.06]">
                        <span class="text-xs font-mono text-emerald-400 flex items-center gap-1.5">
                            <i class="fa-solid fa-code"></i> Solution Editor
                        </span>
                        <div class="flex items-center gap-2">
                            <button type="button" onclick="runCodingTests('${qid}')" id="runCodeBtn-${qid}" 
                                class="text-xs font-mono px-3 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/35 text-cyan-300 transition flex items-center gap-1.5">
                                <i class="fa-solid fa-play text-[10px]"></i> Run Code
                            </button>
                            <button type="button" onclick="submitFinalCoding('${qid}')" id="submitCodeBtn-${qid}" 
                                class="text-xs font-mono px-3.5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition flex items-center gap-1.5 shadow-md shadow-emerald-500/20">
                                <i class="fa-solid fa-check-double text-[10px]"></i> Submit Solution
                            </button>
                        </div>
                    </div>
                    <textarea id="codingTextarea-${qid}" class="code-editor-textarea font-mono text-xs" oninput="saveCodingInput('${qid}', this.value)">${escapeHtml(savedCode)}</textarea>
                </div>

                <!-- Run Console Output -->
                ${runConsoleHtml}

                <!-- Graded Submission Output -->
                ${codingFeedbackHtml}
            </div>
        `;
    } else if (qtype === 'behavioral') {
        const savedAnswer = app.session.behavioralAnswers[qid] || '';
        const bEval = app.session.behavioralEvaluations[qid];

        let behavioralFeedbackHtml = '';
        if (bEval) {
            behavioralFeedbackHtml = `
                <div class="immediate-feedback-card p-4 rounded-xl bg-white/[0.02] border border-amber-500/30 space-y-3 text-xs">
                    <div class="flex items-center justify-between border-b border-white/[0.06] pb-2">
                        <div class="font-bold text-white flex items-center gap-2">
                            <span class="text-emerald-400 font-mono text-sm">${bEval.score}/100</span>
                            <span>${escapeHtml(bEval.verdict)}</span>
                        </div>
                        <span class="text-[10px] font-mono text-slate-400 uppercase">STAR Metric Audit</span>
                    </div>
                    <p class="text-slate-300">${escapeHtml(bEval.feedback)}</p>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] pt-1">
                        <div class="p-2 rounded bg-black/30 border border-white/[0.04]">
                            <strong class="text-emerald-400">Strengths:</strong>
                            <ul class="list-disc list-inside mt-0.5 text-slate-300">
                                ${(bEval.key_strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                            </ul>
                        </div>
                        <div class="p-2 rounded bg-black/30 border border-white/[0.04]">
                            <strong class="text-amber-400">Areas to Improve:</strong>
                            <ul class="list-disc list-inside mt-0.5 text-slate-300">
                                ${(bEval.areas_to_improve || []).map(a => `<li>${escapeHtml(a)}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                    <div class="pt-2 border-t border-white/[0.04]">
                        <div class="text-[11px] font-mono text-emerald-400 font-semibold mb-1">Recommended Executive Rephrasing:</div>
                        <div class="p-3 rounded-lg bg-black/50 text-[11px] text-slate-200 leading-relaxed font-sans italic border border-emerald-500/20">
                            "${escapeHtml(bEval.improved_answer || '')}"
                        </div>
                    </div>
                </div>
            `;
        }

        questionBodyHtml = `
            <div class="behavioral-card space-y-4">
                <div>
                    <div class="flex items-center gap-2 mb-2">
                        <span class="star-helper-badge"><i class="fa-solid fa-star"></i> STAR FRAMEWORK APPLIED</span>
                    </div>
                    <h2 class="text-base font-bold text-white leading-snug">${escapeHtml(q.question)}</h2>
                    <p class="text-xs text-amber-200/80 mt-1 font-mono">${escapeHtml(q.star_framework_prompt || 'Structure your response with: Situation, Task, Action, and Quantifiable Result.')}</p>
                </div>

                <div>
                    <label class="block text-xs font-medium text-slate-300 mb-1.5">Your Response (Type your structured answer below):</label>
                    <textarea id="behavioralTextarea-${qid}" rows="5" placeholder="Draft your situation, exact actions, and measurable business result here..."
                        class="w-full p-4 rounded-xl bg-[#090c15] border border-white/[0.08] text-xs text-white placeholder-slate-600 focus:outline-none focus:border-amber-500 font-sans transition resize-y"
                        oninput="saveBehavioralInput('${qid}', this.value)">${escapeHtml(savedAnswer)}</textarea>
                </div>

                <div class="flex items-center justify-between pt-1">
                    <button type="button" onclick="evaluateBehavioralRealtime('${qid}')" id="evalBehavioralBtn-${qid}" 
                        class="text-xs px-3.5 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 font-semibold transition flex items-center gap-1.5 shadow-sm">
                        <i class="fa-solid fa-wand-magic-sparkles text-[11px]"></i>
                        <span>${bEval ? 'Re-evaluate Answer' : 'Submit & Evaluate with AI'}</span>
                    </button>
                    <button type="button" onclick="toggleStrongAnswer('${qid}')" class="text-xs font-mono text-slate-400 hover:text-white underline">
                        View Exemplar Answer
                    </button>
                </div>

                ${behavioralFeedbackHtml}

                <!-- Sample Strong Answer Box -->
                <div id="sampleStrongBox-${qid}" class="hidden p-4 rounded-xl bg-[#090c15] border border-white/[0.08] text-xs space-y-2">
                    <div class="text-[11px] font-mono text-emerald-400 font-bold uppercase">Executive Exemplar Response:</div>
                    <p class="text-slate-300 leading-relaxed">${escapeHtml(q.sample_strong_answer || 'Strong sample response.')}</p>
                </div>
            </div>
        `;
    }

    const isFirst = app.session.currentIndex === 0;
    const isLast = app.session.currentIndex === total - 1;
    const isFlagged = app.session.flaggedQuestions.has(qid);

    // Primary Next Button Label Logic:
    let nextBtnLabel = 'Next Question';
    let nextBtnAction = `handleNextOrVerify('${qid}')`;

    if (qtype === 'mcq') {
        if (!vState.isVerified) {
            nextBtnLabel = 'Check Answer & Learn';
        } else if (isLast) {
            nextBtnLabel = 'Finish Assessment';
            nextBtnAction = 'submitAssessmentSession()';
        } else {
            nextBtnLabel = 'Proceed to Next Question';
        }
    } else if (qtype === 'coding') {
        if (!app.session.codingResults[qid]) {
            nextBtnLabel = 'Verify & Proceed';
        } else if (isLast) {
            nextBtnLabel = 'Finish Assessment';
            nextBtnAction = 'submitAssessmentSession()';
        }
    } else if (qtype === 'behavioral') {
        if (isLast) {
            nextBtnLabel = 'Finish Assessment';
            nextBtnAction = 'submitAssessmentSession()';
        }
    }

    arena.innerHTML = `
        <div class="studio-card p-6 sm:p-8 space-y-6">
            <!-- Arena Top Header Bar -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
                <div class="flex items-center gap-2.5">
                    <button type="button" onclick="confirmExitArena()" class="text-xs font-mono text-slate-400 hover:text-white flex items-center gap-1">
                        <i class="fa-solid fa-chevron-left text-[10px]"></i> Exit
                    </button>
                    <span class="text-slate-600">|</span>
                    ${typeBadgeHtml}
                </div>
                <div class="flex items-center gap-4 text-xs font-mono">
                    <div class="flex items-center gap-1.5 text-slate-300">
                        <i class="fa-regular fa-clock text-emerald-400"></i>
                        <span id="arenaTimerDisplay">00:00</span>
                    </div>
                    <span class="text-slate-600">|</span>
                    <span class="text-slate-400">Question <strong class="text-white">${app.session.currentIndex + 1}</strong> of ${total}</span>
                </div>
            </div>

            <!-- Question Stepper Bar with Status Indicators -->
            <div class="flex items-center gap-1.5 overflow-x-auto py-1">
                ${stepperHtml}
            </div>

            <!-- Active Question Body -->
            <div class="py-2">
                ${questionBodyHtml}
            </div>

            <!-- Arena Bottom Navigation Footer -->
            <div class="flex items-center justify-between border-t border-white/[0.06] pt-4">
                <button type="button" onclick="navigateArenaQuestion(-1)" ${isFirst ? 'disabled class="studio-pill opacity-40 cursor-not-allowed text-xs"' : 'class="studio-pill text-xs"'}>
                    <i class="fa-solid fa-arrow-left text-[10px] mr-1"></i> Previous
                </button>

                <div class="flex items-center gap-2">
                    <button type="button" onclick="toggleFlagQuestion('${qid}')" class="studio-pill text-xs flex items-center gap-1.5 ${isFlagged ? 'active' : ''}">
                        <i class="fa-solid fa-flag text-[11px] ${isFlagged ? 'text-amber-400' : 'text-slate-400'}"></i>
                        <span>${isFlagged ? 'Flagged' : 'Flag'}</span>
                    </button>

                    <button type="button" onclick="${nextBtnAction}" class="btn-primary-action text-xs py-2 px-5">
                        <span>${nextBtnLabel}</span>
                        <i class="fa-solid fa-arrow-right text-[10px] ml-1"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

    updateArenaTimer();
}

function handleNextOrVerify(qid) {
    const q = app.session.questions[app.session.currentIndex];
    const qtype = q.type || 'mcq';
    const vState = app.session.verifiedQuestions[qid];

    if (qtype === 'mcq') {
        // If not verified yet, verify the answer inline and explain!
        if (!vState || !vState.isVerified) {
            const userChoice = app.session.answers[qid];
            if (!userChoice) {
                showToast('Please select an option before checking answer.', 'error');
                return;
            }
            const correctChoice = strUpper(q.correct_answer || 'A');
            const wasCorrect = (userChoice === correctChoice);

            app.session.verifiedQuestions[qid] = {
                isVerified: true,
                wasCorrect: wasCorrect,
                userChoice: userChoice,
                correctChoice: correctChoice
            };

            renderCurrentArenaQuestion();
            return;
        }
    }

    if (qtype === 'coding') {
        if (!app.session.codingResults[qid]) {
            submitFinalCoding(qid);
            return;
        }
    }

    // If already verified or other type, proceed to next
    if (app.session.currentIndex < app.session.questions.length - 1) {
        navigateArenaQuestion(1);
    } else {
        submitAssessmentSession();
    }
}

function selectArenaMcqOption(qid, letter) {
    const vState = app.session.verifiedQuestions[qid];
    // Once verified, avoid changing to preserve test integrity
    if (vState && vState.isVerified) {
        return;
    }
    app.session.answers[qid] = letter;
    renderCurrentArenaQuestion();
}

function switchCodingTestTab(qid, tab) {
    if (!app.session.activeCodingTab) app.session.activeCodingTab = {};
    app.session.activeCodingTab[qid] = tab;
    renderCurrentArenaQuestion();
}

function saveCustomTestCase(qid, val) {
    if (!app.session.customTestCases) app.session.customTestCases = {};
    app.session.customTestCases[qid] = val;
}

async function runCodingTests(qid) {
    const q = app.session.questions.find(item => String(item.id) === qid);
    const textarea = document.getElementById(`codingTextarea-${qid}`);
    const userCode = textarea ? textarea.value : (app.session.codingSubmissions[qid] || '');
    app.session.codingSubmissions[qid] = userCode;

    const customInput = (app.session.customTestCases && app.session.customTestCases[qid]) || '';

    const btn = document.getElementById(`runCodeBtn-${qid}`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-[10px]"></i> Running...`;
    }

    try {
        const res = await fetch('/api/run-coding', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                problem_title: q.title || 'Coding Challenge',
                question: q.question,
                starter_code: q.starter_code || '',
                solution_code: q.solution_code || '',
                user_code: userCode,
                public_test_cases: q.public_test_cases || q.test_cases || [],
                custom_test_case: customInput,
                name: app.user?.name || 'Candidate'
            })
        });

        const data = await res.json();
        if (res.ok && data.success && data.result) {
            if (!app.session.codingRunResults) app.session.codingRunResults = {};
            app.session.codingRunResults[qid] = data.result;
            renderCurrentArenaQuestion();
            showToast(data.result.all_passed ? 'Public & custom tests passed!' : 'One or more test cases did not pass. Check output console.', data.result.all_passed ? 'success' : 'warning');
        } else {
            showToast(data.error || 'Test run failed.', 'error');
        }
    } catch (e) {
        console.error('Run coding error:', e);
        showToast('Server connection error while testing code.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-play text-[10px]"></i> Run Code`;
        }
    }
}

async function submitFinalCoding(qid) {
    const q = app.session.questions.find(item => String(item.id) === qid);
    const textarea = document.getElementById(`codingTextarea-${qid}`);
    const userCode = textarea ? textarea.value : (app.session.codingSubmissions[qid] || '');
    app.session.codingSubmissions[qid] = userCode;

    const btn = document.getElementById(`submitCodeBtn-${qid}`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-[10px]"></i> Grading Hidden Tests...`;
    }

    try {
        const res = await fetch('/api/evaluate-coding', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                problem_title: q.title || 'Coding Challenge',
                question: q.question,
                starter_code: q.starter_code || '',
                solution_code: q.solution_code || '',
                user_code: userCode,
                public_test_cases: q.public_test_cases || q.test_cases || [],
                hidden_test_cases: q.hidden_test_cases || [],
                test_cases: q.test_cases || [],
                name: app.user?.name || 'Candidate'
            })
        });

        const data = await res.json();
        if (res.ok && data.success && data.result) {
            const cr = data.result;
            if (!app.session.codingResults) app.session.codingResults = {};
            app.session.codingResults[qid] = cr;
            app.session.verifiedQuestions[qid] = {
                isVerified: true,
                wasCorrect: Boolean(cr.passed)
            };
            renderCurrentArenaQuestion();
            showToast(cr.passed ? 'All public and hidden edge-case tests passed! (+1 Mark)' : 'Solution failed on edge cases (0 Marks). Review explanation below.', cr.passed ? 'success' : 'error');
        } else {
            showToast(data.error || 'Code evaluation failed.', 'error');
        }
    } catch (e) {
        console.error('Coding submit error:', e);
        showToast('Server connection error while grading code.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-check-double text-[10px]"></i> Submit Solution`;
        }
    }
}

async function evaluateBehavioralRealtime(qid) {
    const q = app.session.questions.find(item => String(item.id) === qid);
    const textarea = document.getElementById(`behavioralTextarea-${qid}`);
    const answer = textarea ? textarea.value.trim() : (app.session.behavioralAnswers[qid] || '');
    app.session.behavioralAnswers[qid] = answer;

    if (!answer || answer.length < 15) {
        showToast('Please draft at least 2-3 sentences of your response before requesting AI feedback.', 'error');
        return;
    }

    const btn = document.getElementById(`evalBehavioralBtn-${qid}`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Analyzing...`;
    }

    try {
        const res = await fetch('/api/evaluate-behavioral', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: q.question,
                answer: answer,
                name: app.user?.name || 'Candidate',
                role_context: q.topic || 'Software Engineering'
            })
        });

        const data = await res.json();
        if (res.ok && data.success && data.evaluation) {
            const ev = data.evaluation;
            app.session.behavioralEvaluations[qid] = ev;
            app.session.verifiedQuestions[qid] = {
                isVerified: true,
                wasCorrect: ev.score >= 70
            };
            renderCurrentArenaQuestion();
            showToast(`Answer scored: ${ev.score}/100 - ${ev.verdict}`, 'success');
        } else {
            showToast(data.error || 'Behavioral evaluation failed.', 'error');
        }
    } catch (e) {
        console.error('Behavioral evaluation error:', e);
        showToast('Server connection error during evaluation.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-[11px]"></i> Evaluate Response with AI`;
        }
    }
}

function renderHintAccordion(hint) {
    if (!hint || !hint.trim()) return '';
    return `
        <div class="pt-2">
            <details class="group rounded-xl bg-white/[0.02] border border-white/[0.06] p-3 text-xs">
                <summary class="cursor-pointer text-slate-400 group-hover:text-emerald-400 font-mono flex items-center justify-between select-none">
                    <span><i class="fa-solid fa-lightbulb text-amber-400 mr-1.5"></i> Need a Conceptual Clue?</span>
                    <i class="fa-solid fa-chevron-down text-[10px] transition-transform group-open:rotate-180"></i>
                </summary>
                <div class="pt-2 text-slate-300 font-sans leading-relaxed border-t border-white/[0.04] mt-2">
                    ${escapeHtml(hint)}
                </div>
            </details>
        </div>
    `;
}

function renderCodingTestPanel(q, qid) {
    const publicCases = q.public_test_cases || q.test_cases || [];
    const activeTab = (app.session.activeCodingTab && app.session.activeCodingTab[qid]) || 'public';
    const savedCustom = (app.session.customTestCases && app.session.customTestCases[qid]) || '';

    let publicRows = '';
    publicCases.forEach((c, i) => {
        publicRows += `
            <tr class="border-b border-white/[0.04]">
                <td class="p-2.5 font-mono text-[11px] text-cyan-300 font-semibold">${escapeHtml(c.name || `#${i+1}`)}</td>
                <td class="p-2.5 font-mono text-[11px] text-slate-200">${escapeHtml(c.input || '')}</td>
                <td class="p-2.5 font-mono text-[11px] text-emerald-300">${escapeHtml(c.expected || '')}</td>
            </tr>
        `;
    });

    return `
        <div class="rounded-xl border border-white/[0.06] overflow-hidden text-xs bg-black/30">
            <div class="flex items-center justify-between px-3 py-2 bg-white/[0.02] border-b border-white/[0.06]">
                <div class="flex items-center gap-1.5">
                    <button type="button" onclick="switchCodingTestTab('${qid}', 'public')" 
                        class="px-2.5 py-1 rounded-md text-[11px] font-mono transition ${activeTab === 'public' ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200'}">
                        <i class="fa-solid fa-list-check mr-1 text-[10px]"></i> Public Test Cases (${publicCases.length})
                    </button>
                    <button type="button" onclick="switchCodingTestTab('${qid}', 'custom')" 
                        class="px-2.5 py-1 rounded-md text-[11px] font-mono transition ${activeTab === 'custom' ? 'bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30' : 'text-slate-400 hover:text-slate-200'}">
                        <i class="fa-solid fa-flask mr-1 text-[10px]"></i> Custom Test Case
                    </button>
                </div>
                <span class="text-[10px] font-mono text-slate-500 uppercase">
                    ${activeTab === 'public' ? 'Public Visible Cases' : 'Custom Input Sandbox'}
                </span>
            </div>

            ${activeTab === 'public' ? `
                <table class="w-full text-left">
                    <thead class="bg-white/[0.02] text-slate-400 font-mono text-[10px] uppercase">
                        <tr><th class="p-2.5">Test</th><th class="p-2.5">Input Parameters</th><th class="p-2.5">Expected Behavior</th></tr>
                    </thead>
                    <tbody class="divide-y divide-white/[0.04]">${publicRows}</tbody>
                </table>
            ` : `
                <div class="p-3 space-y-2">
                    <label class="block text-[11px] font-mono text-amber-300 font-semibold">
                        Enter Custom Input (Validates with 'Run Code' without affecting marks):
                    </label>
                    <textarea id="customTestCaseInput-${qid}" class="w-full h-16 p-2 rounded-lg bg-black/60 border border-white/[0.08] text-slate-200 font-mono text-[11px] focus:outline-none focus:border-amber-400/50 resize-none" 
                        placeholder="Enter custom input parameters (e.g. Set('temp_token', 'xyz', 45s) -> TryGet('temp_token'))" 
                        oninput="saveCustomTestCase('${qid}', this.value)">${escapeHtml(savedCustom)}</textarea>
                    <div class="text-[10px] text-slate-400 flex items-center gap-1.5">
                        <i class="fa-solid fa-circle-info text-amber-400"></i>
                        <span>Click <strong>'Run Code'</strong> below to test this custom case against your code in real time.</span>
                    </div>
                </div>
            `}
        </div>
    `;
}

function renderTestCases(cases) {
    if (!cases || !cases.length) return '';
    let rows = '';
    cases.forEach((c, i) => {
        rows += `
            <tr class="border-b border-white/[0.04]">
                <td class="p-2 font-mono text-[11px] text-slate-400">#${i+1}</td>
                <td class="p-2 font-mono text-[11px] text-emerald-300">${escapeHtml(c.input || '')}</td>
                <td class="p-2 font-mono text-[11px] text-slate-200">${escapeHtml(c.expected || '')}</td>
            </tr>
        `;
    });
    return `
        <div class="rounded-xl border border-white/[0.06] overflow-hidden text-xs">
            <table class="w-full text-left">
                <thead class="bg-white/[0.03] text-slate-400 font-mono text-[10px] uppercase">
                    <tr><th class="p-2">Case</th><th class="p-2">Input Scenario</th><th class="p-2">Expected Outcome</th></tr>
                </thead>
                <tbody class="divide-y divide-white/[0.04]">${rows}</tbody>
            </table>
        </div>
    `;
}

function saveCodingInput(qid, val) {
    app.session.codingSubmissions[qid] = val;
}

function saveBehavioralInput(qid, val) {
    app.session.behavioralAnswers[qid] = val;
}

function toggleFlagQuestion(qid) {
    if (app.session.flaggedQuestions.has(qid)) {
        app.session.flaggedQuestions.delete(qid);
    } else {
        app.session.flaggedQuestions.add(qid);
    }
    renderCurrentArenaQuestion();
}

function jumpToArenaQuestion(idx) {
    if (idx >= 0 && idx < app.session.questions.length) {
        app.session.currentIndex = idx;
        renderCurrentArenaQuestion();
    }
}

function navigateArenaQuestion(delta) {
    jumpToArenaQuestion(app.session.currentIndex + delta);
}

function toggleStrongAnswer(qid) {
    const box = document.getElementById(`sampleStrongBox-${qid}`);
    if (box) box.classList.toggle('hidden');
}

function confirmExitArena() {
    if (confirm('Are you sure you want to exit the current assessment? Your progress will be discarded.')) {
        if (app.session.timerInterval) clearInterval(app.session.timerInterval);
        document.getElementById('quizArenaContainer').classList.add('hidden');
        document.getElementById('resumeQuizSetupCard').classList.remove('hidden');
    }
}

// ==========================================
// ASSESSMENT SUBMISSION & COMPREHENSIVE ANALYTICS
// ==========================================
async function submitAssessmentSession() {
    if (app.session.timerInterval) clearInterval(app.session.timerInterval);

    const arena = document.getElementById('quizArenaContainer');
    arena.innerHTML = `
        <div class="studio-card p-12 text-center space-y-4">
            <div class="w-12 h-12 mx-auto rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-xl">
                <i class="fa-solid fa-circle-notch fa-spin"></i>
            </div>
            <h2 class="text-base font-bold text-white">Synthesizing Comprehensive Analytics...</h2>
            <p class="text-xs text-slate-400 max-w-sm mx-auto">Evaluating technical MCQ precision, practical code implementations, and behavioral impact metrics.</p>
        </div>
    `;

    try {
        const res = await fetch('/api/evaluate-quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: app.user?.name || document.getElementById('resumeUserName')?.value || 'Candidate',
                questions: app.session.questions,
                answers: app.session.answers,
                coding_submissions: app.session.codingSubmissions,
                coding_results: app.session.codingResults,
                behavioral_answers: app.session.behavioralAnswers,
                quiz_title: app.session.quizTitle,
                company_name: app.session.companyName,
                difficulty: app.session.difficulty
            })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            app.session.evaluation = data;
            renderComprehensiveResults(data);

            if (data.overall_score >= 75 && typeof confetti === 'function') {
                confetti({ particleCount: 80, spread: 60, origin: { y: 0.6 } });
            }
        } else {
            showToast(data.error || 'Evaluation processing failed.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Server error while evaluating assessment.', 'error');
    }
}

function renderComprehensiveResults(res) {
    const arena = document.getElementById('quizArenaContainer');
    const container = document.getElementById('quizResultsContainer');
    arena.classList.add('hidden');
    container.classList.remove('hidden');

    const score = res.overall_score || 0;

    // Build Topic Breakdown Bars
    let topicMetersHtml = '';
    const stats = res.topic_stats || {};
    Object.keys(stats).forEach(t => {
        const item = stats[t];
        topicMetersHtml += `
            <div class="space-y-1">
                <div class="flex items-center justify-between text-xs font-mono">
                    <span class="text-slate-300 truncate max-w-xs">${escapeHtml(t)}</span>
                    <span class="text-emerald-400 font-bold">${item.accuracy}% (${item.correct}/${item.total})</span>
                </div>
                <div class="h-1.5 w-full bg-white/[0.04] rounded-full overflow-hidden">
                    <div class="h-full bg-emerald-500 rounded-full transition-all duration-700" style="width: ${item.accuracy}%"></div>
                </div>
            </div>
        `;
    });

    // Build Detailed Review Cards
    let reviewCardsHtml = '';
    (res.detailed_review || []).forEach(r => {
        const isCorrect = r.is_correct;
        const qtype = r.type || 'mcq';

        let innerContent = '';
        if (qtype === 'mcq') {
            innerContent = `
                <div class="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                    <div class="p-2 rounded bg-black/30 border border-white/[0.04]">
                        <span class="text-slate-400">Your Answer:</span>
                        <strong class="${isCorrect ? 'text-emerald-400' : 'text-rose-400'} ml-1">${r.user_answer}</strong>
                    </div>
                    <div class="p-2 rounded bg-black/30 border border-white/[0.04]">
                        <span class="text-slate-400">Correct Answer:</span>
                        <strong class="text-emerald-400 ml-1">${r.correct_answer}</strong>
                    </div>
                </div>
                <div class="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-xs text-slate-300 mt-2">
                    <strong class="text-emerald-400 font-mono text-[11px] uppercase">Explanation:</strong> ${escapeHtml(r.explanation || '')}
                </div>
            `;
        } else if (qtype === 'coding') {
            innerContent = `
                <div class="space-y-2 pt-1 text-xs">
                    <div class="p-3 rounded-lg bg-black/40 border border-white/[0.04]">
                        <div class="text-[11px] font-mono text-cyan-300 font-bold uppercase mb-1">Your Submitted Code:</div>
                        <pre class="text-[11px] font-mono text-slate-300 overflow-x-auto"><code>${escapeHtml(r.user_code || 'No code')}</code></pre>
                    </div>
                    <div class="p-3 rounded-lg bg-black/40 border border-emerald-500/20">
                        <div class="text-[11px] font-mono text-emerald-400 font-bold uppercase mb-1">Optimal Reference Implementation:</div>
                        <pre class="text-[11px] font-mono text-slate-300 overflow-x-auto"><code>${escapeHtml(r.solution_code || '')}</code></pre>
                    </div>
                </div>
            `;
        } else if (qtype === 'behavioral') {
            innerContent = `
                <div class="space-y-2 pt-1 text-xs">
                    <div class="p-3 rounded-lg bg-black/40 border border-white/[0.04]">
                        <div class="text-[11px] font-mono text-amber-300 font-bold uppercase mb-1">Your Stated Answer:</div>
                        <p class="text-slate-300">${escapeHtml(r.user_response || 'No response')}</p>
                    </div>
                    <div class="p-3 rounded-lg bg-black/40 border border-emerald-500/20">
                        <div class="text-[11px] font-mono text-emerald-400 font-bold uppercase mb-1">Exemplar Interview Delivery:</div>
                        <p class="text-slate-300">${escapeHtml(r.sample_strong_answer || '')}</p>
                    </div>
                </div>
            `;
        }

        reviewCardsHtml += `
            <div class="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                <div class="flex items-center justify-between text-xs font-mono">
                    <span class="text-slate-400">#${r.id} // ${escapeHtml(r.topic)}</span>
                    <span class="${isCorrect ? 'text-emerald-400' : 'text-rose-400'} font-bold">
                        <i class="fa-solid ${isCorrect ? 'fa-check' : 'fa-xmark'} mr-1"></i>
                        ${isCorrect ? 'Validated' : 'Needs Review'}
                    </span>
                </div>
                <h3 class="text-xs sm:text-sm font-semibold text-white leading-snug">${escapeHtml(r.question || r.title || '')}</h3>
                ${innerContent}
            </div>
        `;
    });

    container.innerHTML = `
        <div class="studio-card p-6 sm:p-8 space-y-6">
            <!-- Top Executive Result Banner -->
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6 items-center border-b border-white/[0.06] pb-6">
                <!-- Score Dial (4 Cols) -->
                <div class="md:col-span-4 flex flex-col items-center justify-center p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
                    <div class="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2">Readiness Score</div>
                    <div class="text-5xl font-extrabold text-white font-mono tracking-tight">${score}%</div>
                    <div class="text-xs font-mono text-emerald-400 mt-1 font-semibold">${escapeHtml(res.verdict || '')}</div>
                </div>

                <!-- Sub-Pillars & Summary (8 Cols) -->
                <div class="md:col-span-8 space-y-3.5">
                    <div>
                        <h2 class="text-lg font-bold text-white tracking-tight">${escapeHtml(res.verdict || '')}</h2>
                        <p class="text-xs text-slate-300 mt-1 leading-relaxed">${escapeHtml(res.summary || '')}</p>
                    </div>

                    <!-- 3 Core Score Pillars -->
                    <div class="grid grid-cols-3 gap-2.5 pt-1">
                        <div class="p-3 rounded-xl bg-[#090c15] border border-white/[0.06] text-center">
                            <div class="text-[10px] font-mono text-slate-400 uppercase">Technical MCQ</div>
                            <div class="text-base font-bold text-emerald-400 font-mono mt-0.5">${res.technical_score || 0}%</div>
                        </div>
                        <div class="p-3 rounded-xl bg-[#090c15] border border-white/[0.06] text-center">
                            <div class="text-[10px] font-mono text-slate-400 uppercase">Coding & Logic</div>
                            <div class="text-base font-bold text-cyan-400 font-mono mt-0.5">${res.coding_score || 0}%</div>
                        </div>
                        <div class="p-3 rounded-xl bg-[#090c15] border border-white/[0.06] text-center">
                            <div class="text-[10px] font-mono text-slate-400 uppercase">Behavioral Fit</div>
                            <div class="text-base font-bold text-amber-400 font-mono mt-0.5">${res.behavioral_score || 0}%</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Two High-Impact Analytics Cards: Why Hire You vs Blindspots -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Why Interviewers Will Hire You -->
                <div class="p-5 rounded-2xl bg-emerald-500/[0.03] border border-emerald-500/20 space-y-2.5">
                    <div class="text-xs font-bold text-emerald-400 font-mono uppercase tracking-wider flex items-center gap-1.5">
                        <i class="fa-solid fa-circle-check"></i>
                        <span>Why Interviewers Will Want To Hire You</span>
                    </div>
                    <ul class="space-y-2 text-xs text-slate-300">
                        ${(res.why_hire_you || []).map(w => `<li class="flex items-start gap-2"><i class="fa-solid fa-arrow-right text-[10px] text-emerald-400 mt-1"></i><span>${escapeHtml(w)}</span></li>`).join('')}
                    </ul>
                </div>

                <!-- Critical Blindspots & Action Items -->
                <div class="p-5 rounded-2xl bg-amber-500/[0.03] border border-amber-500/20 space-y-2.5">
                    <div class="text-xs font-bold text-amber-400 font-mono uppercase tracking-wider flex items-center gap-1.5">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        <span>Critical Gaps & What To Fix Before Onsite</span>
                    </div>
                    <ul class="space-y-2 text-xs text-slate-300">
                        ${(res.critical_gaps || []).map(g => `<li class="flex items-start gap-2"><i class="fa-solid fa-bolt text-[10px] text-amber-400 mt-1"></i><span>${escapeHtml(g)}</span></li>`).join('')}
                    </ul>
                </div>
            </div>

            <!-- Topic Performance Meters -->
            <div class="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                <div class="text-xs font-bold text-white uppercase tracking-wider font-mono">Competency Breakdown</div>
                <div class="space-y-2.5 pt-1">${topicMetersHtml}</div>
            </div>

            <!-- Detailed Question-by-Question Review -->
            <div class="space-y-3">
                <div class="flex items-center justify-between">
                    <div class="text-xs font-bold text-white uppercase tracking-wider font-mono">Detailed Question Audit</div>
                    <div class="text-[11px] font-mono text-slate-400">Total: ${res.total_questions} Questions</div>
                </div>
                <div class="space-y-3">${reviewCardsHtml}</div>
            </div>

            <!-- Actions Footer -->
            <div class="flex items-center justify-between border-t border-white/[0.06] pt-5">
                <button type="button" onclick="retakeAssessmentSession()" class="btn-primary-action text-xs py-2.5">
                    <i class="fa-solid fa-arrows-rotate mr-1"></i>
                    <span>Retake New Non-Repeating Session</span>
                </button>
                <button type="button" onclick="switchMajorTab('ats-score')" class="studio-pill text-xs">
                    <span>Audit ATS Score Next -></span>
                </button>
            </div>
        </div>
    `;

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function retakeAssessmentSession() {
    document.getElementById('quizResultsContainer').classList.add('hidden');
    document.getElementById('resumeQuizSetupCard').classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// TAB 3: ATS RESUME AUDIT HANDLER
// ==========================================
async function handleRunAtsAudit() {
    const resumeText = app.resume.text;
    const targetRole = document.getElementById('atsTargetRole').value.trim() || 'Software Engineer';
    const btn = document.getElementById('runAtsBtn');
    const container = document.getElementById('atsReportContainer');

    if (!resumeText || resumeText.length < 20) {
        showToast('Please upload or load a resume document first.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i><span>Diagnosing ATS Compatibility...</span>`;

    try {
        const res = await fetch('/api/ats-audit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_text: resumeText,
                target_role: targetRole
            })
        });

        const data = await res.json();
        if (res.ok && data.success && data.review) {
            renderAtsReport(data.review);
            showToast('ATS diagnostic completed!', 'success');
        } else {
            showToast(data.error || 'ATS analysis failed.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Server error during ATS diagnostic.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-chart-simple text-xs"></i><span>Run Full ATS Diagnostic</span>`;
    }
}

function renderAtsReport(rep) {
    const container = document.getElementById('atsReportContainer');
    container.classList.remove('hidden');

    const score = rep.overall_score || 75;

    // Matched and Missing Keywords Badges
    const matchedBadges = (rep.matched_keywords || []).map(k => `
        <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono text-[11px]">${escapeHtml(k)}</span>
    `).join('');

    const missingBadges = (rep.missing_keywords || []).map(k => `
        <span class="px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20 font-mono text-[11px]">${escapeHtml(k)}</span>
    `).join('');

    // Bullet Point Rewrites
    let bulletHtml = '';
    (rep.bullet_improvements || []).forEach(b => {
        bulletHtml += `
            <div class="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2 text-xs">
                <div class="font-mono text-[10px] text-slate-400 uppercase tracking-wider">${escapeHtml(b.section || 'Experience')}</div>
                <div class="p-2.5 rounded bg-black/40 border border-rose-500/20 text-slate-300">
                    <span class="text-rose-400 font-mono text-[10px] font-bold block mb-0.5">ORIGINAL WEAK PHRASING:</span>
                    "${escapeHtml(b.original)}"
                </div>
                <div class="p-2.5 rounded bg-black/40 border border-emerald-500/25 text-emerald-200">
                    <span class="text-emerald-400 font-mono text-[10px] font-bold block mb-0.5">GOOGLE XYZ FORMULA REWRITE:</span>
                    "${escapeHtml(b.improved)}"
                </div>
                <div class="text-[11px] text-slate-400 font-mono italic">
                    Reason: ${escapeHtml(b.reason || '')}
                </div>
            </div>
        `;
    });

    container.innerHTML = `
        <div class="studio-card p-6 sm:p-8 space-y-6">
            <!-- Header Banner -->
            <div class="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-white/[0.06] pb-5">
                <div>
                    <h2 class="text-lg font-bold text-white tracking-tight">ATS Audit & Recruiter Diagnostic</h2>
                    <p class="text-xs text-slate-400 mt-1 max-w-xl">${escapeHtml(rep.summary || '')}</p>
                </div>
                <div class="text-center p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] min-w-[130px]">
                    <div class="text-[10px] font-mono text-slate-400 uppercase">ATS Match Score</div>
                    <div class="text-4xl font-extrabold text-emerald-400 font-mono mt-0.5">${score}/100</div>
                </div>
            </div>

            <!-- Keyword Breakdown Matrix -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="p-4 rounded-xl bg-emerald-500/[0.02] border border-emerald-500/20 space-y-2">
                    <div class="text-xs font-bold text-emerald-400 font-mono uppercase">Detected High-Value Keywords</div>
                    <div class="flex flex-wrap gap-1.5 pt-1">${matchedBadges || '<span class="text-slate-500">None detected</span>'}</div>
                </div>
                <div class="p-4 rounded-xl bg-rose-500/[0.02] border border-rose-500/20 space-y-2">
                    <div class="text-xs font-bold text-rose-400 font-mono uppercase">Critical Missing Keywords</div>
                    <div class="flex flex-wrap gap-1.5 pt-1">${missingBadges || '<span class="text-slate-500">None</span>'}</div>
                </div>
            </div>

            <!-- Bullet Point Enhancements -->
            <div class="space-y-3">
                <div class="text-xs font-bold text-white uppercase tracking-wider font-mono">Impact Bullet Point Rewrites</div>
                <div class="space-y-3">${bulletHtml}</div>
            </div>
        </div>
    `;

    container.scrollIntoView({ behavior: 'smooth' });
}

// ==========================================
// RESTRICTED ADMIN PORTAL (ISOLATED)
// ==========================================
async function openAdminModal() {
    if (!app.isAdmin) {
        showToast('Access denied. Administrator privileges restricted to kiruthiknivasnkl@gmail.com.', 'error');
        return;
    }
    document.getElementById('adminModal').classList.remove('hidden');
    loadAdminOverview();
}

function closeAdminModal() {
    document.getElementById('adminModal').classList.add('hidden');
}

async function loadAdminOverview() {
    try {
        const res = await fetch('/api/admin/overview');
        const data = await res.json();
        if (res.ok && data.success) {
            app.adminData = data;
            document.getElementById('adminStatUsers').textContent = data.stats.total_users || 0;
            document.getElementById('adminStatVerified').textContent = data.stats.verified_users || 0;
            document.getElementById('adminStatQuizzes').textContent = data.stats.total_quizzes || 0;
            document.getElementById('adminStatAts').textContent = data.stats.total_ats_checks || 0;
            document.getElementById('adminDbProviderLabel').textContent = `Connected to ${data.db_provider} (${data.db_url_masked})`;

            // Populate table
            const tbody = document.getElementById('adminUsersTableBody');
            if (data.users && data.users.length > 0) {
                tbody.innerHTML = data.users.map(u => `
                    <tr class="hover:bg-white/[0.02]">
                        <td class="p-3 text-slate-400">#${u.id}</td>
                        <td class="p-3 text-white font-medium">${escapeHtml(u.name)}</td>
                        <td class="p-3 text-slate-300">${escapeHtml(u.email)}</td>
                        <td class="p-3 text-emerald-400">${escapeHtml(u.primary_skill || '.NET')}</td>
                        <td class="p-3">${u.is_verified ? '<span class="text-emerald-400 font-bold">YES</span>' : '<span class="text-amber-400">PENDING</span>'}</td>
                        <td class="p-3 text-slate-400">${u.created_at || ''}</td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500">No candidate accounts recorded yet.</td></tr>`;
            }
        } else {
            showToast(data.error || 'Admin overview unauthorized.', 'error');
            closeAdminModal();
        }
    } catch (e) {
        console.error(e);
        showToast('Failed to connect to database overview.', 'error');
    }
}

// ==========================================
// AUTHENTICATION MODAL LOGIC
// ==========================================
function openAuthModal(mode) {
    document.getElementById('authModal').classList.remove('hidden');
    toggleAuthForm(mode || 'login');
}

function closeAuthModal() {
    document.getElementById('authModal').classList.add('hidden');
}

function openSetupGuideModal() {
    document.getElementById('setupGuideModal').classList.remove('hidden');
}

function closeSetupGuideModal() {
    document.getElementById('setupGuideModal').classList.add('hidden');
}

function toggleAuthForm(mode) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const otpForm = document.getElementById('otpVerifyForm');
    const title = document.getElementById('authModalTitle');

    loginForm.classList.add('hidden');
    registerForm.classList.add('hidden');
    otpForm.classList.add('hidden');

    if (mode === 'login') {
        loginForm.classList.remove('hidden');
        title.textContent = 'Sign In to SkillSprint Studio';
    } else if (mode === 'register') {
        registerForm.classList.remove('hidden');
        title.textContent = 'Create New Candidate Account';
    } else if (mode === 'otp') {
        otpForm.classList.remove('hidden');
        title.textContent = 'Verify Email Address';
    }
}

async function handleLoginSubmit(event) {
    event.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value.trim();

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            closeAuthModal();
            await checkCurrentUser();
            showToast(`Welcome back, ${data.user.name}!`, 'success');
        } else if (data.requires_verification) {
            document.getElementById('otpTargetEmailDisplay').textContent = email;
            toggleAuthForm('otp');
            showToast(data.error || 'Please enter the 6-digit code sent to your email.', 'info');
        } else {
            showToast(data.error || 'Invalid email or password.', 'error');
        }
    } catch (e) {
        showToast('Server connection error during login.', 'error');
    }
}

async function handleRegisterSubmit(event) {
    event.preventDefault();
    const name = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value.trim();

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                email,
                password,
                primary_skill: document.getElementById('resumePrimarySkill')?.value || '.NET Core / C#',
                secondary_skill: document.getElementById('resumeSecondarySkill')?.value || 'Angular'
            })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            document.getElementById('otpTargetEmailDisplay').textContent = email;
            toggleAuthForm('otp');
            showToast('A 6-digit verification code has been dispatched to your email.', 'success');
        } else {
            showToast(data.error || 'Registration failed.', 'error');
        }
    } catch (e) {
        showToast('Server connection error during registration.', 'error');
    }
}

async function handleOtpSubmit(event) {
    event.preventDefault();
    const email = document.getElementById('otpTargetEmailDisplay').textContent.trim() || document.getElementById('loginEmail').value.trim() || document.getElementById('regEmail').value.trim();
    const otp = document.getElementById('otpInput').value.trim();

    try {
        const res = await fetch('/api/auth/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, otp })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            closeAuthModal();
            await checkCurrentUser();
            showToast('Account verified successfully! Welcome to SkillSprint Studio.', 'success');
        } else {
            showToast(data.error || 'Invalid verification code.', 'error');
        }
    } catch (e) {
        showToast('Server connection error during OTP verification.', 'error');
    }
}

// Keyboard shortcuts (Next / Prev / Option selection)
function setupKeyboardNav() {
    document.addEventListener('keydown', e => {
        const arena = document.getElementById('quizArenaContainer');
        if (!arena || arena.classList.contains('hidden')) return;

        if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

        if (e.key === 'ArrowRight' || e.key === 'n') {
            navigateArenaQuestion(1);
        } else if (e.key === 'ArrowLeft' || e.key === 'p') {
            navigateArenaQuestion(-1);
        } else if (['1', '2', '3', '4'].includes(e.key)) {
            const letters = ['A', 'B', 'C', 'D'];
            const q = app.session.questions[app.session.currentIndex];
            if (q && (q.type === 'mcq' || !q.type)) {
                selectArenaMcqOption(String(q.id), letters[parseInt(e.key) - 1]);
            }
        }
    });
}

function strUpper(str) {
    if (!str) return '';
    return String(str).toUpperCase().trim();
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
