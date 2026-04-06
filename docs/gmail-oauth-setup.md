# Gmail OAuth Setup

These instructions configure a Google Cloud project and generate the `credentials.json` and `token.json` files required by the Gmail integration.

## 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Name it (e.g. `najdi-slevu`) and click **Create**

## 2. Enable the Gmail API

1. In the project, open **APIs & Services** → **Library**
2. Search for **Gmail API** and click it
3. Click **Enable**

## 3. Configure the OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** → **Create**
3. Fill in:
   - App name: `najdi-slevu`
   - User support email: your email
   - Developer contact: your email
4. Click **Save and Continue** through the remaining steps (no scopes needed at this stage)
5. Add your Google account as a **Test user** on the last screen

## 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `najdi-slevu-desktop`
5. Click **Create**
6. Click **Download JSON** — save the file as `credentials.json` in the project root

## 5. Run the First Auth Flow

With your virtual environment active and `credentials.json` in place:

```bash
python - <<'EOF'
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)

import json, pathlib
pathlib.Path("token.json").write_text(creds.to_json())
print("token.json written")
EOF
```

A browser window will open. Sign in with the test account and grant read access. `token.json` is created automatically and reused on subsequent runs.

> **Never commit** `credentials.json` or `token.json` — add them to `.gitignore`.

## .gitignore entries

```
credentials.json
token.json
```
