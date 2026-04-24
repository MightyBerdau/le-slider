from datetime import datetime

def get_current_time():
    """Get the current time in ISO format with timezone.
    
    Returns:
        Current datetime as ISO format string with timezone information
    """
    return datetime.now().astimezone().isoformat()