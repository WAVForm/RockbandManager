import sqlite3
from contextlib import contextmanager

class DatabaseManager:

    def __init__(self, file_path):
        self.file_path = file_path
        self._lock = threading.Lock()

    @contextmanager
    def get_connection(self):
        with self._lock:
            conn = sqlite3.connect(self.file_path, timeout=60)
            try:
                yield conn
            finally:
                conn.close()