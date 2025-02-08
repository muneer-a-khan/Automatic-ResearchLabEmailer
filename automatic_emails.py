import os
import requests
import pandas as pd
import PyPDF2
import json
import time
import smtplib
import re
from openai import OpenAI
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, List, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    raise ValueError("OpenAI API key not found in environment variables")

# Common programming languages and frameworks for better skill extraction
TECH_KEYWORDS = {
    'languages': [
        'Python', 'Java', 'C++', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'C#',
        'Ruby', 'Swift', 'Kotlin', 'R', 'MATLAB', 'SQLite', 'PostgreSQL', 'NoSQL', 'SQL', 'PHP', 'Scala', 'Perl',
        'Assembly', 'Julia', 'Haskell', 'OCaml'
    ],
    'frameworks': [
        'TensorFlow', 'PyTorch', 'React', 'Angular', 'Vue.js', 'Express', 'Next.js', 'Django', 'Flask',
        'Spring', 'Node.js', '.NET', 'pandas', 'scikit-learn', 'NumPy', 'Keras',
        'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'Git', 'Unity', 'OpenGL'
    ]
}

def test_faculty_scraping(url: str, headers: Dict[str, str]) -> None:
    """Test faculty directory scraping for a given URL."""
    print(f"\nTesting scraping for: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Successfully accessed page (Status: {response.status_code})")
        print(f"Content type: {response.headers.get('content-type', 'unknown')}")
        print(f"Content length: {len(response.text)} characters")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Print some basic page information
        print("\nPage Information:")
        print(f"Title: {soup.title.string if soup.title else 'No title'}")
        print(f"Number of links: {len(soup.find_all('a'))}")
        print(f"Number of faculty-related links: {len(soup.find_all('a', href=re.compile('faculty|profile|directory')))}")
        
        # Try different common faculty selectors
        selectors = [
            'div.faculty-member',
            'div.person',
            'div.directory-item',
            '.views-row',
            '.faculty-listing',
            '.directory-listing'
        ]
        
        print("\nTesting common faculty selectors:")
        for selector in selectors:
            elements = soup.select(selector)
            print(f"{selector}: {len(elements)} elements found")
            
            if elements:
                print(f"Sample element classes: {elements[0].get('class', 'No class')}")
                
        # Save the HTML for inspection
        with open('faculty_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("\nSaved HTML to 'faculty_page.html' for inspection")
        
    except Exception as e:
        print(f"Error testing faculty scraping: {e}")

def extract_user_details(pdf_text: str) -> Dict[str, str]:
    """Extract user details from resume using GPT-4."""
    try:
        prompt = f"""
        Extract the following information from this resume:
        1. Full Name
        2. University Name
        3. Major/Degree Program
        4. Email Address (if present)
        5. Expected Graduation Year

        Resume text:
        {pdf_text[:2000]}

        Return the response in this exact JSON format:
        {{
            "name": "Full Name",
            "university": "University Name",
            "major": "Major/Degree",
            "email": "email@example.com",
            "graduation_year": "202X"
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a precise information extraction specialist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )

        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error extracting user details: {e}")
        return {
            "name": "Unknown",
            "university": "Unknown University",
            "major": "Computer Science",
            "email": "",
            "graduation_year": ""
        }

def extract_technical_skills(pdf_text: str) -> Dict[str, List[str]]:
    """Extract programming languages and technical frameworks from resume."""
    try:
        prompt = f"""
        Extract ONLY programming languages and technical frameworks/tools from this resume text.
        Categorize them as either 'languages' or 'frameworks'.
        Include only items that match common programming technologies.
        
        Resume text:
        {pdf_text[:2000]}
        
        Return the response in this exact JSON format:
        {{
            "languages": ["lang1", "lang2"],
            "frameworks": ["framework1", "framework2"]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a technical skill extraction specialist. Extract only verifiable technical skills."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        skills = json.loads(response.choices[0].message.content)
        
        # Validate against known tech keywords
        validated_skills = {
            'languages': [lang for lang in skills['languages'] if lang in TECH_KEYWORDS['languages']],
            'frameworks': [fw for fw in skills['frameworks'] if fw in TECH_KEYWORDS['frameworks']]
        }
        
        return validated_skills
    except Exception as e:
        print(f"Error extracting skills: {e}")
        return {'languages': [], 'frameworks': []}

class AIResearchParser:
    def __init__(self):
        self.research_cache = {}
        
    def extract_research_focus(self, page_content: str, professor_name: str) -> str:
        """Use GPT-4 to extract and summarize research focus from page content."""
        try:
            prompt = f"""
            Extract the main research areas and interests of Professor {professor_name} from their webpage.
            Follow these rules:
            1. Focus on specific technical areas (e.g., "machine learning for computer vision" rather than just "AI")
            2. Include methodologies and applications
            3. Aim for 2-3 main research areas
            4. If multiple areas, separate with semicolons
            5. Keep total length under 100 words
            6. Be specific about subfields
            
            Webpage content:
            {page_content[:2000]}
            """
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a research area extraction specialist. Extract and summarize research focuses accurately and concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error extracting research focus: {e}")
            return "Research areas could not be extracted"

def scrape_professor_page(url: str, headers: Dict[str, str]) -> str:
    """Scrape and clean professor's webpage content."""
    try:
        print(f"\nAttempting to scrape: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        print(f"Successfully fetched page (Status: {response.status_code})")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Print page title
        page_title = soup.title.string if soup.title else "No title found"
        print(f"Page title: {page_title}")
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
            
        # Get text content
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        print(f"Extracted {len(text)} characters of content")
        return text
    except Exception as e:
        print(f"Error scraping professor page: {e}")
        return ""

def generate_personalized_email(user_details: Dict, professor_details: Dict) -> str:
    """Generate a highly personalized email based on research alignment."""
    try:
        prompt = f"""
        Generate a personalized email to Professor {professor_details['name']} using this template:
        
        Context:
        - Student: {user_details['name']} from {user_details['university']}
        - Major: {user_details['major']}
        - Expected Graduation: {user_details.get('graduation_year', 'Not specified')}
        - Programming Languages: {', '.join(user_details['skills']['languages'])}
        - Technical Frameworks: {', '.join(user_details['skills']['frameworks'])}
        - Professor's Research: {professor_details['research']}
        
        Rules:
        1. Mention 1-2 specific aspects of the professor's research
        2. Connect student's technical skills to the research area
        3. Be concise but specific
        4. Show genuine interest in the research topic
        5. Keep it under 200 words
        6. Make it clear why this specific professor's research is interesting
        7. Include student's graduation year if available
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert at writing personalized academic emails that demonstrate genuine interest in a professor's research lab for potential mentoring."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating email: {e}")
        return "Error generating email"

def send_email(to_email: str, csv_filename: str) -> bool:
    """Send CSV file via email."""
    try:
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("EMAIL_PASSWORD")

        if not sender_email or not sender_password:
            raise ValueError("Email credentials not found in environment variables")

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "Research Outreach Emails"

        body = """
        Hello,

        Attached is your CSV file containing professor research areas and personalized email drafts.
        
        The CSV includes:
        - University name
        - Professor name and profile link
        - Research focus areas
        - Personalized email draft
        
        Best regards,
        Research Outreach Assistant
        """

        msg.attach(MIMEText(body, 'plain'))

        # Attach CSV file
        with open(csv_filename, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(csv_filename)}'
            )
            msg.attach(part)

        # Send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)

        print(f"CSV file successfully sent to {to_email}")
        return True

    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def clean_faculty_data(name: str, url: str) -> Tuple[str, str]:
    """Clean and validate faculty data."""
    if name:
        # Remove common titles and clean whitespace
        name = re.sub(r'^(Dr\.|Professor|Prof\.|Mr\.|Mrs\.|Ms\.)\s+', '', name.strip())
        name = re.sub(r'\s+', ' ', name)
        
    if url:
        # Ensure URL is absolute and clean
        if not url.startswith(('http://', 'https://')):
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                base_url = 'https://' + url.split('/')[2]
                url = urljoin(base_url, url)
                
    return name, url

def scrape_with_retry(url: str, headers: Dict[str, str], max_retries: int = 3) -> str:
    """Scrape a URL with retry logic."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print(f"Failed to fetch {url} after {max_retries} attempts")
                return ""


def print_page_structure(soup: BeautifulSoup, university: str):
    """Print detailed HTML structure for debugging."""
    print(f"\nAnalyzing {university} page structure:")
    
    # Print all div classes
    print("\nFound div classes:")
    div_classes = set()
    for div in soup.find_all('div', class_=True):
        div_classes.update(div['class'])
    for class_name in sorted(div_classes):
        print(f"- {class_name}")
    
    # Print all link patterns
    print("\nFound link patterns:")
    link_patterns = set()
    for link in soup.find_all('a', href=True):
        if 'faculty' in link['href'] or 'profile' in link['href'] or 'people' in link['href']:
            link_patterns.add(link['href'][:50] + '...' if len(link['href']) > 50 else link['href'])
    for pattern in sorted(link_patterns):
        print(f"- {pattern}")


def validate_faculty_page(soup: BeautifulSoup, university: str) -> bool:
        """Validate that we've successfully accessed a faculty page."""
        # Check for common error indicators
        error_texts = ['not found', 'error', 'access denied', 'forbidden']
        page_text = soup.get_text().lower()
        
        if any(error in page_text for error in error_texts):
            print(f"Warning: Possible error page detected for {university}")
            return False
            
        # Check for minimum content
        if len(soup.get_text().strip()) < 1000:  # Arbitrary minimum length
            print(f"Warning: Page content seems too short for {university}")
            return False
            
        return True

def debug_faculty_links(soup: BeautifulSoup, university: str):
    """Debug helper to find faculty links."""
    print(f"\nDebugging {university} faculty links:")
    
    # For Virginia Tech
    if 'vt.edu' in university.lower():
        faculty_links = soup.find_all('a', href=lambda x: x and '/people/faculty/' in x)
        print(f"Found {len(faculty_links)} VT faculty links")
        for link in faculty_links[:5]:  # Show first 5 as sample
            print(f"- {link.text.strip()}: {link['href']}")
    
    # For UVA
    elif 'virginia.edu' in university.lower():
        faculty_links = soup.find_all('a', href=lambda x: x and '/faculty/' in x)
        print(f"Found {len(faculty_links)} UVA faculty links")
        for link in faculty_links[:5]:  # Show first 5 as sample
            print(f"- {link.text.strip()}: {link['href']}")

def process_vt_faculty(element: BeautifulSoup) -> Tuple[str, str]:
    """Special processor for Virginia Tech faculty elements."""
    if element.name == 'a' and element.has_attr('href'):
        # Extract name from URL, converting-dashes-to-spaces and removing suffix
        name = element['href'].split('/')[-1].replace('.html', '').replace('-', ' ').title()
        url = urljoin('https://cs.vt.edu', element['href'])
        return name, url
    return None, None

class UniversityScraperFactory:
    @staticmethod
    def create_scraper(university_domain: str) -> dict:
        """Create university-specific scraping rules."""
        scrapers = {
            'gmu.edu': {  # Keep GMU rules as they work well
                'faculty_selector': '.directory-listing .views-row',
                'name_selector': '.field-name-title',
                'link_selector': '.field-name-title a'
            },
            'vt.edu': {  # Updated VT rules based on the actual link pattern
                'faculty_selector': 'a[href*="/people/faculty/"]',  # Find all faculty links directly
                'name_selector': None,  # extract name from the link text
                'link_selector': None   # already have the link from faculty_selector
            },
            'virginia.edu': {  # This works now
                'faculty_selector': '.people_list_item',
                'name_selector': '.people_list_item_header',
                'link_selector': 'a[href*="/faculty/"]'
            }
        }
        
        return scrapers.get(university_domain, {
            'faculty_selector': [
                '.directory-listing .views-row',
                '.people_list_item',
                'a[href*="/people/faculty/"]'
            ],
            'name_selector': [
                '.field-name-title',
                '.people_list_item_header',
                None
            ],
            'link_selector': [
                'a[href*="faculty"]',
                'a[href*="/faculty/"]',
                None
            ]
        })

    


def main():
    # Initialize components
    research_parser = AIResearchParser()
    
    # Headers for requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }
    
    # Get user inputs
    pdf_path = input("Enter path to your resume PDF: ").strip()
    to_email = input("Enter your email address to receive the CSV: ").strip()
    
    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", to_email):
        raise ValueError("Invalid email address format")
    
    # Read resume
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        resume_text = ' '.join(page.extract_text() for page in pdf_reader.pages)
    
    # Extract user details and technical skills
    print("\nExtracting details from resume...")
    user_details = extract_user_details(resume_text)
    user_skills = extract_technical_skills(resume_text)
    user_details['skills'] = user_skills

    print(f"\nExtracted details:")
    print(f"Name: {user_details['name']}")
    print(f"University: {user_details['university']}")
    print(f"Major: {user_details['major']}")
    print(f"Languages: {', '.join(user_skills['languages'])}")
    print(f"Frameworks: {', '.join(user_skills['frameworks'])}")
    
    # University directories
    universities = [
        # ("George Mason University", "https://cs.gmu.edu/directory/by-category/faculty/"),
        ("Virginia Tech", "https://cs.vt.edu/people/faculty.html"),
        # ("University of Virginia", "https://engineering.virginia.edu/departments/computer-science/faculty")
    ]
    
    # First run tests
    print("\nTesting faculty page access...")
    for uni_name, url in universities:
        test_faculty_scraping(url, headers)
    
    all_professors = []
    
    for uni_name, uni_url in universities:
        print(f"\n{'='*50}")
        print(f"Processing {uni_name} at {uni_url}")
        print(f"{'='*50}")
        
        domain = uni_url.split('/')[2]
        scraper_rules = UniversityScraperFactory.create_scraper(domain)
        
        try:
            print(f"Fetching faculty directory...")
            page_content = scrape_with_retry(uni_url, headers)
            if not page_content:
                print(f"Skipping {uni_name} due to failed retrieval")
                continue
                
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Add detailed structure analysis
            print_page_structure(soup, uni_name)
            
            debug_faculty_links(soup, uni_name)
            
            # Try multiple selectors for faculty elements
            faculty_elements = []
            selectors = scraper_rules['faculty_selector']
            if isinstance(selectors, str):
                selectors = [selectors]
                
            for selector in selectors:
                elements = soup.select(selector)
                print(f"Trying selector '{selector}': found {len(elements)} elements")
                faculty_elements.extend(elements)
                if elements:
                    # Show sample of what was found
                    sample = elements[0]
                    print(f"Sample element text: {sample.text[:100].strip()}")
            
            print(f"Found {len(faculty_elements)} potential faculty elements")
            
            for faculty in faculty_elements:
                try:
                    name = None
                    profile_url = None
                    
                    # Special handling for VT
                    if 'vt.edu' in uni_url:
                        name, profile_url = process_vt_faculty(faculty)
                    else:
                        # Regular processing for other universities
                        if isinstance(scraper_rules['name_selector'], list):
                            for selector in scraper_rules['name_selector']:
                                if selector:
                                    name_elem = faculty.select_one(selector)
                                    if name_elem:
                                        name = name_elem.text.strip()
                                        break
                        elif scraper_rules['name_selector']:
                            name_elem = faculty.select_one(scraper_rules['name_selector'])
                            if name_elem:
                                name = name_elem.text.strip()
                        
                        # Extract link
                        if isinstance(scraper_rules['link_selector'], list):
                            for selector in scraper_rules['link_selector']:
                                if selector:
                                    link_elem = faculty.select_one(selector)
                                    if link_elem and link_elem.has_attr('href'):
                                        profile_url = urljoin(uni_url, link_elem['href'])
                                        break
                        elif scraper_rules['link_selector']:
                            link_elem = faculty.select_one(scraper_rules['link_selector'])
                            if link_elem and link_elem.has_attr('href'):
                                profile_url = urljoin(uni_url, link_elem['href'])
                    
                    if name and profile_url:
                        name, profile_url = clean_faculty_data(name, profile_url)
                        print(f"\nFound professor: {name}")
                        print(f"Profile URL: {profile_url}")
                        
                        # Scrape and analyze professor's page
                        page_content = scrape_with_retry(profile_url, headers)
                        if page_content:
                            soup = BeautifulSoup(page_content, 'html.parser')
                            # Remove script and style elements
                            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                                element.decompose()
                            
                            text = soup.get_text(separator=' ', strip=True)
                            research_focus = research_parser.extract_research_focus(text, name)
                            
                            professor_details = {
                                'name': name,
                                'research': research_focus
                            }
                            
                            email_draft = generate_personalized_email(user_details, professor_details)
                            
                            all_professors.append({
                                'University': uni_name,
                                'Professor': name,
                                'Profile Link': profile_url,
                                'Research Focus': research_focus,
                                'Email Draft': email_draft
                            })
                            
                            print(f"Successfully processed: {name}")
                            print(f"Research focus: {research_focus[:100]}...")
                            time.sleep(2)  # Increased delay between requests
                        
                except Exception as e:
                    print(f"Error processing faculty member: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error processing {uni_name}: {e}")
            continue
    
    # Save results
    if all_professors:
        df = pd.DataFrame(all_professors)
        output_file = 'research_outreach_emails.csv'
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nSaved {len(all_professors)} professor details to {output_file}")
        
        # Send email with CSV
        if send_email(to_email, output_file):
            print("Process complete! Check your email for the CSV file.")
        else:
            print("CSV file was created but could not be emailed. Please check the file directly.")
    else:
        print("No professor data collected")

if __name__ == "__main__":
    main()