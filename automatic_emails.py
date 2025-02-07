import os
import requests
import openai
import pandas as pd
import PyPDF2
import smtplib
import mimetypes
from email.message import EmailMessage
from bs4 import BeautifulSoup

# Load OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise ValueError("❌ ERROR: OPENAI_API_KEY environment variable not set!")

# Function to extract details from resume PDF
def extract_resume_details(pdf_path):
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

    # Extract key details dynamically
    name = None
    university = None
    major = None

    # Extract the first non-empty line as the name (assuming it's at the top)
    for line in text.split("\n"):
        if line.strip():
            name = line.strip()
            break

    # Extract university and major dynamically
    for line in text.split("\n"):
        if "University" in line:
            university = line.strip()
        if "B.S." in line or "Bachelor" in line or "Major" in line:
            major = line.strip()

    # Extract skills, languages, developer tools, and frameworks
    skills = []
    languages = []
    developer_tools = []
    software_frameworks = []

    for line in text.split("\n"):
        if "Languages:" in line:
            languages.extend(line.split(":")[1].strip().split(", "))
        if "Developer Tools:" in line:
            developer_tools.extend(line.split(":")[1].strip().split(", "))
        if "Software/Frameworks:" in line:
            software_frameworks.extend(line.split(":")[1].strip().split(", "))

    # Merge all skills into one list
    skills = list(set(languages + developer_tools + software_frameworks))

    return {
        "name": name if name else "Unknown Name",
        "university": university if university else "Unknown University",
        "major": major if major else "Unknown Major",
        "skills": skills if skills else ["No skills found"],
        "resume_text": text
    }

# Function to generate a personalized email draft using OpenAI GPT-4
def generate_email(user_details, professor_name, university, research_focus):
    prompt = f"""
    Generate a professional email for {user_details['name']}, a student at {user_details['university']} majoring in {user_details['major']}.
    The email should express interest in learning about research opportunities in {research_focus}.
    {user_details['name']} has a background in software development with experience in {', '.join(user_details['skills'])}.
    {user_details['name']} is not familiar with the professor's specific research but is eager to learn.
    The email should be structured as:
    - A polite introduction
    - Expressing interest in the lab's research
    - Mentioning the user's background in CS and software development
    - Asking about potential research opportunities or a meeting
    - Ending with contact information.
    """

    response = openai.chat.completions.create(  # NEW API FORMAT
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI that helps generate professional research inquiry emails."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content


# Function to scrape faculty pages for CS professors
def scrape_professors(university, url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find faculty members (Modify based on website structure)
        professors = []
        for link in soup.find_all("a", href=True):
            if "faculty" in link["href"] or "research" in link["href"]:
                professors.append((link.text.strip(), link["href"]))
        
        return professors
    except Exception as e:
        print(f"❌ Error scraping {university}: {e}")
        return []

# Function to send CSV file via email
def send_email(to_email, csv_filename):
    sender_email = "your-email@gmail.com"  # Replace with your email
    sender_password = "your-password"  # Replace with your Google App Password

    msg = EmailMessage()
    msg["Subject"] = "Your Research Outreach Emails"
    msg["From"] = sender_email
    msg["To"] = to_email
    msg.set_content("Attached is the CSV file containing your generated research outreach emails.")

    # Attach CSV file
    mime_type, _ = mimetypes.guess_type(csv_filename)
    mime_type = mime_type or "application/octet-stream"
    with open(csv_filename, "rb") as f:
        msg.add_attachment(f.read(), maintype=mime_type.split("/")[0], subtype=mime_type.split("/")[1], filename=csv_filename)

    # Send email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)
    
    print(f"📧 CSV file sent to {to_email}!")

# Universities to search (ordered by priority)
universities = [
    ("University of Virginia", "https://engineering.virginia.edu/faculty"),
    ("Virginia Tech", "https://cs.vt.edu/People/Faculty.html"),
    ("George Mason University", "https://cs.gmu.edu/people/"),
    ("George Washington University", "https://www.cs.seas.gwu.edu/faculty"),
    ("Georgetown University", "https://cs.georgetown.edu/people/faculty/")
]

# Ask for resume input and email address
pdf_path = input("Enter the path to your resume PDF: ")
to_email = input("Enter your email address to receive the CSV file: ")

user_details = extract_resume_details(pdf_path)

# Collecting data
all_professors = []
for uni, url in universities:
    print(f"🔎 Scraping {uni}...")
    professors = scrape_professors(uni, url)
    for name, link in professors:
        research_focus = "computer science research"  # Adjust based on available data
        email_draft = generate_email(user_details, name, uni, research_focus)
        all_professors.append([uni, name, link, email_draft])

# Save results to a CSV file
csv_filename = "research_outreach_emails.csv"
df = pd.DataFrame(all_professors, columns=["University", "Professor", "Profile Link", "Email Draft"])
df.to_csv(csv_filename, index=False)

# Send CSV file to user via email
send_email(to_email, csv_filename)