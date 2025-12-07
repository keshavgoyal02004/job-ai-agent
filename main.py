import os
import smtplib
import re
import time
import pandas as pd
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

# --- SMART MODEL SELECTION ---
def get_best_model():
    """
    Asks Google API which models are available to this specific API Key
    and selects the best one to avoid 404 errors.
    """
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY missing.")
        return None

    genai.configure(api_key=GEMINI_API_KEY)
    
    try:
        print("🤖 Querying available AI models...")
        available_models = []
        # List all models your key can access
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"   Authorized Models: {available_models}")

        # Strategy: Prefer Flash (Fast/Free) -> Pro (Standard) -> Any
        selected_name = None
        
        # 1. Look for Flash
        for m in available_models:
            if 'flash' in m and '1.5' in m:
                selected_name = m
                break
        
        # 2. Look for Pro if Flash not found
        if not selected_name:
            for m in available_models:
                if 'pro' in m and '1.5' in m:
                    selected_name = m
                    break
        
        # 3. Fallback to whatever is first
        if not selected_name and available_models:
            selected_name = available_models[0]
            
        if selected_name:
            print(f"✅ Selected Model: {selected_name}")
            return genai.GenerativeModel(selected_name)
        else:
            print("❌ No text-generation models found for this API Key.")
            return None

    except Exception as e:
        print(f"⚠️ specific model detection failed: {e}")
        # Last resort fallback
        return genai.GenerativeModel('gemini-pro')

# Initialize the model dynamically
model = get_best_model()

def highlight_keywords(text):
    """Highlights specific tech keywords in the text with HTML/CSS"""
    keywords = ["RHCSA", "Linux", "Node.js", "Kubernetes", "Docker", "DevOps", "MongoDB", "Express", "System Admin", "SRE", "Python", "AWS", "CI/CD"]
    if not text: return ""
    for word in keywords:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        replacement = f'<span style="background-color: #e3f2fd; color: #0d47a1; font-weight: bold; padding: 0 4px; border-radius: 3px;">{word}</span>'
        text = pattern.sub(replacement, text)
    return text

def search_jobs():
    print("🕵️ Searching for jobs (LinkedIn & Indeed)...")
    try:
        # Removed Glassdoor to prevent Error 400
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed"], 
            search_term="Node.js Developer OR DevOps Engineer OR SRE Intern",
            location="Delhi, India", 
            results_wanted=20, 
            hours_old=24, 
            country_urlpatterns={"India": "https://in.indeed.com"}
        )
    except Exception as e:
        print(f"Job search error: {e}")
        return []
    
    target_cities = ["Delhi", "Noida", "Gurgaon", "Gurugram", "Jaipur", "Udaipur"]
    
    unique_jobs = []
    seen_ids = set()
    
    if hasattr(jobs, 'empty') and not jobs.empty:
        job_list = jobs.to_dict('records')
        
        for job in job_list:
            # 1. Location Filter
            loc = str(job.get('location', '')).lower()
            if not any(city.lower() in loc for city in target_cities):
                continue

            # 2. Deduplication (URL or Title+Company)
            job_id = job.get('job_url') or f"{job.get('title')}{job.get('company')}"
            
            if job_id in seen_ids:
                continue
            
            seen_ids.add(job_id)
            unique_jobs.append(job)
    
    print(f"✅ Found {len(unique_jobs)} UNIQUE relevant jobs.")
    return unique_jobs

def analyze_job_fit(job_title, job_desc, company):
    if not model: return "SCORE: 0\nWHY: AI Config Error.\nSTRATEGY: N/A"
    
    if pd.isna(job_desc) or job_desc is None: job_desc = "No description."
    else: job_desc = str(job_desc)
        
    prompt = f"""
    Act as a Technical Recruiter for Yashashav Goyal (RHCSA Certified, Node.js Expert).
    Evaluate: {job_title} at {company}.
    Snippet: {job_desc[:800]}...

    Format:
    SCORE: [0-100]
    WHY: [1 sentence on fit]
    STRATEGY: [1 keyword to highlight]
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # If we hit a rate limit, return a default so the email still sends
        print(f"⚠️ AI Analysis Error: {e}")
        return "SCORE: 50\nWHY: AI unavailable (Error).\nSTRATEGY: Check manually."

def parse_analysis(text):
    score, why, strategy = 0, "Check link manually.", "N/A"
    if not text: return score, why, strategy
    try:
        s = re.search(r"SCORE:\s*(\d+)", text)
        if s: score = int(s.group(1))
        w = re.search(r"WHY:\s*(.*)", text)
        if w: why = w.group(1)
        st = re.search(r"STRATEGY:\s*(.*)", text)
        if st: strategy = st.group(1)
    except: pass
    return score, why, strategy

def send_daily_email(job_data):
    if not job_data: return

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"🚀 Top {len(job_data)} Job Picks: {datetime.now().strftime('%d %b')}"

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f4f6f8; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
            .job-card {{ border: 1px solid #ddd; padding: 15px; margin: 20px; border-radius: 8px; }}
            .title {{ color: #2c3e50; font-size: 18px; font-weight: bold; }}
            .meta {{ color: #666; font-size: 14px; margin-bottom: 10px; }}
            .badge {{ padding: 3px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 12px; }}
            .high {{ background: #27ae60; }} .med {{ background: #f39c12; }} .low {{ background: #c0392b; }}
            .analysis {{ background: #f8f9fa; border-left: 4px solid #007bff; padding: 10px; margin: 10px 0; font-size: 14px; }}
            .btn {{ display: block; background: #007bff; color: white; text-align: center; padding: 10px; text-decoration: none; border-radius: 5px; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h2>Daily Job Matches</h2></div>
    """

    for job in job_data:
        color = "low"
        if job['score'] >= 80: color = "high"
        elif job['score'] >= 50: color = "med"
        
        html_body += f"""
        <div class="job-card">
            <span class="badge {color}">Fit: {job['score']}%</span>
            <div class="title">{job['title']}</div>
            <div class="meta">{job['company']} | {job['location']}</div>
            <div class="analysis">
                <b>AI:</b> {highlight_keywords(job['why'])}<br>
                <b>Tip:</b> Focus on "{job['strategy']}"
            </div>
            <a href="{job['link']}" class="btn">Apply Now</a>
        </div>
        """
        
    html_body += "</div></body></html>"
    msg.attach(MIMEText(html_body, 'html'))

    try:
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(SENDER_EMAIL, EMAIL_PASSWORD)
        s.send_message(msg)
        s.quit()
        print("📧 Email Sent Successfully!")
    except Exception as e:
        print(f"❌ Mail Error: {e}")

def main():
    jobs = search_jobs()
    if not jobs:
        print("No jobs found.")
        return

    analyzed = []
    
    # Analyze max 5 jobs
    for i, job in enumerate(jobs[:5]):
        print(f"[{i+1}/5] Processing: {job['company']}")
        
        desc = str(job.get('description', ''))
        raw = analyze_job_fit(job['title'], desc, job['company'])
        s, w, strat = parse_analysis(raw)
        
        analyzed.append({
            "title": job.get('title', 'Unknown Role'),
            "company": job.get('company', 'Unknown Co'),
            "location": job.get('location', 'India'),
            "link": job.get('job_url', '#'),
            "score": s, "why": w, "strategy": strat
        })

        # CRITICAL: 4-second delay to prevent quota errors
        time.sleep(4)

    # Sort by score descending
    analyzed.sort(key=lambda x: x['score'], reverse=True)
    send_daily_email(analyzed)

if __name__ == "__main__":
    main()
