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

# read keys from streamlit secrets (safe - never shown to users)
serper_key = st.secrets["SERPER_KEY"]
gemini_key = st.secrets["GEMINI_KEY"]

# -------------------------
# SIDEBAR INPUTS
# -------------------------

st.sidebar.header("🎯 Job Search")

# text box for job title
job_title = st.sidebar.text_input("Job title", "Data Analyst")

# text box for location
location = st.sidebar.text_input("Location", "London")

st.sidebar.header("📄 Your CV")

# file upload box - only accepts PDF
cv_file = st.sidebar.file_uploader("Upload your CV (PDF)", type="pdf")

st.sidebar.header("➕ Extra Skills")

# text area for manual skills
manual_skills = st.sidebar.text_area(
    "Add extra skills (one per line)",
    "python\nsql\npower bi\ndata analysis\nanalytics\ngraduate"
)

# search button
search_button = st.sidebar.button("🔍 Find My Jobs")

# -------------------------
# FUNCTION: READ CV
# -------------------------

def read_cv(cv_file):

    # empty string to store all text
    text = ""

    # open the PDF file
    pdf = pdfplumber.open(cv_file)

    # go through every page one by one
    for page in pdf.pages:

        # extract text from this page
        page_text = page.extract_text()

        # only add if page has text (some pages are blank)
        if page_text:
            text = text + page_text + "\n"

    # close the PDF
    pdf.close()

    # return all the text
    return text

# -------------------------
# FUNCTION: GET SKILLS FROM CV
# -------------------------

def get_cv_skills(cv_text, client):

    # ask Gemini to read the CV and list all skills
    prompt = f"""
    Read this CV and list all the skills you find.
    Include programming languages, tools and software.
    Return ONLY a comma separated list. Nothing else.
    Example: python, sql, pandas, power bi, machine learning

    CV:
    {cv_text}
    """

    # send to Gemini using new SDK
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    # split by comma to get a list
    # e.g. "python, sql, pandas" becomes ["python", "sql", "pandas"]
    raw_skills = response.text.split(",")

    # clean each skill - remove spaces, make lowercase
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

    # combine title and description into one text
    job_text = job_title + " " + job_description

    # make lowercase so matching works
    job_text = job_text.lower()

    # list of keywords to look for in job postings
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

    # find which keywords appear in this job
    job_keywords = []
    for word in keywords:
        if word in job_text:
            job_keywords.append(word)

    # find which of those keywords the user also has
    matched = []
    for word in job_keywords:
        # check if this keyword is in user skills
        for user_skill in user_skills:
            # use 'in' both ways to catch partial matches
            # e.g. "data analyst" matches "data analysis"
            if word in user_skill or user_skill in word:
                matched.append(word)
                # stop checking once we find a match
                break

    # calculate score as a percentage
    if len(job_keywords) > 0:
        score = round(len(matched) / len(job_keywords) * 100)
    else:
        score = 0

    return score, matched, job_keywords

# -------------------------
# FUNCTION: WRITE COVER LETTER
# -------------------------

def write_cover_letter(job_title, job_description, cv_text, client):

    # ask Gemini to write a cover letter
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

    # send to Gemini using new SDK
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text

# -------------------------
# MAIN PROGRAM
# -------------------------

# only run when button is clicked
if search_button:

    # check API keys exist
    if not serper_key or not gemini_key:
        st.error("API keys missing - check Streamlit secrets")
        st.stop()

    # start Gemini client using new SDK
    client = genai.Client(api_key=gemini_key)

    # ---- STEP 1: READ CV ----

    cv_text = ""
    cv_skills = []

    if cv_file:

        st.info("📄 Reading your CV...")

        # extract text from PDF
        cv_text = read_cv(cv_file)

        # ask Gemini to find skills in the CV
        cv_skills = get_cv_skills(cv_text, client)

        st.success(f"✅ CV read — found {len(cv_skills)} skills")

    else:
        st.warning("⚠️ No CV uploaded — using manual skills only")

    # ---- STEP 2: COMBINE SKILLS ----

    # split manual skills by new line
    manual_list = []
    for skill in manual_skills.split("\n"):
        cleaned = skill.strip().lower()
        if cleaned:
            manual_list.append(cleaned)

    # combine CV skills + manual skills
    all_skills = cv_skills + manual_list

    # remove duplicates
    all_skills = list(set(all_skills))

    # stop if no skills at all
    if not all_skills:
        st.error("No skills found. Upload a CV or add skills manually.")
        st.stop()

    # show all skills found
    with st.expander("🧠 Your skills detected"):
        st.write(", ".join(all_skills))

    st.markdown("---")

    # ---- STEP 3: SEARCH JOBS ----

    st.info("🔍 Searching for jobs...")

    # send search request to Serper
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

    # get the results
    results = search_response.json()

    # get just the job listings
    jobs = results.get("organic", [])

    # ---- STEP 4: SCORE EACH JOB ----

    st.info("📊 Matching jobs to your skills...")

    # empty list to store scored jobs
    job_list = []

    # go through each job
    for job in jobs:

        # get job details
        title = job.get("title", "N/A")
        link = job.get("link", "N/A")
        description = job.get("snippet", "N/A")

        # score this job against user skills
        score, matched, job_keywords = score_job(
            title,
            description,
            all_skills
        )

        # save the job with its score
        job_list.append({
            "title": title,
            "link": link,
            "description": description,
            "score": score,
            "matched": ", ".join(matched),
            "job_keywords": ", ".join(job_keywords)
        })

    # turn list into a table
    df_jobs = pd.DataFrame(job_list)

    # sort by score - best first
    df_jobs = df_jobs.sort_values("score", ascending=False)
    df_jobs = df_jobs.reset_index(drop=True)

    # ---- STEP 5: SHOW RESULTS ----

    st.markdown("---")
    st.subheader(f"🎯 {len(df_jobs)} jobs found")

    # show each job
    for i, row in df_jobs.iterrows():

        # pick emoji based on score
        if row["score"] > 50:
            emoji = "🟢"
        elif row["score"] > 20:
            emoji = "🟡"
        else:
            emoji = "🔴"

        # show job in expandable section
        with st.expander(
            emoji + " " + row["title"] + " — " + str(row["score"]) + "% match"
        ):

            st.write("**Description:** " + row["description"])

            st.write("**Skills this job wants:** " + row["job_keywords"])

            st.write("**Your matching skills:** " + row["matched"])

            st.markdown("[View Full Job →](" + row["link"] + ")")

            st.divider()

            # cover letter button for this job
            if st.button("✉️ Generate Cover Letter", key="btn_" + str(i)):

                with st.spinner("✍️ Writing your cover letter..."):

                    # pass client instead of model
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
