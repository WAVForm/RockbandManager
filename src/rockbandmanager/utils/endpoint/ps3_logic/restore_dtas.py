from rockbandmanager.utils.retry import retryable
import logging
from ftplib import FTP
from pathlib import Path
from rockbandmanager.models.endpoint import PS3ConnectionInfo

logger = logging.getLogger("Utilities")

@retryable()
def run(ps3_connection_info:PS3ConnectionInfo, dl_cache_path:Path, dta_dirs:dict[str,bool]):
    """Restores cached .dtab files to PS3 as .dta files

    Args:
        ps3_connection_info (PS3ConnectionInfo): PS3 connection info
        dl_cache_path (Path): location where .dta files are downloaded to locally
        dta_dirs (dict[str,bool]): keys are directories where .dta files were found remotely, value is if a .dtab was found 
    """
    try:
        with FTP(encoding='latin-1', timeout=60) as ftp:
            ftp.connect(host=ps3_connection_info.ip, port=ps3_connection_info.port)
            ftp.login()
            for dir in dta_dirs.keys():
                path = dl_cache_path.joinpath(dir, "songs.dtab")
                if not path.exists:
                    continue
                ftp.cwd(dir)
                with open(path, 'rb') as dta_f:
                    ftp.storbinary("STOR songs.dta", dta_f)
                ftp.cwd("/")
    except Exception as e:
        logger.error(f"Error restoring .dtas: {e}, retry...")
        raise    
