# Azure Deployment Guide

## Prerequisites
- Azure account with active subscription
- GitHub repository set up (personal-ms-chatgpt)
- Azure CLI installed locally

## Step 1: Create Azure Resources

1. **Create Resource Group**
   ```powershell
   az group create --name personal-ms-chatgpt-rg --location westeurope
   ```

2. **Create App Service Plan**
   ```powershell
   az appservice plan create \
     --name personal-ms-chatgpt-plan \
     --resource-group personal-ms-chatgpt-rg \
     --sku B1 \
     --is-linux
   ```

3. **Create Web App**
   ```powershell
   az webapp create \
     --name personal-ms-chatgpt \
     --resource-group personal-ms-chatgpt-rg \
     --plan personal-ms-chatgpt-plan \
     --runtime "PYTHON|3.11" \
     --startup-file "startup.sh"
   ```

## Step 2: Configure GitHub Actions

1. **Generate Azure Credentials**
   ```powershell
   az ad sp create-for-rbac \
     --name "personal-ms-chatgpt" \
     --role contributor \
     --scopes /subscriptions/{subscription-id}/resourceGroups/personal-ms-chatgpt-rg \
     --sdk-auth
   ```
   - Save the output JSON - this will be your `AZURE_CREDENTIALS`

2. **Get Publish Profile**
   ```powershell
   az webapp deployment list-publishing-profiles \
     --name personal-ms-chatgpt \
     --resource-group personal-ms-chatgpt-rg \
     --xml
   ```
   - Save the output - this will be your `AZURE_WEBAPP_PUBLISH_PROFILE`

3. **Add GitHub Secrets**
   - Go to GitHub repository → Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `AZURE_CREDENTIALS`: (JSON from step 1)
     - `AZURE_APP_NAME`: "personal-ms-chatgpt"
     - `AZURE_WEBAPP_PUBLISH_PROFILE`: (XML from step 2)

## Step 3: Configure App Settings

1. **Set Environment Variables**
   ```powershell
   az webapp config appsettings set \
     --name personal-ms-chatgpt \
     --resource-group personal-ms-chatgpt-rg \
     --settings \
     MS_GRAPH_CLIENT_ID="your-client-id" \
     MS_GRAPH_CLIENT_SECRET="your-client-secret" \
     MS_GRAPH_TENANT_ID="your-tenant-id" \
     ENVIRONMENT="production"
   ```

2. **Enable HTTPS Only**
   ```powershell
   az webapp update \
     --name personal-ms-chatgpt \
     --resource-group personal-ms-chatgpt-rg \
     --https-only true
   ```

## Step 4: Deploy

1. Push code to main branch or manually trigger the GitHub Action
2. Monitor deployment in GitHub Actions tab
3. Verify deployment at `https://personal-ms-chatgpt.azurewebsites.net`

## Monitoring and Logs

1. **View Logs**
   ```powershell
   az webapp log tail \
     --name personal-ms-chatgpt \
     --resource-group personal-ms-chatgpt-rg
   ```

2. **Enable Application Insights**
   ```powershell
   az monitor app-insights component create \
     --app personal-ms-chatgpt \
     --location westeurope \
     --resource-group personal-ms-chatgpt-rg
   ```

## Troubleshooting

1. **Check Application Logs**
   - Azure Portal → App Service → Logs
   - Or use Azure CLI command above

2. **Common Issues**
   - If deployment fails, check GitHub Actions logs
   - If app doesn't start, check startup command in startup.sh
   - If environment variables are missing, verify in Application Settings

3. **Health Check**
   - Monitor the `/` endpoint for basic health check
   - Set up Azure Monitor alerts for availability 