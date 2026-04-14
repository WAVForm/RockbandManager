import sqlite3
from threading import Lock
from contextlib import contextmanager
import logging
from hashlib import blake2b
from json import load as json_load, dumps as json_dumps
from uuid import uuid4
from .models import Song, SongHash


class DatabaseManager:
    TABLE_CONFIG = {
        'officials': {
            'mandatory_keys': ['artist', 'title', 'wanted'],
            'keys': ['artist', 'title', 'wanted'],
            'store_query': "INSERT OR REPLACE INTO customs (id, artist, title, wanted) VALUES (?, ?, ?, ?)"
        },
        'customs': {
            'mandatory_keys': ['artist', 'title', 'wanted', 'downloaded'],
            'keys': ['artist', 'title', 'diff_drums', 'diff_guitar', 'diff_bass', 'diff_vocals', 'download_url', 'wanted', 'downloaded', 'download_path'],
            'store_query': """
                INSERT OR REPLACE INTO customs 
                (id, artist, title, diff_drums, diff_guitar, diff_bass, diff_vocals, 
                download_url, wanted, downloaded, download_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        }
    }

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
                self.logger.debug("Creating 'customs' table")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS customs (
                        id text PRIMARY KEY,
                        artist TEXT NOT NULL,
                        title TEXT NOT NULL,
                        diff_drums INTEGER,
                        diff_guitar INTEGER,
                        diff_bass INTEGER,
                        diff_vocals INTEGER,
                        download_url TEXT,
                        wanted BOOL NOT NULL,
                        downloaded BOOL NOT NULL
                    )
                """)
                self.logger.debug("Creating 'officials' table")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS officials (
                        id text PRIMARY KEY,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        wanted BOOLEAN NOT NULL,
                        UNIQUE(title, artist)
                    )
                ''')
        except Exception as e:
            self.logger.error(f"Could not initialize to database: {e}")
            raise
    
    def get_all_ids(self, target_table: str) -> list[SongHash]:
        if target_table not in self.TABLE_CONFIG:
            raise ValueError(f"Target table '{target_table}' does not exist")

        try:
            with self.get_cursor() as cursor:
                results = []
                cursor.execute(f"SELECT * FROM {target_table}")
                rows = cursor.fetchall()
                
                for row in rows:
                    row_dict = dict(row)
                    row_id = row_dict.pop("id")
                    
                    # Hashing the remaining data
                    data_str = json_dumps(row_dict, sort_keys=True, default=str).encode()
                    data_hash = blake2b(data_str, usedforsecurity=False).hexdigest()
                    results.append(SongHash(id=row_id, hash=data_hash))
                return results
        except Exception as e:
            self.logger.error(f"Failed to get all ids from '{target_table}': {e}")
            raise

    def get_wanted_ids(self, target_table:str) -> list[SongHash]:
        if target_table not in self.TABLE_CONFIG:
            raise ValueError(f"Target table '{target_table}' does not exist")

        try:
            with self.get_cursor() as cursor:
                results = []
                cursor.execute(f"SELECT * FROM {target_table} WHERE wanted = TRUE")
                rows = cursor.fetchall()
                
                for row in rows:
                    row_dict = dict(row)
                    row_id = row_dict.pop("id")
                    
                    # Hashing the remaining data
                    data_str = json_dumps(row_dict, sort_keys=True, default=str).encode()
                    data_hash = blake2b(data_str, usedforsecurity=False).hexdigest()
                    results.append(SongHash(id=row_id, hash=data_hash))
                return results
        except Exception as e:
            self.logger.error(f"Failed to get wanted ids from '{target_table}': {e}")
            raise

    def get_wanted_undownloaded_ids(self) -> list[SongHash]:
        try:
            with self.get_cursor() as cursor:
                results = []
                cursor.execute("SELECT * FROM customs WHERE (wanted = TRUE AND downloaded = FALSE)")
                rows = cursor.fetchall()
                
                for row in rows:
                    row_dict = dict(row)
                    row_id = row_dict.pop("id")
                    
                    # Hashing the remaining data
                    data_str = json_dumps(row_dict, sort_keys=True, default=str).encode()
                    data_hash = blake2b(data_str, usedforsecurity=False).hexdigest()
                    results.append(SongHash(id=row_id, hash=data_hash))
                return results
        except Exception as e:
            self.logger.error(f"Failed to get undownloaded ids from 'customs': {e}")
            raise

    def get_full_records(self, target_table:str, ids:list[str]) -> list[Song]:
        if not ids:
            return []
        
        if target_table not in self.TABLE_CONFIG:
            raise ValueError(f"Target table '{target_table}' does not exist")

        try:
            with self.get_cursor() as cursor:
                placeholders = ', '.join(['?'] * len(ids))
                query = f"SELECT * FROM {target_table} WHERE id IN ({placeholders})"
                
                cursor.execute(query, ids)
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    row_dict = dict(row)
                    row_id = row_dict.pop("id")
                    results.append(Song(id=row_id, properties=row_dict))
                return results
        except Exception as e:
            self.logger.error(f"Failed to get records from '{target_table}': {e}")
            raise

    def store_songs(self, target_table:str, songs:list[Song]):
        try:
            if target_table not in self.TABLE_CONFIG:
                raise ValueError(f"Unknown table: {target_table}")

            table_spec = self.TABLE_CONFIG[target_table]
            data_to_insert = []

            for song in songs:
                if not all(k in song for k in table_spec['mandatory_keys']):
                    raise ValueError(f"Song missing mandatory keys for {target_table}")
                row = [uuid4().hex] + [song.properties.get(k) for k in table_spec['keys']]
                data_to_insert.append(tuple(row))

            with self.get_cursor() as cursor:
                cursor.executemany(table_spec['store_query'], data_to_insert)
        except Exception as e:
            self.logger.error(f"Failed to store songs into '{target_table}': {e}")
            raise

    def update_songs(self, target_table:str, song_updates:list[Song]):
        if target_table not in self.TABLE_CONFIG:
            raise ValueError(f"Unknown table: {target_table}")

        try:
            with self.get_cursor() as cursor:
                for update in song_updates:
                    if not update.properties:
                        continue
                    
                    for k in update.properties.keys():
                        if k not in self.TABLE_CONFIG[target_table]['keys']:
                            update.properties.pop(k)

                    set_clause = ", ".join([f"{column} = ?" for column in update.properties.keys()])
                    values = list(update.properties.values()) + [update.id]

                    query = f"UPDATE {target_table} SET {set_clause} WHERE id = ?"
                    cursor.execute(query, values)   
        except Exception as e:
            self.logger.error(f"Failed to update songs in {target_table}: {e}")
            raise