from rockbandmanager.utils.retry import retryable
from rockbandmanager.models.song import Song
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger("Utilities")

@retryable()
def process_exclusion(songs:list[Song], whitelist:list[Song]):
    '''
    Helper function to make exclusion multithreaded
    '''
    try:
        for song in songs:
            if song in whitelist:
                logger.debug(f"Whitelisted {song}")
                song.wanted = True
            else:
                logger.debug(f"Excluded {song}")
                song.wanted = False
        logger.debug(f"Finished processing exclusion of {len(songs)} songs")
        return True
    except Exception as e:
        logger.debug(f"Error processing exclusion: {e}")
        raise

def run(songs:dict[str, list[Song]], whitelist:list[Song]):
    try:
        logger.info("Excluding blacklisted songs")
        with ThreadPoolExecutor() as executor:
            exclusion_futures = [executor.submit(process_exclusion, song_set, whitelist) for song_set in songs.values()]
            for future in as_completed(exclusion_futures):
                if not future.result():
                    raise Exception("Failed excluding a set of songs")
    except Exception as e:
        logger.debug(f"Error during automatic exclusion: {e}")
        raise
