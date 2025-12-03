"""
Shared utility functions for authentication and security.

This module provides JWT token generation, password hashing,
and other security-related utilities.
"""

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password (str): Plain text password
        hashed_password (str): Hashed password
        
    Returns:
        bool: True if password matches, False otherwise
        
    Example:
        >>> hashed = get_password_hash("mypassword")
        >>> verify_password("mypassword", hashed)
        True
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password (str): Plain text password
        
    Returns:
        str: Hashed password
        
    Example:
        >>> hashed = get_password_hash("mypassword")
        >>> len(hashed) > 0
        True
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data (dict): Data to encode in the token
        expires_delta (timedelta, optional): Token expiration time
        
    Returns:
        str: JWT token
        
    Example:
        >>> token = create_access_token({"sub": "testuser"})
        >>> len(token) > 0
        True
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode a JWT access token.
    
    Args:
        token (str): JWT token
        
    Returns:
        dict: Decoded token data or None if invalid
        
    Example:
        >>> token = create_access_token({"sub": "testuser"})
        >>> data = decode_access_token(token)
        >>> data is not None
        True
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def sanitize_input(input_str: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        input_str (str): Input string to sanitize
        
    Returns:
        str: Sanitized string
        
    Example:
        >>> sanitize_input("<script>alert('xss')</script>")
        '&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;'
    """
    import html
    if input_str is None:
        return ""
    return html.escape(str(input_str).strip())


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email (str): Email address
        
    Returns:
        bool: True if valid email format, False otherwise
        
    Example:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid-email")
        False
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_rating(rating: float) -> bool:
    """
    Validate rating value.
    
    Args:
        rating (float): Rating value
        
    Returns:
        bool: True if rating is between 1 and 5, False otherwise
        
    Example:
        >>> validate_rating(4.5)
        True
        >>> validate_rating(6.0)
        False
    """
    return 1.0 <= rating <= 5.0
