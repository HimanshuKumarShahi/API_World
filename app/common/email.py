import logging
from email.message import EmailMessage
import aiosmtplib
from app.core.config import settings

logger = logging.getLogger("uvicorn")


async def send_email_async(to_email: str, subject: str, html_content: str) -> None:
    """
    Sends an HTML email asynchronously via SMTP.
    Also logs the link in console for easy local development/testing.
    """
    logger.info(f"\n--- [EMAIL DISPATCH TO: {to_email}] ---\nSubject: {subject}\n{html_content}\n--------------------------------------")

    if settings.SMTP_USER == "API_World@gmail.com":
        logger.warning("SMTP not configured with real credentials. Skipping actual SMTP send (use the logged link above).")
        return

    message = EmailMessage()
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(html_content, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
        )
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")


async def send_verification_email(to_email: str, token: str) -> None:
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <h3>Welcome to {settings.PROJECT_NAME}!</h3>
    <p>Please verify your email address by clicking the link below:</p>
    <p><a href="{verify_url}">{verify_url}</a></p>
    <p>Or use this token directly in Swagger (/api/v1/auth/verify-email): <b>{token}</b></p>
    <p>This link expires in {settings.EMAIL_TOKEN_EXPIRE_MINUTES} minutes.</p>
    """
    await send_email_async(to_email, "Verify Your Email Address", html)


async def send_reset_password_email(to_email: str, token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <h3>Password Reset Request</h3>
    <p>Click the link below to reset your password:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>Or use this token directly in Swagger (/api/v1/auth/reset-password): <b>{token}</b></p>
    <p>If you did not request this, please ignore this email.</p>
    """
    await send_email_async(to_email, "Reset Your Password", html)