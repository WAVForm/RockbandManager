class PS3ConnectionInfo:
    def __init__(self, ip:str, port:int, ls:str):
        self.ip: str = ip
        self.port: int = port
        self.ls_style: str = ls #could use a enum, meh