"""
Input sanitization utility using Bleach
"""
import bleach

# Allowed tags and attributes for rich text (e.g. bios)
# Very restrictive for security
ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'a', 'p', 'br']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel']
}

def sanitize_text(text: str, strip: bool = True) -> str:
    """
    Sanitize text input to remove potentially harmful HTML/scripts
    
    Args:
        text: Input text
        strip: Whether to strip disallowed tags (True) or escape them (False)
        
    Returns:
        Sanitized string
    """
    if not text:
        return text
        
    # Linkify URLs automatically
    clean_text = bleach.clean(
        text, 
        tags=ALLOWED_TAGS, 
        attributes=ALLOWED_ATTRIBUTES, 
        strip=strip
    )
    
    return bleach.linkify(clean_text)

def sanitize_username(username: str) -> str:
    """Strict username sanitization"""
    if not username:
        return ""
    return bleach.clean(username, tags=[], strip=True).strip()
