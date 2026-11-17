import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

def generate_otp() -> str:
    """Generate a random 6-digit numeric verification OTP."""
    return f"{random.randint(100000, 999999)}"

def send_otp_email(recipient_email: str, recipient_name: str, otp_code: str, purpose: str = "Account Verification") -> Tuple[bool, str, Dict[str, Any]]:
    """
    Send OTP code via SMTP if configured, or return dev mode instructions.
    Returns (success, message, extra_info).
    """
    smtp_server = os.environ.get("SMTP_SERVER", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_EMAIL", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()

    is_pwd_reset = "password" in purpose.lower()
    subject = f"Your SkillSprint Password Reset Code: {otp_code}" if is_pwd_reset else f"Your SkillSprint Verification Code: {otp_code}"
    heading = "Reset Your Password" if is_pwd_reset else "Verify your email address"
    body_msg = "We received a request to reset your password. Use the verification code below to set a new password:" if is_pwd_reset else "Welcome to SkillSprint! Use the one-time verification code below to verify your account and begin your technical interview preparation:"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; padding: 20px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #131b2e; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
            .logo {{ font-size: 20px; font-weight: 800; color: #818cf8; letter-spacing: -0.5px; margin-bottom: 24px; }}
            .otp-box {{ background: #1e1b4b; border: 1px dashed #6366f1; border-radius: 12px; padding: 18px; text-align: center; margin: 24px 0; font-family: monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #c7d2fe; }}
            .footer {{ font-size: 12px; color: #64748b; margin-top: 24px; text-align: center; border-top: 1px solid #1e293b; padding-top: 16px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">⚡ SkillSprint Studio</div>
            <h2 style="color: #ffffff; margin-top: 0;">{heading}</h2>
            <p style="color: #94a3b8; font-size: 14px; line-height: 1.5;">Hello <strong>{recipient_name}</strong>,</p>
            <p style="color: #94a3b8; font-size: 14px; line-height: 1.5;">{body_msg}</p>
            <div class="otp-box">{otp_code}</div>
            <p style="color: #64748b; font-size: 12px;">This code expires in 15 minutes. If you did not request this code, please disregard this email.</p>
            <div class="footer">
                SkillSprint Studio • AI Interview & Technical Career OS
            </div>
        </div>
    </body>
    </html>
    """

    # If SMTP is configured, send real email
    if smtp_server and smtp_user and smtp_password:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"SkillSprint Studio <{smtp_user}>"
            msg["To"] = recipient_email
            
            part_text = MIMEText(f"Hello {recipient_name},\n\nYour verification code is: {otp_code}\n\nValid for 15 minutes.", "plain")
            part_html = MIMEText(html_content, "html")
            msg.attach(part_text)
            msg.attach(part_html)
            
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                server.starttls()
                
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_email, msg.as_string())
            server.quit()
            
            print(f"[Email] Real OTP sent via SMTP to {recipient_email}")
            return True, "Verification code sent to your email.", {"dev_mode": False}
        except Exception as e:
            print(f"[Email Warning] SMTP delivery failed ({e}), falling back to instant verification preview.")

    # Fallback / Development mode when SMTP is not configured
    print(f"\n=======================================================")
    print(f"[DEV MODE OTP] Email: {recipient_email} | OTP: {otp_code}")
    print(f"=======================================================\n")
    
    return True, f"OTP generated! (Dev preview code: {otp_code})", {
        "dev_mode": True,
        "otp_preview": otp_code,
        "tip": "To enable real email dispatch, configure SMTP_EMAIL and SMTP_PASSWORD in Settings."
    }
