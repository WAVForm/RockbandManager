from rockbandmanager.utils.retry import retryable
from rockbandmanager.utils.dtaprocessing.conversion import nested_list_to_dta
from rockbandmanager.models.song import Song

from pathlib import Path
from shutil import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import logging

logger = logging.getLogger("Utilities")
write_lock = Lock()


@retryable()
def create_modified_dta(dir_songs:dict[str,list[Song]], modified_dtas: dict[str, str], dir:str):
    '''
    Helper function to create modified .dta file strings before writing them
    '''
    try:
        logger.debug(f"Finalizing {len(dir_songs[dir])} songs at {dir}")
        modified_content = ""
        for song in dir_songs[dir]:
            if song.wanted:
                logger.debug(f"Adding {song} back to .dta at {dir}")
                modified_content += nested_list_to_dta(song.content) + "\n"
        with write_lock:
            modified_dtas[dir] = modified_content
        return True
    except Exception as e:
        logger.debug(f"Error creating modified .dta strings from {dir}: {e}")
        raise

@retryable()
def write_modified_dta(ul_cache_path:str, dl_cache_path:str, modified_dtas:dict[str,str], dir:str):
    '''
    Helper function to write modified .dta file string
    '''
    try:
        ul_path = Path(ul_cache_path).joinpath(dir) #make path if doesn't exist
        ul_path.mkdir(parents=True, exist_ok=True)

        copy(Path(dl_cache_path).joinpath(dir).joinpath("songs.dta"), ul_path.joinpath("songs.dtab")) #create backup .dta
        with open(ul_path.joinpath("songs.dta"), "w") as dta_f: #make the dta
            dta_f.write(modified_dtas[dir])
        logger.debug(f"Done writing to {ul_path}")
        return True
    except Exception as e:
        logger.debug(f"Error writing modified .dta originally from {dir}: {e}")
        raise

def run(dl_cache_path:str, ul_cache_path:str, dir_songs:dict[str, list[Song]]):
    '''
    Finalize changes and create the files
    '''
    modified_dtas: dict[str, str] = {}#temporary dictionary, key is path value is modifed contents

    logger.info("finalizing .dta files to send back")
    try:
        with ThreadPoolExecutor() as executor:
            dirs = dir_songs.keys()
            logger.info("Creating new .dta strings to write to files")
            create_futures = [executor.submit(create_modified_dta, dir_songs, modified_dtas, dir) for dir in dirs]
            for future in as_completed(create_futures):
                if not future.result():
                    raise Exception("a .dta file string failed to be created")

            logger.info("Writing new .dta strings to files")
            write_futures = [executor.submit(write_modified_dta, ul_cache_path, dl_cache_path, modified_dtas, dir) for dir in dirs]
            for future in as_completed(write_futures):
                if not future.result():
                    raise Exception("a .dta file string failed to be writted")

        logger.info("Modified .dta files finalized")
    except Exception as e:
        logger.debug(f"Error finalizing modified .dtas: {e}")
        raise