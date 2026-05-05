from flask import Flask, jsonify, send_from_directory, request
import requests, os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuration — loaded from .env (see .env.example)
# Production: load from Azure Key Vault instead of .env
# ---------------------------------------------------------------------------
TENANT_ID     = os.getenv("AZURE_TENANT_ID")
CLIENT_ID     = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
WORKSPACE_ID  = os.getenv("PBI_WORKSPACE_ID")
REPORT_ID     = os.getenv("PBI_REPORT_ID")
USERNAME      = os.getenv("PBI_USERNAME")
PASSWORD      = os.getenv("PBI_PASSWORD")


def get_aad_token():
    """
    Authenticates using Master User (ROPC) pattern.
    Production upgrade: change grant_type to 'client_credentials'
    and remove username/password — service principal only.
    """
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "grant_type":    "password",        # Production: "client_credentials"
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username":      USERNAME,          # Production: remove this line
        "password":      PASSWORD,          # Production: remove this line
        "scope":         "https://analysis.windows.net/powerbi/api/.default"
    })
    data = resp.json()
    if "access_token" not in data:
        return None
    return data["access_token"]


def get_dataset_id(aad_token):
    """Fetches the dataset ID associated with the report."""
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/reports/{REPORT_ID}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {aad_token}"})
    return resp.json().get("datasetId", "")


def get_embed_token(aad_token, username, role):
    """
    Generates a short-lived embed token with RLS identity.
    The username and role are embedded in the token — Power BI
    applies the DAX filter for that role against the dataset.
    The browser never controls which role is assigned.
    """
    dataset_id = get_dataset_id(aad_token)
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/reports/{REPORT_ID}/GenerateToken"
    resp = requests.post(url,
        headers={"Authorization": f"Bearer {aad_token}"},
        json={
            "accessLevel": "View",
            "identities": [{
                "username": username,    # who is viewing
                "roles":    [role],      # which RLS role
                "datasets": [dataset_id] # which dataset RLS applies to
            }]
        }
    )
    return resp.json()


@app.route("/api/embed-token")
def embed_token():
    """
    Token endpoint — called by the frontend to get an embed token.
    Production: derive username and role from verified session/JWT
    instead of query params.
    """
    role_map = {
        "executive": "Role_Executives",
        "hr":        "Role_HR",
        "employee":  "Role_Employee"
    }

    # Production: replace these two lines with session-based identity
    username = request.args.get("username", os.getenv("PBI_USERNAME"))
    role_key = request.args.get("role", "employee")
    rls_role = role_map.get(role_key, "Role_Employee")

    aad_token = get_aad_token()
    if not aad_token:
        return jsonify({"error": "Failed to get AAD token"}), 500

    embed_data = get_embed_token(aad_token, username, rls_role)

    return jsonify({
        "token":    embed_data.get("token"),
        "embedUrl": f"https://app.powerbi.com/reportEmbed?reportId={REPORT_ID}&groupId={WORKSPACE_ID}",
        "reportId": REPORT_ID
    })


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)