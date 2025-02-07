import os
import requests
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
import pandas as pd
import PyPDF2
import smtplib
import mimetypes
import re
import time
from email.message import EmailMessage
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Load OpenAI API key securely
if not openai.api_key:
    raise ValueError("ERROR: OPENAI_API_KEY environment variable not set!")

def extract_resume_details(pdf_path):
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

        # More robust extraction using regex patterns
        name_pattern = r"^([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)"
        university_pattern = r"(?:University|College|Institute)[^,\n]*"
        major_pattern = r"(?:B\.S\.|Bachelor).*?(?:Computer Science|CS|Software Engineering|Computing)[^,\n]*"

        name = re.search(name_pattern, text, re.MULTILINE)
        university = re.search(university_pattern, text)
        major = re.search(major_pattern, text)

        # Extract skills more comprehensively
        skills_section = re.search(r"(?:Skills|Technologies|Technical Skills):(.+?)(?:\n\n|\Z)", text, re.DOTALL)
        skills = []
        if skills_section:
            skills = [skill.strip() for skill in re.split(r'[,|•]', skills_section.group(1)) if skill.strip()]

        return {
            "name": name.group(1) if name else "Unknown Name",
            "university": university.group(0) if university else "Unknown University",
            "major": major.group(0) if major else "Computer Science",
            "skills": skills or ["Programming", "Data Structures", "Algorithms"],
            "resume_text": text
        }
    except Exception as e:
        print(f"❌ Error extracting resume details: {e}")
        return {
            "name": "Unknown Name",
            "university": "Unknown University",
            "major": "Computer Science",
            "skills": ["Programming", "Data Structures", "Algorithms"],
            "resume_text": ""
        }

def is_valid_professor(name, link):
    # More lenient validation
    if not name or not link:
        return False

    name_lower = name.lower()
    invalid_patterns = [
        r'/directory/?$', 
        r'/faculty/?$',
        r'/staff/?$',
        r'404',
        r'not[-\s]found'
    ]

    if any(re.search(pattern, link.lower()) for pattern in invalid_patterns):
        return False

    valid_titles = [
        "professor",
        "faculty",
        "assistant",
        "associate",
        "lecturer",
        "researcher",
        "ph.d"
    ]

    return any(title in name_lower for title in valid_titles)

def scrape_professors(university, directory_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(directory_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        professor_links = set()

        # University-specific scraping logic
        if "gmu.edu" in directory_url:
            for prof in soup.find_all("div", class_="faculty-member"):
                name_elem = prof.find(["h3", "h4", "strong"])
                link_elem = prof.find("a", href=True)

                if name_elem and link_elem:
                    name = name_elem.text.strip()
                    link = urljoin(directory_url, link_elem["href"])
                    if is_valid_professor(name, link):
                        professor_links.add((name, link))

        elif "vt.edu" in directory_url:
            for prof in soup.find_all("div", class_=["views-row", "person-teaser"]):
                name_elem = prof.find(["h2", "h3", "strong"])
                link_elem = prof.find("a", href=True)

                if name_elem and link_elem:
                    name = name_elem.text.strip()
                    link = urljoin(directory_url, link_elem["href"])
                    if is_valid_professor(name, link):
                        professor_links.add((name, link))

        elif "virginia.edu" in directory_url:
            for prof in soup.find_all(["div", "li"], class_=["person", "faculty-staff-item"]):
                name_elem = prof.find(["h3", "h4", "strong"])
                link_elem = prof.find("a", href=True)

                if name_elem and link_elem:
                    name = name_elem.text.strip()
                    link = urljoin(directory_url, link_elem["href"])
                    if is_valid_professor(name, link):
                        professor_links.add((name, link))

        else:
            # Generic fallback scraping
            for link in soup.find_all("a", href=True):
                name = link.text.strip()
                url = urljoin(directory_url, link["href"])
                if is_valid_professor(name, url):
                    professor_links.add((name, url))

        # Process each professor's page
        professor_data = []
        for name, prof_url in professor_links:
            try:
                print(f"Scraping profile for: {name}")
                prof_response = requests.get(prof_url, headers=headers, timeout=20)
                prof_soup = BeautifulSoup(prof_response.text, "html.parser")

                # Extract research interests
                research_area = None
                research_keywords = ["research", "interests", "areas", "expertise"]

                # Look for research information in various elements
                for keyword in research_keywords:
                    # Try headers first
                    for header in prof_soup.find_all(["h2", "h3", "h4"]):
                        if keyword.lower() in header.text.lower():
                            next_elem = header.find_next_sibling(["p", "div", "ul"])
                            if next_elem:
                                research_area = next_elem.text.strip()
                                break

                    if not research_area:
                        # Try looking for sections with research-related class names
                        research_section = prof_soup.find(class_=re.compile(f".*{keyword}.*", re.I))
                        if research_section:
                            research_area = research_section.text.strip()

                # If no research area found, use OpenAI to analyze the page content
                if not research_area:
                    page_text = prof_soup.get_text()[:5000]  # First 5000 characters
                    response = client.chat.completions.create(model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Extract the main research areas and interests from this professor's webpage. If none are explicitly stated, identify the likely research focus based on the content."},
                        {"role": "user", "content": page_text}
                    ])
                    research_area = response.choices[0].message.content.strip()

                if research_area:
                    professor_data.append((name, prof_url, research_area))
                    # Add delay to avoid rate limiting
                    time.sleep(1)

            except Exception as e:
                print(f"Error processing {prof_url}: {e}")
                continue

        return professor_data

    except Exception as e:
        print(f"Error scraping {university}: {e}")
        return []

def generate_email(user_details, professor_name, university, research_focus):
    try:
        skills_text = ", ".join(user_details["skills"][:3])  # Use top 3 skills

        # Clean and format research focus
        research_focus = research_focus.strip()
        if len(research_focus) > 100:
            research_focus = research_focus[:100].rsplit(' ', 1)[0] + "..."

        email_template = f"""Dear Professor {professor_name},

I hope this message finds you well. My name is {user_details['name']}, and I am a Computer Science student at {user_details['university']}. I am reaching out because I am particularly interested in your research on {research_focus}.

My technical background includes experience with {skills_text}, and I am eager to apply these skills to research problems in your area of expertise. I am especially interested in understanding how these technologies can be applied to advance your current research projects.

Would you be available for a brief meeting to discuss potential research opportunities in your lab? I would greatly appreciate the chance to learn more about your work and explore ways I might contribute to your research goals.

Thank you for your time and consideration.

Best regards,
{user_details['name']}
{user_details['university']} | {user_details['major']}
"""
        return email_template

    except Exception as e:
        print(f"Error generating email: {e}")
        return "Error generating email template"

def send_email(to_email, csv_filename):
    try:
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("EMAIL_PASSWORD")

        if not sender_email or not sender_password:
            raise ValueError("Email credentials not set in environment variables!")

        msg = EmailMessage()
        msg["Subject"] = "Research Outreach Emails"
        msg["From"] = sender_email
        msg["To"] = to_email
        msg.set_content("Attached is your generated research outreach emails CSV file.")

        with open(csv_filename, "rb") as f:
            file_data = f.read()
            msg.add_attachment(file_data, maintype="application", subtype="csv", filename=csv_filename)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)

        print(f" CSV file successfully sent to {to_email}")

    except Exception as e:
        print(f" Error sending email: {e}")

def main():
    # University directories
    universities = [
        ("George Mason University", "https://cs.gmu.edu/directory/by-category/faculty/"),
        ("Virginia Tech", "https://cs.vt.edu/people/faculty.html"),
        ("University of Virginia", "https://engineering.virginia.edu/department/computer-science/faculty"),
        ("George Washington University", "https://www.cs.seas.gwu.edu/faculty"),
        ("Georgetown University", "https://cs.georgetown.edu/people/faculty/")
    ]

    try:
        # Get user inputs
        pdf_path = input("Enter the path to your resume PDF: ").strip()
        to_email = input("Enter your email address: ").strip()

        # Validate inputs
        if not os.path.exists(pdf_path):
            raise ValueError(f"Resume file not found: {pdf_path}")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", to_email):
            raise ValueError(f"Invalid email address: {to_email}")

        # Extract resume details
        print("Extracting resume details...")
        user_details = extract_resume_details(pdf_path)

        # Scrape professor data
        all_professors = []
        for uni, url in universities:
            print(f"\n Scraping {uni}...")
            professors = scrape_professors(uni, url)
            print(f"Found {len(professors)} professors at {uni}")

            for name, link, research_focus in professors:
                email_draft = generate_email(user_details, name, uni, research_focus)
                all_professors.append([uni, name, link, research_focus, email_draft])

        # Save to CSV
        if all_professors:
            csv_filename = "research_outreach_emails.csv"
            df = pd.DataFrame(all_professors, columns=[
                "University", 
                "Professor", 
                "Profile Link", 
                "Research Focus", 
                "Email Draft"
            ])
            df.to_csv(csv_filename, index=False, encoding='utf-8')
            print(f"\n Generated {len(all_professors)} email drafts")

            # Send email with CSV
            send_email(to_email, csv_filename)
        else:
            print("\n⚠️ No professor data was collected. Please check the university URLs and try again.")

    except Exception as e:
        print(f"\n Error in main execution: {e}")

if __name__ == "__main__":
    main()