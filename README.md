# Movie Agent Demo

Flask REST API and web interface for the Movie Agent Service.

**Author:** Alireza Barzin Zanganeh  
**Website:** [zanganehai.com](https://www.zanganehai.com/about)

## Overview

This Flask application provides a web interface and REST API for the Movie Agent Service. It offers an interactive UI for movie queries, poster analysis, and programmatic API endpoints.

## Features

- Web UI with chat interface and image analysis
- REST API for programmatic access
- Encrypted API key storage
- Session-based memory isolation
- Automatic query classification

## Quick Start

### Prerequisites

- Python 3.10+
- Movie Agent Service (parent directory)
- OpenAI API key (required for embeddings)
- Groq or OpenAI API key (for LLM)

### Installation

```bash
pip install -r requirements.txt

export PYTHONPATH=../movie-agent-service/src:$PYTHONPATH

python app.py
```

The application runs on `http://localhost:8765` by default.

## First-Time Setup

On first launch, you'll see a setup wizard:

1. Choose LLM provider (Groq or OpenAI)
2. Enter API keys (encrypted and stored locally)
3. Configure optional settings (vision, fuzzy matching, etc.)

Configuration files (`config.encrypted` and `.master_key`) are gitignored and never exposed in logs or responses. To reset configuration, delete these files or use the "Reset Config" button in the UI.

## Web UI

### Chat Interface

The chat interface supports:
- Natural language movie search
- Recommendations and queries
- Interactive quizzes
- Rating comparisons (shows top-rated movies by category)
- Actor, director, and year searches
- Statistics queries with formatted output

### Image Analysis

Upload movie poster images (JPG, PNG, JPEG) to:
- Identify the movie title
- Analyze visual mood and themes
- Infer genres from visual elements
- Get confidence scores

After analysis, you can ask questions about the movie in the chat interface.

## API Endpoints

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
  "quiz_data": null
}
```

### POST /poster

Analyze a movie poster image.

**Request:** `multipart/form-data` with `image` field

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

### POST /reset-config

Reset configuration (requires authentication in production).

## Statistics Display

Statistics responses are automatically formatted in the UI:
- Top rated movies (ranked list)
- Highest/lowest rated movies
- Average ratings with counts
- Genre distributions

When using the API programmatically, statistics are returned as formatted text in the `answer` field. You can detect statistics responses by checking the `tools_used` field for `get_movie_statistics`.

## Session Management

The API uses Flask sessions for state management:
- Unique session ID per browser session
- Conversation history
- Quiz state (questions, score)
- Poster context (last analyzed poster)

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request
- `500`: Server error
- `503`: Service not configured

Error responses include JSON with an `error` field describing the issue.

## Development

### Project Structure

```
movie-agent-demo/
├── app.py              # Flask application
├── config_manager.py  # Configuration management
├── templates/         # HTML templates
├── static/           # CSS and JavaScript
└── logs/             # Application logs
```

### Running in Development

```bash
export FLASK_DEBUG=1
python app.py
```

Logs are written to `logs/flask_app_YYYYMMDD.log` with request/response details, errors, and performance metrics.

## Limitations

This demo uses a limited movie dataset. Results may not include all movies compared to a production database.

## License

MIT License - see LICENSE file for details.
