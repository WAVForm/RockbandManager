import logging, logging.config
import asyncio
import sqlite3
import os
import requests
import fastapi
import uvicorn
import contextlib
import datetime

from rv_scraper import RVScraper
from xlsx_manager import XLSXManager

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'rbmanager.log',
            'formatter': 'default',
        },
        'stdout': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'loggers': {
        'Server': {
            'handlers': ['file', 'stdout'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'RVScraper': {
            'handlers': ['file', 'stdout'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'XLSXManager': {
            'handlers': ['file', 'stdout'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'DatabaseManager': {
            'handlers': ['file', 'stdout'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
})

GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR4Dzf5x_5XHKEUa-hp9x6UV9AtFoKKUZPY9uVcZRNMEZl1yn6rBiTT6f6Zj3zdlUuIiOrmBdhZj20w/pub?output=xlsx'

def get_time_until_midnight():
    now = datetime.datetime.now()
    tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.datetime.min.time())
    return (tomorrow-now).total_seconds()

def run_rv_scraper():
    rv_scraper = RVScraper()
    rv_scraper.populate_db()

# TODO rvscraper
#def download_and_prepare_wanted_customs():
    # TODO database manager
    # conn = sqlite3.connect("songs.db")
    # cursor = conn.cursor()
    # cursor.execute("SELECT file_id, download_url FROM customs WHERE wanted=1 AND local_path IS NULL")
    # wanted = cursor.fetchall()
    # conn.close()

    for file_id, url in wanted:
        path = download_and_process(url)
        update_path_in_db(file_id, path)

def update_xlsx():
    xlsx_manager = XLSXManager(GOOGLE_SHEET_URL)
    xlsx_manager.download_google_sheet_xlsx()
    xlsx_manager.update_wanted_from_sheets()
    xlsx_manager.export_songs()
    xlsx_manager.export_customs()


async def daily_update():
    while True:
        try:
            run_rv_scraper()
            download_and_prepare_wanted_customs()
            update_xlsx()
            logger.info("Daily update complete. Sleeping until midnight...")
        except Exception as e:
            logger.error(f"Error during daily update: {e}")
        
        await asyncio.sleep(get_time_until_midnight())        

# TODO rvscraper what is not database manager
# def download_and_process(url):
#     response = requests.get(url)
#     if response.status_code != 200:
#         logger.error(f"Failed to download file from {url}")
#         return None

#     os.makedirs("customs_downloads", exist_ok=True)

#     # Save the file
#     file_path = os.path.join("customs_downloads", os.path.basename(url))
#     with open(file_path, 'wb') as f:
#         f.write(response.content)

#     # TODO convert to .pkg

#     return file_path

# def update_path_in_db(file_id, path):
#     pass
#     # TODO database manager
#     # conn = sqlite3.connect("songs.db")
#     # cursor = conn.cursor()
#     # cursor.execute("UPDATE songs SET local_path=? WHERE file_id=?", (path, file_id))
#     # conn.commit()
#     # conn.close()


if __name__ == "__main__":
    logger = logging.getLogger("Server")

    @contextlib.asynccontextmanager
    async def lifespan(app: fastapi.FastAPI):
        task = asyncio.create_task(daily_update())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = fastapi.FastAPI(lifespan=lifespan)

    @app.get("/whitelist")
    def get_whitelist(response: fastapi.Response):
        try:
            # TODO database manager
            # conn = sqlite3.connect("songs.db")
            # cursor = conn.cursor()
            # cursor.execute("SELECT artist, title FROM songs WHERE excluded = 0")
            # res = cursor.fetchall()
            if len(rows) == 0:
                response.status_code = 204
                return []
            songs = [(row[0],row[1]) for row in rows]
            return songs
        except Exception as e:
            logger.error(f"[Server] Error getting whitelist: {e}")
            response.status_code = 400
            return []

    @app.post("/songs")
    async def update_whitelist(request: fastapi.Request, response: fastapi.Response):
        try:
            songs = await request.json()
            if not isinstance(songs, list):
                raise ValueError("Expected list of songs")

            # TODO database manager
            # conn = sqlite3.connect("songs.db")
            # cursor = conn.cursor()
            # cursor.execute('''
            # CREATE TABLE IF NOT EXISTS songs (
            #     id INTEGER PRIMARY KEY AUTOINCREMENT,
            #     title TEXT NOT NULL,
            #     artist TEXT NOT NULL,
            #     excluded BOOLEAN NOT NULL,
            #     reason TEXT,
            #     UNIQUE(title, artist)
            # )
            # ''')

            for song in songs:
                if not isinstance(song, dict):
                    raise ValueError("Expected song to be a dictionary")
                if 'title' not in song or 'artist' not in song:
                    raise ValueError("Song must have a title and artist at minimum")
                title = song["title"]
                artist = song["artist"]
                if len(title) > 500 or len(artist) > 500:
                    raise ValueError("Title and artist must be under 500 characters")
                excluded = song.get("excluded", False)
                reason = song.get("reason", "")

                # TODO check if song in database, if so only update if excluded is different. If not in database then add

                # TODO database manager
                # cursor.execute('''
                # INSERT INTO songs (title, artist, excluded, reason)
                # VALUES (?, ?, ?, ?)
                # ON CONFLICT(title, artist) DO UPDATE SET
                #     excluded=excluded,
                #     reason=excluded
                # ''', (title, artist, excluded, reason))

            # conn.commit()
            # conn.close()
            return "OK"
        except Exception as e:
            response.status_code = 400
            return f"[Server] Error updating whitelist: {e}"

    # Add an endpoint to download the latest XLSX
    @app.get("/xlsx")
    async def get_latest_xlsx():
        return fastapi.responses.FileResponse(XLSXManager(GOOGLE_SHEET_URL).OUTPUT_FILE)

    uvicorn.run(app, host="0.0.0.0", port=8000)
