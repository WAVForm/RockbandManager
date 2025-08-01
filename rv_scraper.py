import requests
import json
import time
import os
import requests
import logging
import subprocess
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from retry import retryable, RetryError
from database_manager import DatabaseManager

class RVScraper:
    # === Constants ===
    BASE_URL = "https://rhythmverse.co/api/rb3/songfiles/list" #TODO make configurable
    HEADERS = { #TODO make configurable
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0)",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }
    DATA_TEMPLATE = "sort%5B0%5D%5Bsort_by%5D=update_date&sort%5B0%5D%5Bsort_order%5D=DESC&data_type=full&page={page}&records=25" #TODO make configurable
    PROGRESS_FILE = "progress.json" #TODO make configurable
    DL_PATH = "downloads/customs/" #TODO make configurable
    ONYX_PATH = 'C:/Users/Programming/Downloads/onyx_cli/onyx.exe' #TODO make configurable

    def __init__(self):
        self.logger = logging.getLogger('RVScraper')
        self.logger.debug("Starting RVScraper")

    def load_progress(self): #DEBUG LOGGED
        '''
        In case operation was interupted, load progress
        '''
        self.logger.debug("Loading progress from last run")
        if os.path.exists(self.PROGRESS_FILE):
            with open(self.PROGRESS_FILE, "r") as f:
                data = json.load(f)
                self.logger.debug("Found last run's progress")
                return (data.get("last_page", 1), data.get("retry_pages", []))
        self.logger.debug("No progress found")
        return (1, [])

    def save_progress(self, last_page, retry_pages): #DEBUG LOGGED
        '''
        Save scraper's progress in case of sudden interuption
        '''
        self.logger.debug("Saving progress for next run")
        with open(self.PROGRESS_FILE, "w") as f:
            json.dump({
                "last_page": last_page,
                "retry_pages": sorted(retry_pages)
            }, f, indent=2)

    # === Main ===
    def scrape(self, max_page=100000): #DEBUG LOGGED
        def page_generator(retry_pages, start, max):
            self.logger.debug("Yielding retry pages first")
            for page in retry_pages:
                yield page
            self.logger.debug(f"Yielding the rest of the range from {start} to {max}")
            for page in range(start, max):
                if page in retry_pages:
                    continue
                yield page
            
        @retryable(retries=1, fallback=False)
        def parse_page(page_number): #DEBUG LOGGED
            @retryable()
            def fetch_page(page_number): #DEBUG LOGGED
                self.logger.debug(f"[Page {page_number}] Fetching page")
                try:
                    self.logger.debug(f"[Page {page_number}] Formatting request body")
                    body = self.DATA_TEMPLATE.format(page=page_number)
                    self.logger.debug(f"[Page {page_number}] Sending request")
                    response = requests.post(self.BASE_URL, headers=self.HEADERS, data=body, timeout=60)
                    response.raise_for_status()
                    self.logger.info(f"[Page {page_number}] fetched successfully")
                    return response.json()
                except Exception as e:
                    self.logger.error(f"[Page {page_number}] Request failed: {e}, retry...")
                    raise RetryError(e)
                
            try:
                json_data = fetch_page(page_number)
                if not json_data:
                    raise Exception(f"[Page {page_number}] Fetch failed.")
                songs_raw = json_data.get("data", {}).get("songs", [])
                if not isinstance(songs_raw, list):
                    raise Exception(f"[Page {page_number}] Invalid song list structure.")
                songs = []
                file_ids = []
                self.logger.debug(f"[Page {page_number}] Parsing fetched page")
                for entry in songs_raw:
                    try:
                        self.logger.debug(f"[Page {page_number}] getting 'file' and 'data'")
                        data = entry.get("file")
                        meta = entry.get("data")
                        if not isinstance(data, dict) or not isinstance(meta, dict):
                            self.logger.debug(f"[Page {page_number}] 'meta' or 'data' are not dictionaries")
                            continue
                        file_id = data["file_id"]
                        self.logger.debug(f"[Page {page_number}] Adding {file_id} to list 'file_ids'")
                        file_ids.append(file_id)
                        song = {
                            "file_id": file_id,
                            "artist": meta.get("artist", ""),
                            "title": meta.get("title", ""),
                            "diff_drums": data.get("diff_drums"),
                            "diff_guitar": data.get("diff_guitar"),
                            "diff_bass": data.get("diff_bass"),
                            "diff_vocals": data.get("diff_vocals"),
                            "download_url": data.get('download_url', ''),
                            "wanted": False,
                            "downloaded": False,
                            "download_path": ""
                        }
                        self.logger.debug(f"[Page {page_number}] Adding {song} to list 'songs'")
                        songs.append(song)
                    except Exception as e:
                        raise Exception(f"[Page {page_number}] Parse error: {e}")
                if len(songs) == 0:
                    raise Exception(f"[Page {page_number}] No valid songs.")
                database_manager = DatabaseManager()
                existing_ids = database_manager.find_file_ids(file_ids)
                if len(existing_ids) == len(file_ids): # If ALL songs on page exist in database, signal to stop crawling
                    self.logger.info(f"[Page {page_number}] All songs already in DB, stopping further scraping.")
                    return False  # signal to stop
                else:
                    self.logger.debug(f"[Page {page_number}] Not all existed in the database, but these did: {[id for id in file_ids if id in existing_ids]}")
                    self.logger.debug(f"File IDs: {file_ids} | Existing File IDs: {existing_ids}")
                database_manager.save_songs(songs, target_table="customs")
                self.logger.info(f"[Page {page_number}] Saved {len(songs)} new songs.")
                return True  # success, continue scraping
            except Exception as e:
                self.logger.error(f"[Page {page_number}] Unexpected error during parsing: {e}")
                raise RetryError(e)

        try:
            pages_signaling_stop = 0
            stop_scraping = False
            last_page, retry_pages = self.load_progress()
            self.logger.info(f"Starting scraping. Last page: {last_page}, Pending retries: {retry_pages}")
            with ThreadPoolExecutor() as executor:
                self.logger.debug("Starting multithreaded page processing")
                page_gen = page_generator(retry_pages, last_page, max_page)
                max_concurrent = 20
                scrape_futures = {}
                for _ in range(max_concurrent):
                    page_number = next(page_gen)
                    future = executor.submit(parse_page, page_number)
                    scrape_futures[future] = page_number
                while scrape_futures:
                    for future in as_completed(scrape_futures):
                        page_number = scrape_futures[future]
                        try:
                            proceed = future.result()
                            if page_number in retry_pages:
                                self.logger.debug(f"Page {page_number} was in retry pages and is not removed")
                                retry_pages.remove(page_number)
                                pages_signaling_stop = 0
                            if proceed: #success
                                self.logger.debug(f"Page {page_number} was successful, setting last page")
                                last_page = max(page_number+1, last_page)
                            elif not proceed: #stop
                                self.logger.info(f"Stopping scraping as page {page_number} indicates no new songs")
                                pages_signaling_stop += 1
                                if pages_signaling_stop >= 5:
                                    stop_scraping = True
                            del scrape_futures[future]
                            if not stop_scraping:
                                page_number = next(page_gen)
                                future = executor.submit(parse_page, page_number)
                                scrape_futures[future] = page_number
                        except Exception as e:
                            retry_pages.append(page_number)
                            self.logger.error(f"Exception processing page {page_number}: {e}")
        except Exception as e:
            self.logger.error(f"Error while scraping: {type(e)}{e}")
            self.save_progress(last_page, retry_pages)
            raise
        try:
            os.remove(self.PROGRESS_FILE)
        except Exception as e:
            pass
        self.logger.info("Scraping complete.")

    def prepare_customs(self): #DEBUG LOGGED
        @retryable()
        def download_song(file_id, download_url):
            try:
                full_download_url = f"https://rhythmverse.co"+download_url
                self.logger.debug("Testing if URL from scraping is valid")
                try:
                    response = requests.head(full_download_url, allow_redirects=True, timeout=5)
                    if response.status_code > 400:
                        self.logger.debug(f"URL schema of '{download_url}' is not valid as of now")
                        return ""
                except Exception as e:
                    self.logger.error(f"Error testing download URL: {e}")
                    RetryError(e)
                self.logger.debug(f"Setting path where {file_id} will save to")
                dl_path = os.path.join(self.DL_PATH, file_id)
                self.logger.debug(f"Making download request")
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                self.logger.debug(f"Saving download stream to {dl_path}")
                with open(dl_path) as song_f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                self.logger.info(f"Successfully downloaded {file_id}")
                return dl_path
            except Exception as e:
                self.logger.error(f"Error downloading song: {e}")
                raise RetryError(e)
        
        @retryable()
        def process_download(artist, title, dl_path):#DEBUG LOGGED
            def subp_run(cmd):
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                return result.stdout
            try:
                content_id = f"UP0006-BLUS30463_00-RB3CUST{artist}_{title}".replace(' ', "")
                self.logger.debug("Running Onyx to import downloaded custom")
                import_result = subp_run([self.ONYX_PATH, "import", dl_path]) #get path where everything was imported
                self.logger.debug("Finding import folder path")
                import_path = re.search(r"/Done! Created files:\s*(.*)", import_result)
                if import_path:
                    self.logger.debug("Successfully found path")
                    import_path = import_path.group(1).strip()
                else:
                    raise RetryError("Could not determine path of import")
                self.logger.debug("Running Onyx to convert imported data to .pkg")
                pkg_result = subp_run([self.ONYX_PATH, "pkg", content_id, import_path]) #get path of output .pkg
                self.logger.debug("Finding .pkg path")
                pkg_path = re.search(r"/Done! Created files:\s*(.*\.pkg)", pkg_result)
                if pkg_path:
                    self.logger.debug("Successfully found path")
                    pkg_path = pkg_path.group(1).strip()
                    self.logger.debug(f"Removing import folder at: {import_path}")
                    shutil.rmtree(import_path)
                else:
                    raise RetryError("Could not determine path of .pkg")
                self.logger.info(f"Downloaded custom successfully processed and can be found at: {pkg_path}")
                return pkg_path
            except Exception as e:
                self.logger.error(f"Error while processing download: {e}")
                raise RetryError(e)

        try:
            self.logger.debug("Starting custom song download & processing")
            database_manager = DatabaseManager()
            wanted_file_ids = database_manager.get_wanted_undownloaded_file_ids_customs()
            self.logger.debug(f"Got back the following 'file_id's: {wanted_file_ids}")
            if not wanted_file_ids or not len(wanted_file_ids) > 0:
                return
            wanted_artists_titles = database_manager.find_artist_and_title_customs(wanted_file_ids)
            self.logger.debug(f"Got back the following 'artist' and 'title's: {wanted_artists_titles}")
            wanted_download_urls = database_manager.find_download_urls(wanted_file_ids)
            self.logger.debug(f"Got back the following 'download_url's: {wanted_download_urls}")
            self.logger.debug("Zipping together all info for wanted songs")
            self.logger.debug(f"Before: {wanted_file_id}, {wanted_artists_titles}, {wanted_download_urls}")
            wanted = list(zip(wanted_file_ids, wanted_artists_titles, wanted_download_urls))
            self.logger.debug(f"After: {wanted}")
            updated_songs = []
            for song in wanted:
                self.logger.debug("Downloading the song")
                dl_path = download_song(song[0], song[2])
                if not dl_path:
                    continue
                self.logger.debug("Processing the downloaded file")
                pkg_path = process_download(song[1][0], song[1][1], dl_path)
                self.logger.debug("Adding song to list")
                updated_songs.append({"file_id":song[0], "download_path":pkg_path})
            self.logger.debug("Updating database with new paths to .pkg files")
            database_manager.update_download_paths(updated_songs)
        except Exception as e:
            self.logger.error(f"Error while preparing custom songs: {e}")
            raise


