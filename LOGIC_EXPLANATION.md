# How Our AI Study Assistant Works

A quick explanation of what we built and how it works.

## The Big Picture

Students upload their course slides, and our system:
1. Extracts and ranks important topics
2. Builds a concept map showing how topics connect
3. Provides a smart chatbot that can explain, teach, and help practice

---

## 1. Topic Extraction & Ranking

**What it does:** Finds all important topics from the slides and ranks them by importance.

**How it works:**
- Uses Mistral AI to intelligently extract topics (no fixed limit - finds as many as are important)
- Scores topics based on where they appear:
  - Slide titles = 10 points
  - Learning objectives = 15 points (titles), 8 points (body)
  - Summary slides = 12 points (titles), 6 points (body)
  - Body text = 1 point per mention
  - First/last slides = +3 bonus
  - Central topics in concept map = +2 bonus
- Ranks into three groups: exam_critical, core, extra

**Key idea:** Topics in titles and learning objectives are more important. The system finds all important topics, not just a fixed number.

---

## 2. Concept Map

**What it does:** Shows how topics connect to each other visually.

**How it works:**
- Creates connections between topics using:
  - Same slide co-occurrence (3.0 points)
  - Title-bullet relationships (4.0 points)
  - Semantic similarity via embeddings (0.5-1.0 points)
  - Mistral AI analysis for content-based relationships (10.0 points - highest priority)
- Only shows edges with strength ≥ 2.0 (filters noise)
- **Transitive reduction:** Removes redundant edges. If A→B and B→C, then A→C is redundant and removed. This makes the map cleaner and more tree-like.
- Opens in fullscreen instantly when clicked
- Auto-scrolls to top when returning to dashboard

**Key idea:** The map shows real relationships, not random co-occurrences. It's simplified to be tree-like and easy to understand.

---

## 3. Smart Chatbot

**What it does:** Acts like a smart, friendly friend who can help with four main things:
1. Explain why topics were ranked the way they were
2. Teach topics step-by-step (progressive learning)
3. Explain how two topics connect (or say if they don't)
4. Generate practice questions

**How it works:**
- Uses Mistral AI with RAG (Retrieval-Augmented Generation) to ground answers in the actual slides
- **Persona:** Smart, friendly friend tone throughout - like talking to your best friend who's really good at explaining things
- **Teaching:** When asked to teach a topic, it explains one aspect at a time, then asks if you want to continue. Each step teaches something NEW (no repetition). Uses chat history to track what was already covered.
- **Responses:** One good paragraph, concise and natural. No "In summary:" sections.
- **Intent detection:** Smart enough to understand follow-up questions and maintain context

**Key idea:** The chatbot feels like a conversation with a knowledgeable friend, not a robot. It's grounded in your actual slides but uses AI intelligence to explain things well.

---

## 4. Previous Sessions

**What it does:** Saves your tutoring sessions so you can come back to them later.

**How it works:**
- When you upload new slides, your current session (including all chat history) is automatically saved
- Sessions appear in a left sidebar on the welcome page
- Click any session card to restore it
- Delete button (🗑️) to remove sessions
- No duplicate saves - clicking on an already-saved session doesn't save it again

**Key idea:** Like ChatGPT - your work is automatically saved and easily accessible.

---

## 5. Topic Explanation Process

**What it does:** When you ask about a topic, it finds the right information and explains it well.

**How it works:**
1. **Understand the topic** - Identifies the topic, its importance level, and related terms
2. **Retrieve context** - Searches slides using:
   - Direct mentions (15 points)
   - Semantic similarity via embeddings (up to 10 points)
   - Structural importance - learning objectives (+10), summaries (+7), titles (+8)
   - Gets top 5 most relevant snippets
3. **Generate explanation** - Mistral AI explains using the retrieved context, adjusting depth based on importance level

**Key idea:** Answers are grounded in YOUR slides, not generic explanations. The system finds the right context and explains it at the right depth.

---

## Technical Details

- **AI Model:** Mistral AI (`mistral-small-latest`) for all intelligent tasks
- **Temperature:** 0.7 for natural, conversational responses
- **RAG:** Uses embeddings and semantic search to find relevant slide content
- **No fixed limits:** System finds as many topics as are important, ranks them intelligently
- **Transitive reduction:** Algorithm removes redundant edges from concept map
- **Session management:** All state saved in Streamlit session state

---

## Summary

The system treats slides as structured data, intelligently extracts and ranks topics, builds a clean concept map showing real relationships, and provides a friendly chatbot that feels like talking to a smart friend. Everything is grounded in the student's actual materials, and the AI uses its intelligence to explain things clearly and helpfully.
