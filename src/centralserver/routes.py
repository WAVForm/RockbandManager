from h11 import Data
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
from .models import Song, SongHash
from centralserver.database_manager import DatabaseManager

logger = logging.getLogger("CentralServer")
db_manager = DatabaseManager()
router = FastAPI()

@router.get("/ids/{table}", response_model=list[str] | dict[str,str])
async def get_song_data(table:str):
    """Get all song data as JSON"""
    try:
        return db_manager.get_all_ids(table)
    except Exception as e:
        msg = f"Error getting customs: {e}" 
        logger.error(msg)
        return JSONResponse({"error":msg}, status_code=400)

# @router.get("/songs/{table}", response_model=SongsModel)
# async def get_song_data(table:str):
#     """Get all song data as JSON"""
#     try:
#         return db_manager.get_all_fields(table)
#     except Exception as e:
#         msg = f"Error getting customs: {e}" 
#         logger.error(msg)
#         return JSONResponse({"error":msg}, status_code=400)

# @router.post("/songs/{table}")
# async def update_customs(request:Request, table:str):
#     """Update song data"""
#     try:
#         data = await request.json()
#         db_manager.update_wanted(data["updates"], target_table=table)
#         return {"success": True, "message": f"Updated {len(data["updates"])} customs songs"}
#     except Exception as e:
#         msg = f"Error updating customs: {e}" 
#         logger.error(msg)
#         return JSONResponse({"error": msg},status_code=400)

# @router.get("/whitelist")
# def get_whitelist():
#     try:
#         return db_manager.get_wanted_official_songs()
#     except Exception as e:
#         msg = f"[Server] Error getting whitelist: {e}"
#         logger.error(msg)
#         return JSONResponse({"error":msg}, status_code=400)





# @router.post("/songs")
# async def update_officials(request: fastapi.Request, response: fastapi.Response):
#     try:
#         logger.debug("Updating 'officials' table in DB")
#         logger.debug("Getting json from request")
#         songs = await request.json()
#         logger.debug("Checking if songs is list")
#         if not isinstance(songs, list):
#             raise ValueError("Expected list of songs")
#         logger.debug("Firing up DatabaseManager")
#         db_m = DatabaseManager()
#         logger.debug("Saving songs to 'officials'")
#         db_m.save_songs(songs, "officials")                
#         return "OK"
#     except Exception as e:
#         logger.error(f"Error during updating db: {e}")
#         response.status_code = 400
#         return f"[Server] Error updating whitelist: {e}"

router.mount("/", StaticFiles(directory="www"), name="www")