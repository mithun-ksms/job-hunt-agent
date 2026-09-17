# import libraries
from google import genai
import streamlit as st
import requests
import pandas as pd
import pdfplumber

# -------------------------
# PAGE SETUP
# -------------------------

st.set_page_config(
    page_title="AI Job Search Agent",
    page_icon="🤖"
)

st.title("🤖 AI Job Search Agent")

st.write("Upload your CV and find jobs that match your skills.")

# -------------------------
# API KEYS FROM SECRETS
# -------------------------

serper_key = st.secrets["SERPER_KEY"]
gemini_key = st.secrets["GEMINI_KEY"]

# -------------------------
# SIDEBAR INPUTS
# -------------------------

st.sidebar.header("🎯 Job Search")

job_title = st.sidebar.text_input("Job title", "Data Analyst")

location = st.sidebar.text_input("Location", "London")

st.sidebar.header("📄 Your CV")

cv_file = st.sidebar.file_uploader("Upload your CV (PDF)", type="pdf")

st.sidebar.header("➕ Extra Skills")

manual_skills = st.sidebar.text_area(
    "Add extra skills (one per line)",
    "python\nsql\npower bi\ndata analysis\nanalytics\ngraduate"
)

search_button = st.sidebar.button("🔍 Find My Jobs")

# -------------------------
# FUNCTION: READ CV
# -------------------------

def read_cv(cv_file):

    text = ""

    pdf = pdfplumber.open(cv_file)

    for page in pdf.pages:

        page_text = page.extract_text()

        if page_text:
            text = text + page_text + "\n"

    pdf.close()

    return text

# -------------------------
# FUNCTION: GET SKILLS FROM CV
# -------------------------

def get_cv_skills(cv_text, client):

    # limit text to avoid overloading the API
    prompt = f"""
    Read this CV and list all the skills you find.
    Include programming languages, tools and software.
    Return ONLY a comma separated list. Nothing else.
    Example: python, sql, pandas, power bi, machine learning

    CV:
    {cv_text[:3000]}
    """

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    raw_skills = response.text.split(",")

    skills = []
    for skill in raw_skills:
        cleaned = skill.strip().lower()
        if cleaned:
            skills.append(cleaned)

    return skills

# -------------------------
# FUNCTION: SCORE A JOB
# -------------------------

def score_job(job_title, job_description, user_skills):

    job_text = (job_title + " " + job_description).lower()

    keywords = [
        "python", "sql", "machine learning",
        "data analysis", "data analyst",
        "data analytics", "analytics",
        "pandas", "numpy", "power bi",
        "tableau", "excel", "tensorflow",
        "pytorch", "scikit-learn", "nlp",
        "streamlit", "plotly", "shap",
        "statistics", "data visualisation",
        "aws", "azure", "git", "github",
        "graduate", "entry level", "degree",
        "dashboard", "reporting", "insight",
        "analytical", "analysis", "r"
    ]

    job_keywords = []
    for word in keywords:
        if word in job_text:
            job_keywords.append(word)

    matched = []
    for word in job_keywords:
        for user_skill in user_skills:
            if word in user_skill or user_skill in word:
                matched.append(word)
                break

    if len(job_keywords) > 0:
        score = round(len(matched) / len(job_keywords) * 100)
    else:
        score = 0

    return score, matched, job_keywords

# -------------------------
# FUNCTION: WRITE COVER LETTER
# -------------------------

def write_cover_letter(job_title, job_description, cv_text, client):

    prompt = f"""
    Write a short professional cover letter for this job.

    Job title: {job_title}
    Job description: {job_description}

    Use this CV to personalise it:
    {cv_text[:2000]}

    Rules:
    - Write exactly 3 short paragraphs
    - Professional but warm tone
    - Mention specific projects from the CV
    - Do not make up any information
    - Make it specific to this exact job
    """

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    return response.text

# -------------------------
# MAIN PROGRAM
# -------------------------

if search_button:

    if not serper_key or not gemini_key:
        st.error("API keys missing - check Streamlit secrets")
        st.stop()

    # start Gemini client
    client = genai.Client(api_key=gemini_key)

    # ---- STEP 1: READ CV ----

    cv_text = ""
    cv_skills = []

    if cv_file:

        st.info("📄 Reading your CV...")

        cv_text = read_cv(cv_file)

        cv_skills = get_cv_skills(cv_text, client)

        st.success(f"✅ CV read — found {len(cv_skills)} skills")

    else:
        st.warning("⚠️ No CV uploaded — using manual skills only")

    # ---- STEP 2: COMBINE SKILLS ----

    manual_list = []
    for skill in manual_skills.split("\n"):
        cleaned = skill.strip().lower()
        if cleaned:
            manual_list.append(cleaned)

    all_skills = list(set(cv_skills + manual_list))

    if not all_skills:
        st.error("No skills found. Upload a CV or add skills manually.")
        st.stop()

    with st.expander("🧠 Your skills detected"):
        st.write(", ".join(all_skills))

    st.markdown("---")

    # ---- STEP 3: SEARCH JOBS ----

    st.info("🔍 Searching for jobs...")

    search_response = requests.post(
        "https://google.serper.dev/search",
        json={
            "q": job_title + " jobs " + location + " graduate entry level",
            "num": 10,
            "gl": "uk"
        },
        headers={
            "X-API-KEY": serper_key,
            "Content-Type": "application/json"
        }
    )

    results = search_response.json()
    jobs = results.get("organic", [])

    # ---- STEP 4: SCORE EACH JOB ----

    st.info("📊 Matching jobs to your skills...")

    job_list = []

    for job in jobs:

        title = job.get("title", "N/A")
        link = job.get("link", "N/A")
        description = job.get("snippet", "N/A")

        score, matched, job_keywords = score_job(
            title,
            description,
            all_skills
        )

        job_list.append({
            "title": title,
            "link": link,
            "description": description,
            "score": score,
            "matched": ", ".join(matched),
            "job_keywords": ", ".join(job_keywords)
        })

    df_jobs = pd.DataFrame(job_list)
    df_jobs = df_jobs.sort_values("score", ascending=False)
    df_jobs = df_jobs.reset_index(drop=True)

    # ---- STEP 5: SHOW RESULTS ----

    st.markdown("---")
    st.subheader(f"🎯 {len(df_jobs)} jobs found")

    for i, row in df_jobs.iterrows():

        if row["score"] > 50:
            emoji = "🟢"
        elif row["score"] > 20:
            emoji = "🟡"
        else:
            emoji = "🔴"

        with st.expander(
            emoji + " " + row["title"] + " — " + str(row["score"]) + "% match"
        ):

            st.write("**Description:** " + row["description"])
            st.write("**Skills this job wants:** " + row["job_keywords"])
            st.write("**Your matching skills:** " + row["matched"])
            st.markdown("[View Full Job →](" + row["link"] + ")")
            st.divider()

            if st.button("✉️ Generate Cover Letter", key="btn_" + str(i)):

                with st.spinner("✍️ Writing your cover letter..."):

                    letter = write_cover_letter(
                        row["title"],
                        row["description"],
                        cv_text,
                        client
                    )

                    st.text_area(
                        "Your cover letter:",
                        letter,
                        height=300,
                        key="letter_" + str(i)
                    )

                    st.download_button(
                        "⬇️ Download Cover Letter",
                        letter,
                        file_name="cover_letter_" + str(i+1) + ".txt",
                        key="download_" + str(i)
                    )
