"""
Partners User List Job

Fetches password-protected PDF from Partners Credit email,
unlocks it, and uploads to the Partners Credit channel in Teams.
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
SUBJECT_FILTER = "User List"

# Teams channel: Nexus-App > Partners Credit
TEAM_ID = "57f03bc5-c699-407d-9b31-9c062ba4728d"
CHANNEL_ID = "19:ecd5913c21ba45019c12964afcb897ab@thread.tacv2"
DRIVE_ID = "b!mpZUhKpGR0qiU-4qvYykc7RryjJEvyVHpjNblKqqWq9mithcaTeQRpypoH-LjrxX"
FOLDER_ID = "01GS6S2FXDYGWD3EA645EZ6Z5YQUKEZU2P"


def _upload_to_teams(token: str, unlocked_bytes: bytes, filename: str) -> str:
    """Upload PDF to Teams channel files and return the web URL"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/pdf"
    }

    # Upload file to the channel's SharePoint folder
    upload_url = (
        f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}"
        f"/items/{FOLDER_ID}:/{filename}:/content"
    )

    resp = requests.put(upload_url, headers=headers, data=unlocked_bytes, timeout=60)

    if resp.status_code in (200, 201):
        file_data = resp.json()
        web_url = file_data.get("webUrl", "")
        logger.info(f"Uploaded to SharePoint: {filename}")
        return web_url
    else:
        raise Exception(f"Upload failed: HTTP {resp.status_code} - {resp.text[:200]}")


def _post_webhook_notification(webhook_url: str, filename: str, file_url: str):
    """Post an Adaptive Card notification to Teams via Power Automate webhook"""
    timestamp = datetime.now(timezone.utc).strftime('%m/%d/%Y %I:%M %p UTC')
    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Partners Credit User List",
                            "weight": "Bolder",
                            "size": "Medium"
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "File", "value": filename},
                                {"title": "Processed", "value": timestamp},
                                {"title": "Status", "value": "Unlocked and uploaded"}
                            ]
                        },
                        {
                            "type": "ActionSet",
                            "actions": [
                                {
                                    "type": "Action.OpenUrl",
                                    "title": "Open File",
                                    "url": file_url
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }

    resp = requests.post(webhook_url, json=payload, timeout=60)

    if resp.status_code in (200, 201, 202):
        logger.info("Posted notification to Teams channel")
    else:
        logger.warning(f"Webhook notification failed: HTTP {resp.status_code} - {resp.text[:200]}")


def run(context):
    """
    Check for new Partners Credit emails, unlock PDF attachments,
    and upload to Teams channel.
    """
    mailbox = context.config.get("monitor_mailbox", "nexus@highlandsmortgage.com")

    # Fetch recent emails with subject filter (server-side)
    messages = context.graph_client.read_recent_emails(
        mailbox=mailbox,
        subject_filter=SUBJECT_FILTER,
        minutes_ago=4320,  # 3 days — state tracking prevents reprocessing
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

    # Get Graph API token for file upload
    auth = context.config.get('_auth')
    if not auth:
        logger.error("No auth available for file upload")
        return
    token = auth.get_token(["https://graph.microsoft.com/.default"])
    if not token:
        logger.error("Failed to acquire token for file upload")
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

            # Upload to Teams channel SharePoint folder
            file_url = _upload_to_teams(token, unlocked_bytes, filename)

            # Post notification card with link to file
            webhook_url = context.config.get("teams_webhook_url")
            if webhook_url:
                _post_webhook_notification(webhook_url, filename, file_url)
            else:
                logger.info("No webhook URL configured - file uploaded but no notification sent")

            context.state.mark_processed(JOB_NAME, msg_id)
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing email '{subject}': {e}")
            error_count += 1

    logger.info(f"Job complete: {processed_count} processed, {error_count} errors, "
               f"{len(matching)} total emails checked")
