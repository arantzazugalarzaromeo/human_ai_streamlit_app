# AI Study Assistant - Complete System Documentation

## Overview

The AI Study Assistant is a Streamlit-based web application that helps university students study more effectively by analyzing their course materials (PDFs, PowerPoint presentations, images) and providing intelligent study support. The system extracts key topics, ranks them by importance, builds a concept map showing relationships, and provides an AI-powered chatbot tutor that can explain topics, answer questions, and generate practice questions.

---

## System Architecture

### Technology Stack
- **Frontend Framework**: Streamlit (Python web framework)
- **AI Model**: Mistral AI (`mistral-small-latest`) via LangChain
- **Text Processing**: PyPDF2, python-pptx, pytesseract (OCR)
- **Semantic Search**: sentence-transformers (all-MiniLM-L6-v2 embeddings)
- **Graph Visualization**: Graphviz
- **Session Management**: Streamlit session state
- **File Storage**: Local filesystem (`uploads/` directory)

### Project Structure
```
Human-AI-/
├── app.py                          # Main router and page configuration
├── screens/                        # UI screens/pages
│   ├── welcome.py                 # Welcome page with file upload and session management
│   ├── analyzing.py               # Loading screen during analysis
│   ├── dashboard.py               # Main dashboard with topic rankings and chat
│   └── concept_map.py             # Concept map visualization
├── analysis/                      # Core analysis pipeline
│   ├── pipeline.py                # Main analysis orchestrator
│   ├── text_extraction.py         # Extract text from PDFs, PPTX, images
│   ├── topic_extraction.py        # Extract and score topics
│   └── topic_graph.py             # Build concept map graph
├── services/                      # AI and business logic services
│   ├── dashboard_chat_service.py  # Main chatbot service (4 capabilities)
│   ├── mistral_service.py         # Topic teaching service
│   ├── edge_tutor_service.py      # Connection explanation service
│   ├── practice_questions_service.py  # Practice question generation
│   ├── concept_map_service.py     # AI-powered relationship analysis
│   ├── rag_service.py             # Retrieval-Augmented Generation
│   ├── topic_analysis_service.py  # Mistral-based topic extraction
│   └── evaluation_service.py      # Quality assurance evaluator
├── components/                    # Reusable UI components
│   └── chat.py                    # Chat interface component
└── utils/                         # Utility functions
    └── file_validation.py         # File size and validation checks
```

---

## Core Workflow

### 1. File Upload & Validation (`screens/welcome.py`)

**Process:**
1. User uploads files (PDF, PPTX, PNG, JPG, JPEG) via Streamlit file uploader
2. Files are saved to `uploads/` directory
3. `utils/file_validation.py` validates:
   - Individual file size ≤ 50 MB
   - Total size ≤ 200 MB
   - Files are not empty
4. Valid files are stored in `st.session_state["saved_files"]`
5. User clicks "Start analysis" button

**Session Management:**
- Previous sessions are stored in `st.session_state["previous_sessions"]` (max 5 sessions)
- Each session contains: `name`, `analysis_result`, `saved_files`, `uploaded_files`, `chats`
- Sessions are auto-saved when user uploads new files (current session is saved first)
- Sessions can be restored by clicking on session cards in the left sidebar
- Sessions can be deleted with the 🗑️ button

---

### 2. Text Extraction (`analysis/text_extraction.py`)

**Process:**
1. `extract_all_text()` processes each file based on extension:
   - **PDF**: Uses PyPDF2 to extract text from each page
   - **PPTX**: Uses python-pptx to extract text from shapes, identifies titles vs body text
   - **Images**: Uses pytesseract OCR to extract text
2. For PPTX files, also extracts structured slide data:
   - `title`: Slide title text
   - `body`: Slide body text
   - `is_learning_objectives`: Detected if slide contains "learning objectives", "by the end", "objectives", etc.
   - `is_key_ideas`: Detected if slide contains "key ideas", "summary", "takeaways", etc.
   - `slide_index`: Position of slide in presentation
3. Returns:
   - `text_dict`: Mapping of file_path → extracted_text
   - `extraction_errors`: List of error messages for failed files
   - `structured_slides`: Mapping of file_path → list of structured slide dicts (PPTX only)

---

### 3. Topic Extraction (`analysis/topic_extraction.py`)

**Two Approaches:**

#### A. Mistral-Based Extraction (Primary)
- Uses `services/topic_analysis_service.py`
- Sends document text to Mistral AI with prompt to extract 5-15 key topics
- Mistral returns JSON array with topic names, importance levels, and reasons
- More intelligent, understands context and importance

#### B. Pattern-Based Extraction (Fallback)
- Extracts headings (short lines, ALL CAPS, Title Case, numbered/bulleted)
- Extracts frequent n-grams (bigrams and trigrams appearing ≥2 times)
- Scores topics using `_score_importance_structured()`:
  - **Slide titles**: 10.0 points
  - **Learning objectives slide titles**: 15.0 points
  - **Learning objectives slide body**: 8.0 points
  - **Key ideas/summary slide titles**: 12.0 points
  - **Key ideas/summary slide body**: 6.0 points
  - **Early slides (first 3 or 10%)**: +3.0 bonus
  - **Recap slides (last 3 or 10%)**: +3.0 bonus
  - **Body text mentions**: 1.0 point per mention

**Importance Assignment:**
- Uses dynamic thresholds based on score distribution (not fixed thirds)
- Finds natural breaks in score distribution (like ChatGPT would)
- Rules:
  - Topics in learning objectives → at least "core"
  - Topics with only 1 mention and score < 5.0 → "extra"
  - Exam-critical threshold: top 30% of score range OR score ≥ 15.0
  - Core threshold: middle 40% of score range OR score ≥ 8.0
- Returns list of topics with: `name`, `importance` (exam_critical/core/extra), `score`

**No Fixed Limits:**
- System extracts ALL important topics (not limited to 15)
- Importance labels filter by actual importance
- Like ChatGPT - finds as many topics as are important

---

### 4. Topic Graph Construction (`analysis/topic_graph.py`)

**Process:**
1. Creates nodes for each topic (with normalized IDs)
2. Builds edges using multiple signals:

   **A. Mistral AI Analysis (Highest Priority - 10.0 points)**
   - Uses `services/concept_map_service.py`
   - Mistral analyzes topics and content to determine parent-child relationships
   - Returns directed edges (parent → child) based on actual content understanding
   - Example: "Machine Learning" → "Neural Networks" (neural networks are a type of ML)

   **B. Structured Slide Patterns:**
   - **Co-occurrence on same slide** (3.0 points): Topics appearing together
   - **Title-bullet relationships** (4.0 points): Topic in title → topic in body (hierarchical)
   - **Consecutive slides** (0.5 points): Topics on adjacent slides
   - **Semantic similarity** (0.5-1.0 points): Using sentence-transformers embeddings

   **C. Importance-Based Hierarchy:**
   - More important topics (exam_critical) become parents of less important topics
   - Directed edges: parent → child

3. **Transitive Reduction:**
   - Removes redundant edges using `_transitive_reduction()`
   - If A → B and B → C exist, then A → C is redundant and removed
   - Creates cleaner, more tree-like structure

4. **Edge Filtering:**
   - Only edges with strength ≥ 2.0 are included
   - Filters out weak/noise connections

5. Returns graph with: `nodes` (id, label, importance) and `edges` (list of (parent_id, child_id) tuples)

---

### 5. Centrality-Based Re-ranking (`analysis/pipeline.py`)

**Process:**
1. After graph is built, calculates centrality scores:
   - Counts number of edges per node
   - Normalizes by maximum edge count
2. Adds centrality boost to topic scores: `score += centrality * 2.0`
3. Re-sorts topics by updated scores
4. Re-assigns importance labels using dynamic thresholds (same logic as topic extraction)

---

### 6. Analysis Pipeline (`analysis/pipeline.py`)

**Main Function: `analyze_files(file_paths)`**

**Steps:**
1. Extract text from all files → `text_dict`, `extraction_errors`, `structured_slides`
2. Extract topics (Mistral if available, else pattern-based) → `topics`
3. Build topic graph → `topic_graph`
4. Calculate centrality and re-rank topics
5. Return analysis result:
   ```python
   {
       "topics": [...],              # List of topic dicts
       "topic_graph": {...},         # Graph with nodes and edges
       "text_dict": {...},           # For RAG later
       "structured_slides": {...},   # For RAG later
       "extraction_errors": [...],   # Error messages
       "summary": {...},             # Stats (num_files, num_topics, etc.)
       "estimated_seconds": 5-15     # Time estimate
   }
   ```

---

## User Interface

### Welcome Page (`screens/welcome.py`)

**Layout:**
- **Left Sidebar** (1/7 width): "Previous Sessions" list
  - Shows up to 5 saved sessions
  - Each session: clickable card with session name (file names)
  - Delete button (🗑️) for each session
- **Main Content** (6/7 width): Centered
  - Title: "Study Less. Understand More."
  - Upload message
  - File uploader (drag & drop or click)
  - "Start analysis" button

**Features:**
- Auto-saves current session when uploading new files (if session exists)
- Prevents duplicate saves (checks if session already exists by comparing file lists)
- Reset/undo functionality for accidental uploads

---

### Analyzing Page (`screens/analyzing.py`)

**Display:**
- Loading spinner animation
- Title: "Analyzing your material..."
- Task list:
  - 📚 Extracting key topics
  - 🎯 Ranking topics by importance
  - 🔗 Linking ideas and building concept map
- Timer showing elapsed time
- Auto-redirects to dashboard when analysis completes

---

### Dashboard Page (`screens/dashboard.py`)

**Layout:**
- **Left Column**: Topic rankings
  - Each topic shown as a card with:
    - Colored dot (red=exam_critical, yellow=core, green=extra)
    - Topic name
    - Subtitle explaining importance level
- **Right Column**:
  - Concept map button (hand-drawn style with curved line)
  - Upload new slides button
  - Chat interface (`components/chat.py`)

**Features:**
- Auto-scrolls to top when returning from concept map
- Session saving when clicking "Upload new slides"

---

### Concept Map Page (`screens/concept_map.py`)

**Display:**
- Fullscreen Graphviz visualization (90vh height)
- Horizontal layout (left-to-right)
- Nodes:
  - Ellipse shape, colored by importance (red/yellow/green)
  - Text wrapped to fit (max 20 chars per line)
  - Uniform size for all nodes
- Edges:
  - Directed arrows (parent → child)
  - Purple color (#8b5cf6)
  - Pen width 2.0
- "CLOSE" button (red, large) returns to dashboard

**Features:**
- Opens in fullscreen immediately
- Unconnected nodes appear on top (horizontal line)
- Connected nodes appear below

---

## AI Chatbot System

### Main Chat Service (`services/dashboard_chat_service.py`)

**Four Capabilities:**

#### 1. Ranking Explanations
- **Intent Detection**: Keywords like "why", "important", "ranked", "priority"
- **Process**:
  - Uses `_get_dashboard_chain()` (Mistral with friendly persona)
  - Explains why topics were ranked certain ways based on actual content
  - Quality assurance via `evaluate_and_revise_ranking_response()`

#### 2. Topic Teaching
- **Intent Detection**: Keywords like "teach", "explain", "learn about", "what is"
- **Process**:
  - Uses `_get_teaching_chain()` (Mistral with friendly persona)
  - Retrieves relevant snippets using RAG (`services/rag_service.py`)
  - Progressive teaching: One paragraph at a time, asks if user wants to continue
  - Maintains context via `previous_messages` parameter
  - Tracks `teaching_topic` and `part_tracking` in session state
  - Quality assurance via `evaluate_and_revise_topic_response()`

#### 3. Connection Explanations
- **Intent Detection**: Keywords like "connect", "relationship", "related", "how are"
- **Process**:
  - Uses `explain_topic_connection()` from `services/edge_tutor_service.py`
  - Retrieves co-occurrence snippets where both topics appear
  - Explains how topics relate (or says if they don't)
  - Quality assurance via `evaluate_and_revise_edge_response()`

#### 4. Practice Questions
- **Intent Detection**: Keywords like "practice", "question", "exercise", "quiz"
- **Process**:
  - Uses `generate_practice_questions()` from `services/practice_questions_service.py`
  - Generates 2-3 exam-style questions
  - Varies question types (conceptual, calculation, application)
  - Quality assurance via `evaluate_and_revise_topic_response()`

**Intent Detection Logic:**
- `_detect_intent()` analyzes user question
- Handles follow-up questions (uses "it", "this", "that") by inferring from conversation context
- Maintains teaching context (if already teaching a topic, continues teaching)
- Defaults to ranking if intent unclear

**Topic Extraction:**
- `_extract_topic_names()` finds mentioned topics in question
- Supports partial matches and word-based matching
- For connections, extracts two topic names

**Context Awareness:**
- Passes `previous_messages` to maintain conversation context
- Teaching chain uses chat history to avoid repetition
- Can infer topics from recent conversation if not explicitly mentioned

---

### RAG Service (`services/rag_service.py`)

**Retrieval-Augmented Generation for Grounding Answers**

**Process:**
1. `retrieve_relevant_snippets()` scores text chunks using three signals:

   **A. Direct Mentions (15.0 points)**
   - Exact phrase match
   - Synonym matches (5.0 points)
   - Word overlap (2.0 points per word)

   **B. Semantic Similarity (0-10.0 points)**
   - Uses sentence-transformers embeddings
   - Cosine similarity between topic and chunk embeddings
   - Scaled to 0-10 range

   **C. Structural Importance (0-10.0 points)**
   - In title: +8.0
   - In learning objectives slide: +10.0
   - In key ideas/summary slide: +7.0
   - In examples: +3.0

2. Returns top 5 snippets sorted by combined score
3. Snippets are passed to Mistral as context for grounded answers

**Co-occurrence Retrieval:**
- `retrieve_co_occurrence_snippets()` finds sentences where both topics appear
- Used for connection explanations

---

### Quality Assurance (`services/evaluation_service.py`)

**Invisible Evaluator System**

**Process:**
1. Every AI response is evaluated by a second Mistral model (strict evaluator)
2. Evaluator checks:
   - **Grounding**: Uses information from slides? Avoids hallucinations?
   - **Depth vs Importance**: Appropriate detail for exam_critical/core/extra?
   - **Clarity & Structure**: Clear, understandable, well-organized?
   - **Coverage**: Covers main points from slides?
   - **Tone & Cognitive Load**: Friendly, appropriate length?
   - **Actionability**: Clear next steps?

3. If any score < 4, response is revised by a revision chain
4. Student only sees the perfected response (evaluation is invisible)

**Three Evaluation Types:**
- `evaluate_and_revise_topic_response()`: For topic teaching
- `evaluate_and_revise_edge_response()`: For connection explanations
- `evaluate_and_revise_ranking_response()`: For ranking explanations

---

## AI Model Configuration

### Mistral AI Settings

**Model**: `mistral-small-latest`

**Temperature Settings:**
- **Topic Teaching**: 0.7 (natural, friend-like responses)
- **Ranking Explanations**: 0.7 (natural, conversational)
- **Connection Explanations**: 0.7 (natural, friendly)
- **Practice Questions**: 0.7 (natural, helpful)
- **Topic Extraction**: 0.2 (consistent extraction)
- **Concept Map Relationships**: 0.2 (consistent analysis)
- **Quality Evaluator**: 0.1 (strict, consistent evaluation)
- **Revision Chain**: 0.3 (creative improvements)

**Persona:**
- "Smart student friend" who can explain the whole lecture in a day
- Friendly, warm, encouraging
- Natural, conversational language (not robotic)
- Maintains context throughout conversation
- Grounds answers in uploaded materials (RAG)

---

## Session State Management

**Key Session State Variables:**

```python
st.session_state["page"]                    # Current page: "welcome" | "analyzing" | "dashboard" | "concept_map"
st.session_state["saved_files"]             # List of file paths
st.session_state["uploaded_files"]          # Streamlit uploaded file objects
st.session_state["analysis_result"]         # Complete analysis result dict
st.session_state["previous_sessions"]       # List of saved session dicts
st.session_state["dashboard_chat_messages"] # Chat history for dashboard
st.session_state["_reset_performed"]        # Flag for reset confirmation
st.session_state["_reset_backup"]           # Backup of state before reset
st.session_state["_from_concept_map"]       # Flag to scroll to top
```

**Teaching Progress Tracking:**
```python
st.session_state["dashboard_chat_messages_teaching_topic"]  # Current topic being taught
st.session_state["dashboard_chat_messages_teaching_part"]   # Current part number
```

---

## File Validation (`utils/file_validation.py`)

**Rules:**
- Individual file size: ≤ 50 MB
- Total size: ≤ 200 MB
- Files must exist and not be empty

**Process:**
- Validates each file individually
- Tracks total size across all files
- Returns: `(is_valid, valid_files, error_message)`
- Invalid files are removed from uploads directory

---

## Error Handling

**Text Extraction Errors:**
- Stored in `analysis_result["extraction_errors"]`
- Displayed as warnings on dashboard
- Analysis continues with successfully extracted files

**Mistral API Errors:**
- Falls back to pattern-based extraction if Mistral unavailable
- Chat shows error message if API key missing
- Quality evaluator failures return original response (safety fallback)

**File Validation Errors:**
- Invalid files are skipped
- User sees error message with details
- Valid files are still processed

---

## Key Design Decisions

### 1. Dynamic Topic Extraction
- No fixed limits on number of topics
- Uses intelligent thresholds based on score distribution
- Like ChatGPT - finds as many topics as are important

### 2. Transitive Reduction
- Removes redundant edges for cleaner concept map
- Creates more tree-like structure
- Improves visual clarity

### 3. Progressive Teaching
- One paragraph at a time
- Asks if user wants to continue
- Maintains context to avoid repetition
- Natural conversation flow

### 4. Quality Assurance
- Invisible evaluator perfects all responses
- Students only see high-quality answers
- Ensures accuracy, appropriate depth, clarity

### 5. Context-Aware Chatbot
- Maintains conversation context
- Handles follow-up questions naturally
- Infers topics from conversation if not explicitly mentioned

### 6. RAG Grounding
- All answers grounded in uploaded materials
- Uses multiple signals (direct mentions, semantic similarity, structural importance)
- Prevents hallucinations

### 7. Session Management
- Auto-saves sessions (like ChatGPT)
- Prevents duplicate saves
- Easy restoration of previous work

---

## Dependencies

**Core:**
- `streamlit>=1.28.0`: Web framework
- `langchain>=0.1.0`: LLM orchestration
- `langchain-mistralai>=0.1.0`: Mistral AI integration
- `mistralai>=1.0.0`: Mistral AI SDK

**Text Processing:**
- `pypdf2>=3.0.0`: PDF extraction
- `python-pptx>=0.6.21`: PowerPoint extraction
- `pillow>=10.0.0`: Image processing
- `pytesseract>=0.3.10`: OCR

**AI/ML:**
- `sentence-transformers>=2.2.0`: Semantic embeddings
- `numpy>=1.24.0`: Numerical operations

**Utilities:**
- `python-dotenv>=1.0.0`: Environment variable management
- `pandas>=2.1.0`: Data manipulation
- `networkx>=3.2.0`: Graph operations (if needed)
- `plotly>=5.17.0`: Visualization (if needed)

---

## Environment Setup

**Required:**
- Python 3.8+
- Virtual environment (recommended)
- `.env` file with `MISTRAL_API_KEY=your_key_here`

**Installation:**
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

**Running:**
```bash
streamlit run app.py
```

---

## Future Enhancements (Potential)

1. **Database Storage**: Replace session state with database for persistence
2. **User Authentication**: Multi-user support with accounts
3. **Export Features**: Export concept maps, topic lists, chat history
4. **Advanced Visualizations**: Interactive concept map with zoom/pan
5. **Collaborative Features**: Share sessions with classmates
6. **Mobile Support**: Responsive design for mobile devices
7. **Offline Mode**: Local LLM support for privacy
8. **Analytics**: Track study patterns and progress

---

## Summary

The AI Study Assistant is a comprehensive system that:
1. **Extracts** text from various file formats
2. **Identifies** key topics using AI and pattern matching
3. **Ranks** topics by importance using dynamic, intelligent thresholds
4. **Builds** a concept map showing relationships (with transitive reduction)
5. **Provides** an AI chatbot tutor with 4 capabilities (ranking, teaching, connections, practice)
6. **Grounds** all answers in uploaded materials using RAG
7. **Ensures** quality through invisible evaluator system
8. **Manages** sessions automatically (like ChatGPT)

The system is designed to feel like talking to a smart friend who understands the material deeply but explains it simply, helping students study more effectively and feel more confident about exams.

