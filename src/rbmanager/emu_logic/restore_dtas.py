import logging
import os.path as osp
from shutil import copy

logger = logging.getLogger("RBManager")

def run(emu_path:str, dl_cache_path:str, dta_dirs:dict):
    try:
        for dir in dta_dirs.keys():
            path = osp.join(dl_cache_path, dir, "songs.dta")
            if not osp.exists(path):
                continue
            copy(path, osp.join(emu_path, dir, "songs.dta"))
    except Exception as e:
        logger.error(f"Error restoring .dtas: {e}")
        raise
