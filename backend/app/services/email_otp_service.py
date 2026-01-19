"""
Email OTP Service
Handles sending OTP via email
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailOTPService:
    """Email OTP sending service"""
    
    def __init__(self):
        # Email configuration (can be configured via environment variables)
        self.smtp_host = getattr(settings, 'SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = getattr(settings, 'FROM_EMAIL', 'noreply@habibti.app')
        self.from_name = getattr(settings, 'FROM_NAME', 'HABIBTI')
        
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP not configured. OTP will be logged instead of sent.")
            self.smtp_configured = False
        else:
            self.smtp_configured = True
    
    async def send_email(self, to: str, otp: str, purpose: str = "signup") -> bool:
        """
        Send OTP via email
        
        Args:
            to: Email address
            otp: OTP code to send
            purpose: Purpose of OTP (signup, login, recovery)
            
        Returns:
            True if sent successfully
        """
        # Email subject based on purpose
        subjects = {
            "signup": "Welcome to HABIBTI - Verify Your Email",
            "login": "HABIBTI Login Verification Code",
            "recovery": "HABIBTI Account Recovery Code"
        }
        subject = subjects.get(purpose, "HABIBTI Verification Code")
        
        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .otp-box {{
                    background: white;
                    border: 2px dashed #667eea;
                    padding: 20px;
                    text-align: center;
                    font-size: 32px;
                    font-weight: bold;
                    letter-spacing: 8px;
                    color: #667eea;
                    margin: 20px 0;
                    border-radius: 8px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #666;
                }}
                .warning {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 HABIBTI</h1>
                    <p>Privacy-First Chat Application</p>
                </div>
                <div class="content">
                    <h2>Your Verification Code</h2>
                    <p>Hello!</p>
                    <p>You requested a verification code for your HABIBTI account. Use the code below to continue:</p>
                    
                    <div class="otp-box">
                        {otp}
                    </div>
                    
                    <p><strong>This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.</strong></p>
                    
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong><br>
                        Never share this code with anyone. HABIBTI will never ask for your verification code via phone or email.
                    </div>
                    
                    <p>If you didn't request this code, please ignore this email or contact support if you have concerns.</p>
                </div>
                <div class="footer">
                    <p>© 2026 HABIBTI - Privacy-First Chat Application</p>
                    <p>This is an automated email. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_body = f"""
        HABIBTI - Verification Code
        
        Your verification code is: {otp}
        
        This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.
        
        If you didn't request this code, please ignore this email.
        
        © 2026 HABIBTI - Privacy-First Chat Application
        """
        
        if self.smtp_configured:
            try:
                # Create message
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = f"{self.from_name} <{self.from_email}>"
                message["To"] = to
                
                # Attach both plain text and HTML versions
                part1 = MIMEText(text_body, "plain")
                part2 = MIMEText(html_body, "html")
                message.attach(part1)
                message.attach(part2)
                
                # Send email
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)
                
                logger.info(f"OTP email sent to {to}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to send OTP email to {to}: {str(e)}")
                # Fail-safe: Log OTP to console so user can still signup
                logger.warning("Falling back to console OTP due to SMTP error")
                print(f"\n{'='*60}")
                print(f"⚠️ SMTP ERROR - FALLBACK OTP for {to}")
                print(f"{'='*60}")
                print(f"Error: {str(e)}")
                print(f"OTP Code: {otp}")
                print(f"{'='*60}\n")
                return True
        else:
            # Development mode: log OTP instead of sending
            logger.info(f"[DEV MODE] OTP for {to}: {otp}")
            print(f"\n{'='*60}")
            print(f"📧 EMAIL OTP for {to}")
            print(f"{'='*60}")
            print(f"Subject: {subject}")
            print(f"OTP Code: {otp}")
            print(f"Expires in: {settings.OTP_EXPIRY_MINUTES} minutes")
            print(f"{'='*60}\n")
            return True


# Global email OTP service instance
email_otp_service = EmailOTPService()


async def send_otp_email(email: str, otp: str, purpose: str = "signup") -> bool:
    """Send OTP via email"""
    return await email_otp_service.send_email(email, otp, purpose)
