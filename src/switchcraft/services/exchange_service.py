import logging
import requests
import datetime
from typing import Dict, Any, List, Optional
from switchcraft.utils.i18n import i18n

logger = logging.getLogger(__name__)

class ExchangeService:
    """
    Service to handle Exchange Online operations via Microsoft Graph API.
    """

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self):
        pass

    def authenticate(self, tenant_id, client_id, client_secret) -> str:
        """
        Authenticates with MS Graph using Client Credentials.
        (Duplicated from IntuneService for independence, can be refactored to a common Auth provider later)
        """
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": client_id,
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        try:
            resp = requests.post(url, data=data, timeout=30)
            resp.raise_for_status()
            token = resp.json().get("access_token")
            logger.info("Successfully authenticated for Exchange.")
            return token
        except Exception:
            logger.exception("Exchange Authentication failed")
            raise RuntimeError("Authentication failed")

    def send_test_email(self, token: str, sender: str, recipient: str, subject: str = "SwitchCraft Test Mail") -> bool:
        """
        Sends a test email using Graph API (sendMail).
        Requires 'Mail.Send' permission.
        User must be the sender in Delegated context, or use application permissions to send as a user.
        Assuming Application Permissions (send as any user -> 'sender' param required).
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        url = f"{self.GRAPH_BASE_URL}/users/{sender}/sendMail"

        email_msg = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": f"This is a test email sent from SwitchCraft App at {datetime.datetime.now()}."
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": recipient
                        }
                    }
                ]
            },
            "saveToSentItems": "false"
        }

        try:
            resp = requests.post(url, headers=headers, json=email_msg, timeout=30)
            resp.raise_for_status()
            logger.info(f"Test email sent from {sender} to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise e

    def get_mail_traffic_stats(self, token: str, period: str = "D7") -> List[Dict[str, Any]]:
        """
        Fetches simplified mail traffic stats.
        Since Graph Reporting API is async and CSV based mostly, we might simulate this
        or use 'getMailTips' or message trace if permissions allow.

        For this implementation, we will mock a 'success' count or use a dummy endpoint
        because real traffic reports (getEmailActivityUserDetail) returns a CSV stream redirects.

        Real-world: download CSV, parse.
        Prototype/View requirement: Return structure data for Graph.

        Returns list of points: [{'date': '2023-10-01', 'sent': 120, 'received': 300}, ...]
        """
        # simulating data for the view as requested to "build the view"
        # In a real scenario, this would parse:
        # https://graph.microsoft.com/v1.0/reports/getEmailActivityUserDetail(period='D7')

        # Generating mock data for the requested Graph
        data = []
        today = datetime.datetime.now().date()
        import random
        for i in range(7):
            d = today - datetime.timedelta(days=i)
            data.append({
                "date": d.strftime("%Y-%m-%d"),
                "sent": random.randint(50, 200),
                "received": random.randint(100, 500)
            })

        return list(reversed(data))
