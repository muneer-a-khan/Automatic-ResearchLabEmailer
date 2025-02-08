# Automatic Research Lab Emailer

## Overview
The **Automatic Research Lab Emailer** is a Python-based tool that automates the process of extracting research interests from university faculty pages and generating personalized outreach emails. The script:
* Scrapes faculty directories for professor names and profile links
* Extracts research focus areas from professor profile pages
* Parses user resumes to identify technical skills and educational background
* Uses GPT-4 to generate personalized outreach emails
* Outputs the extracted information as a CSV file and optionally emails it

## Features
* **Automated Faculty Scraping:** Extract faculty names, research areas, and profile links from university websites
* **AI-Powered Research Extraction:** Uses GPT-4 to summarize professors' research focus
* **Resume Parsing:** Extracts relevant skills, university, major, and graduation year from a resume PDF
* **Personalized Email Generation:** Generates a tailored outreach email for each professor
* **Email Sending:** Sends the extracted data as a CSV file to the user

## Requirements

### Prerequisites
Ensure you have Python 3.8+ installed along with the required dependencies.

### Install Dependencies
```bash
pip install -r requirements.txt
```

The `requirements.txt` file should contain:
```
beautifulsoup4
pandas
requests
PyPDF2
openai
```

## Setup Instructions

### 1. Set Up API Keys
Create an `.env` file in the project directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

### 2. Configure Email Credentials (Optional)
If you want to email the results, add the following environment variables to `.env`:
```
SENDER_EMAIL=your_email@example.com
EMAIL_PASSWORD=your_email_password
```

### 3. Running the Script
To run the script, execute:
```bash
python main.py
```

The script will prompt you to:
1. Enter the path to your resume PDF
2. Enter your email address (to receive the CSV file)

### 4. Customizing for a Specific University
To add or modify university scraping rules:
* Edit the `UniversityScraperFactory` class in `main.py`
* Update faculty page URLs in the `universities` list

Example:
```python
universities = [
    ("Virginia Tech", "https://cs.vt.edu/people/faculty.html"),
    ("University of Virginia", "https://engineering.virginia.edu/departments/computer-science/faculty"),
]
```

## Output
* The extracted faculty information and emails are saved as `research_outreach_emails.csv`
* If email sending is enabled, the CSV is sent to the provided email

## Troubleshooting

### Common Issues & Fixes
1. **Scraping issues?** Check `faculty_page.html` to debug selectors
2. **No research extracted?** Try increasing `temperature` in `GPT-4` requests
3. **Email not sent?** Verify SMTP credentials and check spam filters

## Contributing
Feel free to submit pull requests for new university scrapers or improved AI models.

## License
GPL-3.0 License

## Contact
For questions, contact [Muneer Khan](https://github.com/muneerkhan007).
