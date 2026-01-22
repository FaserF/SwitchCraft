import logging
import requests
import datetime
from typing import Dict, Any, List

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

    def search_messages(self, token: str, mailbox: str, query: str = None) -> List[Dict[str, Any]]:
        """
        Search for messages in a mailbox.
        Requires 'Mail.Read.All' or 'Mail.ReadWrite.All'.
        """
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.GRAPH_BASE_URL}/users/{mailbox}/messages"
        params = {"$top": 20, "$select": "subject,from,receivedDateTime,hasAttachments"}

        if query:
            params["$search"] = f'"{query}"'

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json().get("value", [])
        except Exception as e:
            logger.error(f"Failed to search messages for {mailbox}: {e}")
            raise e

    def get_oof_settings(self, token: str, mailbox: str) -> Dict[str, Any]:
        """
        Get Out of Office settings.
        Requires 'MailboxSettings.Read'.
        """
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.GRAPH_BASE_URL}/users/{mailbox}/mailboxSettings/automaticRepliesSetting"
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get OOF for {mailbox}: {e}")
            raise e

    def set_oof_settings(self, token: str, mailbox: str, oof_data: Dict[str, Any]) -> bool:
        """
        Update Out of Office settings.
        Requires 'MailboxSettings.ReadWrite'.
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        url = f"{self.GRAPH_BASE_URL}/users/{mailbox}/mailboxSettings"
        data = {"automaticRepliesSetting": oof_data}
        try:
            resp = requests.patch(url, headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to set OOF for {mailbox}: {e}")
            raise e

    def get_delegates(self, token: str, mailbox: str) -> List[Dict[str, Any]]:
        """
        List delegates for a mailbox.
        Requires 'User.ReadWrite.All' or 'Directory.ReadWrite.All' in some cases.
        """
        headers = {"Authorization": f"Bearer {token}"}
        # url = f"{self.GRAPH_BASE_URL}/users/{mailbox}/mailboxSettings/delegateMeetingMessageDeliveryOptions" # Proxy for delegation info
        # Or more direct for delegates (Requires specific permissions):
        # url = f"{self.GRAPH_BASE_URL}/users/{mailbox}/delegates" (Beta)

        try:
            # We'll use the beta endpoint for better results if allowed, fallback to v1.0
            beta_url = f"https://graph.microsoft.com/beta/users/{mailbox}/delegates"
            resp = requests.get(beta_url, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("value", [])
            return []
        except Exception:
            return []

    def get_mail_traffic_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Fetches simplified mail traffic stats.
        Dummy implementation for now, preserved for compatibility.
        """
        today = datetime.datetime.now().date()
        data = []
        for i in range(days):
            d = today - datetime.timedelta(days=i)
            data.append({
                "date": d.strftime("%Y-%m-%d"),
                "sent": 10 + (i * 5),
                "received": 20 + (i * 10),
                "blocked": i
            })
        return list(reversed(data))
