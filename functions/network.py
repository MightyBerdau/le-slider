import socket

def get_local_ip():
    """Get the local IP address of the machine.
    
    Returns:
        Local IP address as a string
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 80)) # no actual connection, but checking for IP
        return s.getsockname()[0]