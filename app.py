import streamlit as st
import requests
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="AI Job Search Agent", layout="wide", page_icon="🤖")

st.title("🤖 AI Job Search Agent")
st.markdown("**Finds graduate data jobs, scores them against your skills, and writes cover letters automatically**")
st.markdown("---")

# ---- SIDEBAR — user inputs ----
st.sidebar.header("⚙️ Your Details")

job_title = st.sidebar.text_input("Job title to search", value="Data Analyst")
location = st.sidebar.text_input("Location", value="London")
skills_input = st.sidebar.text_area(
    "Your skills (one per line)",
    value="python\nmachine learning\nnlp\nsql\npower bi\ndata analysis\nanalytics\ngraduate"
)
serper_key = st.sidebar.text_input("Serper API Key", type="password")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password")
search_btn = st.sidebar.button("🔍 Find Jobs")

# ---- MAIN LOGIC ----
if search_btn:
    if not serper_key or not gemini_key:
        st.error("Please enter both API keys in the sidebar")
    else:
        # parse skills
        MY_SKILLS = [s.strip().lower() for s in skills_input.split('\n') if s.strip()]

        # configure gemini
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        # search jobs
        with st.spinner("🔍 Searching for jobs..."):
            response = requests.post(
                "https://google.serper.dev/search",
                json={
                    "q": f"{job_title} jobs {location} entry level graduate 2026",
                    "num": 10,
                    "gl": "uk"
                },
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"}
            )
            results = response.json()
            jobs = results.get('organic', [])

        # build dataframe
        job_list = []
        for job in jobs:
            job_list.append({
                "title": job.get("title", "N/A"),
                "link": job.get("link", "N/A"),
                "snippet": job.get("snippet", "N/A"),
            })
        df_jobs = pd.DataFrame(job_list)

        # score jobs
        with st.spinner("📊 Scoring jobs against your skills..."):
            for i, row in df_jobs.iterrows():
                full_text = (row['title'] + " " + row['snippet']).lower()
                matches = [s for s in MY_SKILLS if s in full_text]
                score = round((len(matches) / len(MY_SKILLS)) * 100)
                df_jobs.at[i, 'match_score'] = score
                df_jobs.at[i, 'matched_skills'] = ", ".join(matches)

            df_jobs = df_jobs.sort_values('match_score', ascending=False).reset_index(drop=True)

        # show results
        st.subheader(f"🎯 Found {len(df_jobs)} jobs — ranked by match score")

        for i, row in df_jobs.iterrows():
            with st.expander(f"{'🟢' if row['match_score'] > 10 else '🟡'} {row['title']} — {row['match_score']}% match"):
                st.markdown(f"**Link:** [{row['link']}]({row['link']})")
                st.markdown(f"**Description:** {row['snippet']}")
                st.markdown(f"**Skills matched:** `{row['matched_skills']}`")

                # generate cover letter on demand
                if st.button(f"✉️ Generate Cover Letter", key=f"btn_{i}"):
                    with st.spinner("Writing cover letter..."):
                        prompt = f"""
                        Write a short professional cover letter for:
                        Job: {row['title']}
                        Description: {row['snippet']}
                        
                        Applicant:
                        - Name: Mithun Surriya KS
                        - Degree: BSc AI and Data Science, UEL, 89%
                        - Dissertation: AI tourism chatbot, 91%
                        - Projects: London deprivation analyser (R² 0.897), Berlin deprivation analysis (R² 0.97), YouTube sentiment dashboard
                        - Skills: Python, ML, NLP, SQL, Power BI, Streamlit, SHAP
                        - Right to work: Graduate Route Visa
                        
                        3 paragraphs, professional but warm tone.
                        """
                        response = model.generate_content(prompt)
                        st.text_area("Your cover letter:", response.text, height=300)
