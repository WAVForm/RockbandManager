import logging
import os

logger = logging.getLogger("RBManager")

def get_game_folders(emu_path, root_game_path):
    '''
    Helper function to find game folders
    '''
    logger.info("Looking for game folders...")
    try:
        game_folders = []
        path = os.path.join(emu_path, root_game_path)
        for game_folder in os.listdir(path):
            game_folders.append(os.path.join(path, game_folder))
        logger.info("Found game folders")
        return game_folders
    except Exception as e:
        logger.error(f"Error finding game folders: {e}")
        raise

def get_usr_dirs(game_folders):
    '''
    Helper function to find game folders
    '''
    logger.info("Looking for 'USRDIR' folders...")
    try:
        usr_dirs = []
        for game_folder in game_folders:
            path = os.path.join(game_folder, "USRDIR")
            if os.path.isdir(path):
                usr_dirs.append(path)
        logger.info("Found game folders containig 'USRDIR'")
        return usr_dirs
    except Exception as e:
        logger.error(f"Error finding USRDIRs: {e}")
        raise

def get_song_folders(usr_dirs):
    '''
    Helper function to find game folders
    '''
    logger.info("Looking for song folders...")
    try:
        song_folders = []
        for usr_dir in usr_dirs:
            for in_usr_dir in os.listdir(usr_dir):
                if in_usr_dir == 'gen':
                    continue
                songs_path = os.path.join(usr_dir, in_usr_dir, "songs")
                if os.path.isdir(songs_path):
                    song_folders.append(songs_path)
        logger.info("Found song folders")
        return song_folders
    except Exception as e:
        logger.error(f"Error finding song folders: {e}")
        raise

def find_dta_files(song_folders):
    '''
    Helper function to find .dta files
    '''
    logger.info("Looking for .dta files...")
    try:
        dta_dirs = {}
        for song_folder in song_folders:
            dta_found = False
            dtab_found = False
            for file in os.listdir(song_folder):
                if file.endswith(".dtab"):
                    dtab_found = True
                    break
                elif file.endswith(".dta"):
                    dta_found = True
            if dtab_found:
                dta_dirs[song_folder] = True
            elif dta_found:
                dta_dirs[song_folder] = False
        logger.info("Found .dta files")
        return dta_dirs
    except Exception as e:
        logger.error(f"Error finding .dta files: {e}")
        raise

def run(emu_path:str, root_game_path:str="dev_hdd0/game"):
    game_folders = get_game_folders(emu_path=emu_path, root_game_path=root_game_path)
    usr_dirs = get_usr_dirs(game_folders)
    song_folders = get_song_folders(usr_dirs)
    return find_dta_files(song_folders)
    