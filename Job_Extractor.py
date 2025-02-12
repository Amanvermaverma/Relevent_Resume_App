import streamlit as st
import zipfile
import os
import pandas as pd
import re
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_groq import ChatGroq
import PyPDF2
import docx

st.title("🥜🔗 Resume Analysis App")

# --- SIDEBAR: YOUR CONTACT DETAILS ---
st.sidebar.title("📌 About the Developer")
st.sidebar.write("**👨‍💻 Aman Verma**")  # Replace with your name
st.sidebar.write("📧 Vermaa188@gmail.com")  # Replace with your email
st.sidebar.write("📞 +91-8299103191")  # Replace with your phone number
st.sidebar.markdown("---")  # Separator


# Sidebar: Usage and Features as a Dropdown
with st.sidebar.expander("📌 Usage & Features", expanded=False):
    st.markdown("### ✨ Features")
    st.markdown("""
    - **Bulk Resume Upload**: Supports PDF, DOCX, and TXT formats.
    - **AI-Powered Scoring**: Uses LLMs (ChatGroq) to evaluate resumes based on job descriptions.
    - **Interactive Dashboard**: Displays resume scores and experience details.
    - **ATS Optimization Check**: Helps in optimizing resumes for Applicant Tracking Systems.
    - **Automated Email Generation**: Option to send interview invitations to top candidates.
    - **CSV Export**: Download resume analysis results for further review.
    """)

    st.markdown("### 🔧 Usage")
    st.markdown("""
    1. **Upload Resumes**: Upload individual or bulk resumes (ZIP file).
    2. **Enter Job Description**: Paste the job description for evaluation.
    3. **Analyze Resumes**: Click the analyze button to score resumes.
    4. **View Results**: Check the candidate rankings and experience breakdown.
    5. **Send Emails (Optional)**: Send an interview invite to the top candidate.
    6. **Download Results**: Export analysis in CSV format.
    """)



# Custom API Key Option
use_custom_key = st.checkbox("Use your own LLM API key?")
if use_custom_key:
    user_api_key = st.text_input("Enter your LLM API key:", type="password")
    groq_api_key = user_api_key
else:
    groq_api_key = st.secrets["GROQ_api_key"]

# File Processing Functions
def extract_pdf_text(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
    return text

def extract_docx_text(docx_file):
    doc = docx.Document(docx_file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_text_file(file):
    return file.read().decode("utf-8")

# Resume Processing
resumes = []

# Option 1: Upload Individual Resume Files
uploaded_files = st.file_uploader("Upload individual resumes (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"],
                                  accept_multiple_files=True)

if uploaded_files:
    for file in uploaded_files:
        file_type = file.name.split(".")[-1].lower()
        if file_type == "pdf":
            text = extract_pdf_text(file)
        elif file_type == "docx":
            text = extract_docx_text(file)
        elif file_type == "txt":
            text = extract_text_file(file)
        else:
            continue
        resumes.append({"file_name": file.name, "text": text})

# Option 2: Upload a ZIP Folder Containing Resumes
uploaded_zip = st.file_uploader("OR Upload a ZIP file containing multiple resumes", type=["zip"])
if uploaded_zip:
    with zipfile.ZipFile(uploaded_zip, "r") as zip_ref:
        zip_ref.extractall("uploaded_resumes")
    for root, dirs, files in os.walk("uploaded_resumes"):
        for file in files:
            file_path = os.path.join(root, file)
            file_type = file.split(".")[-1].lower()
            if file_type == "pdf":
                with open(file_path, "rb") as f:
                    text = extract_pdf_text(f)
            elif file_type == "docx":
                text = extract_docx_text(file_path)
            elif file_type == "txt":
                with open(file_path, "rb") as f:
                    text = extract_text_file(f)
            else:
                continue
            resumes.append({"file_name": file, "text": text})

if resumes:
    st.success(f"Uploaded and extracted {len(resumes)} resumes!")

# Job Description Input
job_description = st.text_area("Paste the job description here", height=150)
company_name = st.text_input("Enter your company name", value="XYZ Pvt Ltd")

# Scoring Function
def score_resume(resume_text, job_description):
    try:
        start_time = time.time()
        llm = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name="mixtral-8x7b-32768")
        prompt = f"""
        Job Description:
        {job_description}

        Resume:
        {resume_text}

        Rate this resume from 0 to 100 based on its relevance to the job description.
        Also, extract:
        - Candidate Name (if available)
        - Total Experience in years
        - Relevant Experience in years

        Provide details in the following format:
        Score: X out of 100
        Total Experience: Y years
        Relevant Experience: Z years
        Reasoning: [Detailed explanation]
        """
        response = llm.invoke(prompt)
        response_content = response.content

        # Extract details using regex
        score_match = re.search(r"(\d{1,3})\s*out\s*of\s*100", response_content)
        score = int(score_match.group(1)) if score_match else "No score found"

        experience_match = re.search(r"Total Experience: (\d+) years", response_content)
        total_experience = int(experience_match.group(1)) if experience_match else "Unknown"

        relevant_exp_match = re.search(r"Relevant Experience: (\d+) years", response_content)
        relevant_experience = int(relevant_exp_match.group(1)) if relevant_exp_match else "Unknown"

        reasoning_start = response_content.find("Reasoning:")
        reasoning = response_content[reasoning_start:].strip() if reasoning_start != -1 else "No reasoning provided"

        end_time = time.time()
        return score, total_experience, relevant_experience, reasoning, round(end_time - start_time, 2)
    except Exception as e:
        st.error(f"Error scoring resume: {e}")
        return "Error", "Error", "Error", "Error", "Error"

# Analyze Resumes
if st.button("Analyze Resumes"):
    if not job_description:
        st.error("Please paste a job description before analyzing!")
    else:
        results = []
        for resume in resumes:
            score, total_exp, relevant_exp, reasoning, processing_time = score_resume(resume["text"], job_description)
            candidate_name = re.search(r"Name: (.*?)\\n", resume["text"])
            candidate_name = candidate_name.group(1) if candidate_name else resume["file_name"]
            results.append({
                "Candidate Name": candidate_name,
                "Total Experience (Years)": total_exp,
                "Relevant Experience (Matches)": relevant_exp,
                "Score": score,
                "Relevance": reasoning,
                "Processing Time (Seconds)": processing_time
            })

        results_df = pd.DataFrame(results)
        st.subheader("Analysis Results")
        st.dataframe(results_df)

        st.subheader("Resume Score Visualization")
        valid_scores_df = results_df[results_df["Score"].apply(lambda x: isinstance(x, int))]
        if not valid_scores_df.empty:
            st.bar_chart(data=valid_scores_df.set_index("Candidate Name")["Score"])
        else:
            st.warning("No valid numeric scores to display in the chart.")

        st.download_button(
            "Download Results",
            data=results_df.to_csv(index=False),
            file_name="resume_analysis_report.csv",
            mime="text/csv",
        )

        # Email Option
        send_email = st.checkbox("Send Interview Invitation to Top Candidate?")
        if send_email and not results_df.empty:
            top_candidate = results_df.iloc[0]
            recipient_email = st.text_input("Enter candidate's email:")
            if st.button("Send Email"):
                sender_email = "your_email@example.com"
                sender_password = "your_password"

                msg = MIMEMultipart()
                msg["From"] = sender_email
                msg["To"] = recipient_email
                msg["Subject"] = f"Interview Invitation - {job_description}"

                email_body = f"""
                Dear {top_candidate['Candidate Name']},

                We were impressed with your profile and would like to invite you for an interview for the {job_description} position at {company_name}.

                Please let us know your availability for the interview. Looking forward to your response!

                Best regards,  
                HR Team, {company_name}
                """
                msg.attach(MIMEText(email_body, "plain"))

                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)

                st.success(f"Email sent to {recipient_email}!")
