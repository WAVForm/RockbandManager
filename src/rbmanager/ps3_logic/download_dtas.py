from retry import retryable, RetryError
import logging
from ftplib import FTP
import os

logger = logging.getLogger("RBManager")

@retryable()
def run(ps3_ip:str, dl_cache_path:str, dta_dirs:dict):
    try:
        dtas = {}
        with FTP(ps3_ip, encoding="latin-1", timeout=60) as ftp:
            logger.info("Connected to PS3, logging in and downloading .dta/dtab...")
            ftp.login()
            for dir, dtab_found in dta_dirs.values():
                ftp.cwd(dir)
                downloaded_dta_path = os.path.join(dl_cache_path, dir)
                os.makedirs(downloaded_dta_path, exist_ok=True)
                file = "songs.dtab" if dtab_found else "songs.dta"
                with open(os.path.join(downloaded_dta_path, "songs.dtab"), "wb") as dta_f:
                    ftp.retrbinary(f"RETR {file}", dta_f.write)
                    dtas[downloaded_dta_path] = ""
                ftp.cwd("/")
        return dtas
    except Exception as e:
        logger.error(f"Error downloading .dtas: {e}, retry...")
        raise RetryError(e)
