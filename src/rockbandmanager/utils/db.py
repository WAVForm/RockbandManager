import sqlite3
from threading import Lock
from contextlib import contextmanager
import logging
from json import load as json_load
from rockbandmanager.models.song import Song

logger = logging.getLogger("Utilities")
db_lock = Lock()
config = json_load(open("config.json", 'r'))["dbmanager"]

@contextmanager
def get_cursor():
    '''
    Establishes connection to database and gives cursor
    '''
    logger.debug("Waiting for lock")
    with db_lock:
        logger.debug("Getting connection")
        conn = sqlite3.connect(config["file_path"], timeout=60)
        logger.debug("Getting cursor")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            logger.debug("Yielding cursor to requestor")
            yield cursor
        finally:
            logger.debug("Cleaning up connection")
            cursor.close()
            conn.commit()
            conn.close()
            logger.debug("Connection cleaned up")

def init_db(): #DEBUG LOGGED
    '''
    Set up and connect to database
    '''
    try:
        with get_cursor() as cursor:
            logger.debug("Creating 'songs' table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS songs (
                    id text PRIMARY KEY,
                    artist TEXT NOT NULL,
                    title TEXT NOT NULL,
                    wanted BOOL NOT NULL,
                    downloaded BOOL NOT NULL,
                    diff_band INTEGER NOT NULL
                    diff_drums INTEGER NOT NULL
                    diff_guitar INTEGER NOT NULL
                    diff_bass INTEGER NOT NULL
                    diff_vocals INTEGER NOT NULL
                    diff_keys INTEGER NOT NULL
                    diff_real_guitar INTEGER NOT NULL
                    diff_real_bass INTEGER NOT NULL
                    diff_real_keys INTEGER NOT NULL
                    download_url: TEXT
                )
            """)
    except Exception as e:
        logger.error(f"Could not initialize to database: {e}")
        raise
    
def get_all_ids() -> list[str]:
    try:
        with get_cursor() as cursor:
            cursor.execute("SELECT id FROM songs")
            results = [id for id in cursor.fetchall()]
            return results
    except Exception as e:
        logger.error(f"Failed to get all ids: {e}")
        raise

def get_wanted_ids() -> list[str]:
    try:
        with get_cursor() as cursor:
            cursor.execute("SELECT id FROM songs WHERE (wanted = TRUE)")
            results = [id for id in cursor.fetchall()]
            return results
    except Exception as e:
        logger.error(f"Failed to get wanted ids: {e}")
        raise

def get_wanted_undownloaded_ids() -> list[str]:
    try:
        with get_cursor() as cursor:
            cursor.execute("SELECT id FROM songs WHERE (wanted = TRUE AND downloaded = FALSE)")
            results = [id for id in cursor.fetchall()]
            return results
    except Exception as e:
        logger.error(f"Failed to get undownloaded ids: {e}")
        raise

def get_full_records(ids:list[str]) -> list[Song]:
    if not ids:
        return []
    try:
        with get_cursor() as cursor:
            query = f"SELECT * FROM songs WHERE id IN ({', '.join(['?'] * len(ids))})"
            
            cursor.execute(query, ids)
            rows = cursor.fetchall()
            
            results = [Song.model_validate(dict(row), extra="ignore") for row in rows]
            return results
    except Exception as e:
        logger.error(f"Failed to get full records for ids ({ids}): {e}")
        raise

def store_songs(songs:list[Song]):
    try:
        data_to_insert = []
        fields_to_store = ["id", "artist", "title", "diff_band", "diff_drums", "diff_guitar", "diff_bass", "diff_vocals", "diff_keys", "diff_real_guitar", "diff_real_bass", "diff_real_keys"]
        
        for song in songs:
            song_dict = song.model_dump(include=set(fields_to_store))
            data_to_insert.append(tuple(song_dict[f] for f in fields_to_store))

        query = f"REPLACE INTO songs ({','.join(fields_to_store)}) VALUES ({', '.join(['?'] * len(fields_to_store))})"

        with get_cursor() as cursor:
            cursor.executemany(query, data_to_insert)

    except Exception as e:
        logger.error(f"Failed to store songs: {e}")
        raise