import smtplib
from email.mime.text import MIMEText

from backend.app.core.config import settings

# ---- Brand styling (single source of truth) ----
BRAND_COLOR = "#4F46E5"
TEXT_COLOR = "#1F2937"
MUTED_COLOR = "#6B7280"
BG_COLOR = "#F3F4F6"
FONT_FAMILY = "Arial, Helvetica, sans-serif"


def send_email(to_email: str, subject: str, body: str) -> None:
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def _button(link: str, text: str) -> str:
    """
    Table-based button — <a> with padding renders inconsistently in Outlook,
    but a table cell with a background color is reliable across all major clients.
    """
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td align="center" bgcolor="{BRAND_COLOR}"
            style="border-radius:6px;">
          <a href="{link}" target="_blank"
             style="display:inline-block; padding:14px 32px; font-family:{FONT_FAMILY};
                    font-size:15px; font-weight:600; color:#ffffff; text-decoration:none;">
            {text}
          </a>
        </td>
      </tr>
    </table>
    """


def _wrap_email(inner_html: str, preheader: str) -> str:
    """
    Full HTML document with table-based layout.
    - DOCTYPE + meta tags: required for consistent rendering across clients
    - preheader: hidden text controlling the inbox preview snippet
    - table layout: Outlook (Word engine) only reliably supports tables, not div/flex
    """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>ProjectSphere</title>
    </head>
    <body style="margin:0; padding:0; background-color:{BG_COLOR};">
      <div style="display:none; max-height:0; overflow:hidden; font-size:1px; color:{BG_COLOR};">
        {preheader}
      </div>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background-color:{BG_COLOR};">
        <tr>
          <td align="center" style="padding:32px 16px;">
            <table role="presentation" width="480" cellpadding="0" cellspacing="0" border="0"
                   style="background-color:#ffffff; border-radius:8px; max-width:480px; width:100%;">
              <tr>
                <td style="padding:32px; font-family:{FONT_FAMILY}; color:{TEXT_COLOR};">

                  <h2 style="margin:0 0 20px 0; color:{BRAND_COLOR}; font-size:20px;">
                    ProjectSphere
                  </h2>

                  {inner_html}

                  <p style="margin-top:32px; margin-bottom:0; font-size:14px; color:{TEXT_COLOR};">
                    Best regards,<br>
                    <strong>The ProjectSphere Team</strong>
                  </p>

                  <p style="margin-top:20px; margin-bottom:0; font-size:12px; color:{MUTED_COLOR};
                            border-top:1px solid #E5E7EB; padding-top:16px;">
                    If you didn't expect this email, you can safely ignore it.
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


def send_verification_code_email(to_email: str, code: str) -> None:
    inner = f"""
    <p style="margin:0 0 12px 0;">Welcome to <strong>ProjectSphere</strong>!</p>
    <p style="margin:0 0 8px 0;">Your verification code is:</p>
    <p style="font-size:32px; font-weight:700; letter-spacing:4px;
              color:{BRAND_COLOR}; margin:16px 0;">{code}</p>
    <p style="font-size:14px; color:{MUTED_COLOR}; margin:0;">
        Enter this code in the app to verify your account. This code expires in 10 minutes.
    </p>
    """
    send_email(
        to_email,
        "Your ProjectSphere verification code",
        _wrap_email(inner, preheader=f"Your verification code is {code}"),
    )


def send_welcome_email(to_email: str, name: str) -> None:
    inner = f"""
    <p style="margin:0 0 12px 0;">Hi {name},</p>
    <p style="margin:0 0 12px 0;">Your email has been verified. Welcome to <strong>ProjectSphere</strong>!</p>
    <p style="margin:0;">You can now log in and get started.</p>
    """
    send_email(
        to_email,
        "Welcome to ProjectSphere",
        _wrap_email(inner, preheader="Your account is verified and ready to go."),
    )


def send_password_reset_email(to_email: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    inner = f"""
    <p style="margin:0 0 12px 0;">You requested a password reset for <strong>ProjectSphere</strong>.</p>
    <p style="margin:0 0 20px 0;">Click the button below to set a new password:</p>
    {_button(link, "Reset Password")}
    <p style="font-size:13px; color:{MUTED_COLOR}; margin-top:24px;">
        This link expires in 30 minutes. If you didn't request this, ignore this email.
    </p>
    """
    send_email(
        to_email,
        "Reset your ProjectSphere password",
        _wrap_email(
            inner, preheader="Reset your password — link expires in 30 minutes."
        ),
    )


def send_supervisor_invite_email(to_email: str, name: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/auth/set-password?token={token}"
    inner = f"""
    <p style="margin:0 0 12px 0;">Hi {name},</p>
    <p style="margin:0 0 12px 0;">You've been added as a supervisor on <strong>ProjectSphere</strong>.</p>
    <p style="margin:0 0 20px 0;">Click the button below to set your password and activate your account:</p>
    {_button(link, "Set Password & Activate")}
    <p style="font-size:13px; color:{MUTED_COLOR}; margin-top:24px;">
        This link expires in 30 minutes.
    </p>
    """
    send_email(
        to_email,
        "You're invited to ProjectSphere",
        _wrap_email(inner, preheader="You've been invited as a supervisor."),
    )


def send_task_created_email(to_email: str, task_title: str, deadline: str) -> None:
    inner = f"""
    <p style="margin:0 0 12px 0;">A new task has been assigned to your group:</p>
    <p style="font-size:18px; font-weight:600; color:{BRAND_COLOR}; margin:0 0 8px 0;">{task_title}</p>
    <p style="margin:0; font-size:14px; color:{MUTED_COLOR};">Deadline: {deadline}</p>
    """
    send_email(
        to_email,
        f"New task assigned: {task_title}",
        _wrap_email(inner, preheader=f"New task: {task_title}"),
    )


def send_evidence_submitted_email(
    to_email: str, task_title: str, group_name: str
) -> None:
    inner = f"""
    <p style="margin:0 0 12px 0;">Group <strong>{group_name}</strong> submitted evidence for:</p>
    <p style="font-size:18px; font-weight:600; color:{BRAND_COLOR}; margin:0;">{task_title}</p>
    <p style="margin-top:12px; font-size:14px; color:{MUTED_COLOR};">Please review it in ProjectSphere.</p>
    """
    send_email(
        to_email,
        f"Submission received: {task_title}",
        _wrap_email(inner, preheader=f"{group_name} submitted evidence."),
    )


def send_group_at_risk_email(to_email: str, group_name: str, reason: str) -> None:
    inner = f"""
    <p style="margin:0 0 12px 0;">Group <strong>{group_name}</strong> is now flagged at-risk.</p>
    <p style="margin:0; font-size:14px; color:{MUTED_COLOR};">Reason: {reason}</p>
    """
    send_email(
        to_email,
        f"Group at-risk: {group_name}",
        _wrap_email(inner, preheader=f"{group_name} needs attention."),
    )


def send_proposal_decision_email(
    to_emails: list[str], status: str, feedback: str | None = None
) -> None:
    if status == "approved":
        inner = f"""
        <p style="margin:0 0 12px 0;">Your proposal has been <strong>approved</strong>!</p>
        <p style="margin:0; font-size:14px; color:{MUTED_COLOR};">You can now proceed with your assigned tasks.</p>
        """
        subject = "Your proposal was approved"
    else:
        inner = f"""
        <p style="margin:0 0 12px 0;">Your proposal has been <strong>rejected</strong>.</p>
        <p style="margin:0; font-size:14px; color:{MUTED_COLOR};">Feedback: {feedback or "No feedback provided."}</p>
        """
        subject = "Your proposal was rejected"

    for email in to_emails:
        send_email(email, subject, _wrap_email(inner, preheader=subject))


def send_thesis_delete_warning_email(
    to_emails: list[str], group_name: str, days_left: int
) -> None:
    inner = f"""
    <p style="margin:0 0 12px 0;">Group <strong>{group_name}</strong>'s thesis/project submission has not been approved yet.</p>
    <p style="margin:0; font-size:14px; color:{MUTED_COLOR};">
        It will be automatically deleted in {days_left} day(s) if not approved before then.
        Please contact your supervisor or admin.
    </p>
    """
    for email in to_emails:
        send_email(
            email,
            "Action needed: your submission will be auto-deleted soon",
            _wrap_email(
                inner, preheader="Your submission is about to be auto-deleted."
            ),
        )
