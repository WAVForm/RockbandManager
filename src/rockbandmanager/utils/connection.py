from re import match

def get_ip_and_port() -> tuple[str, int]:
    """Gets user input to attempt to extract IP and port

    Returns:
        tuple[str, int]: Returns (ip, port)
    """
    pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})"
    res = match(pattern, input("Please enter the IP and port (x.x.x.x:xxxxx)>: "))
    if not res:
        raise Exception("Input did not match pattern")
    ip, port = res.groups()
    port = int(port)
    octets = list(map(int, ip.split('.')))
    if any(o <0 or o > 255 for o in octets):
        raise Exception("IP Octet(s) value out of range")
    if port < 0 or port > 65535:
        raise Exception("Port value out of range")
    return (ip,port)