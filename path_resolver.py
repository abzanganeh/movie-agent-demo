"""
Path resolver for locating movie-agent-service.

Encapsulates path resolution logic following Single Responsibility Principle.
"""
import os
import sys
from pathlib import Path
from typing import Optional


class ServicePathResolver:
    """
    Resolves path to movie-agent-service library.
    
    Single Responsibility: Path resolution only.
    """
    
    def __init__(self, base_file: str):
        """
        Initialize resolver with base file path.
        
        :param base_file: Path to the file that needs to resolve service path (typically __file__)
        """
        self._base_file = base_file
        self._resolved_path: Optional[Path] = None
    
    def resolve(self) -> Optional[Path]:
        """
        Resolve path to movie-agent-service/src.
        
        :return: Path to service src directory, or None if not found
        """
        if self._resolved_path is not None:
            return self._resolved_path
        
        try:
            # Get absolute path of base file
            current_file = Path(self._base_file).resolve()
            
            # Try parent directory (sibling to movie-agent-service)
            service_path = current_file.parent.parent / "movie-agent-service" / "src"
            
            # Fallback: try same directory
            if not service_path.exists():
                service_path = current_file.parent / "movie-agent-service" / "src"
            
            if service_path.exists():
                self._resolved_path = service_path.resolve()
                return self._resolved_path
                
        except (OSError, ValueError):
            # Fallback: use os.path for compatibility
            base_dir = os.path.dirname(os.path.abspath(self._base_file))
            # Try parent directory
            service_path = os.path.join(os.path.dirname(base_dir), "movie-agent-service", "src")
            if not os.path.exists(service_path):
                # Try same directory
                service_path = os.path.join(base_dir, "movie-agent-service", "src")
            if os.path.exists(service_path):
                self._resolved_path = Path(os.path.abspath(service_path))
                return self._resolved_path
        
        return None
    
    def add_to_sys_path(self) -> bool:
        """
        Add resolved service path to sys.path.
        
        :return: True if path was added, False otherwise
        """
        resolved = self.resolve()
        if resolved:
            sys.path.insert(0, str(resolved))
            return True
        return False

