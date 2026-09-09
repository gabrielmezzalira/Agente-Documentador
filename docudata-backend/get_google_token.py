"""
Rode este script para gerar o refresh token de Dados ou Dev.

Pré-requisitos:
  pip install google-auth-oauthlib

Como usar:
  1. No Google Cloud Console → APIs & Services → Credentials
     → Create Credentials → OAuth 2.0 Client ID → Desktop app
  2. Cole o Client ID e Client Secret abaixo (ou passe como args)
  3. Dados: python3 get_google_token.py
     Dev:   python3 get_google_token.py --dev
  4. Autorize no browser que vai abrir
  5. Copie os valores impressos no terminal para o .env
"""

import sys

IS_DEV = "--dev" in sys.argv
TOKEN_ENV_NAME = "GOOGLE_REFRESH_TOKEN_DEV" if IS_DEV else "GOOGLE_REFRESH_TOKEN"

CLIENT_ID = input("Cole o GOOGLE_CLIENT_ID: ").strip()
CLIENT_SECRET = input("Cole o GOOGLE_CLIENT_SECRET: ").strip()

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("\nInstale a dependência primeiro:")
    print("  pip install google-auth-oauthlib")
    sys.exit(1)

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=SCOPES,
)

creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\n✅ Copie estes valores para o .env:\n")
print(f"GOOGLE_CLIENT_ID={CLIENT_ID}")
print(f"GOOGLE_CLIENT_SECRET={CLIENT_SECRET}")
print(f"{TOKEN_ENV_NAME}={creds.refresh_token}")
