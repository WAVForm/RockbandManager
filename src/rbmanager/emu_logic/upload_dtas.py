import logging
import os.path as osp
from shutil import copy

logger = logging.getLogger("RBManager")

def run(emu_path:str, ul_cache_path:str, dta_dirs:dict):
    try:
        for dir in dta_dirs.keys():
            path = osp.join(ul_cache_path, dir)
            emu_path = osp.join(emu_path, dir)
            logger.info(f"Copying .dta at {path}, to {emu_path}")
            copy(osp.join(path, "songs.dta"), osp.join(emu_path, "songs.dta"))
            copy(osp.join(path, "songs.dtab"), osp.join(emu_path, "songs.dtab"))
    except Exception as e:
        logger.error(f"Error uploading .dtas: {e}, retry...")
        raise
