#!/usr/bin/env python3
"""
Flask REST API for Movie Agent Service.

Minimal Flask app that uses the MovieAgentApp public API.
No internal imports - only the public facade.

Features secure first-time setup with encrypted configuration storage.
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from dotenv import load_dotenv

# Add movie-agent-service to path
# Note: movie-agent-service should be installed or cloned as a sibling directory
service_path = Path(__file__).parent.parent / "movie-agent-service" / "src"
# Fallback: try current directory if parent doesn't exist
if not service_path.exists():
    service_path = Path(__file__).parent / "movie-agent-service" / "src"
sys.path.insert(0, str(service_path))

# Public API imports only
from movie_agent.app import MovieAgentApp
from movie_agent.config import MovieAgentConfig
from movie_agent.interaction import IntentRouter, IntentType
from config_manager import SecureConfigManager, validate_setup_data

# Load environment variables (for non-sensitive defaults)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(32)  # For session management

# Setup logging
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Clean up old logs on startup
try:
    from movie_agent.utils import cleanup_logs
    cleanup_logs(str(logs_dir), max_files=10, max_age_days=7, pattern="flask_app_*.log")
except Exception as e:
    # Don't fail startup if cleanup fails
    print(f"Warning: Log cleanup failed: {e}")

log_file = logs_dir / f"flask_app_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Flask app started. Logging to: {log_file}")

# Global instances
config_manager = SecureConfigManager()
intent_router = IntentRouter()
agent_app: Optional[MovieAgentApp] = None


def _initialize_agent_from_config():
    """Initialize agent from secure config."""
    global agent_app
    
    # Reuse existing agent if already initialized (preserves SessionContext)
    if agent_app is not None:
        return
    
    if not config_manager.is_configured():
        logger.warning("Config not initialized. Agent will not be available.")
        return
    
    try:
        config_data = config_manager.load_config()
        
        # Set environment variables for service layer based on LLM provider
        llm_provider = config_data.get("llm_provider", "groq")
        
        if llm_provider == "groq":
            # Set GROQ_API_KEY for Groq provider
            if config_data.get("groq_api_key"):
                os.environ["GROQ_API_KEY"] = config_data["groq_api_key"]
        elif llm_provider == "openai":
            # Set OPENAI_API_KEY for OpenAI provider
            if config_data.get("openai_llm_api_key"):
                os.environ["OPENAI_API_KEY"] = config_data["openai_llm_api_key"]
            elif config_data.get("openai_api_key"):
                os.environ["OPENAI_API_KEY"] = config_data["openai_api_key"]
        
        # Always set OPENAI_API_KEY for embeddings (required for vector store)
        if config_data.get("openai_api_key"):
            os.environ["OPENAI_API_KEY"] = config_data["openai_api_key"]
        
        # Create config object
        # Service layer should handle path resolution (separation of concerns)
        config = MovieAgentConfig(
            llm_provider=config_data.get("llm_provider", "openai"),
            llm_model=config_data.get("llm_model", "gpt-4o-mini"),
            enable_vision=config_data.get("enable_vision", True),
            enable_memory=config_data.get("enable_memory", True),
            memory_max_turns=config_data.get("memory_max_turns", 10),
            faiss_index_path=config_data.get("faiss_index_path"),  # Service layer resolves paths
            warmup_on_start=False,  # Disable auto-warmup in service init, MovieAgentApp handles it
            verbose=True,  # Enable verbose logging to debug poster analysis
        )
        
        # Initialize agent app
        agent_app = MovieAgentApp(config)
        agent_app.initialize()
        logger.info("Agent initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}", exc_info=True)
        agent_app = None


@app.route("/")
def index():
    """Serve main UI."""
    if not config_manager.is_configured():
        return redirect(url_for("setup"))
    return render_template("index.html")


@app.route("/setup", methods=["GET", "POST"])
def setup():
    """First-time setup endpoint."""
    if request.method == "GET":
        if config_manager.is_configured():
            return redirect(url_for("index"))
        return render_template("setup.html")
    
    # POST: Process setup data
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Validate setup data
        is_valid, error_message = validate_setup_data(data)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        # Save encrypted config
        config_manager.save_config(data)
        logger.info("Configuration saved successfully")
        
        # Initialize agent
        _initialize_agent_from_config()
        
        return jsonify({"status": "success", "message": "Configuration saved"})
    
    except Exception as e:
        logger.error(f"Setup error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    """Chat endpoint."""
    try:
        # Ensure agent is initialized
        if not config_manager.is_configured():
            return jsonify({"error": "Service not configured. Please complete setup first."}), 503
        
        _initialize_agent_from_config()
        
        if agent_app is None:
            return jsonify({"error": "Agent initialization failed. Please check configuration."}), 500
        
        # Get query from request
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400
        
        query = data["query"].strip()
        if not query:
            return jsonify({"error": "Empty query"}), 400
        
        # Route intent
        intent = intent_router.route(query)
        
        # Get or create session ID for memory isolation
        import uuid
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        session_id = session['session_id']
        
        # Service layer handles all memory and context (poster context, conversation history)
        # Flask app is just a thin UI layer - pass query and session_id only
        logger.info(f"Chat query - Session: {session_id}, Intent: {intent.name}")
        
        try:
            response = agent_app.chat(query, session_id=session_id)
            
            # Log successful response
            logger.info(f"Chat response - Session: {session_id}, Tools: {response.tools_used}, Latency: {response.latency_ms}ms")
            
            # Convert response to dict
            result = {
                "answer": response.answer,
                "movies": response.movies,
                "tools_used": response.tools_used,
                "llm_latency_ms": response.llm_latency_ms,
                "tool_latency_ms": response.tool_latency_ms,
                "latency_ms": response.latency_ms,
                "reasoning_type": response.reasoning_type,
            }
            
            # Add resolution metadata if available
            if response.resolution_metadata:
                result["resolution_metadata"] = response.resolution_metadata
            
            # Add quiz data if available (structured JSON for frontend)
            if response.quiz_data:
                result["quiz_data"] = response.quiz_data
            
            return jsonify(result)
        except Exception as agent_error:
            logger.error(f"Agent error - Session: {session_id}, Query: {query if 'query' in locals() else 'unknown'}, Error: {str(agent_error)}", exc_info=True)
            raise
    
    except Exception as e:
        logger.error(f"Chat endpoint error - Query: {query if 'query' in locals() else 'unknown'}, Error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/poster", methods=["POST"])
def poster():
    """Poster analysis endpoint."""
    # Ensure agent is initialized
    if not config_manager.is_configured():
        return jsonify({"error": "Service not configured. Please complete setup first."}), 503
    
    _initialize_agent_from_config()
    
    if agent_app is None:
        return jsonify({"error": "Agent initialization failed. Please check configuration."}), 500
    
    try:
        if "image" not in request.files:
            return jsonify({"error": "Missing 'image' file in form data"}), 400
        
        file = request.files["image"]
        if not file.filename:
            return jsonify({"error": "Empty file"}), 400
        
        # Save to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Get or create session ID for memory isolation (same as chat)
            import uuid
            if 'session_id' not in session:
                session['session_id'] = str(uuid.uuid4())
            session_id = session['session_id']
            
            # Clear previous poster state (reset on new upload)
            session.pop('poster_state', None)
            logger.info(f"Cleared previous poster_state - Session: {session_id}")
            
            # Use orchestration service directly (not through agent)
            # This is application logic, not agent logic
            logger.info(f"Analyzing poster via orchestration service - Session: {session_id}, File: {file.filename}, Path: {tmp_path}")
            
            try:
                # Use orchestration service (deterministic, testable, OOP-correct)
                # MovieAgentApp.analyze_poster() internally uses PosterOrchestrationService
                # Service layer automatically stores poster result in session memory
                poster_response = agent_app.analyze_poster(tmp_path, session_id=session_id)
                
                # Log detailed response for debugging
                logger.info(f"Poster analysis result - Session: {session_id}, Title: {poster_response.title}, Mood: {poster_response.mood}, Confidence: {poster_response.confidence}, Caption: {poster_response.caption[:50] if poster_response.caption else 'None'}...")
                
                # Store poster state in Flask session for UI display only (service layer handles memory)
                from datetime import datetime
                
                poster_state = {
                    "title": poster_response.title,
                    "mood": poster_response.mood,
                    "confidence": poster_response.confidence,
                    "caption": poster_response.caption,
                    "timestamp": datetime.now().isoformat(),
                }
                session['poster_state'] = poster_state
                
                # Optional: Add to multi-poster history (bounded deque)
                if 'poster_history' not in session:
                    session['poster_history'] = []
                poster_history = session['poster_history']
                poster_history.append(poster_state)
                # Keep only last 3 posters
                if len(poster_history) > 3:
                    poster_history = poster_history[-3:]
                    session['poster_history'] = poster_history
                
                logger.info(f"Stored poster_state in session - Session: {session_id}, Title: {poster_response.title or 'None'}, Mood: {poster_response.mood}, Confidence: {poster_response.confidence}")
                
                return jsonify({
                    "title": poster_response.title,  # Orchestration service-synthesized title
                    "caption": poster_response.caption,  # Vision tool caption
                    "mood": poster_response.mood,  # Orchestration service-synthesized mood
                    "confidence": poster_response.confidence,  # Orchestration service-synthesized confidence
                    "inferred_genres": poster_response.inferred_genres,  # From vision tool
                })
            except Exception as orchestration_error:
                logger.error(f"Orchestration error during poster analysis - Session: {session_id}, Error: {str(orchestration_error)}", exc_info=True)
                raise
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
    
    except Exception as e:
        logger.error(f"Poster analysis error - File: {file.filename if 'file' in locals() else 'unknown'}, Error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/reset-config", methods=["POST"])
def reset_config():
    """Reset configuration endpoint."""
    try:
        config_manager.delete_config()  # Correct method name
        logger.info("Configuration reset")
        return jsonify({"status": "success", "message": "Configuration reset"})
    except Exception as e:
        logger.error(f"Error resetting config: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/clear-poster", methods=["POST"])
def clear_poster():
    """Clear poster state from session."""
    try:
        import uuid
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        session_id = session['session_id']
        
        # Clear poster state in service layer (SessionContext)
        if agent_app and hasattr(agent_app, '_service'):
            agent_app._service.clear_memory(session_id)
        
        # Clear Flask session state (UI only)
        session.pop('poster_state', None)
        session.pop('poster_history', None)
        logger.info(f"Cleared poster_state - Session: {session_id}")
        
        return jsonify({"status": "success", "message": "Poster state cleared"})
    except Exception as e:
        logger.error(f"Error clearing poster state: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8765))
    app.run(host="0.0.0.0", port=port, debug=True)
