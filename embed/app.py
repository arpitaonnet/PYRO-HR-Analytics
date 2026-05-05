from flask import Flask, jsonify, send_from_directory
import requests, os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TENANT_ID     = os.getenv("AZURE_TENANT_ID")
CLIENT_ID     = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
WORKSPACE_ID  = os.getenv("PBI_WORKSPACE_ID")
REPORT_ID     = os.getenv("PBI_REPORT_ID")
USERNAME      = os.getenv("PBI_USERNAME")
PASSWORD      = os.getenv("PBI_PASSWORD")

def get_aad_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "grant_type":    "password",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username":      USERNAME,
        "password":      PASSWORD,
        "scope":         "https://analysis.windows.net/powerbi/api/.default"
    })
    data = resp.json()
    print("AAD Response:", data)  # add this line
    if "access_token" not in data:
        print("AAD token error:", data)
        return None
    return data["access_token"]

def get_embed_token(aad_token, username, role):
    dataset_id = get_dataset_id(aad_token)
    print("Dataset ID:", dataset_id)

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/reports/{REPORT_ID}/GenerateToken"
    resp = requests.post(url,
        headers={"Authorization": f"Bearer {aad_token}"},
        json={
            "accessLevel": "View",
            "identities": [{
                "username": username,
                "roles":    [role],
                "datasets": [dataset_id]
            }]
        }
    )
    print("Embed token response:", resp.json())
    return resp.json()

def get_dataset_id(aad_token):
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/reports/{REPORT_ID}"
    resp = requests.get(url,
        headers={"Authorization": f"Bearer {aad_token}"}
    )
    return resp.json().get("datasetId", "")

@app.route("/api/embed-token")
def embed_token():
    from flask import request
    role_map = {
        "executive": "Role_Executives",
        "hr":        "Role_HR",
        "employee":  "Role_Employee"
    }
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