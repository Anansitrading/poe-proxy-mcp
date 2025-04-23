"""
Session management for the Poe API client.

This module provides functionality for managing conversation sessions,
including creating, retrieving, updating, and deleting sessions.
"""
import time
import uuid
from typing import Dict, List, Optional, Any
import fastapi_poe as fp

from utils import logger


class SessionManager:
    """
    Manager for Poe API conversation sessions.
    """
    
    def __init__(self, expiry_minutes: int = 60):
        """
        Initialize the session manager.
        
        Args:
            expiry_minutes (int): Session expiry time in minutes
        """
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.expiry_minutes = expiry_minutes
        logger.info(f"Session manager initialized with {expiry_minutes} minute expiry")
    
    def create_session(self) -> str:
        """
        Create a new session.
        
        Returns:
            str: The session ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "messages": [],
            "created_at": time.time(),
            "last_accessed": time.time(),
        }
        logger.debug(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session by ID.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            Optional[Dict[str, Any]]: The session data, or None if not found
        """
        if session_id not in self.sessions:
            logger.debug(f"Session not found: {session_id}")
            return None
        
        # Update last accessed time
        self.sessions[session_id]["last_accessed"] = time.time()
        
        # Check if session has expired
        if self._is_session_expired(session_id):
            logger.debug(f"Session expired: {session_id}")
            self.delete_session(session_id)
            return None
        
        return self.sessions[session_id]
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """
        Get an existing session or create a new one.
        
        Args:
            session_id (Optional[str]): The session ID to retrieve
            
        Returns:
            str: The session ID (either the existing one or a new one)
        """
        if session_id and session_id in self.sessions:
            # Check if session has expired
            if self._is_session_expired(session_id):
                logger.debug(f"Session expired: {session_id}")
                self.delete_session(session_id)
                return self.create_session()
            
            # Update last accessed time
            self.sessions[session_id]["last_accessed"] = time.time()
            logger.debug(f"Retrieved existing session: {session_id}")
            return session_id
        
        return self.create_session()
    
    def update_session(
        self, 
        session_id: str, 
        user_message: str, 
        bot_message: str,
    ) -> bool:
        """
        Update a session with new messages.
        
        Args:
            session_id (str): The session ID
            user_message (str): The user message to add
            bot_message (str): The bot message to add
            
        Returns:
            bool: True if the session was updated, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.debug(f"Cannot update non-existent session: {session_id}")
            return False
        
        # Add the new messages
        session["messages"].append(fp.ProtocolMessage(role="user", content=user_message))
        session["messages"].append(fp.ProtocolMessage(role="assistant", content=bot_message))
        
        # Update last accessed time
        session["last_accessed"] = time.time()
        
        logger.debug(f"Updated session {session_id} with new messages")
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            bool: True if the session was deleted, False otherwise
        """
        if session_id not in self.sessions:
            logger.debug(f"Cannot delete non-existent session: {session_id}")
            return False
        
        del self.sessions[session_id]
        logger.debug(f"Deleted session: {session_id}")
        return True
    
    def get_messages(self, session_id: str) -> List[fp.ProtocolMessage]:
        """
        Get the messages for a session.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            List[fp.ProtocolMessage]: The messages for the session
        """
        session = self.get_session(session_id)
        if not session:
            logger.debug(f"Cannot get messages for non-existent session: {session_id}")
            return []
        
        return session["messages"]
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            int: The number of sessions cleaned up
        """
        expired_sessions = []
        
        for session_id in self.sessions:
            if self._is_session_expired(session_id):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.delete_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    def _is_session_expired(self, session_id: str) -> bool:
        """
        Check if a session has expired.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            bool: True if the session has expired, False otherwise
        """
        if session_id not in self.sessions:
            return True
        
        last_accessed = self.sessions[session_id]["last_accessed"]
        expiry_time = last_accessed + (self.expiry_minutes * 60)
        
        return time.time() > expiry_time