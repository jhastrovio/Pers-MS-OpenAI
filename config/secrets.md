# 🔐 Project Secrets Reference

> Internal-only. DO NOT COMMIT this file. Use for onboarding, config audits, and secret management.

---

## ✅ Azure Authentication (OAuth2 / Token Exchange)

| Key | Description | Storage |
|-----|-------------|---------|
| `AZURE_TENANT_ID` | Azure AD tenant used for login flows | GitHub Secret / Azure App Setting |
| `AZURE_CLIENT_ID` | App registration ID | GitHub Secret / Azure App Setting |
| `AZURE_CLIENT_SECRET` | App registration secret | GitHub Secret / Azure App Setting |

---

## 🤖 Azure OpenAI Configuration

| Key | Description | Storage |
|-----|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | URL for Azure OpenAI resource | GitHub Secret / Azure App Setting |
| `AZURE_OPENAI_API_KEY` | API key for Azure OpenAI access | GitHub Secret / Azure App Setting |
| `AZURE_OPENAI_API_VERSION` | API version used (e.g., 2023-05-15) | GitHub Variable / `.env` |
| `AZURE_COMPLETION_DEPLOYMENT_ID` | Deployment name for `gpt-35-turbo` or similar | GitHub Variable / `.env` |
| `AZURE_EMBEDDING_DEPLOYMENT_ID` | Deployment name for `text-embedding-ada-002` | GitHub Variable / `.env` |

---

## 🧠 OpenAI (Optional Fallback)

| Key | Description | Storage |
|-----|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (non-Azure) | `.env` (local only) |
| `EMBEDDING_MODEL_NAME` | e.g. `text-embedding-ada-002` | `.env` |
| `COMPLETION_MODEL_NAME` | e.g. `gpt-4`, `gpt-3.5-turbo` | `.env` |

---

## 👤 App Metadata

| Key | Description | Storage |
|-----|-------------|---------|
| `USER_EMAIL` | Developer or default user identity | GitHub Variable / `.env` |
| `APP_USER_EMAIL` | Alias used internally | `.env` |

---

## 🛠 GitHub / Deployment

| Key | Description | Storage |
|-----|-------------|---------|
| `AZURE_APP_NAME` | Name of the App Service | GitHub Secret |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription used for deployments | GitHub Secret |
| `AZURE_WEBAPP_PUBLISH_PROFILE` | Deployment profile from Azure | GitHub Secret |

---

## ⏳ Future Placeholder Keys

| Key | Purpose |
|-----|---------|
| `STORAGE_ACCOUNT_NAME` | Azure Blob / File use |
| `DATABASE_URL` | External PostgreSQL, CosmosDB, etc. |
| `SECRET_SALT_KEY` | For hashing / token signing |
| `REDIS_URL` | For caching, if used |
