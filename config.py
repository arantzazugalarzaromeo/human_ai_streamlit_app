"""
Configuration file for API keys and settings
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Mistral AI Configuration
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Note: API key is optional - the app will show a message if not configured
# For Streamlit Cloud, set MISTRAL_API_KEY in the Secrets section






