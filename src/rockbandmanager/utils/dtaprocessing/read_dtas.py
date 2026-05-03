from rockbandmanager.utils.retry import retryable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Lock
from rockbandmanager.utils.dtaprocessing.conversion import dta_to_nested_list
from rockbandmanager.models.song import Song
import logging

logger = logging.getLogger("Utilities")
append_lock = Lock()

@retryable()
def process_dta(songs:dict[str, list[Song]], dl_cache_path:Path, dir:str):
    '''
    Helper function that sends .dta to be processed and return list of songs.
    '''
    try:
        file_path = dl_cache_path.joinpath(dir)
        logger.debug(f"Processing .dtab file at {file_path}")
        song_list = []
        with open(file_path.joinpath("songs.dta"), 'r') as dta_f:
            nested = dta_to_nested_list(dta_f.read())
        logger.debug(f"Got back a nested list from {file_path}, extracting songs")
        
        for metadata in nested:
            song_dict = {}
            for entry in metadata:
                match entry[0]:
                    case 'name':
                        song_dict['title'] = str(entry[1]).strip('" ')
                    case 'artist':
                        song_dict['artist'] = entry[1]
                    case 'rank':
                        for rank in entry[1:]:
                            match rank[0]:
                                case 'band':
                                    diff = rank[1]
                                    ratings = [1, 159, 219, 274, 328, 383, 454]
                                    star_diff = sum(1 for r in ratings if r <= diff) - 1
                                    song_dict['diff_band'] = star_diff
                                case 'guitar':
                                    diff = rank[1]
                                    ratings = [1, 145, 194, 247, 301, 354, 406]
                                    star_diff = sum(1 for r in ratings if r <= diff) - 1
                                    song_dict['diff_guitar'] = star_diff
                                case 'drum':
                                    diff = rank[1]
                                    ratings = [1, 133, 169, 208, 294, 349, 401]
                                    star_diff = sum(1 for r in ratings if r <= diff) - 1
                                    song_dict['diff_drum'] = star_diff
                                case 'bass':
                                    diff = rank[1]
                                    ratings = [1, 166, 220, 259, 298, 349, 401]
                                    star_diff = sum(1 for r in ratings if r <= diff) - 1
                                    song_dict['diff_bass'] = star_diff                  
                                case 'vocals':
                                    diff = rank[1]
                                    ratings = [1, 139, 180, 220, 259, 298, 373]
                                    star_diff = sum(1 for r in ratings if r <= diff) - 1
                                    song_dict['diff_voc'] = star_diff
                                case 'keys':
                                    diff = rank[1]
                                    star_diff = -1 if diff == 0 else 0
                                    song_dict['diff_keys'] = star_diff
                                case 'real_keys':
                                    diff = rank[1]
                                    star_diff = -1 if diff == 0 else 0
                                    song_dict['diff_real_keys'] = star_diff
                                case 'real_bass':
                                    diff = rank[1]
                                    star_diff = -1 if diff == 0 else 0
                                    song_dict['diff_real_bass'] = star_diff
                                case 'real_guitar':
                                    diff = rank[1]
                                    star_diff = -1 if diff == 0 else 0
                                    song_dict['diff_real_guitar'] = star_diff
            song_dict["content"] = metadata
            song_list.append(Song.model_validate(song_dict, extra="ignore"))
        with append_lock:
            songs[dir] = song_list
        return True
    except Exception as e:
        logger.debug(f"Error processing .dta: {e}, retry...")
        raise

def run(dl_cache_path:Path, dta_dirs:set[str]) -> dict[str, list[Song]]:
        '''
        Open each .dta that was downloaded and process it
        '''                
        logger.info("Processing downloaded .dtas")
        try:
            songs: dict[str, list[Song]] = {}
            with ThreadPoolExecutor() as executor:
                dta_process_futures = [executor.submit(process_dta, songs, dl_cache_path, dir) for dir in dta_dirs]
                for future in as_completed(dta_process_futures):
                    if not future.result():
                        raise Exception("Failed processing .dtas")
                amount_of_songs = len([song for songs in songs.values() for song in songs])
                logger.info(f"{amount_of_songs} total songs found.")
            return songs
        except Exception as e:
            logger.error(f"Error reading .dtas: {e}")
            raise