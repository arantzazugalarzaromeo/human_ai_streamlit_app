@echo off
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Starting Streamlit...
streamlit run app.py --server.headless false
pause

