import logging
import logging.config
from tempfile import gettempdir
from pathlib import Path

from requests import get, post

from rockbandmanager.utils.endpoint.ps3_logic import (
    download_dtas,
    get_dta_dirs,
    get_ps3_connection,
    restore_dtas,
    upload_dtas,
)
from rockbandmanager.utils.dtaprocessing import read_dtas, write_dtas, cross_ref_whitelist
from rockbandmanager.utils.connection import get_ip_and_port
from rockbandmanager.utils import setup

if __name__ == "__main__":
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "file": {
                    "level": "DEBUG",
                    "class": "logging.FileHandler",
                    "filename": "client.log",
                    "formatter": "default",
                },
                "stdout": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "loggers": {
                "Client": {
                    "handlers": ["file", "stdout"],
                    "level": "DEBUG",
                    "propagate": False,
                },
                "Utilities": {
                    "handlers": ["file"],
                    "level": "DEBUG",
                    "propagate": False,
                },
            },
        }
    )
    logger = logging.getLogger("Client")

    try:
        logger.info("Setting up, reading configuration file")
        config = setup.run(project_root_dir=Path(__file__).resolve().parent.parent.parent, temp_dir=Path(gettempdir()), owner="client")
        logger.info("Successfully set up")

        logger.info("Getting PS3 connection")
        ps3_connection_info = get_ps3_connection.run()
        logger.info("Successfully got PS3 connection")

        logger.info("Getting .dta/.dtab directories")
        dta_dirs = get_dta_dirs.run(ps3_connection_info=ps3_connection_info, root_game_path=config["root_game_path"])
        logger.info("Successfully got .dta/.dtab directories")

        user_input = input(
            "Would you like to restore song data backup?\nNote: this is in case something messed up Rockband and will exit the program immediately after finishing.\n(y/n)>: "
        )
        if len(user_input) > 0 and user_input.lower()[0] == "y":
            try:
                restore_dtas.run(ps3_connection_info=ps3_connection_info, dl_cache_path=Path(config["dl_cache_path"]), dta_dirs=dta_dirs)
                logger.info("Successfully restored .dta files")
            except Exception:
                logger.error("Failed restoring .dta files")
            exit()

        logger.info("Downloading/copying .dta/.dtab")
        dta_dirs = download_dtas.run(ps3_connection_info=ps3_connection_info, dl_cache_path=Path(config["dl_cache_path"]), dta_dirs=dta_dirs)
        logger.info("Successfully downloaded/copied .dta/.dtab")

        logger.info("Processing .dta/.dtab files")
        dir_songs = read_dtas.run(Path(config["dl_cache_path"]), dta_dirs)
        logger.info("Successfully processed .dta/.dtab files")

        print("Please enter the central server's IP and port")
        try:
            server_ip, server_port = get_ip_and_port()
        except Exception as e:
            logger.error(f"Failed on getting central server's IP: {e}")

        logger.info("Updating songs on server")
        try:
            response = post(
                f"http://{server_ip}:{server_port}/",
                json=[song.model_dump(mode="json") for songs in dir_songs.values() for song in songs]
            )
            if response.status_code == 400:
                raise Exception(
                    f"Server responded with '{response.status_code}|{response.content}'"
                )
        except Exception as e:
            logger.error(f"Failed to sending songs to server: {e}")
        logger.info("Successfully updated songs")

        logger.info("Getting whitelist information from server")
        try:
            response = get(f"http://{server_ip}:{server_port}/whitelist")
            if response.status_code == 204:
                logger.warning("Server had no table 'officials' in database")
            else:
                print(response.json())
                input("Testicles")
        except Exception as e:
            logger.error(f"failed updating whitelist: {e}")
        logger.info("Succesfully updated whitelist")

        logger.info("Update songs by whitelist")
        cross_ref_whitelist.run(dir_songs, whitelist)
        logger.info("Sucessfully updated songs by whitelist")

        # user_input = input("Would you like to manually audit the excluded songs?\n(y/n)>: ")
        # if user_input.lower()[0] == 'y':
        #     song_manager.manual_confirmation()

        logger.info("Finalizing new .dta files for upload")
        write_dtas.run(
            dl_cache_path=config["dl_cache_path"],
            ul_cache_path=config["ul_cache_path"],
            dir_songs=dir_songs
        )
        logger.info("Successfully finalized new .dta files")

        logger.info("Uploading updated .dta/.dtab files")
        upload_dtas.run(ps3_connection_info=ps3_connection_info, ul_cache_path=Path(config["ul_cache_path"]), dta_dirs=dta_dirs)
        logger.info("Successfully uploaded updated .dta/.dtab files")

        user_input = input("Would you like to process custom songs?\n(y/n)>: ")
        if user_input.lower()[0] != "y":
            exit()

        # TODO add custom song processing: get wanted customs, download files from url, convert to .pkg, tell RBManager to send them to applicable directory on target

    except Exception as e:
        logger.error(f"General Error:{e}")
