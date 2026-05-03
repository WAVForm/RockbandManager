import logging
import os
from shutil import copy

logger = logging.getLogger("RBManager")

def run(emu_path:str, dl_cache_path:str, dta_dirs:dict):
    try:
        logger.info("Copying .dta...")
        for dir, dtab_found in dta_dirs.values():
            cached_dta_path = os.path.join(dl_cache_path, dir)
            dta_source_path = os.path.join(emu_path, dir)
            os.makedirs(cached_dta_path, exist_ok=True)
            file = "songs.dtab" if dtab_found else "songs.dta"
            copy(os.path.join(dta_source_path, file), os.path.join(cached_dta_path, "songs.dtab"))
    except Exception as e:
        logger.error(f"Error finding downloading .dtas: {e}, retry...")
        raise
