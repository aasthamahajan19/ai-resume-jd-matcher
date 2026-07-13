import os
import tempfile
import streamlit as st

from parse_documents import load_document
from generate_report import analyze_resume_against_jd
from resume_editor import tailor_resume

# -----------------------------
# PAGE CONFIG (MUST BE FIRST)
# -----------------------------
st.set_page_config(
    page_title="Resume vs JD Analyzer",
    page_icon="📄",
    layout="wide"
)

# -----------------------------
# SIDEBAR
# -----------------------------
with st.sidebar:

    st.header("🔑 Gemini API")

    api_key = st.text_input(
        "Enter your Gemini API Key",
        type="password",
        help="Your API key is used only for this session."
    )

    st.markdown(
        "[Get Gemini API Key](https://aistudio.google.com/app/apikey)"
    )

    if api_key:
        st.success("API Key Loaded")
    else:
        st.info("Enter your Gemini API key.")

    st.divider()

    if st.button("🗑 Clear Session"):
        st.session_state.clear()
        st.rerun()

# -----------------------------
# TITLE
# -----------------------------

st.title("📄 Resume vs Job Description Analyzer")

st.write(
    "Upload your resume, paste the Job Description, "
    "analyze the match, and generate a tailored resume."
)

# -----------------------------
# SESSION STATE
# -----------------------------

if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None

if "tailored_result" not in st.session_state:
    st.session_state.tailored_result = None

if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""

if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""

# -----------------------------
# RESUME UPLOAD
# -----------------------------

st.header("1️⃣ Upload Resume")

uploaded_file = st.file_uploader(
    "Upload Resume",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:

    suffix = os.path.splitext(uploaded_file.name)[1]

    temp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as tmp:

            tmp.write(uploaded_file.getbuffer())

            temp_path = tmp.name

        resume_text = load_document(temp_path)

        st.session_state.resume_text = resume_text

        st.success("Resume Loaded Successfully")

        with st.expander("Resume Preview"):

            st.text_area(
                "",
                resume_text,
                height=300
            )

    except Exception as e:

        st.error(str(e))

    finally:

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

# -----------------------------
# JOB DESCRIPTION
# -----------------------------

st.header("2️⃣ Job Description")

jd_text = st.text_area(
    "Paste Job Description",
    value=st.session_state.jd_text,
    height=300
)

st.session_state.jd_text = jd_text

# -----------------------------
# ANALYZE
# -----------------------------

st.header("3️⃣ Analyze Resume")

if st.button(
    "🔍 Analyze Resume",
    use_container_width=True,
    type="primary"
):

    if not api_key.strip():

        st.error("Please enter your Gemini API key.")

        st.stop()

    if not st.session_state.resume_text.strip():

        st.error("Please upload a resume.")

        st.stop()

    if not st.session_state.jd_text.strip():

        st.error("Please paste a Job Description.")

        st.stop()

    with st.spinner("Analyzing..."):

        try:

            results = analyze_resume_against_jd(
                api_key,
                st.session_state.jd_text,
                st.session_state.resume_text
            )

            st.session_state.analysis_results = results

        except Exception as e:

            st.error(str(e))

# -----------------------------
# RESULTS
# -----------------------------

results = st.session_state.analysis_results

if results:

    st.divider()

    st.header("📊 Match Results")

    score = results["overall_score"]

    summary = results["summary"]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Match", f"{score}%")
    c2.metric("Strong", summary["strong"])
    c3.metric("Weak", summary["weak"])
    c4.metric("Missing", summary["missing"])

    st.progress(score / 100)

    st.subheader("Requirement Analysis")

    requirements = results["requirements"]

    for i, req in enumerate(requirements, 1):

        verdict = req["verdict"]

        if verdict == "strong":
            icon = "🟢"
        elif verdict == "weak":
            icon = "🟡"
        else:
            icon = "🔴"

        with st.expander(
            f"{icon} {i}. {req['requirement']}"
        ):

            st.write(
                f"**Category:** {req['category']}"
            )

            st.write(
                f"**Type:** {req['type']}"
            )

            st.write(
                f"**Verdict:** {verdict}"
            )

            if req["evidence_quote"]:

                st.info(req["evidence_quote"])

            else:

                st.warning(
                    "No evidence found."
                )

            st.write(req["reasoning"])
    # -----------------------------
# TAILOR RESUME
# -----------------------------

if (
    st.session_state.resume_text.strip()
    and st.session_state.jd_text.strip()
):

    st.divider()

    st.header("✍️ Tailor Resume to Job Description")

    st.write(
        "Generate an ATS-friendly version of your resume "
        "without inventing skills or experience."
    )

    if st.button(
        "✨ Generate Tailored Resume",
        use_container_width=True
    ):

        if not api_key.strip():

            st.error("Please enter your Gemini API Key.")

            st.stop()

        with st.spinner("Generating tailored resume..."):

            try:

                tailored = tailor_resume(
                    api_key,
                    st.session_state.jd_text,
                    st.session_state.resume_text
                )

                st.session_state.tailored_result = tailored

                st.success(
                    "Tailored Resume Generated Successfully!"
                )

            except Exception as e:

                st.error(str(e))

# -----------------------------
# DISPLAY TAILORED RESUME
# -----------------------------

tailored = st.session_state.tailored_result

if tailored:

    st.divider()

    st.header("📝 Tailored Resume")

    if tailored.get("error"):

        st.error(
            tailored["error"]
        )

    edited_resume = st.text_area(
        "Edit Resume",
        value=tailored.get(
            "tailored_resume",
            ""
        ),
        height=500
    )

    st.subheader("✅ Changes Made")

    changes = tailored.get(
        "changes_made",
        []
    )

    if changes:

        for change in changes:

            st.markdown(
                f"- {change}"
            )

    else:

        st.info(
            "No changes were reported."
        )

    st.subheader(
        "⚠️ Missing Job Requirements"
    )

    missing = tailored.get(
        "missing_keywords",
        []
    )

    if missing:

        for item in missing:

            st.warning(item)

    else:

        st.success(
            "No unsupported requirements detected."
        )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(
            "📥 Download TXT",
            data=edited_resume,
            file_name="Tailored_Resume.txt",
            mime="text/plain",
            use_container_width=True
        )

    with col2:

        import io
        from docx import Document

        doc = Document()

        for line in edited_resume.split("\n"):
            doc.add_paragraph(line)

        buffer = io.BytesIO()

        doc.save(buffer)

        buffer.seek(0)

        st.download_button(
            "📄 Download DOCX",
            data=buffer,
            file_name="Tailored_Resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

st.divider()

st.caption(
    "Resume vs JD Analyzer • Powered by Gemini AI"
)