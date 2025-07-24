import logging, logging.config
import webbrowser
import asyncio
import sqlite3
import fastapi
import os
import requests
from fastapi import FastAPI, Request, responses
from datetime import datetime, timedelta
from rv_scraper import RVScraper
from xlsx_manager import XLSXManager
from contextlib import asynccontextmanager

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
            'filename': ' rbmanager.log',
            'formatter': 'default',
        },
        'stdout': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'loggers': {
        'RBManager': {
            'handlers': ['file', 'stdout'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
})
logger = logging.getLogger("RBManager")
GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR4Dzf5x_5XHKEUa-hp9x6UV9AtFoKKUZPY9uVcZRNMEZl1yn6rBiTT6f6Zj3zdlUuIiOrmBdhZj20w/pub?output=xlsx'

def get_time_until_midnight():
    now = datetime.now()
    tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
    return (tomorrow-now).total_seconds()

async def daily_update():
    while True:
        try:
            run_rv_scraper()
            download_and_prepare_wanted_customs()
            update_xlsx()
            logger.info("Daily update complete. Sleeping until midnight...")
        except Exception as e:
            logger.exception(f"Error during daily update: {e}")
        
        await asyncio.sleep(get_time_until_midnight())

def run_rv_scraper():
    rv_scraper = RVScraper()
    rv_scraper.populate_db()        

def download_and_prepare_wanted_customs():
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, download_url FROM customs WHERE wanted=1 AND local_path IS NULL")
    wanted = cursor.fetchall()
    conn.close()

    for file_id, url in wanted:
        path = download_and_process(url)
        update_path_in_db(file_id, path)

def download_and_process(url):
    # Download the file
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"Failed to download file from {url}")
        return None

    # Create a directory to save the files if it doesn't exist
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # Save the file
    file_path = os.path.join("downloads", os.path.basename(url))
    with open(file_path, 'wb') as f:
        f.write(response.content)

    # Here you can add any additional processing steps

    return file_path

def update_path_in_db(file_id, path):
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE songs SET local_path=? WHERE file_id=?", (path, file_id))
    conn.commit()
    conn.close()

def update_xlsx():
    xlsx_manager = XLSXManager(GOOGLE_SHEET_URL)
    xlsx_manager.download_google_sheet_xlsx()
    xlsx_manager.update_wanted_from_sheets()
    xlsx_manager.export_songs()
    xlsx_manager.export_customs()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs when the app starts
    task = asyncio.create_task(daily_update())
    yield
    # This runs when the app shuts down
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/whitelist")
def get_whitelist():
    try:
        conn = sqlite3.connect("songs.db")
        cursor = conn.cursor()
        cursor.execute("SELECT title, artist FROM songs WHERE excluded = 0")
        res = cursor.fetchall()
        if not len(res) > 0:
            return fastapi.responses.Response(status_code=204)
        songs = {row[1]:row[0] for row in res}
        conn.close()
        return songs
    except Exception as e:
        logger.error(f"[Server] Error getting whitelist: {e}")
        return {}

@app.post("/songs")
async def update_whitelist(request: Request):
    songs = await request.json()
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT NOT NULL,
        excluded BOOLEAN NOT NULL,
        reason TEXT,
        UNIQUE(title, artist)
    )
    ''')

    for song in songs:
        title = song.get("title")
        artist = song.get("artist")
        excluded = song.get("excluded", False)
        reason = song.get("reason", "")

        if not title or not artist:
            continue  # skip invalid entries

        cursor.execute('''
        INSERT INTO songs (title, artist, excluded, reason)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(title, artist) DO UPDATE SET
            excluded=excluded,
            reason=excluded
        ''', (title, artist, excluded, reason))

    conn.commit()
    conn.close()
    return {"status": "ok"}

# Add an endpoint to download the latest XLSX
@app.get("/xlsx")
async def get_latest_xlsx():
    xlsx_manager = XLSXManager(GOOGLE_SHEET_URL)
    return responses.FileResponse(xlsx_manager.OUTPUT_FILE)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
