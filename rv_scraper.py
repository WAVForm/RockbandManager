import requests
import sqlite3
import json
import time
import os
import threading
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

class RVScraper:
    # === Constants ===
    BASE_URL = "https://rhythmverse.co/api/rb3/songfiles/list"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0)",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }
    DATA_TEMPLATE = "sort%5B0%5D%5Bsort_by%5D=update_date&sort%5B0%5D%5Bsort_order%5D=DESC&data_type=full&page={page}&records=25"
    PROGRESS_FILE = "progress.json"
    DB_FILE = "songs.db"
    DL_PATH = "downloads/customs/"
    LOCK = threading.Lock()

    def __init__(self):
        self.logger = logging.getLogger('RBManager')
        self.load_progress()
        self.init_db()

    # === Database ===
    def init_db(self):
        '''
        Set up and connect to database
        '''
        try:
            db_connection = sqlite3.connect(self.DB_FILE)
            cursor = db_connection.cursor()
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS customs (
                        file_id TEXT PRIMARY KEY,
                        artist TEXT,
                        title TEXT,
                        diff_drums INTEGER,
                        diff_guitar INTEGER,
                        diff_bass INTEGER,
                        diff_vocals INTEGER,
                        download_url TEXT,
                        wanted BOOL NOT NULL,
                        local_path TEXT
                    )
                """)
            db_connection.commit()
            db_connection.close()
        except Exception as e:
            self.logger.error(f"[RVScraper] Could not connect to database: {e}")

    def save_to_db(self, songs):
        '''
        Write list of songs to database.
        '''
        try:
            with self.LOCK:
                db_connection = sqlite3.connect(self.DB_FILE)
                cursor = db_connection.cursor()
                for song in songs:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO customs (
                                file_id, artist, title, diff_drums, diff_guitar,
                                diff_bass, diff_vocals, download_url, wanted
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            song["file_id"],
                            song["artist"],
                            song["title"],
                            song["diff_drums"],
                            song["diff_guitar"],
                            song["diff_bass"],
                            song["diff_vocals"],
                            song["download_url"],
                            False,
                        ))
                    except sqlite3.Error as e:
                        self.logger.error(f"[RVScraper] SQLite error: {e}")
                db_connection.commit()
                db_connection.close()
        except Exception as e:
            self.logger.error(f"[RVScraper] Could not write songs to database: {e}")

    def file_ids_exist(self, file_ids):
        '''
        Check if file_ids exist in the DB.
        '''
        if not file_ids:
            return set()
        placeholders = ",".join("?" for _ in file_ids)
        query = f"SELECT file_id FROM customs WHERE file_id IN ({placeholders})"
        with sqlite3.connect(self.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(query, file_ids)
            rows = cursor.fetchall()
        return set(row[0] for row in rows)

    # === Progress Saving ===
    def load_progress(self):
        if os.path.exists(self.PROGRESS_FILE):
            with open(self.PROGRESS_FILE, "r") as f:
                data = json.load(f)
                self.last_page, self.retry_pages = data.get("last_page", 1), set(data.get("retry_pages", []))
        self.last_page, self.retry_pages =  1, set()

    def save_progress(self):
        '''
        Save scraper's progress
        '''
        with open(self.PROGRESS_FILE, "w") as f:
            json.dump({
                "last_page": self.last_page,
                "retry_pages": sorted(list(self.retry_pages))
            }, f, indent=2)

    # === Communication ===
    def fetch_page(self, page, max_attempts=10):
        '''
        Try to fetch a page and retry on fail, return response
        '''
        body = self.DATA_TEMPLATE.format(page=page)
        for attempt in range(max_attempts):
            try:
                response = requests.post(self.BASE_URL, headers=self.HEADERS, data=body, timeout=10)
                if response.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    self.logger.warning(f"[RVScraper] [Page {page}] Rate limited (429). Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as e:
                wait = 2 * (attempt + 1)
                self.logger.error(f"[RVScraper] [Page {page}] Request failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
        self.logger.warning(f"[RVScraper] Couldn't fetch page {page}, timed out.")
        return None

    def parse_and_save_with_retry(self, page):
        '''
        Parse JSON and save data
        '''
        try:
            json_data = self.fetch_page(page)
            if not json_data:
                self.logger.warning(f"[RVScraper] [Page {page}] Fetch failed.")
                return None  # signal retry

            songs_raw = json_data.get("data", {}).get("songs", [])
            if not isinstance(songs_raw, list):
                self.logger.warning(f"[RVScraper] [Page {page}] Invalid songs structure.")
                return False # signal stop

            songs = []
            file_ids = []
            for entry in songs_raw:
                try:
                    data = entry.get("file")
                    meta = entry.get("data")
                    if not isinstance(data, dict) or not isinstance(meta, dict):
                        continue
                    file_id = data["file_id"]
                    file_ids.append(file_id)
                    song = {
                        "file_id": file_id,
                        "artist": meta.get("artist", ""),
                        "title": meta.get("title", ""),
                        "diff_drums": data.get("diff_drums"),
                        "diff_guitar": data.get("diff_guitar"),
                        "diff_bass": data.get("diff_bass"),
                        "diff_vocals": data.get("diff_vocals"),
                        "download_url": f"https://rhythmverse.co{data.get('download_url', '')}"
                    }
                    songs.append(song)
                except Exception as e:
                    self.logger.error(f"[RVScraper] [Page {page}] Parse error: {e}")

            if not songs:
                self.logger.warning(f"[RVScraper] [Page {page}] No valid songs.")
                return None  # no songs but consider page processed

            existing_ids = self.file_ids_exist(file_ids)

            # If ALL songs on page exist, signal to stop crawling
            if len(existing_ids) == len(file_ids):
                self.logger.info(f"[RVScraper] [Page {page}] All songs already in DB, stopping further scraping.")
                return False  # signal to stop

            self.save_to_db(songs)
            self.logger.info(f"[RVScraper] [Page {page}] Saved {len(songs)} new songs.")
            return True  # success, continue scraping
        except Exception as e:
            self.logger.error(f"[RVScraper] [Page {page}] Unexpected error in parse_and_save_with_retry: {e}")
            return None  # signal retry

    # === Main ===
    def populate_db(self, max_page=100000):
        self.logger.info(f"[RVScraper] Starting. Last page: {self.last_page}, Pending retries: {sorted(self.retry_pages)}")

        executor = ThreadPoolExecutor(max_workers=6)
        parse_queue = list(self.retry_pages) + list(range(self.last_page, max_page))
        futures = {executor.submit(self.parse_and_save_with_retry, page):page for page in parse_queue}
        stop_scraping = False
        for future in as_completed(futures):
            if stop_scraping:
                continue

            try:
                page = futures[future]
                result = future.result()
                if result is True:
                    self.last_page = max(page + 1, self.last_page)
                elif result is False:
                    self.logger.info(f"[RVScraper] Stopping scraper as page {page} indicates no new songs")
                    for f in futures:
                        f.cancel()
                    os.remove(self.PROGRESS_FILE)
                    break               
                else:
                    self.retry_pages.add(page)
            except Exception as e:
                self.logger.error(f"[RVScraper] [Page {page}] Unexpected thread error: {e}")
                self.retry_pages.add(page)
            with self.LOCK:
                self.save_progress()

        if not executor._shutdown:
            executor.shutdown()
        self.logger.info("[RVScraper] Scraping complete.")

    def download_song(self, file_id):
        db_connection = sqlite3.connect(self.DB_FILE)
        cursor = db_connection.cursor()
        cursor.execute('''
        SELECT download_url
        FROM customs
        WHERE file_id=?
        ''', file_id)
        download_url = 'https://rhythmverse.co'+cursor.fetchone()
        conn.close()

        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            with open(self.DL_PATH+file_id) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return self.DL_PATH+file_id
            self.logger.info(f"[RVScraper] Successfully downloaded song {file_id}")
        except Exception as e:
            self.logger.error(f"[RVScraper] Error downloading/writing file: {e}")
            return None
        