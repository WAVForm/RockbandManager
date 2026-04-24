import sqlite3
from threading import Lock
from contextlib import contextmanager
import logging
from json import load as json_load
from src.models import Song


class DatabaseManager:
    def __init__(self):
        self.logger = logging.getLogger("DatabaseManager")
        self._lock = Lock()
        self.config = json_load(open("config.json", 'r'))["dbmanager"]
        self.init_db()

    @contextmanager
    def get_cursor(self):
        '''
        Establishes connection to database and gives cursor
        '''
        self.logger.debug("Waiting for lock")
        with self._lock:
            self.logger.debug("Getting connection")
            conn = sqlite3.connect(self.config["file_path"], timeout=60)
            self.logger.debug("Getting cursor")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                self.logger.debug("Yielding cursor to requestor")
                yield cursor
            finally:
                self.logger.debug("Cleaning up connection")
                cursor.close()
                conn.commit()
                conn.close()
                self.logger.debug("Connection cleaned up")

    def init_db(self): #DEBUG LOGGED
        '''
        Set up and connect to database
        '''
        try:
            with self.get_cursor() as cursor:
                self.logger.debug("Creating 'songs' table")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS songs (
                        id text PRIMARY KEY,
                        artist TEXT NOT NULL,
                        title TEXT NOT NULL,
                        type TEXT NOT NULL,
                        diff_drums INTEGER,
                        diff_guitar INTEGER,
                        diff_bass INTEGER,
                        diff_vocals INTEGER,
                        download_url TEXT,
                        wanted BOOL NOT NULL,
                        downloaded BOOL NOT NULL
                    )
                """)
        except Exception as e:
            self.logger.error(f"Could not initialize to database: {e}")
            raise
    
    def get_all_ids(self, target_type: str) -> list[str]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT id FROM songs WHERE type = (?)", target_type)
                results = [id for id in cursor.fetchall()]
                return results
        except Exception as e:
            self.logger.error(f"Failed to get all ids of type '{target_type}': {e}")
            raise

    def get_wanted_ids(self, target_type:str) -> list[str]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT id FROM songs WHERE (type = (?) AND wanted = TRUE)", target_type)
                results = [id for id in cursor.fetchall()]
                return results
        except Exception as e:
            self.logger.error(f"Failed to get wanted ids of type '{target_type}': {e}")
            raise

    def get_wanted_undownloaded_ids(self) -> list[str]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT id FROM songs WHERE (type = custom AND wanted = TRUE AND downloaded = FALSE)")
                results = [id for id in cursor.fetchall()]
                return results
        except Exception as e:
            self.logger.error(f"Failed to get undownloaded ids: {e}")
            raise

    def get_full_records(self, ids:list[str]) -> list[Song]:
        if not ids:
            return []
        try:
            with self.get_cursor() as cursor:
                placeholders = ', '.join(['?'] * len(ids))
                query = f"SELECT * FROM songs WHERE id IN ({placeholders})"
                
                cursor.execute(query, ids)
                rows = cursor.fetchall()
                
                results = [Song.model_validate(dict(row), extra="ignore") for row in rows]
                return results
        except Exception as e:
            self.logger.error(f"Failed to get full records for ids ({ids}): {e}")
            raise

    def store_songs(self, songs:list[Song]):
        try:
            data_to_insert = []
            query = "REPLACE INTO songs (artist, diff_bass, diff_drums, diff_guitar, diff_vocals, downloaded, download_url, id, title, type. wanted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            for song in songs:
                vals = sorted(tuple([v for k,v in song.model_dump(mode="json").items()]))
                print("Keys are sorted as: ",sorted(tuple([k for k,v in song.model_dump(mode="json").items()])), "\nExpected: (artist, diff_bass, diff_drums, diff_guitar, diff_vocals, downloaded, download_url, id, title, type. wanted)")
                data_to_insert.append(vals)

            with self.get_cursor() as cursor:
                cursor.executemany(query, data_to_insert)

        except Exception as e:
            self.logger.error(f"Failed to store songs: {e}")
            raise