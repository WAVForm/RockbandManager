import logging, logging.config
from requests import get, post
from ipaddress import ip_address
from re import match

from rb_manager import RBManager
from song_manager import SongManager

if __name__ == "__main__":
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
                'filename': 'client.log',
                'formatter': 'default',
            },
            'stdout': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
        },
        'loggers': {
            'Client': {
                'handlers': ['file', 'stdout'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'RBManager': {
                'handlers': ['file', 'stdout'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'SongManager': {
                'handlers': ['file', 'stdout'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    })
    logger = logging.getLogger("Client")

    song_manager = SongManager()
    rb_manager = RBManager()

    try:
        user_input = input("Select one of the following:\n1. Connect to a PS3 Remotely\n2.Provide path to root of emulator\n>: ")
        match int(user_input):
            case 1:
                logger.info("Getting PS3 connection")
                while True:
                    if not rb_manager.get_ps3_connection():
                        logger.error("Could not connect with provided input.")
                    else:
                        break
                logger.info("Successfully got PS3 connection")
            case 2:
                logger.info("Getting PS3 emulator path")
                while True:
                    if not rb_manager.get_emulator_path():
                        logger.error("Could not use provided path.")
                    else:
                        break
            case _:
                print("The selection must be in range")
        
        logger.info("Getting .dta/.dtab directories")
        if not rb_manager.get_dta_dirs():
            raise Exception("Failed getting directories of .dta/.dtab files, check log.")
        logger.info("Successfully got .dta/.dtab directories")

        user_input = input("Would you like to restore .dta files back?\nNote: this is in case something messed up the Rockband game and will exit the program immediately after finishing.\n(y/n)>: ")
        if user_input.lower()[0] == 'y':
            try:
                rb_manager.restore_dtas()
                logger.info("Successfully restored .dta files")
            except Exception as e:
                logger.error("Failed restoring .dta files")
            exit()

        logger.info("Downloading/copying .dta/.dtab")
        dta_download_attempt = rb_manager.download_dtas()
        if type(dta_download_attempt) != tuple:
            raise Exception("Failed downloading/copying .dta/.dtab files, check log.")
        dta_paths = dta_download_attempt[1]
        logger.info("Successfully downloaded/copied .dta/.dtab")

        logger.info("Processing .dtab files")
        if not song_manager.read_dtas(dta_paths):
            raise Exception("Failed processing .dta/.dtab files, check log.")
        logger.info("Successfully processed .dtab files")

        print("The next part requires the central server for whitelist information")
        try:
            pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})"
            res = match(pattern, input("Please enter the IP and port (x.x.x.x:xxxxx)>: "))
            if not res:
                raise Exception()
            server_ip, server_port = res.groups()
            octets = list(map(int, server_ip.split('.')))
            if any(o <0 or o > 255 for o in octets):
                raise Exception("Octets out of range")
        except Exception as e:
            logger.error(f"Failed on getting central server's IP: {e}")

        logger.info("Getting whitelist information from server")
        try:
            response = get(f"http://{server_ip}:{server_port}/whitelist")
            if response.status_code == 204:
                logger.warning("Server had no table 'officials' in database")
            else:
                song_manager.whitelist = [(entry["artist"], entry["title"]) for entry in response.json()]
        except Exception as e:
            logger.error(f"failed updating whitelist: {e}")
        logger.info("Succesfully updated whitelist")

        logger.info("Excluding songs by blacklist")
        if not song_manager.exclude_blacklisted():
            raise Exception("Failed excluding songs by blacklist, check log.")
        logger.info("Sucessfully excluded songs by blacklist")

        user_input = input("Would you like to manually audit the excluded songs?\n(y/n)>: ")
        if user_input.lower()[0] == 'y':
            song_manager.manual_confirmation()
        
        logger.info("Updating excluded songs on server")
        try:
            response = post(f"http://{server_ip}:{server_port}/songs", json=[{"title":song.name, "artist":song.artist, "wanted":(not song.excluded)} for song in song_manager.kept + song_manager.excluded])
            if response.status_code != 200:
                raise Exception(f"Server responded with '{response.status_code}|{response.content}'")
        except Exception as e:
            logger.error(f"Failed to sending excluded songs to server: {e}")
        logger.info("Successfully updated excluded songs")

        logger.info("Finalizing new .dta files for upload")
        if not song_manager.finalize():
            raise Exception("Failed finalizing updated .dta files, check log.")
        logger.info("Successfully finalized new .dta files")

        logger.info("Uploading updated .dta/.dtab files")
        if not rb_manager.upload():
            raise Exception("Failed uploading updated .dta/.dtab files, check log.")
        logger.info("Successfully uploaded updated .dta/.dtab files")

        user_input = input("Would you like to process custom songs?\n(y/n)>: ")
        if user_input.lower()[0] != 'y':
            exit()
        
        #TODO add custom song processing: get wanted customs, download files from url, convert to .pkg, tell RBManager to send them to applicable directory on target

    except Exception as e:
        logger.error(f"General Error:{e}")