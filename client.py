from re import match
import logging, logging.config
import requests

from rb_manager import RBManager
from song_manager import SongManager

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

song_manager = SongManager()
rb_manager = RBManager()

while True:
    pattern = r"\b((?:\d{1,3}\.){3}\d{1,3}):([0-9]{1,5})"
    res = match(pattern, input("Please enter the backend's IP and port (x.x.x.x:xxxxx)>: "))
    if not res:
        print("IP and Port is invalid.")
        continue
    ip, port = res.groups()
    server_ip = f"{ip}:{port}"

    try:
        print("Select one of the following:\n1. Connect to a PS3 Remotely\n2.Provide path to root of emulator")
        user_input = input(">: ")
        match int(user_input):
            case 1:
                logger.info("[RBClient] Getting PS3 connection")
                while True:
                    if not rb_manager.get_ps3_connection():
                        print("Could not connect with provided input.")
                    else:
                        break
                logger.info("[RBClient] Successfully got PS3 connection")
            case 2:
                logger.info("[RBCLient] Getting PS3 emulator path")
                while True:
                    if not rb_manager.get_emulator_path():
                        print("Could not use provided path.")
                    else:
                        break
            case _:
                pass
        
        logger.info("[RBClient] Getting .dta/.dtab directories")
        if not rb_manager.get_dta_dirs():
            raise Exception("Failed getting directories of .dta/.dtab files, check log.")
        logger.info("[RBClient] Successfully got .dta/.dtab directories")

        logger.info("[RBClient] Downloading/copying .dta/.dtab")
        dta_download_attempt = rb_manager.download_dtas()
        if type(dta_download_attempt) != tuple:
            raise Exception("Failed downloading/copying .dta/.dtab files, check log.")
        logger.info("[RBClient] Successfully downloaded/copied .dta/.dtab")
        
        user_input = input("Would you like to restore .dta files back? Note: this is in case something messed up the Rockband database and will exit the program immediately after finishing.\n(y/n)>: ")
        if user_input.lower().startswith("y"):
            try:
                rb_manager.reuploaddtas()
                logger.info("[RBClient] Successfully restored .dta files")
            except Exception as e:
                logger.error("[RBClient] Failed restoring .dta files")
            exit()

        logger.info("[RBClient] Processing .dtab files")
        song_manager.dtas = dta_download_attempt[1]
        if not song_manager.read_dtas():
            raise Exception("Failed processing .dta/.dtab files, check log.")
        logger.info("[RBClient] Successfully processed .dtab files")

        logger.info("[RBClient] Getting whitelist information from server")
        try:
            response = requests.get("http://"+server_ip+"/whitelist")
            if response.status_code == 204:
                logger.warning("[RBClient] Server had no song database")
            else:   
                song_manager.whitelist = response.json()
        except Exception as e:
            logger.error(f"[RBClient] failed updating whitelist: {e}")
        logger.info("[RBClient] Succesfully updated whitelist")

        logger.info("[RBClient] Excluding songs by whitelist")
        if not song_manager.exclude_from_whitelist():
            raise Exception("Failed excluding songs by whitelist, check log.")
        logger.info("[RBClient] Sucessfully excluded songs by whitelist")

        user_input = input("Would you like to manually audit the excluded songs? Note: there is double confirmation for exclusion in case you make a mistake\n(y/n)>: ")
        if user_input.lower().startswith("y"):
            song_manager.manual_elimination()
        
        logger.info("[RBClient] Updating excluded songs on server")
        try:
            response = requests.post("http://"+server_ip+"/songs", json=[{"title":song.name, "artist":song.artist, "excluded":song.excluded, "reason":song.reason} for song in song_manager.kept + song_manager.excluded])
            if response.status_code != 200:
                raise Exception(f"Server responded with '{response.status_code}|{response.content}'")
        except Exception as e:
            logger.error(f"[RBClient] Failed to sending excluded songs to server: {e}")
        #TODO update database to mark songs excluded
        logger.info("[RBClient] Successfully updated excluded songs")

        logger.info("[RBClient] Finalizing new .dta files for upload")
        if not song_manager.finalize():
            raise Exception("Failed finalizing updated .dta files, check log.")
        logger.info("[RBClient] Successfully finalized new .dta files")

        logger.info("[RBClient] Uploading updated .dta/.dtab files")
        if not rb_manager.upload():
            raise Exception("Failed uploading updated .dta/.dtab files, check log.")
        logger.info("[RBClient] Successfully uploaded updated .dta/.dtab files")

        user_input = input("Would you like to process custom songs?\n>: ")
        if user_input.lower().startswith("y"):
            pass

    except Exception as e:
        print(f"Error:{e}")