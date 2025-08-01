import sqlite3
import threading
from contextlib import contextmanager
import logging


class DatabaseManager:
    TABLES = ["customs", "officials"]
    FILE_PATH = "rb.db" #TODO make configurable

    def __init__(self):
        self.logger = logging.getLogger("DatabaseManager")
        self.logger.debug("Starting DatabaseManager")
        self.file_path = self.FILE_PATH
        self._lock = threading.Lock()
        self.init_db()

    @contextmanager
    def get_cursor(self): #DEBUG LOGGED
        '''
        Establishes connection to database and gives cursor
        '''
        self.logger.debug("Waiting for lock")
        with self._lock:
            self.logger.debug("Getting connection")
            conn = sqlite3.connect(self.file_path, timeout=60)
            self.logger.debug("Getting cursor")
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
                        file_id TEXT PRIMARY KEY,
                        artist TEXT NOT NULL,
                        title TEXT NOT NULL,
                        diff_drums INTEGER,
                        diff_guitar INTEGER,
                        diff_bass INTEGER,
                        diff_vocals INTEGER,
                        download_url TEXT,
                        wanted BOOL NOT NULL,
                        downloaded BOOL NOT NULL,
                        download_path TEXT
                    )
                """)
                self.logger.debug("Creating 'officials' table")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS officials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        wanted BOOLEAN NOT NULL,
                        UNIQUE(title, artist)
                    )
                ''')
        except Exception as e:
            self.logger.error(f"Could not initialize to database: {e}")
            raise
    
    def save_songs(self, songs, target_table=""): #DEBUG LOGGED
        self.logger.debug(f"Saving {len(songs)} songs to {target_table}")
        try:
            self.logger.debug("Checking if 'target_table' is valid")
            if target_table not in self.TABLES:
                raise ValueError(f"Provide a valid target table you want to save songs to ({self.TABLES})")
            self.logger.debug("Checking if 'songs' is a list")
            if not isinstance(songs, list):
                raise ValueError(f"'songs' needs to be a list")
            self.logger.debug("Checking if there are songs")
            if not len(songs) > 0:
                raise ValueError(f"'songs' needs to have a nonzero length")
            self.logger.debug("Checking if any songs are not a dictionary")
            if any([not isinstance(song, dict) for song in songs]):
                raise ValueError(f"Every song in the list must be a dictionary")
            
            if target_table == "customs":
                self.logger.debug("Checking if every song has the required fields")
                necessary_fields = ["file_id", "artist", "title", "diff_drums", "diff_guitar", "diff_bass", "diff_vocals", "download_url", "wanted", "downloaded", "download_path"]
                for field in necessary_fields:
                    if any([not field in song for song in songs]):
                        raise ValueError(f"Every song needs to have the necessary fields: ({necessary_fields})")
                try:
                    with self.get_cursor() as cursor:
                        for song in songs:
                            self.logger.debug(f"Adding song {song} to database")
                            cursor.execute(
                                """
                                INSERT OR REPLACE INTO customs 
                                    (file_id, artist, title, diff_drums, diff_guitar, diff_bass, diff_vocals, download_url, wanted, downloaded, download_path)
                                    VALUES
                                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, 
                                (
                                    song["file_id"], 
                                    song["artist"], 
                                    song["title"], 
                                    song["diff_drums"], 
                                    song["diff_guitar"], 
                                    song["diff_bass"], 
                                    song["diff_vocals"], 
                                    song["download_url"], 
                                    song["wanted"], 
                                    song["downloaded"], 
                                    song["download_path"],
                                )
                            )
                except Exception as e:
                    self.logger.error(f"Failed saving songs to database: {e}")
                    raise
            elif target_table == "officials":
                self.logger.debug("Checking if every song has the required fields for the 'officials' table")
                necessary_fields = ["artist", "title", "wanted"]
                for field in necessary_fields:
                    if any([not field in song for song in songs]):
                        raise ValueError(f"Every song needs to have the necessary fields: ({necessary_fields})")
                try:
                    with self.get_cursor() as cursor:
                        for song in songs:
                            self.logger.debug(f"Adding song {song} to database")
                            cursor.execute(
                                """
                                INSERT OR REPLACE INTO officials 
                                    (artist, title, wanted)
                                    VALUES
                                    (?, ?, ?)
                                """, 
                                (
                                    song["artist"], 
                                    song["title"], 
                                    song["wanted"],  
                                )
                            )
                except Exception as e:
                    self.logger.error(f"Failed saving songs to database: {e}")
                    raise
        except Exception as e:
            self.logger.error(f"Failed to save songs to database: {e}")
            raise
    
    def update_download_paths(self, songs): #DEBUG LOGGED
        self.logger.debug(f"Updating {len(songs)} songs' 'download_path's")
        try:
            self.logger.debug("Checking if 'songs' is a list")
            if not isinstance(songs, list):
                raise ValueError(f"'songs' needs to be a list")
            self.logger.debug("Checking if there are songs")
            if not len(songs) > 0:
                raise ValueError(f"'songs' needs to have a nonzero length")
            self.logger.debug("Checking if any songs are not a dictionary")
            if any([not isinstance(song, dict) for song in songs]):
                raise ValueError(f"Every song in the list must be a dictionary")
            self.logger.debug("Checking if every song has the required fields")
            necessary_fields = ["file_id", "download_path"]
            for field in necessary_fields:
                if any([not field in song for song in songs]):
                    raise ValueError(f"Every song needs to have the necessary fields: ({necessary_fields})")
            with self.get_cursor() as cursor:
                for song in songs:
                    self.logger.debug(f"Updating {song["file_id"]}'s 'download_path' to {song["download_path"]}")
                    cursor.execute(
                        """
                        UPDATE customs
                        SET download_path = ?
                        WHERE file_id = ?
                        """,
                        (
                        song["download_path"],
                        song["file_id"],
                        )
                    )
        except Exception as e:
            self.logger.error(f"Failed to update download paths: {e}")
            raise
    
    def update_wanted(self, songs, target_table=""):
        self.logger.debug("Checking if 'target_table' is valid")
        if target_table not in self.TABLES:
            raise ValueError(f"Provide a valid target table you want to save songs to ({self.TABLES})")
        self.logger.debug("Checking if 'songs' is a list")
        if not isinstance(songs, list):
            raise ValueError(f"'songs' needs to be a list")
        self.logger.debug("Checking if there are songs")
        if not len(songs) > 0:
            raise ValueError(f"'songs' needs to have a nonzero length")
        self.logger.debug("Checking if any songs are not a dictionary")
        if any([not isinstance(song, dict) for song in songs]):
            raise ValueError(f"Every song in the list must be a dictionary")

        if target_table == "customs":
            self.logger.debug("Checking if every song has the required fields")
            necessary_fields = ["file_id", "wanted"]
            for field in necessary_fields:
                if any([not field in song for song in songs]):
                    raise ValueError(f"Every song needs to have the necessary fields: ({necessary_fields})")
            try:
                with self.get_cursor() as cursor:
                    for song in songs:
                        self.logger.debug(f"Updating wanted for {song}")
                        cursor.execute(
                            """
                            UPDATE customs
                            SET wanted = ?
                            WHERE file_id = ?
                            """, 
                            (
                                song["wanted"],
                                song["file_id"], 
                            )
                        )
            except Exception as e:
                self.logger.error(f"Failed updating wanted: {e}")
                raise
        elif target_table == "officials":
            self.logger.debug("Checking if every song has the required fields")
            necessary_fields = ["title", "artist", "wanted"]
            for field in necessary_fields:
                if any([not field in song for song in songs]):
                    raise ValueError(f"Every song needs to have the necessary fields: ({necessary_fields})")
            try:
                with self.get_cursor() as cursor:
                    for song in songs:
                        self.logger.debug(f"Updating wanted for {song}")
                        cursor.execute(
                            """
                            UPDATE customs
                            SET wanted = ?
                            WHERE (title = ? AND artist = ?)
                            """, 
                            (
                                song["wanted"],
                                song["title"],
                                song["artist"], 
                            )
                        )
            except Exception as e:
                self.logger.error(f"Failed updating wanted: {e}")
                raise
    # === Get All ===
    def get_all_file_ids(self): #DEBUG LOGGED
        self.logger.debug("Getting all 'file_id's")
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT file_id FROM customs
                    """
                )
                return [entry[0] for entry in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get all 'file_id's: {e}")
            raise

    def get_wanted_official_songs(self): #DEBUG LOGGED
        self.logger.debug("Getting all wanted songs in 'official'")
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT title, artist FROM officials
                    WHERE wanted = TRUE
                    """
                )
                return [{"title":entry[0], "artist":entry[1]} for entry in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get wanted official songs: {e}")
            raise
    
    def get_wanted_file_ids_customs(self): #DEBUG LOGGED
        self.logger.debug("Getting all 'file_id's of wanted songs")
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT file_id FROM customs
                    WHERE wanted = TRUE
                    """
                )
                return [entry[0] for entry in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get wanted custom songs: {e}")
            raise
    
    def get_wanted_undownloaded_file_ids_customs(self): #DEBUG LOGGED
        self.logger.debug("Getting all 'file_id's of wanted and undownloaded songs")
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT file_id FROM customs
                    WHERE wanted = TRUE AND downloaded = FALSE
                    """
                )
                return [entry[0] for entry in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get wanted custom songs: {e}")
            raise

    # === Get Certain ===
    def find_file_ids(self, file_ids):#DEBUG LOGGED
        self.logger.debug(f"Looking if any 'file_id's are in the database that matches: {file_ids}")
        if not len(file_ids) > 0:
            raise ValueError("'file_ids' cannot be empty")
        return [file_id for file_id in self.get_all_file_ids() if file_id in file_ids]

    def find_download_urls(self, file_ids):#DEBUG LOGGED
        self.logger.debug(f"Looking for any 'download_url's that have a 'file_id' that matches: {file_ids}")
        try:
            if not len(file_ids) > 0:
                raise ValueError("'file_ids' cannot be empty")
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT file_id, download_url FROM customs
                    """
                )
                all_download_urls = cursor.fetchall()
                return [entry[1] for entry in all_download_urls if entry[0] in file_ids]
        except Exception as e:
            self.logger.error(f"Failed to find download urls: {e}")
            raise
    
    def find_artist_and_title_customs(self, file_ids):#DEBUG LOGGED #TODO remove?
        self.logger.debug(f"Looking for 'artist' and 'title' that have a 'file_id' that matches: {file_ids}")
        if not len(file_ids) > 0:
            raise ValueError("'file_ids' cannot be empty")
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT file_id, artist, title FROM customs
                    """
                )
                return [(entry[1], entry[2]) for entry in cursor.fetchall() if entry[0] in file_ids]
        except Exception as e:
            self.logger.error(f"Failed to get artists and titles for {file_id}: {e}")
            raise
    
    def get_all_fields(self, target_table=""):
        self.logger.debug(f"Getting all fields in table {target_table}")
        if target_table not in self.TABLES:
            raise ValueError(f"Provide a valid target table you want to save songs to ({self.TABLES})")
        try:
            if target_table == "officials":
                with self.get_cursor() as cursor:
                    cursor.execute(
                        '''
                        SELECT title, artist, wanted FROM officials
                        '''
                    )
                    return [{"title":entry[0], "artist":entry[1], "wanted":entry[2]} for entry in cursor.fetchall()]
            elif target_table == "customs":
                with self.get_cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT file_id, artist, title, diff_drums, diff_guitar, diff_bass, diff_vocals, wanted, downloaded FROM customs
                        """
                    )
                    return [{"file_id": entry[0], "artist":entry[1], "title":entry[2], "diff_drums":entry[3], "diff_guitar":entry[4], "diff_bass":entry[5], "diff_vocals":entry[6], "wanted":entry[7], "downloaded":entry[8]} for entry in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get all fields for {target_table}: {e}")
            raise

#RUN COMMANDS ON DATABASE HERE
# db_m = DatabaseManager()
# with db_m.get_cursor() as cursor:
#     cursor.execute(
#         '''
        
#         '''
#     )