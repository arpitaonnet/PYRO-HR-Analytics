# Production Deployment Guide

## Current Implementation (Master User Pattern)

This project uses the **Master User (ROPC)** authentication pattern.
Suitable for development, demos, and portfolio showcasing.

### Why Master User was used
- Tenant licence: Power BI Standard + Fabric Trial
- Power BI Application permissions require PPU or Azure AD Premium P1
- Application permissions not available in Azure AD portal under current licence

### Limitations
- Admin password stored in configuration
- MFA must be disabled on master account
- Token tied to a real user account
- Not recommended for customer-facing production systems

---

## Production Implementation (Service Principal Pattern)

### Licence requirements
- Power BI Premium Per User (PPU) ~$20/user/month
- OR Azure AD Premium P1 ~$6/user/month
- OR Fabric F SKU capacity

### Step 1 — Azure AD
- App Registration → API permissions
- Add **Application permissions** (not Delegated):
  - `Report.ReadAll`
  - `Dataset.ReadAll`
- Grant admin consent

### Step 2 — Power BI Admin Portal
- Tenant settings → Developer settings
- Enable "Service principals can use Fabric APIs"
- Apply to specific security group containing PYRO-Embed-App

### Step 3 — Azure Key Vault
```bash
az keyvault create --name pyro-keyvault --resource-group pyro-rg
az keyvault secret set --vault-name pyro-keyvault \
  --name "pbi-client-secret" --value "your-secret"
```

### Step 4 — Code changes (app.py)

**Change 1 — Switch grant_type**
```python
# Current (Master User)
"grant_type": "password",
"username":   USERNAME,
"password":   PASSWORD,

# Production (Service Principal)
"grant_type": "client_credentials",
# remove username and password entirely
```

**Change 2 — Read secret from Key Vault**
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

kv = SecretClient(
    vault_url="https://pyro-keyvault.vault.azure.net/",
    credential=DefaultAzureCredential()
)
CLIENT_SECRET = kv.get_secret("pbi-client-secret").value
```

**Change 3 — Get user identity from session**
```python
# Current (insecure — trusts frontend)
username = request.args.get("username")
role_key = request.args.get("role")

# Production (secure — from verified session)
username = session["user"]["email"]
role_key = session["user"]["pbi_role"]
```

### Step 5 — Deploy to Azure App Service
```bash
az webapp create \
  --name pyro-embed \
  --resource-group pyro-rg \
  --runtime "PYTHON:3.11"

az webapp config appsettings set \
  --name pyro-embed \
  --settings \
    AZURE_TENANT_ID=your-tenant-id \
    AZURE_CLIENT_ID=your-client-id \
    KEY_VAULT_URL=https://pyro-keyvault.vault.azure.net/
```

### Step 6 — Security hardening
- Enable HTTPS only on App Service
- Set CORS to your frontend domain only
- Enable Application Insights for monitoring
- Set up proactive token refresh before expiry

---

## Architecture comparison

| Concern | Master User (current) | Service Principal (production) |
|---|---|---|
| Auth flow | ROPC — username + password | Client credentials — no password |
| MFA | Must be disabled | Always enabled |
| Secret storage | .env file | Azure Key Vault |
| User identity | Query params | Verified session/JWT |
| Deployment | Local machine | Azure App Service |
| Monitoring | print() statements | Azure Application Insights |

---

## Key insight

The embed architecture, RLS logic, and GenerateToken flow are
**identical** between both patterns. The only difference is
**how the backend authenticates to Azure AD**.

Upgrading from Master User to Service Principal is a
**one-line change** in the token request — everything else stays the same.