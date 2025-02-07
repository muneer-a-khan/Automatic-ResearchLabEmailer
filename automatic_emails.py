import os
import requests
import openai
import pandas as pd
import PyPDF2
import smtplib
import mimetypes
import re
from email.message import EmailMessage
from bs4 import BeautifulSoup


# Load OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")


if not openai.api_key:
   raise ValueError("❌ ERROR: OPENAI_API_KEY environment variable not set!")


# Function to extract details from resume PDF
def extract_resume_details(pdf_path):
   with open(pdf_path, "rb") as file:
       reader = PyPDF2.PdfReader(file)
       text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])


   # Extract key details dynamically
   name, university, major = None, None, None


   # Extract first non-empty line as name
   for line in text.split("\n"):
       if line.strip():
           name = line.strip()
           break


   # Extract university & major dynamically
   for line in text.split("\n"):
       if "University" in line:
           university = line.strip()
       if "B.S." in line or "Bachelor" in line or "Major" in line:
           major = line.strip()


   # Extract skills, languages, tools, frameworks
   skills, languages, developer_tools, frameworks = [], [], [], []


   for line in text.split("\n"):
       if "Languages:" in line:
           languages.extend(line.split(":")[1].strip().split(", "))
       if "Developer Tools:" in line:
           developer_tools.extend(line.split(":")[1].strip().split(", "))
       if "Software/Frameworks:" in line:
           frameworks.extend(line.split(":")[1].strip().split(", "))


   skills = list(set(languages + developer_tools + frameworks))


   return {
       "name": name or "Unknown Name",
       "university": university or "Unknown University",
       "major": major or "Unknown Major",
       "skills": skills or ["No skills found"],
       "resume_text": text
   }


# Function to detect real professors from faculty pages
def is_valid_professor(name):
   """
   Determines if the scraped name is likely to be a real professor.
   Filters out general pages and directories.
   """
   invalid_terms = ["faculty", "staff", "research", "directory", "emeritus", "our", "team"]
   name_lower = name.lower()


   # Exclude names with invalid terms
   if any(term in name_lower for term in invalid_terms):
       return False


   # Acceptable patterns: "Dr. John Doe", "Professor John Doe", "Jane Doe, Ph.D."
   return bool(re.search(r"(Dr\.|Professor|Ph\.D\.|Assistant Professor|Associate Professor|Lecturer)", name))


# Function to scrape only real professors
def scrape_professors(university, directory_url):
   try:
       response = requests.get(directory_url)
       soup = BeautifulSoup(response.text, "html.parser")


       professor_links = []
       for link in soup.find_all("a", href=True):
           url = link["href"]
           text = link.text.strip()


           # Filter potential professor profile links
           if len(text.split()) > 1 and ("faculty" in url or "people" in url or "research" in url):
               full_url = url if url.startswith("http") else directory_url + "/" + url
               professor_links.append(full_url)


       # Visit each professor's page to extract details
       professor_data = []
       for prof_url in professor_links:
           try:
               prof_response = requests.get(prof_url)
               prof_soup = BeautifulSoup(prof_response.text, "html.parser")


               name = prof_soup.find("h1") or prof_soup.find("title")
               name = name.text.strip() if name else None


               # Extract research area
               research_area = None
               for header in prof_soup.find_all(["h2", "h3"]):
                   if "Research" in header.text or "Interests" in header.text:
                       research_area = header.find_next_sibling("p")
                       research_area = research_area.text.strip() if research_area else None
                       break


               if name:
                   professor_data.append((name, prof_url, research_area or "Computer Science Research"))


           except Exception as e:
               print(f"⚠️ Skipped {prof_url} due to error: {e}")


       return professor_data


   except Exception as e:
       print(f"❌ Error scraping {university}: {e}")
       return []


# Function to generate AI-powered email drafts
def generate_email(user_details, professor_name, university, research_focus):
   email_template = f"""
   Dear Professor {professor_name},


   I hope this message finds you well. My name is {user_details['name']}, and I am a Computer Science student at {user_details['university']}.
   I am reaching out because I am interested in learning more about research in {research_focus}.
   While I am not yet familiar with your specific work, I came across your research on {research_focus}, and I would love the opportunity to learn more.


   I have experience working with {', '.join(user_details['skills'])}, which I have used to develop interactive applications and manage structured data.
   Although my background is primarily in software development, I am eager to explore how computational techniques can be applied to {research_focus}.


   Would you be available to discuss potential opportunities to work in your lab?
   I would greatly appreciate the opportunity to learn from your research and explore ways I might contribute.
   Looking forward to your response!


   Best regards,
   {user_details['name']}
   {user_details['university']} | B.S. Computer Science
   Email: {user_details.get('email', 'No email provided')}
   Phone: {user_details.get('phone', 'No phone provided')}
   """
   return email_template


# Function to send the CSV via email
def send_email(to_email, csv_filename):
   sender_email = os.getenv("SENDER_EMAIL")
   sender_password = os.getenv("EMAIL_PASSWORD")


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


# University scraping list (fixed for better accuracy)
universities = [
   ("University of Virginia", "https://engineering.virginia.edu/department/computer-science/faculty"),
   ("Virginia Tech", "https://website.cs.vt.edu/people/faculty.html"),
   ("George Mason University", "https://cec.gmu.edu/about/meet-our-faculty/computer-science-faculty"),
   ("George Washington University", "https://www.cs.seas.gwu.edu/faculty"),
   ("Georgetown University", "https://cs.georgetown.edu/people/faculty/")
]


# User input
pdf_path = input("Enter the path to your resume PDF: ")
to_email = input("Enter your email address to receive the CSV file: ")


user_details = extract_resume_details(pdf_path)


# Collecting data
all_professors = []
for uni, url in universities:
   print(f"🔎 Scraping {uni}...")
   professors = scrape_professors(uni, url)
   for name, link in professors:
       research_focus = "computer science research"
       email_draft = generate_email(user_details, name, uni, research_focus)
       all_professors.append([uni, name, link, email_draft])


# Save results
csv_filename = "research_outreach_emails.csv"
df = pd.DataFrame(all_professors, columns=["University", "Professor", "Profile Link", "Email Draft"])
df.to_csv(csv_filename, index=False)


# Send CSV
send_email(to_email, csv_filename)



