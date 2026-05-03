from rockbandmanager.utils.retry import retryable
import logging
from ftplib import FTP
from pathlib import Path
from rockbandmanager.models.endpoint import PS3ConnectionInfo

logger = logging.getLogger("Utilities")

@retryable()
def run(ps3_connection_info:PS3ConnectionInfo, dl_cache_path:Path, dta_dirs:dict) -> set[str]:
    try:
        dtas = set[str]()
        with FTP(encoding="latin-1", timeout=60) as ftp:
            ftp.connect(host=ps3_connection_info.ip,port=ps3_connection_info.port)
            logger.info("Connected to PS3, logging in and downloading .dta/dtab...")
            ftp.login()
            for dir, dtab_found in dta_dirs.items():
                ftp.cwd(dir)
                dl_path = Path(dl_cache_path.joinpath(dir))
                dl_path.mkdir(parents=True, exist_ok=True)
                file = "songs.dtab" if dtab_found else "songs.dta"
                with open(dl_path.joinpath("songs.dta"), "wb") as dta_f:
                    ftp.retrbinary(f"RETR {file}", dta_f.write)
                    dtas.add(dir)
                ftp.cwd("/")
        return dtas
    except Exception as e:
        logger.error(f"Error downloading .dtas: {e}, retry...")
        raise
