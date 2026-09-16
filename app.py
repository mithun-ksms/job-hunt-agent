import streamlit as st
import requests
import pandas as pd
import google.generativeai as genai
import pdfplumber

# -------------------------
# PAGE SETUP
# -------------------------

st.set_page_config(
    page_title="AI Job Search Agent",
    page_icon="🤖"
)

st.title("🤖 AI Job Search Agent")

st.write(
    "Upload your CV, add your skills, "
    "and find graduate jobs that match you."
)

# -------------------------
# API KEYS FROM SECRETS
# -------------------------

serper_key = st.secrets["SERPER_KEY"]
gemini_key = st.secrets["GEMINI_KEY"]

# -------------------------
# SIDEBAR
# -------------------------

st.sidebar.header("🎯 Job Search")

job_title = st.sidebar.text_input(
    "Job title",
    "Data Analyst"
)

location = st.sidebar.text_input(
    "Location",
    "London"
)

st.sidebar.header("📄 Your CV")

# CV upload
cv_file = st.sidebar.file_uploader(
    "Upload your CV (PDF)",
    type="pdf"
)

st.sidebar.header("➕ Extra Skills")

manual_skills = st.sidebar.text_area(
    "Add extra skills (one per line)",
    placeholder="python\nsql\npower bi"
)

search_button = st.sidebar.button(
    "🔍 Find My Jobs"
)

# -------------------------
# READ CV
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
# FIND SKILLS IN CV
# -------------------------

def get_cv_skills(cv_text, model):

    prompt = f"""
    Read this CV and find all the skills.
    Include programming languages,
    tools, software and technical skills.
    Return ONLY skills separated by commas.
    Example: python, sql, pandas, power bi

    CV:
    {cv_text}
    """

    response = model.generate_content(prompt)

    skills = response.text.split(",")

    skills = [
        skill.strip().lower()
        for skill in skills
        if skill.strip()
    ]

    return skills

# -------------------------
# MATCH JOB WITH SKILLS
# -------------------------

def match_job(title, description, my_skills):

    job_text = (title + " " + description).lower()

    possible_skills = [
        "python", "sql", "machine learning",
        "data analysis", "data analytics",
        "pandas", "numpy", "power bi",
        "tableau", "excel", "tensorflow",
        "pytorch", "scikit-learn", "nlp",
        "streamlit", "plotly", "shap",
        "random forest", "statistics",
        "data visualisation", "aws",
        "azure", "git", "github", "r"
    ]

    # skills mentioned in job
    job_skills = [
        skill for skill in possible_skills
        if skill in job_text
    ]

    # skills user has that match job
    matched_skills = [
        skill for skill in job_skills
        if skill in my_skills
    ]

    # calculate score
    if len(job_skills) > 0:
        score = round(
            len(matched_skills) / len(job_skills) * 100
        )
    else:
        score = 0

    return score, matched_skills, job_skills

# -------------------------
# COVER LETTER
# -------------------------

def make_cover_letter(title, description, cv_text, model):

    prompt = f"""
    Write a short professional cover letter.

    Job: {title}
    Description: {description}
    CV: {cv_text[:2000]}

    Rules:
    - 3 short paragraphs
    - Professional but warm tone
    - Mention relevant projects from the CV
    - Do not invent information
    - Make it specific to this job
    """

    response = model.generate_content(prompt)

    return response.text

# -------------------------
# MAIN PROGRAM
# -------------------------

if search_button:

    # -------------------------
    # START GEMINI
    # -------------------------

    genai.configure(api_key=gemini_key)

    model = genai.GenerativeModel(
        "gemini-3.5-flash"
    )

    # -------------------------
    # READ CV IF UPLOADED
    # -------------------------

    cv_text = ""
    cv_skills = []

    if cv_file:

        st.info("📄 Reading your CV...")

        cv_text = read_cv(cv_file)

        cv_skills = get_cv_skills(cv_text, model)

        st.success(
            f"✅ CV scanned — "
            f"found {len(cv_skills)} skills"
        )

    else:

        st.warning(
            "⚠️ No CV uploaded — "
            "using manual skills only"
        )

    # -------------------------
    # COMBINE SKILLS
    # -------------------------

    manual_list = [
        skill.strip().lower()
        for skill in manual_skills.split("\n")
        if skill.strip()
    ]

    all_skills = list(set(cv_skills + manual_list))

    if not all_skills:

        st.error(
            "No skills found. "
            "Upload a CV or add skills manually."
        )

        st.stop()

    # show combined skills
    with st.expander("🧠 Skills detected"):
        st.write(", ".join(all_skills))

    st.markdown("---")

    # -------------------------
    # SEARCH JOBS
    # -------------------------

    st.info("🔍 Searching for jobs...")

    response = requests.post(

        "https://google.serper.dev/search",

        json={
            "q": (
                f"{job_title} jobs "
                f"{location} "
                f"graduate entry level"
            ),
            "num": 10,
            "gl": "uk"
        },

        headers={
            "X-API-KEY": serper_key,
            "Content-Type": "application/json"
        }
    )

    results = response.json()
    jobs = results.get("organic", [])

    # -------------------------
    # MATCH JOBS
    # -------------------------

    st.info("📊 Matching jobs to your skills...")

    job_list = []

    for job in jobs:

        title = job.get("title", "N/A")
        link = job.get("link", "N/A")
        description = job.get("snippet", "N/A")

        score, matched, job_skills = match_job(
            title,
            description,
            all_skills
        )

        job_list.append({
            "title": title,
            "link": link,
            "description": description,
            "score": score,
            "matched_skills": ", ".join(matched),
            "job_skills": ", ".join(job_skills)
        })

    df_jobs = pd.DataFrame(job_list)

    df_jobs = df_jobs.sort_values(
        "score",
        ascending=False
    ).reset_index(drop=True)

    # -------------------------
    # SHOW RESULTS
    # -------------------------

    st.markdown("---")
    st.subheader(f"🎯 {len(df_jobs)} Jobs Found")

    for i, row in df_jobs.iterrows():

        # colour based on score
        if row['score'] > 50:
            emoji = "🟢"
        elif row['score'] > 20:
            emoji = "🟡"
        else:
            emoji = "🔴"

        with st.expander(
            f"{emoji} {row['title']} "
            f"— {row['score']}% match"
        ):

            st.write(
                f"**Description:** {row['description']}"
            )

            st.write(
                f"**Skills this job wants:** "
                f"`{row['job_skills']}`"
            )

            st.write(
                f"**Your matching skills:** "
                f"`{row['matched_skills']}`"
            )

            st.markdown(
                f"[View Full Job →]({row['link']})"
            )

            st.divider()

            # cover letter button
            if st.button(
                "✉️ Generate Cover Letter",
                key=f"btn_{i}"
            ):

                with st.spinner(
                    "✍️ Writing your cover letter..."
                ):

                    letter = make_cover_letter(
                        row["title"],
                        row["description"],
                        cv_text,
                        model
                    )

                    st.text_area(
                        "Your Cover Letter:",
                        letter,
                        height=300,
                        key=f"letter_{i}"
                    )

                    st.download_button(
                        "⬇️ Download Cover Letter",
                        letter,
                        file_name=f"cover_letter_{i+1}.txt",
                        key=f"download_{i}"
                    )
