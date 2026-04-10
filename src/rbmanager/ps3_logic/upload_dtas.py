from retry import retryable, RetryError
import logging
from ftplib import FTP
import os.path as osp
from .models import PS3ConnectionInfo

logger = logging.getLogger("RBManager")

@retryable()
def run(ps3_connection_info:PS3ConnectionInfo, ul_cache_path:str, dta_dirs:dict):
    try:
        with FTP(encoding='latin-1', timeout=60) as ftp:
            ftp.connect(host=ps3_connection_info.ip, port=ps3_connection_info.port)
            ftp.login()
            for dir in dta_dirs.keys():
                path = osp.join(ul_cache_path, dir)
                logger.info(f"Uploading .dta at {path}, to {dir}")
                ftp.cwd(dir)
                with open(osp.join(path, "songs.dta"), 'rb') as dta_f:
                    ftp.storbinary("STOR songs.dta", dta_f)
                with open(osp.join(path, "songs.dtab"), 'rb') as dtab_f:
                    ftp.storbinary("STOR songs.dtab", dtab_f)
                ftp.cwd("/")
    except Exception as e:
        logger.error(f"Error uploading .dtas: {e}, retry...")
        raise RetryError(e)
