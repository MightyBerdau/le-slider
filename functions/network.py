import socket

def get_local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 80)) # no actual connection, but checking for IP
        return s.getsockname()[0]