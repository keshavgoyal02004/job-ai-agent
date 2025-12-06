import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jobspy import scrape_jobs
import google.generativeai as genai
from datetime import datetime

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- YASHASHAV'S PROFILE CONTEXT ---
CANDIDATE_PROFILE = """
Name: Yashashav Goyal
Education: B.Tech CSE (CGPA 9.23)
Certifications: RHCSA (Red Hat Certified System Administrator)
Skills: Node.js, Express, MongoDB, Docker, Kubernetes, Linux, DevOps, C++.
"""

def highlight_keywords(text):
    """Highlights specific tech keywords in the text with HTML/CSS"""
    keywords = ["RHCSA", "Linux", "Node.js", "Kubernetes", "Docker", "DevOps", "MongoDB", "Express", "System Admin", "SRE"]
    
    for word in keywords:
        # Case insensitive replacement with a styled span
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        # Light blue background with bold dark blue text
        replacement = f'<span style="background-color: #e3f2fd; color: #0d47a1; font-weight: bold; padding: 0 4px; border-radius: 3px;">{word}</span>'
        text = pattern.sub(replacement, text)
    return text

def search_jobs():
    print("🕵️ Searching for jobs...")
    try:
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term="Node.js Developer OR DevOps Engineer OR SRE Intern",
            location="Delhi, India", 
            results_wanted=15, 
            hours_old=24, 
            country_urlpatterns={"India": "https://in.indeed.com"}
        )
    except Exception as e:
        print(f"Job search failed: {e}")
        return []
    
    target_cities = ["Delhi", "Noida", "Gurgaon", "Gurugram", "Jaipur", "Udaipur"]
    
    filtered_jobs = []
    if not jobs.empty:
        for index, row in jobs.iterrows():
            loc = str(row.get('location', '')).lower()
            if any(city.lower() in loc for city in target_cities):
                filtered_jobs.append(row)
    
    print(f"✅ Found {len(filtered_jobs)} relevant jobs.")
    return filtered_jobs

def analyze_job_fit(job_title, job_desc, company):
    prompt = f"""
    Act as a Technical Recruiter for Yashashav Goyal (RHCSA Certified, Node.js Expert).
    
    Evaluate this role: {job_title} at {company}.
    Description Snippet: {job_desc[:1000]}...

    Output STRICTLY in this format:
    SCORE: [Number 0-100]
    WHY: [One sentence explaining why his RHCSA/Node.js skills match.]
    STRATEGY: [One specific keyword to mention in the cover letter.]
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "SCORE: 0\nWHY: Error analyzing.\nSTRATEGY: N/A"

def parse_analysis(analysis_text):
    """Extracts score and text from the AI response safely"""
    score = 0
    why = "Analysis unavailable"
    strategy = "N/A"
    
    try:
        # Extract Score
        score_match = re.search(r"SCORE:\s*(\d+)", analysis_text)
        if score_match:
            score = int(score_match.group(1))
            
        # Extract Why
        why_match = re.search(r"WHY:\s*(.*)", analysis_text)
        if why_match:
            why = why_match.group(1)

        # Extract Strategy
        strat_match = re.search(r"STRATEGY:\s*(.*)", analysis_text)
        if strat_match:
            strategy = strat_match.group(1)
            
    except Exception:
        pass
        
    return score, why, strategy

def send_daily_email(job_data):
    if not job_data:
        return

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"🚀 Career Agent: {len(job_data)} New Matches ({datetime.now().strftime('%d %b')})"

    # CSS Styles for a modern look
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f8; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; padding: 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            .header {{ background-color: #2c3e50; color: #ffffff; padding: 20px; text-align: center; }}
            .header h2 {{ margin: 0; font-size: 22px; }}
            .content {{ padding: 20px; }}
            .job-card {{ border: 1px solid #e1e4e8; border-radius: 8px; padding: 15px; margin-bottom: 20px; background-color: #fff; }}
            .job-title {{ color: #2c3e50; font-size: 18px; font-weight: bold; margin: 0 0 5px 0; }}
            .company {{ color: #666; font-size: 14px; margin-bottom: 10px; }}
            .score-badge {{ display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; margin-bottom: 10px; }}
            .high-score {{ background-color: #27ae60; }} /* Green */
            .med-score {{ background-color: #f39c12; }} /* Orange */
            .low-score {{ background-color: #c0392b; }} /* Red */
            .analysis-box {{ background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 10px; font-size: 14px; color: #444; margin: 10px 0; }}
            .btn {{ display: block; width: 100%; text-align: center; background-color: #007bff; color: white; padding: 10px 0; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 15px; }}
            .btn:hover {{ background-color: #0056b3; }}
            .footer {{ text-align: center; font-size: 12px; color: #aaa; padding: 20px; background-color: #f4f6f8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Daily Career Opportunities</h2>
                <p style="margin:5px 0 0 0; font-size:14px; opacity:0.8;">Target: North India | DevOps & Node.js</p>
            </div>
            <div class="content">
                <p>Hi Yashashav, found <strong>{len(job_data)}</strong> jobs today matching your RHCSA & Backend profile.</p>
    """

    for job in job_data:
        # Determine Color based on score
        score_class = "low-score"
        if job['score'] >= 85: score_class = "high-score"
        elif job['score'] >= 60: score_class = "med-score"

        # Highlight keywords in the 'Why' section
        highlighted_why = highlight_keywords(job['why'])

        html_body += f"""
        <div class="job-card">
            <div class="score-badge {score_class}">Fit Score: {job['score']}/100</div>
            <h3 class="job-title">{job['title']}</h3>
            <div class="company">🏢 {job['company']} &nbsp;|&nbsp; 📍 {job['location']}</div>
            
            <div class="analysis-box">
                <strong>🤖 AI Analysis:</strong> {highlighted_why}<br><br>
                <strong>🔑 Resume Strategy:</strong> Highlight "{job['strategy']}"
            </div>
            
            <a href="{job['link']}" class="btn">Apply Now 🚀</a>
        </div>
        """

    html_body += """
                <div class="footer">
                    Automated by GitHub Actions • Gemini AI • JobSpy
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("📧 Beautiful email sent!")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def main():
    jobs = search_jobs()
    if not jobs:
        print("No jobs found.")
        return

    processed_jobs = []
    
    # Process top 7 jobs
    for job in jobs[:7]: 
        print(f"🧠 Analyzing {job['company']}...")
        desc = job.get('description', 'No description.')
        raw_analysis = analyze_job_fit(job['title'], desc, job['company'])
        score, why, strategy = parse_analysis(raw_analysis)
        
        processed_jobs.append({
            "title": job['title'],
            "company": job['company'],
            "location": job['location'],
            "link": job['job_url'],
            "score": score,
            "why": why,
            "strategy": strategy
        })

    # Sort: Highest score first
    processed_jobs.sort(key=lambda x: x['score'], reverse=True)
    
    send_daily_email(processed_jobs)

if __name__ == "__main__":
    main()
