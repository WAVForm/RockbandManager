from retry import retryable, RetryError
import logging
from ftplib import FTP
import os.path as osp

logger = logging.getLogger("RBManager")

@retryable()
def run(ps3_ip:tuple[str,int], ul_cache_path:str, dta_dirs:dict):
    try:
        with FTP(encoding='latin-1', timeout=60) as ftp:
            ftp.connect(host=ps3_ip[0], port=ps3_ip[1])
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
