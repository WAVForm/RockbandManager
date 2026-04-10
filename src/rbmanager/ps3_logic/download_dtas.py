from retry import retryable, RetryError
import logging
from ftplib import FTP
import os
from .models import PS3ConnectionInfo

logger = logging.getLogger("RBManager")

@retryable()
def run(ps3_connection_info:PS3ConnectionInfo, dl_cache_path:str, dta_dirs:dict) -> set[str]:
    try:
        dtas = set[str]()
        with FTP(encoding="latin-1", timeout=60) as ftp:
            ftp.connect(host=ps3_connection_info.ip,port=ps3_connection_info.port)
            logger.info("Connected to PS3, logging in and downloading .dta/dtab...")
            ftp.login()
            for dir, dtab_found in dta_dirs.items():
                ftp.cwd(dir)
                os.makedirs(os.path.join(dl_cache_path, dir), exist_ok=True)
                file = "songs.dtab" if dtab_found else "songs.dta"
                with open(os.path.join(os.path.join(dl_cache_path, dir), "songs.dta"), "wb") as dta_f:
                    ftp.retrbinary(f"RETR {file}", dta_f.write)
                    dtas.add(dir)
                ftp.cwd("/")
        return dtas
    except Exception as e:
        logger.error(f"Error downloading .dtas: {e}, retry...")
        raise RetryError(e)
