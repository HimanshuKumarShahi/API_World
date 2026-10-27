import logging
from email.message import EmailMessage
import aiosmtplib
from app.core.config import settings

logger = logging.getLogger("uvicorn")


def build_html_email(title: str, subtitle: str, button_text: str, action_url: str, token: str) -> str:
    """Generates a modern, responsive HTML email template for Mailtrap / Production SMTP."""
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; background-color:#f4f7fa; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding: 40px 16px;">
        <tr>
          <td align="center">
            <table width="100%" style="max-width: 560px; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.06);">
              <tr>
                <td style="background:#0f172a; padding:24px 32px; text-align:center;">
                  <h2 style="margin:0; color:#ffffff; font-size:20px; letter-spacing:0.5px;">{settings.PROJECT_NAME}</h2>
                </td>
              </tr>
              <tr>
                <td style="padding:32px;">
                  <h3 style="margin-top:0; color:#1e293b; font-size:18px;">{title}</h3>
                  <p style="color:#475569; font-size:15px; line-height:1.6;">{subtitle}</p>
                  <div style="text-align:center; margin: 28px 0;">
                    <a href="{action_url}" style="background:#2563eb; color:#ffffff; text-decoration:none; padding:12px 28px; border-radius:8px; font-weight:600; font-size:15px; display:inline-block;">
                      {button_text}
                    </a>
                  </div>
                  <p style="color:#64748b; font-size:13px; margin-bottom:8px;">
                    <strong>Testing in Swagger UI or Postman?</strong> Copy your token below:
                  </p>
                  <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:12px; font-family:monospace; font-size:12px; color:#0f172a; word-break:break-all;">
                    {token}
                  </div>
                  <p style="color:#94a3b8; font-size:12px; margin-top:24px; margin-bottom:0;">
                    This token expires in {settings.EMAIL_TOKEN_EXPIRE_MINUTES} minutes. If you did not request this, you can safely ignore this email.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


async def send_email_async(
    to_email: str,
    subject: str,
    action_url: str,
    token: str,
    endpoint_hint: str,
    html_content: str,
) -> None:
    """
    Prints a clean, tag-free summary in Console Mode, or dispatches a styled HTML email via Mailtrap/SMTP.
    """
    if settings.EMAIL_PROVIDER == "console" or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        console_output = (
            f"\n╔══════════════════════════════════════════════════════════════════════╗\n"
            f"║  📧 CONSOLE EMAIL DISPATCH ({settings.PROJECT_NAME})\n"
            f"╠══════════════════════════════════════════════════════════════════════╣\n"
            f"║  To       : {to_email}\n"
            f"║  Subject  : {subject}\n"
            f"║  Endpoint : POST {endpoint_hint}\n"
            f"╠══════════════════════════════════════════════════════════════════════╣\n"
            f"║  🔗 Frontend Link:\n"
            f"║  {action_url}\n"
            f"║\n"
            f"║  🔑 Copy Token (for Swagger / Postman):\n"
            f"║  {token}\n"
            f"╚══════════════════════════════════════════════════════════════════════╝\n"
        )
        logger.info(console_output)
        return

    message = EmailMessage()
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(f"Action link: {action_url}\nToken: {token}")
    message.add_alternative(html_content, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
        )
        logger.info(f"📨 Email sent to {to_email} via {settings.EMAIL_PROVIDER.upper()}")
    except Exception as e:
        logger.error(f"❌ SMTP Error ({settings.EMAIL_PROVIDER}): Failed to send email to {to_email}: {e}")


async def send_verification_email(to_email: str, token: str) -> None:
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    html = build_html_email(
        title="Verify Your Email Address",
        subtitle="Welcome aboard! Please confirm your email address to activate your account.",
        button_text="Verify Email Address",
        action_url=verify_url,
        token=token,
    )
    await send_email_async(
        to_email=to_email,
        subject="Verify Your Email Address",
        action_url=verify_url,
        token=token,
        endpoint_hint="/api/v1/auth/verify-email",
        html_content=html,
    )


async def send_reset_password_email(to_email: str, token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = build_html_email(
        title="Password Reset Request",
        subtitle="We received a request to reset the password for your account. Click the button below to choose a new password.",
        button_text="Reset My Password",
        action_url=reset_url,
        token=token,
    )
    await send_email_async(
        to_email=to_email,
        subject="Reset Your Password",
        action_url=reset_url,
        token=token,
        endpoint_hint="/api/v1/auth/reset-password",
        html_content=html,
    )