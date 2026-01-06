"""
Secure configuration manager for Flask app.

Handles first-time setup, encrypted storage, and secure key management.
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet


class SecureConfigManager:
    """
    Manages secure storage of API keys and configuration.
    
    Uses encryption to store sensitive data locally.
    """
    
    def __init__(self, config_file: str = "config.encrypted", master_key_file: str = ".master_key"):
        """
        Initialize secure config manager.
        
        :param config_file: Path to encrypted config file
        :param master_key_file: Path to master encryption key file
        """
        self.config_file = Path(config_file)
        self.master_key_file = Path(master_key_file)
        self._cipher = None
    
    def is_configured(self) -> bool:
        """Check if configuration exists."""
        return self.config_file.exists() and self.master_key_file.exists()
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key."""
        if self.master_key_file.exists():
            # Load existing key
            with open(self.master_key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            # Store key (in production, use proper key management)
            with open(self.master_key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions (Unix only)
            try:
                os.chmod(self.master_key_file, 0o600)  # Read/write for owner only
            except Exception:
                pass  # Windows doesn't support chmod
            return key
    
    def _get_cipher(self) -> Fernet:
        """Get or create Fernet cipher."""
        if self._cipher is None:
            key = self._get_or_create_master_key()
            self._cipher = Fernet(key)
        return self._cipher
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration securely (encrypted).
        
        :param config: Configuration dictionary
        """
        cipher = self._get_cipher()
        
        # Convert to JSON and encrypt
        config_json = json.dumps(config, indent=2)
        encrypted = cipher.encrypt(config_json.encode('utf-8'))
        
        # Save encrypted config
        with open(self.config_file, 'wb') as f:
            f.write(encrypted)
        
        # Set restrictive permissions (Unix only)
        try:
            os.chmod(self.config_file, 0o600)  # Read/write for owner only
        except Exception:
            pass  # Windows doesn't support chmod
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration (decrypted).
        
        :return: Configuration dictionary or None if not configured
        """
        if not self.is_configured():
            return None
        
        try:
            cipher = self._get_cipher()
            
            # Load and decrypt
            with open(self.config_file, 'rb') as f:
                encrypted = f.read()
            
            decrypted = cipher.decrypt(encrypted)
            config = json.loads(decrypted.decode('utf-8'))
            
            return config
        except Exception as e:
            # If decryption fails, config might be corrupted
            raise ValueError(f"Failed to load configuration: {e}")
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.
        
        :param updates: Dictionary of updates to merge
        """
        current = self.load_config() or {}
        current.update(updates)
        self.save_config(current)
    
    def delete_config(self) -> None:
        """Delete configuration files (for reset)."""
        if self.config_file.exists():
            self.config_file.unlink()
        if self.master_key_file.exists():
            self.master_key_file.unlink()


def validate_setup_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate setup form data.
    
    :param data: Form data dictionary
    :return: Tuple of (is_valid, error_message)
    """
    # Check required fields
    if not data.get('llm_provider'):
        return False, "LLM provider is required"
    
    if data.get('llm_provider') == 'groq' and not data.get('groq_api_key'):
        return False, "Groq API key is required when using Groq"
    
    if data.get('llm_provider') == 'openai' and not data.get('openai_api_key'):
        return False, "OpenAI API key is required when using OpenAI"
    
    if not data.get('openai_api_key'):
        return False, "OpenAI API key is required for embeddings"
    
    # Validate API key format (basic checks)
    if data.get('openai_api_key') and not data['openai_api_key'].startswith('sk-'):
        return False, "OpenAI API key format appears invalid (should start with 'sk-')"
    
    if data.get('groq_api_key') and not data['groq_api_key'].startswith('gsk_'):
        return False, "Groq API key format appears invalid (should start with 'gsk_')"
    
    return True, None

