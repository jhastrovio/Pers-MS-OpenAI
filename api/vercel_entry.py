from core.api_1_4_0.main_FastApi import app
from dotenv import load_dotenv

load_dotenv(override=True)  # Ensure environment variables are loaded

# This is required for Vercel's serverless functions
# The app variable is used by Vercel to serve the API 