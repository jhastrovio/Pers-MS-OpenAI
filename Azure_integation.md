# Azure Integration in Personal MS Assistant

## 1. Authentication and Authorization

### Microsoft Graph API Authentication
The project uses MSAL (Microsoft Authentication Library) for secure authentication:

```python
# src/graph_1/auth.py
def get_access_token(client_id, client_secret, tenant_id):
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        authority=authority,
        client_credential=client_secret
    )
    token_response = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return token_response["access_token"]
```

This authentication flow:
1. Uses client credentials (client ID and secret)
2. Acquires tokens for Microsoft Graph API
3. Supports application-level permissions

## 2. Email Integration

### Email Fetching Process
The system fetches emails using Microsoft Graph API:

```python
# src/graph_1/fetch_emails.py
def fetch_emails(client_id, client_secret, tenant_id, user_email, max_pages=10):
    token = get_access_token(client_id, client_secret, tenant_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages?$top=50"
    
    # Delta sync support
    last_cursor = load_cursor(CURSOR_FILE)
    if last_cursor:
        url += f"&$filter=lastModifiedDateTime gt {last_cursor}"
```

Key features:
1. **Pagination Support**: Fetches emails in batches of 50
2. **Delta Sync**: Only fetches new/updated emails using cursor tracking
3. **Rich Email Data**: Captures:
   - Subject
   - Sender information
   - Received date
   - Body content
   - Web link
   - Last modified time

## 3. OneDrive Integration

### File Fetching and Processing
The system handles OneDrive files with delta sync support:

```python
# src/graph_1/fetch_onedrive.py
def fetch_from_graph(output_file, client_id, client_secret, tenant_id, user_email):
    access_token = get_access_token(client_id, client_secret, tenant_id)
    base_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/FXStrategy:/children"
    
    # Delta sync implementation
    cursor_time = load_cursor(CURSOR_FILE)
    if cursor_time:
        # Only fetch files modified after last sync
        params = {
            "$orderby": "lastModifiedDateTime desc",
            "$select": "id,name,lastModifiedDateTime,size,file,fileSystemInfo"
        }
```

Key features:
1. **File Type Support**:
   - Text files (.txt)
   - Word documents (.docx)
   - PDF files (.pdf)
   - PowerPoint presentations (.pptx)
   - Excel/CSV files

2. **Smart Processing**:
   ```python
   def extract_text(file_path):
       suffix = file_path.suffix.lower()
       if suffix == ".txt":
           return file_path.read_text(encoding="utf-8")
       elif suffix == ".docx":
           doc = Document(file_path)
           return "\n".join(p.text for p in doc.paragraphs)
       # ... handles other file types
   ```

3. **Delta Sync Implementation**:
   - Tracks last modified times
   - Only downloads new or modified files
   - Maintains cursor state between runs

## 4. Azure OpenAI Integration

The project integrates with Azure OpenAI for embeddings and completions:

```json
{
  "azure_openai_endpoint": "https://pmsgapril25.openai.azure.com/",
  "azure_openai_key": "***************",
  "azure_embedding_model": "text-embedding-ada-002",
  "azure_completion_model": "gpt-35-turbo",
  "azure_deployment_id": "gpt-35-turbo",
  "azure_openai_api_version": "2023-05-15"
}
```

## 5. Data Flow Example

Here's a complete example of how data flows through the system:

1. **Authentication**:
   ```python
   # Get access token
   token = get_access_token(client_id, client_secret, tenant_id)
   ```

2. **Fetch Emails**:
   ```python
   # Fetch recent emails
   emails = fetch_emails(
       client_id=secrets["client_id"],
       client_secret=secrets["client_secret"],
       tenant_id=secrets["tenant_id"],
       user_email=secrets["user_email"]
   )
   ```

3. **Fetch OneDrive Files**:
   ```python
   # Download and process OneDrive files
   fetch_from_graph(
       output_file=output_path,
       client_id=secrets["client_id"],
       client_secret=secrets["client_secret"],
       tenant_id=secrets["tenant_id"],
       user_email=secrets["user_email"]
   )
   ```

4. **Process and Store**:
   - Files are stored in appropriate directories
   - Text is extracted and processed
   - Structured data is handled separately

## 6. Security and Best Practices

1. **Secret Management**:
   - Secrets stored in `config/secrets.json`
   - Never committed to version control
   - Consider using Azure Key Vault for production

2. **Error Handling**:
   ```python
   try:
       # API calls
   except Exception as e:
       print(f"❌ Error processing {file_name}: {e}")
   ```

3. **Logging**:
   - Comprehensive logging of operations
   - UTF-8 support for international content
   - Performance timing for operations

## 7. Azure Resources Used

The project utilizes several Azure resources:
1. **Azure OpenAI Service**:
   - Embedding model: text-embedding-ada-002
   - Completion model: gpt-35-turbo

2. **Microsoft Graph API**:
   - Email access
   - OneDrive file access
   - User profile information

3. **App Service**:
   - FastAPI backend hosting
   - Application Insights for monitoring

Would you like me to dive deeper into any specific aspect of the Azure integration?
