"""
Partners User List Job

Fetches password-protected PDF from Partners Credit email,
unlocks it, and posts to Teams via Power Automate webhook.
"""

import base64
import io
import logging
from datetime import datetime, timezone
import requests
import pikepdf

logger = logging.getLogger('NexusMonitor.jobs.partners_user_list')

JOB_NAME = "partners_user_list"
INTERVAL_MINUTES = 5

SENDER_FILTER = "support@partnerscredit.com"
SUBJECT_FILTER = "Partners User List"
KEYVAULT_PASSWORD_SECRET = "partnerscredit-admin-password"


def run(context):
    """
    Check for new Partners Credit emails, unlock PDF attachments,
    and post to Teams via webhook.
    """
    mailbox = context.config.get("monitor_mailbox", "nexus@highlandsmortgage.com")
    webhook_url = context.config.get("teams_webhook_url")

    if not webhook_url:
        logger.error("No teams_webhook_url configured - skipping job")
        return

    # Fetch recent emails with subject filter (server-side), 24h window
    messages = context.graph_client.read_recent_emails(
        mailbox=mailbox,
        subject_filter=SUBJECT_FILTER,
        minutes_ago=1440,
        max_results=50
    )

    if not messages:
        logger.info("No new emails found")
        return

    # Client-side sender filter
    matching = []
    for msg in messages:
        sender = msg.get('from', {}).get('emailAddress', {}).get('address', '').lower()
        if SENDER_FILTER.lower() in sender:
            matching.append(msg)

    if not matching:
        logger.info(f"Found {len(messages)} email(s) but none from {SENDER_FILTER}")
        return

    # Get PDF password from Key Vault
    try:
        pdf_password = context.keyvault.get_vendor_credential('partnerscredit', 'admin-password')
    except Exception as e:
        logger.error(f"Failed to get PDF password from Key Vault: {e}")
        return

    processed_count = 0
    error_count = 0

    for msg in matching:
        msg_id = msg.get('id')
        subject = msg.get('subject', 'Unknown')

        if context.state.is_processed(JOB_NAME, msg_id):
            continue

        logger.info(f"Processing email: {subject}")

        try:
            # Get attachments
            attachments = context.graph_client.get_message_attachments(mailbox, msg_id)

            # Find first PDF
            pdf_attachment = None
            for att in attachments:
                content_type = (att.get('contentType') or '').lower()
                name = (att.get('name') or '').lower()
                if 'pdf' in content_type or name.endswith('.pdf'):
                    pdf_attachment = att
                    break

            if not pdf_attachment:
                logger.warning(f"No PDF attachment found in email: {subject}")
                context.state.mark_processed(JOB_NAME, msg_id)
                continue

            filename = pdf_attachment.get('name', 'Partners_User_List.pdf')
            logger.info(f"Found PDF: {filename}")

            # Decode attachment
            pdf_bytes = base64.b64decode(pdf_attachment['contentBytes'])

            # Unlock PDF
            try:
                input_stream = io.BytesIO(pdf_bytes)
                output_stream = io.BytesIO()
                with pikepdf.open(input_stream, password=pdf_password) as pdf:
                    pdf.save(output_stream, encryption=False)
                unlocked_bytes = output_stream.getvalue()
                logger.info(f"PDF unlocked: {filename} ({len(unlocked_bytes)} bytes)")
            except pikepdf.PasswordError:
                logger.error(f"Wrong PDF password for: {filename} - will retry next cycle")
                error_count += 1
                continue

            # POST to Power Automate webhook
            payload = {
                "filename": filename,
                "content": base64.b64encode(unlocked_bytes).decode('utf-8'),
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            }

            response = requests.post(webhook_url, json=payload, timeout=60)

            if response.status_code in (200, 201, 202):
                logger.info(f"Posted to Teams: {filename} (HTTP {response.status_code})")
                context.state.mark_processed(JOB_NAME, msg_id)
                processed_count += 1
            else:
                logger.error(f"Webhook failed: HTTP {response.status_code} - {response.text[:200]}")
                error_count += 1

        except Exception as e:
            logger.error(f"Error processing email '{subject}': {e}")
            error_count += 1

    logger.info(f"Job complete: {processed_count} processed, {error_count} errors, "
               f"{len(matching)} total emails checked")
