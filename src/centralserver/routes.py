from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
from src.models import Song
from centralserver.database_manager import DatabaseManager

logger = logging.getLogger("CentralServer")
db_manager = DatabaseManager()
router = FastAPI()

@router.get("/ids/{type}", response_model=list[str])
async def get_song_ids(type:str):
    try:
        return db_manager.get_all_ids(type)
    except Exception as e:
        msg = f"Error getting all ids of type {type}: {e}" 
        logger.error(msg)
        return JSONResponse({"error":msg}, status_code=400)

@router.get("/whitelist", response_model=list[str])
def get_whitelist():
    try:
        return db_manager.get_wanted_ids("official")
    except Exception as e:
        msg = f"Error getting whitelist: {e}"
        logger.error(msg)
        return JSONResponse({"error":msg}, status_code=400)

@router.get("/dlqueue", response_model=list[str])
def get_wanted_undownloaded():
    try:
        return db_manager.get_wanted_undownloaded_ids()
    except Exception as e:
        msg = f"Error getting download queue: {e}"
        logger.error(msg)
        return JSONResponse({"error":msg}, status_code=400)


@router.get("/fulls", response_model=list[Song])
async def get_full_records(ids:list[str]):
    """Get all song data as JSON"""
    try:
        return db_manager.get_full_records(ids)
    except Exception as e:
        msg = f"Error getting full records for ids ({ids}): {e}" 
        logger.error(msg)
        return JSONResponse({"error":msg}, status_code=400)

@router.post("/")
async def update_songs(song_updates:list[Song]):
    """Get all song data as JSON"""
    try:
        return db_manager.store_songs(song_updates)
    except Exception as e:
        msg = f"Error updating songs ({song_updates}): {e}" 
        logger.error(msg)
        return JSONResponse({"error":msg}, status_code=400)


router.mount("/", StaticFiles(directory="www"), name="www")