"""
Email service for sending verification and password reset emails
"""
import logging
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.from_name = settings.smtp_from_name
        self.use_tls = settings.smtp_tls
    
    def is_configured(self) -> bool:
        """Check if email service is configured"""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email"""
        if not self.is_configured():
            logger.warning("Email service not configured, skipping email send")
            # In development, log the email content
            logger.info(f"Would send email to {to_email}: {subject}")
            logger.debug(f"Content: {text_content or html_content}")
            return True  # Return True to not block the flow
        
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            if text_content:
                message.attach(MIMEText(text_content, "plain"))
            message.attach(MIMEText(html_content, "html"))
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=self.use_tls
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_verification_email(self, to_email: str, token: str, user_name: Optional[str] = None) -> bool:
        """Send email verification email"""
        verification_url = f"{settings.frontend_url}/verify-email?token={token}"
        
        subject = "Verify your email - AI Content Platform"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0a0a0f; color: #e8e8ef; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .card {{ background-color: #141419; border-radius: 16px; padding: 40px; border: 1px solid #2a2a35; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #6366f1; margin-bottom: 30px; }}
                h1 {{ color: #e8e8ef; font-size: 24px; margin-bottom: 20px; }}
                p {{ color: #8b8b9e; line-height: 1.6; margin-bottom: 20px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; 
                          padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #6b6b7e; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <div class="logo">AI Content Platform</div>
                    <h1>Verify your email address</h1>
                    <p>Hi{f' {user_name}' if user_name else ''},</p>
                    <p>Thanks for signing up! Please click the button below to verify your email address and activate your account.</p>
                    <p><a href="{verification_url}" class="button">Verify Email</a></p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; font-size: 14px;">{verification_url}</p>
                    <p>This link will expire in 24 hours.</p>
                    <div class="footer">
                        <p>If you didn't create an account, you can safely ignore this email.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        AI Content Platform - Verify your email
        
        Hi{f' {user_name}' if user_name else ''},
        
        Thanks for signing up! Please verify your email address by clicking the link below:
        
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you didn't create an account, you can safely ignore this email.
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_password_reset_email(self, to_email: str, token: str, user_name: Optional[str] = None) -> bool:
        """Send password reset email"""
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        
        subject = "Reset your password - AI Content Platform"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0a0a0f; color: #e8e8ef; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .card {{ background-color: #141419; border-radius: 16px; padding: 40px; border: 1px solid #2a2a35; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #6366f1; margin-bottom: 30px; }}
                h1 {{ color: #e8e8ef; font-size: 24px; margin-bottom: 20px; }}
                p {{ color: #8b8b9e; line-height: 1.6; margin-bottom: 20px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; 
                          padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; }}
                .warning {{ background-color: #f59e0b20; border: 1px solid #f59e0b40; border-radius: 8px; padding: 16px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #6b6b7e; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <div class="logo">AI Content Platform</div>
                    <h1>Reset your password</h1>
                    <p>Hi{f' {user_name}' if user_name else ''},</p>
                    <p>We received a request to reset your password. Click the button below to create a new password.</p>
                    <p><a href="{reset_url}" class="button">Reset Password</a></p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; font-size: 14px;">{reset_url}</p>
                    <div class="warning">
                        <p style="color: #f59e0b; margin: 0;">⚠️ This link will expire in 1 hour for security reasons.</p>
                    </div>
                    <div class="footer">
                        <p>If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        AI Content Platform - Reset your password
        
        Hi{f' {user_name}' if user_name else ''},
        
        We received a request to reset your password. Click the link below to create a new password:
        
        {reset_url}
        
        This link will expire in 1 hour for security reasons.
        
        If you didn't request a password reset, you can safely ignore this email.
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_welcome_email(self, to_email: str, user_name: Optional[str] = None) -> bool:
        """Send welcome email after verification"""
        dashboard_url = f"{settings.frontend_url}/dashboard"
        
        subject = "Welcome to AI Content Platform! 🎉"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0a0a0f; color: #e8e8ef; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .card {{ background-color: #141419; border-radius: 16px; padding: 40px; border: 1px solid #2a2a35; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #6366f1; margin-bottom: 30px; }}
                h1 {{ color: #e8e8ef; font-size: 24px; margin-bottom: 20px; }}
                p {{ color: #8b8b9e; line-height: 1.6; margin-bottom: 20px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; 
                          padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; }}
                .features {{ background-color: #1e1e26; border-radius: 8px; padding: 20px; margin: 20px 0; }}
                .feature {{ margin: 12px 0; }}
                .feature-icon {{ color: #10b981; margin-right: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <div class="logo">AI Content Platform</div>
                    <h1>Welcome aboard! 🎉</h1>
                    <p>Hi{f' {user_name}' if user_name else ''},</p>
                    <p>Your email has been verified and your account is now active. You're all set to start creating amazing AI-powered content!</p>
                    <div class="features">
                        <p style="color: #e8e8ef; font-weight: 600; margin-bottom: 16px;">Here's what you can do:</p>
                        <div class="feature"><span class="feature-icon">✓</span> Create AI brand personas</div>
                        <div class="feature"><span class="feature-icon">✓</span> Discover trending topics</div>
                        <div class="feature"><span class="feature-icon">✓</span> Generate stunning images</div>
                        <div class="feature"><span class="feature-icon">✓</span> Create engaging captions</div>
                    </div>
                    <p><a href="{dashboard_url}" class="button">Go to Dashboard</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        AI Content Platform - Welcome!
        
        Hi{f' {user_name}' if user_name else ''},
        
        Your email has been verified and your account is now active!
        
        Here's what you can do:
        - Create AI brand personas
        - Discover trending topics
        - Generate stunning images
        - Create engaging captions
        
        Get started: {dashboard_url}
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()
