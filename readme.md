# 📄 Resume vs JD Analyzer

A Streamlit app that compares your resume against a job description, scores the match, and generates an ATS-friendly tailored version of your resume — powered by Google's Gemini API.

## ✨ Features

- **Resume parsing** — upload PDF, DOCX, or TXT resumes
- **Requirement extraction** — automatically pulls discrete, checkable requirements (skills, experience, education, tools) from any job description
- **Evidence matching** — evaluates each requirement against your resume with a `strong` / `weak` / `missing` verdict and supporting quote
- **Match score** — weighted overall compatibility score, with required requirements weighted higher than preferred ones
- **Resume tailoring** — rewrites your resume to better align with the JD using only facts already present in your original resume (no invented skills or experience)
- **Missing requirements report** — honestly flags JD requirements your resume doesn't currently support, instead of fabricating them

## 🛠 Tech Stack

- [Streamlit](https://streamlit.io/) — UI
- [Google Gemini API](https://ai.google.dev/) (`gemini-2.5-flash`) — requirement extraction, evidence matching, resume tailoring
- `pdfplumber` — PDF text extraction
- `python-docx` — DOCX reading/writing

## 🚀 Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/your-username/resume-jd-analyzer.git
   cd resume-jd-analyzer
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   streamlit run app.py
   ```

5. **Get a Gemini API key**
   Grab one from [Google AI Studio](https://aistudio.google.com/app/apikey) and paste it into the sidebar when the app opens. Your key is used only for your session and is never stored or committed.

## 📁 Project Structure

```
├── app.py                    # Streamlit UI and app flow
├── config.py                 # Gemini client + model config
├── gemini_helper.py          # Shared Gemini call wrapper with retry/backoff
├── parse_documents.py        # PDF/DOCX/TXT resume text extraction
├── parse_resume.py           # Breaks resume into discrete experience units
├── extract_requirements.py   # Extracts checkable requirements from the JD
├── evidence_matcher.py       # Matches resume evidence against requirements (batched)
├── generate_report.py        # Orchestrates analysis + scoring
├── resume_editor.py          # Generates the tailored resume
└── requirements.txt
```

## ⚠️ Notes & Limitations

- **Free-tier Gemini quota**: the free tier allows 20 requests/day per model. Evidence checks are batched (multiple requirements per API call) to keep usage well within this limit, but very large job descriptions may still use several calls.
- **No fabricated experience**: by design, the tailoring step will never invent skills, projects, or experience not already present in your original resume. Genuine gaps are reported in the "Missing Job Requirements" section rather than papered over — this is intentional, to keep your resume honest.
- Analysis quality depends on how explicitly your resume names tools/skills — vague phrasing can cause real experience to be under-matched.

## 📜 License

MIT (or update to your preferred license)
