# Movie Agent API

Flask REST API with Web UI for Movie Agent Service.

**Author:** Alireza Barzin Zanganeh  
**Website:** [zanganehai.com](https://www.zanganehai.com/about)

## Overview

This Flask application provides a web interface and REST API for the Movie Agent Service. It offers an intuitive UI for movie queries and poster analysis, along with programmatic API endpoints.

## Features

- **Web UI**: Interactive chat interface and image analysis
- **REST API**: Programmatic access to all service features
- **Secure Configuration**: Encrypted API key storage
- **Session Management**: Isolated user sessions with memory
- **Intent Routing**: Automatic query classification

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Movie Agent Service installed (see parent directory)
- OpenAI API key (required)
- LLM API key (Groq or OpenAI)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH to include movie-agent-service
export PYTHONPATH=../movie-agent-service/src:$PYTHONPATH

# Run the Flask app
python app.py
```

The application will start on `http://localhost:8765`

## First-Time Setup

On first launch, you'll be guided through a setup wizard:

1. **LLM Provider**: Choose Groq (recommended) or OpenAI
2. **API Keys**: Enter your API keys securely
   - OpenAI API key (required for embeddings)
   - Groq API key (if using Groq for LLM)
   - OpenAI LLM key (if using OpenAI for LLM)
3. **Optional Settings**: Configure vision, fuzzy matching, etc.

**Security:**
- API keys are encrypted and stored locally
- Keys are never exposed in logs or responses
- Configuration files are gitignored

**Reset Configuration:**
- Click "Reset Config" in the UI, or
- Delete `config.encrypted` and `.master_key` files

## Web UI

### Chat Tab

Interactive chat interface for movie queries:
- Natural language movie search
- Movie recommendations
- Interactive quizzes (one question at a time)
- Movie comparisons
- Actor/director/year searches

### Image Analysis Tab

Upload and analyze movie posters:
- **What to Upload**: Movie poster images (JPG, PNG, JPEG)
- **Best Results**: Clear, high-quality poster images
- **Analysis Output**: Movie title, mood, genres, confidence score
- After analysis, ask questions about the movie in the Chat tab

The system uses computer vision to extract visual features and match them with the movie database.

## API Endpoints

### GET /

Serves the web UI homepage.

**Response:** HTML page

---

### POST /chat

Send a chat query to the agent.

**Request:**
```json
{
  "query": "find sci-fi movies from the 90s"
}
```

**Response:**
```json
{
  "answer": "Here are some sci-fi movies from the 1990s:\n\n- The Matrix (1999)\n- Terminator 2 (1991)",
  "movies": ["The Matrix", "Terminator 2"],
  "tools_used": ["movie_search"],
  "llm_latency_ms": 450,
  "tool_latency_ms": 320,
  "latency_ms": 770,
  "reasoning_type": "tool_calling",
  "confidence": 0.9,
  "quiz_data": null
}
```

**Quiz Response (when quiz is active):**
```json
{
  "answer": "Question 1 of 3:",
  "quiz_data": {
    "quiz_active": true,
    "question_id": 1,
    "question": "What year was \"The Matrix\" released?",
    "options": ["1999", "1998", "2000"],
    "progress": {
      "current": 1,
      "total": 3
    },
    "topic": "movies",
    "mode": "random"
  }
}
```

**Status Codes:**
- `200`: Success
- `400`: Bad request (missing query)
- `500`: Server error
- `503`: Service not configured

---

### POST /poster

Analyze a movie poster image.

**Request:**
- Content-Type: `multipart/form-data`
- Form field: `image` (file)

**Response:**
```json
{
  "caption": "science fiction movie poster with futuristic cityscape",
  "title": "The Matrix",
  "mood": "Dark",
  "confidence": 0.9,
  "inferred_genres": ["Sci-Fi", "Action"]
}
```

**Status Codes:**
- `200`: Success
- `400`: Bad request (no image provided)
- `500`: Server error
- `503`: Service not configured

---

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "configured": true
}
```

**Status Codes:**
- `200`: Service is healthy
- `503`: Service not configured

---

### POST /reset-config

Reset configuration (requires authentication in production).

**Response:**
```json
{
  "status": "success",
  "message": "Configuration reset"
}
```

## Session Management

The API uses Flask sessions to manage user state:
- Each browser session gets a unique session ID
- Session state includes:
  - Conversation history
  - Quiz state (active questions, score)
  - Poster context (last analyzed poster)

## Error Handling

All endpoints return appropriate HTTP status codes:
- `400`: Client error (bad request)
- `500`: Server error (internal error)
- `503`: Service unavailable (not configured)

Error responses include a JSON body:
```json
{
  "error": "Error message description"
}
```

## Development

### Project Structure

```
movie-agent-api/
├── app.py              # Flask application
├── config_manager.py  # Secure configuration management
├── templates/         # HTML templates
│   ├── index.html    # Main UI
│   └── setup.html    # Setup wizard
├── static/           # Static assets
│   ├── script.js     # Frontend JavaScript
│   └── style.css     # Styles
└── logs/             # Application logs
```

### Running in Development

```bash
# Enable debug mode
export FLASK_DEBUG=1
python app.py
```

### Logging

Logs are written to `logs/flask_app_YYYYMMDD.log`:
- Request/response logging
- Error tracking
- Performance metrics

## Limitations

This is a demo version using a limited movie dataset. Results may not include all movies compared to a full production database.

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Author

**Alireza Barzin Zanganeh**  
Software Engineer | ML Engineer | GenAI Practitioner

For more information, visit [zanganehai.com](https://www.zanganehai.com/about)
