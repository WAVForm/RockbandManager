from rockbandmanager.utils.retry import retryable
import logging
from ftplib import FTP
from pathlib import Path
from rockbandmanager.models.endpoint import PS3ConnectionInfo

from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("Utilities")

@retryable()
def upload_to_dir(ps3_connection_info:PS3ConnectionInfo, ul_cache_path:Path, dir:str):
    """Attempts to upload the newly updated .dta files back to the PS3

    Args:
        ps3_connection_info (PS3ConnectionInfo): PS3 connection information
        ul_cache_path (Path): location where files cached for upload are stored locally
        dta_dirs (set[str]): directories where .dta/ab files were found remotely
    """
    try:
        with FTP(encoding='latin-1', timeout=60) as ftp:
            ftp.connect(host=ps3_connection_info.ip, port=ps3_connection_info.port)
            ftp.login()
            path = ul_cache_path.joinpath(dir)
            logger.info(f"Uploading .dta/.dtab at {path}, to {dir}")
            ftp.cwd(dir)
            with open(path.joinpath("songs.dta"), 'rb') as dta_f:
                ftp.storbinary("STOR songs.dta", dta_f)
            with open(path.joinpath("songs.dtab"), 'rb') as dtab_f:
                ftp.storbinary("STOR songs.dtab", dtab_f)
            ftp.cwd("/")
        logger.info(f"Uploaded .dta/.dtab at {path}, to {dir}")
        return True
    except Exception as e:
        logger.error(f"Error uploading .dta/dtab: {e}")
        raise

def run(ps3_connection_info:PS3ConnectionInfo, ul_cache_path:Path, dta_dirs:set[str]):
    try:
        with ThreadPoolExecutor() as executor:
            create_futures = [executor.submit(upload_to_dir, ps3_connection_info, ul_cache_path, dir) for dir in dta_dirs]
            for future in as_completed(create_futures):
                if not future.result():
                    raise Exception("Uploading modified .dta files failed")

        logger.info("Modified .dta files uploaded")
    except Exception as e:
        logger.debug(f"Error uploading modified .dtas: {e}")
        raise

    
