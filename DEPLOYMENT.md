# Deployment Guide for Streamlit Cloud

This guide will help you deploy your AI Study Assistant to Streamlit Cloud.

## Prerequisites

1. **GitHub Account**: You need a GitHub account
2. **Streamlit Cloud Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)
3. **Mistral API Key**: You'll need your Mistral API key

## Step 1: Prepare Your Repository

1. Make sure your code is in a GitHub repository
2. Ensure `requirements.txt` is in the root directory
3. Ensure `app.py` is in the root directory
4. Make sure `.env` is in `.gitignore` (never commit API keys!)

## Step 2: Push to GitHub

If you haven't already, push your code to GitHub:

```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

## Step 3: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"Sign in with GitHub"** and authorize Streamlit
3. Click **"New app"**
4. Fill in the form:
   - **Repository**: Select your repository
   - **Branch**: `main` (or your default branch)
   - **Main file path**: `app.py`
   - **App URL**: Choose a custom URL (optional)
5. Click **"Deploy!"**

## Step 4: Add Your API Key (Secrets)

1. After deployment starts, go to your app's settings
2. Click **"Secrets"** in the sidebar
3. Add your Mistral API key:

```
MISTRAL_API_KEY=your_actual_api_key_here
```

4. Click **"Save"**
5. The app will automatically redeploy with the new secrets

## Step 5: Verify Deployment

1. Wait for the deployment to complete (usually 1-2 minutes)
2. Visit your app URL
3. Test uploading a file and asking questions
4. Check the logs if there are any errors

## Troubleshooting

### App won't start
- Check the logs in Streamlit Cloud dashboard
- Verify `requirements.txt` has all dependencies
- Make sure `app.py` is in the root directory

### API errors
- Verify `MISTRAL_API_KEY` is set in Secrets
- Check the format: `MISTRAL_API_KEY=your_key` (no quotes, no spaces)

### Import errors
- Make sure all Python files are in the repository
- Check that all imports are correct

### File upload issues
- Streamlit Cloud has file size limits
- Large files may timeout

## Notes

- The app will automatically redeploy when you push to GitHub
- You can set up custom domains in Streamlit Cloud settings
- Monitor usage and costs for your Mistral API

