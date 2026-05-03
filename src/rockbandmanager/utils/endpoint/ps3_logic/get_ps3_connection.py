from rockbandmanager.utils.retry import retryable
from ftplib import FTP
from rockbandmanager.models.endpoint import PS3ConnectionInfo
from rockbandmanager.utils.connection import get_ip_and_port
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger("Utilities")

def _determine_ls_style(ip:str, port:int) -> str:
    """Attempts to determine the supported 'ls' style for the FTP server

    Args:
        ip (str): The IP address of the PS3
        port (int): The port where the FTP server is listening

    Returns:
        str: Returns 'nlst' or 'mlsd'
    """
    def try_mlsd():
        with FTP(encoding='latin-1', timeout=60) as ftp:
            ftp.connect(host=ip,port=port)
            ftp.login()
            next(ftp.mlsd())
            return True

    def try_nlst():
        with FTP(encoding='latin-1', timeout=60) as ftp:
            ftp.connect(host=ip,port=port)
            ftp.login()
            ftp.nlst()
            return True

    logger.debug("Determining 'ls' command style for connection")
    try:
        with ThreadPoolExecutor() as e:
            mlsd_future = e.submit(try_mlsd)
            if not mlsd_future.result():
                logger.error("MLSD failed.")
                raise Exception("MLSD Failed")
            else:
                logger.debug("MLSD completed successfully.")
                return "mlsd"
    except Exception:
        logger.error("MLSD failed.")
        with ThreadPoolExecutor() as e:
            nlst_future = e.submit(try_nlst)
            if not nlst_future.result():
                logger.error("NLST failed.")
                raise Exception("NLST Failed")
            else:
                logger.debug("NLST completed successfully.")
                return "nlst"
        

@retryable()
def run() -> PS3ConnectionInfo:
    """Attempts to get valid PS3 connection details from user

    Args:
        root_game_path (str, optional): The root directory PS3 game data will be found at. Defaults to "/dev_hdd0/game".

    Returns:
        PS3ConnectionInfo: Connection information for the PS3 (IP, port, and 'ls' style)
    """
    try:
        logger.info("Trying to get PS3 connection")
        ip,port = get_ip_and_port()
        ls_style = _determine_ls_style(ip, port)
        logger.info("PS3 Connection Validated")
        return PS3ConnectionInfo(ip, port, ls_style)
    except Exception as e:
        logger.debug(f"Error getting PS3 connection: {e}")
        raise