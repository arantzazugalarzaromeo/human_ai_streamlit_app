# AI Study Assistant

AI-powered study assistant for university students that analyzes course materials and provides personalized learning paths.

## Local Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate it:
   ```bash
   source venv/bin/activate  # Mac/Linux
   .\venv\Scripts\Activate.ps1  # Windows PowerShell
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your Mistral API key:
   ```
   MISTRAL_API_KEY=your_api_key_here
   ```

5. Run the app:
   ```bash
   streamlit run app.py
   ```

## Deploy to Streamlit Cloud

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

**Quick Steps:**
1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app" and connect your repository
4. Set main file to `app.py`
5. Add `MISTRAL_API_KEY` in the Secrets section
6. Deploy!

## Project Structure

- `app.py` - Main router and global styles
- `screens/` - Screen components (welcome, dashboard, etc.)
- `components/` - Reusable UI components
- `services/` - Business logic and API integrations
- `analysis/` - File processing and topic extraction
- `config.py` - Configuration for API keys
- `requirements.txt` - Python dependencies
