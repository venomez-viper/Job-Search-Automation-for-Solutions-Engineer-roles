"""
notifier.py — Send daily job digest via Gmail SMTP.
Supports High Match / Stretch classification labels in the email layout.
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from fetchers.base import Job

logger = logging.getLogger(__name__)

_LABEL_STYLE = {
    "High Match":       ("🟢", "#1a7f37", "#d4edda"),
    "Stretch but Apply": ("🟡", "#856404", "#fff3cd"),
}


def _build_html(jobs: list[Job], run_date: str) -> str:
    rows = ""
    for i, job in enumerate(jobs, 1):
        label = getattr(job, "label", "High Match")
        icon, label_color, label_bg = _LABEL_STYLE.get(label, ("⚪", "#555", "#f0f0f0"))

        loc = job.location or ""
        loc_icon = "🏙️ " if "chicago" in loc.lower() else ("🌐 " if "remote" in loc.lower() else "📍 ")

        # Get score breakdown if available
        bd = getattr(job, "breakdown", None)
        breakdown_tip = ""
        if bd:
            tip_parts = []
            if bd.core_matches:
                tip_parts.append(f"Core: {', '.join([m.split('(')[0] for m in bd.core_matches[:3]])}")
            if bd.tool_matches:
                tip_parts.append(f"Tools: {', '.join([m.split('(')[0] for m in bd.tool_matches[:2]])}")
            if bd.transferable_matches:
                tip_parts.append(f"Transferable: {', '.join([m.split('→')[0] for m in bd.transferable_matches[:2]])}")
            if bd.ramp_keywords_found:
                tip_parts.append(f"Ramp: {bd.ramp_keywords_found[0]}")
            breakdown_tip = " &bull; ".join(tip_parts)

        rows += f"""
        <tr style="background:{'#f9f9f9' if i % 2 == 0 else '#ffffff'}; border-bottom:1px solid #eee;">
          <td style="padding:12px 8px; font-weight:bold; color:#1a73e8; text-align:center;">{i}</td>
          <td style="padding:12px 8px;">
            <a href="{job.url}" style="color:#1a1a1a; text-decoration:none; font-weight:700; font-size:14px;">{job.title}</a>
            {f'<br><small style="color:#888; font-size:11px;">{breakdown_tip}</small>' if breakdown_tip else ""}
          </td>
          <td style="padding:12px 8px; font-weight:600; color:#333;">{job.company}</td>
          <td style="padding:12px 8px; color:#555; white-space:nowrap;">{loc_icon}{loc}</td>
          <td style="padding:12px 8px; text-align:center;">
            <span style="background:#e8f0fe; color:#1a73e8; padding:2px 8px; border-radius:10px; font-weight:700; font-size:13px;">{job.score}</span>
          </td>
          <td style="padding:12px 8px; text-align:center;">
            <span style="background:{label_bg}; color:{label_color}; padding:3px 10px; border-radius:10px; font-size:12px; font-weight:600; white-space:nowrap;">{icon} {label}</span>
          </td>
          <td style="padding:12px 8px; color:#aaa; font-size:11px;">{job.date_posted}</td>
        </tr>"""

    high_count = sum(1 for j in jobs if getattr(j, "label", "") == "High Match")
    stretch_count = len(jobs) - high_count

    return f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:960px;margin:0 auto;background:#f5f7fa;padding:20px;">
      <div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);color:white;padding:28px 32px;border-radius:12px 12px 0 0;">
        <h1 style="margin:0;font-size:22px;font-weight:700;">🎯 Daily Job Digest — {run_date}</h1>
        <p style="margin:8px 0 0;opacity:.88;font-size:13px;">
          <span style="background:rgba(255,255,255,.2);padding:2px 10px;border-radius:8px;margin-right:8px;">🟢 {high_count} High Match</span>
          <span style="background:rgba(255,255,255,.2);padding:2px 10px;border-radius:8px;">🟡 {stretch_count} Stretch but Apply</span>
        </p>
      </div>

      <div style="background:#fff;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 12px 12px;overflow:hidden;">
        <table style="width:100%;border-collapse:collapse;" cellspacing="0" cellpadding="0">
          <thead>
            <tr style="background:#f5f7ff;border-bottom:2px solid #e0e8ff;">
              <th style="padding:10px 8px;text-align:center;color:#555;font-size:11px;text-transform:uppercase;">#</th>
              <th style="padding:10px 8px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Role &amp; Match Signals</th>
              <th style="padding:10px 8px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Company</th>
              <th style="padding:10px 8px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Location</th>
              <th style="padding:10px 8px;text-align:center;color:#555;font-size:11px;text-transform:uppercase;">Score</th>
              <th style="padding:10px 8px;text-align:center;color:#555;font-size:11px;text-transform:uppercase;">Label</th>
              <th style="padding:10px 8px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Posted</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>

      <div style="margin-top:16px;padding:12px 16px;background:#fff;border-radius:8px;border:1px solid #e0e0e0;font-size:12px;color:#666;">
        <strong>Legend:</strong> &nbsp;
        🟢 <strong>High Match</strong> — strong functional + tool alignment. Apply immediately. &nbsp;|&nbsp;
        🟡 <strong>Stretch but Apply</strong> — strong functional fit, some tool gap. Your background transfers; worth applying.
      </div>
      <p style="color:#bbb;font-size:10px;text-align:center;margin-top:12px;">
        Job Hunt Automation &bull; Powered by Greenhouse / Lever / Ashby / Workable APIs &bull; Chicago + Remote roles
      </p>
    </body>
    </html>"""


def send_email(jobs: list[Job], dry_run: bool = False) -> bool:
    sender    = os.environ.get("EMAIL_SENDER", "")
    password  = os.environ.get("EMAIL_PASSWORD", "")
    recipient = os.environ.get("EMAIL_RECIPIENT", sender)

    if not sender or not password:
        logger.error("EMAIL_SENDER / EMAIL_PASSWORD not set. Skipping email.")
        return False

    run_date = datetime.now().strftime("%B %d, %Y")
    high = sum(1 for j in jobs if getattr(j, "label", "") == "High Match")
    subject = f"🎯 Daily Jobs — {run_date} | {high} High Match, {len(jobs)-high} Stretch"
    html_body = _build_html(jobs, run_date)

    if dry_run:
        print("\n" + "=" * 65)
        print(f"DRY RUN — {subject}")
        print("=" * 65)
        for i, job in enumerate(jobs, 1):
            label = getattr(job, "label", "?")
            print(f"  #{i:2d} [{job.score:3d}] [{label:16s}] {job.company:25s} | {job.title}")
            print(f"       📍 {job.location:20s} | {job.url}")
        print("=" * 65 + "\n")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = sender
        msg["To"]      = recipient
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        logger.info(f"Email sent → {recipient}: {len(jobs)} jobs ({high} High Match).")
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False
