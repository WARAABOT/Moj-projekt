"""Run ONCE per channel on your own computer to allow uploads:

    pip install google-auth-oauthlib
    python faceless/get_token.py client_secret.json

A browser opens: log in, pick the YouTube channel, click Allow. The printed refresh token
goes into a GitHub secret named YT_TOKEN_<CHANNEL> (e.g. YT_TOKEN_HISTORY).
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]

flow = InstalledAppFlow.from_client_secrets_file(
    sys.argv[1] if len(sys.argv) > 1 else "client_secret.json",
    SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
print("\nRefresh token (keep it secret):\n" + creds.refresh_token)
