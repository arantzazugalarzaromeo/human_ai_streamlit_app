# utils/safe_render.py
"""
Simple utility to safely render markdown content that might contain regex patterns.
Renders as HTML to completely bypass Streamlit's markdown parser.
"""
import streamlit as st
import html
import re


def safe_markdown(text: str) -> None:
    """
    Safely render markdown by converting to HTML and bypassing Streamlit's parser.
    This prevents JavaScript regex errors in the browser.
    """
    if not text:
        return
    
    # Convert markdown to HTML manually to bypass Streamlit's markdown parser
    # Process line by line to handle bullet points correctly
    lines = text.split('\n')
    html_lines = []
    
    for line in lines:
        if not line.strip():
            html_lines.append('<br>')
            continue
            
        # Escape HTML first
        escaped_line = html.escape(line)
        
        # Convert markdown patterns to HTML
        # Bold **text** - must come before italic
        escaped_line = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', escaped_line)
        # Italic *text* (but not if it's part of **)
        escaped_line = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', escaped_line)
        # Code `text`
        escaped_line = re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped_line)
        # Links [text](url)
        escaped_line = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', escaped_line)
        
        # Handle bullet points (- or •)
        if line.strip().startswith('-') or line.strip().startswith('•'):
            escaped_line = escaped_line.lstrip('-•').lstrip()
            html_lines.append(f'<li>{escaped_line}</li>')
        else:
            html_lines.append(f'<div>{escaped_line}</div>')
    
    # Wrap in container
    html_text = '<div style="line-height: 1.6;">' + ''.join(html_lines) + '</div>'
    
    # Render as HTML to completely bypass markdown parsing
    st.markdown(html_text, unsafe_allow_html=True)

