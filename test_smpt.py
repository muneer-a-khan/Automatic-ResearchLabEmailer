import smtplib

# Replace these with your details
sender_email = "your_email@gmail.com"  
sender_password = "your_generated_app_password"  
receiver_email = "your_email@gmail.com"  # You can send a test email to yourself

try:
    # Connect to Gmail SMTP Server
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(sender_email, sender_password)
    
    # Send a test email
    subject = "SMTP Test Successful"
    body = "This is a test email to confirm that your Gmail SMTP setup is working."
    message = f"Subject: {subject}\n\n{body}"
    
    server.sendmail(sender_email, receiver_email, message)
    server.quit()
    
    print("Email sent successfully! Check your inbox.")
except Exception as e:
    print(f"SMTP Error: {e}")
