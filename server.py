import logging, logging.config
import asyncio
import sqlite3
import os
import requests
import fastapi
import uvicorn
import contextlib
import datetime

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from rv_scraper import RVScraper
from xlsx_manager import XLSXManager
from database_manager import DatabaseManager

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
            'filename': 'server.log',
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

def get_time_until_midnight():
    now = datetime.datetime.now()
    tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.datetime.min.time())
    return (tomorrow-now).total_seconds()

def run_rv_scraper():
    rv_scraper = RVScraper()
    rv_scraper.scrape()
    rv_scraper.prepare_customs()

async def daily_update():
    while True:
        try:
            run_rv_scraper()
            logger.info("Daily update complete. Sleeping until midnight...")
        except Exception as e:
            logger.error(f"Error during daily update: {e}")
        
        await asyncio.sleep(get_time_until_midnight())        

from typing import List, Dict, Any
from pydantic import BaseModel

class CustomsUpdateRequest(BaseModel):
    updates: List[Dict[str, Any]]

class OfficialsUpdateRequest(BaseModel):
    updates: List[Dict[str, Any]]

if __name__ == "__main__":
    logger = logging.getLogger("Server")
    templates = Jinja2Templates(directory="www/templates")

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

    @app.get("/")
    async def read_root(request: fastapi.Request):
        """Main page with database editor interface"""
        try:         
            return templates.TemplateResponse("index.html", {
                "request": request,
            })
        except Exception as e:
            logger.error(f"Error loading main page: {e}")
            return fastapi.responses.JSONResponse({"error":"Error loading main page"}, status_code=400)

    @app.get("/api/customs")
    async def get_customs():
        """Get all customs data as JSON"""
        try:
            db_m = DatabaseManager()
            customs_data = db_m.get_all_fields("customs")
            return {
                "data":customs_data
            }
        except Exception as e:
            logger.error(f"Error getting customs: {e}")
            raise fastapi.responses.JSONResponse({"error":"Error getting customs"}, status_code=400)

    @app.get("/api/officials")
    async def get_officials():
        """Get all officials data as JSON"""
        try:
            db_m = DatabaseManager()
            officials_data = db_m.get_all_fields("officials")
            return {
                "data":officials_data
            }
        except Exception as e:
            logger.error(f"Error getting officials: {e}")
            raise fastapi.responses.JSONResponse({"error":"Error getting officials"}, status_code=400)

    @app.post("/api/customs/update")
    async def update_customs(request: fastapi.Request):
        """Update wanted status for customs songs"""
        try:
            data = await request.json()
            if "updates" not in data:
                raise ValueError("Request does not have 'update'")
            db_m = DatabaseManager()
            db_m.update_wanted(data["updates"], target_table="customs")
            return {"success": True, "message": f"Updated {len(data["updates"])} customs songs"}
        except Exception as e:
            logger.error(f"Error updating customs: {e}")
            return fastapi.responses.JSONResponse({"error":f"Error updating customs: {e}"},status_code=400)

    @app.post("/api/officials/update")
    async def update_officials(request: fastapi.Request):
        """Update wanted status for officials songs"""
        try:
            data = await request.json()
            if "updates" not in data:
                raise ValueError("Request does not have 'update'")
            db_m = DatabaseManager()
            db_m.update_wanted(data["updates"], target_table="officials")
            return {"success": True, "message": f"Updated {len(data["updates"])} officials songs"}
        except Exception as e:
            logger.error(f"Error updating officials: {e}")
            return fastapi.responses.JSONResponse({"error":f"Error updating officials: {e}"},status_code=400)

    @app.get("/whitelist")
    def get_whitelist(response: fastapi.Response):
        try:
            db_m = DatabaseManager()
            return db_m.get_wanted_official_songs()
        except Exception as e:
            logger.error(f"[Server] Error getting whitelist: {e}")
            response.status_code = 400
            return "Error"

    @app.post("/songs")
    async def update_officials(request: fastapi.Request, response: fastapi.Response):
        try:
            logger.debug("Updating 'officials' table in DB")
            logger.debug("Getting json from request")
            songs = await request.json()
            logger.debug("Checking if songs is list")
            if not isinstance(songs, list):
                raise ValueError("Expected list of songs")
            logger.debug("Firing up DatabaseManager")
            db_m = DatabaseManager()
            logger.debug("Saving songs to 'officials'")
            db_m.save_songs(songs, "officials")                
            return "OK"
        except Exception as e:
            logger.error(f"Error during updating db: {e}")
            response.status_code = 400
            return f"[Server] Error updating whitelist: {e}"

    uvicorn.run(app, host="0.0.0.0", port=8000)
