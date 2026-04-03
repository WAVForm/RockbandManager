from retry import retryable, RetryError
import logging
from ftplib import FTP
import os.path as osp

logger = logging.getLogger("RBManager")

'''
Due to stability issues with connecting to PS3, all functions automatically retry and a new FTP connection is made each step.
'''

@retryable()
def get_game_folders(ps3_ip, root_game_path):
    '''
    Helper function to find game folders
    '''
    try:
        game_folders = []
        with FTP(ps3_ip, encoding="latin-1", timeout=60) as ftp:
            logger.info("Connected to PS3, logging in and finding game folders...")
            ftp.login()
            ftp.cwd(root_game_path)
            for game_folder, t in ftp.mlsd():
                if game_folder == "." or game_folder == "..":
                    continue
                elif t["type"] == "dir":
                    game_folders.append(osp.join(root_game_path,game_folder))
        logger.info("Found game folders")
        return game_folders
    except Exception as e:
        logger.error(f"Error finding game folders: {e}, retry...")
        raise RetryError(e)
    
@retryable()
def get_usr_dirs(game_folders, ps3_ip): 
    '''
    Helper function to find 'USRDIR' folders
    '''
    try:
        usr_dirs = []
        with FTP(ps3_ip, encoding="latin-1", timeout=60) as ftp:
            logger.info("Connected to PS3, logging in and finding USRDIRs...")
            ftp.login()
            for game_folder in game_folders:
                ftp.cwd(game_folder)
                for in_game_folder, t in ftp.mlsd():
                    if in_game_folder == "USRDIR":
                        usr_dirs.append(osp.join(game_folder, "USRDIR"))
                ftp.cwd("/")
        logger.info("Found game folders containig 'USRDIR'")
        return usr_dirs
    except Exception as e:
        logger.error(f"Error finding USRDIRs: {e}, retry...")
        raise RetryError(e)

@retryable()
def get_song_folders(usr_dirs, ps3_ip):
    '''
    Helper function to find song folders
    '''
    try:
        song_folders = []
        with FTP(ps3_ip, encoding="latin-1", timeout=60) as ftp:
            self.logger.info("Connected to PS3, logging in and finding song folders...")
            ftp.login()
            for usr_dir in usr_dirs:
                ftp.cwd(usr_dir)
                for in_usr_dir,t in ftp.mlsd():
                    if in_usr_dir == "." or in_usr_dir == "..":
                        continue
                    if t["type"] == "dir" and in_usr_dir != "gen":
                        path = osp.join(usr_dir, in_usr_dir)
                        ftp.cwd(path)
                        for song_folder,t in ftp.mlsd():
                            if song_folder == "songs":
                                song_folders.append(osp.join(path, "songs"))
                                ftp.cwd("/")
                                break
                    ftp.cwd("/")
                ftp.cwd("/")                              
        logger.info("Found song folders")
        return song_folders
    except Exception as e:
        logger.error(f"Error finding song folders: {e}, retry...")
        raise RetryError(e)

@retryable()
def find_dta_files(song_folders, ps3_ip):
    '''
    Helper function to find .dta files
    '''
    try:
        dta_dirs = {}
        with FTP(ps3_ip, encoding="latin-1", timeout=60) as ftp:
            logger.info("Connected to PS3, logging in and finding .dta files...")
            ftp.login()
            for song_folder in song_folders:
                ftp.cwd(song_folder)
                dta_found = False
                dtab_found = False
                for file,t in ftp.mlsd():
                    if t["type"] == "file":
                        if file.endswith(".dtab"):
                            dtab_found = True
                            break
                        elif file.endswith(".dta"):
                            dta_found = True
                if dtab_found:
                    dta_dirs[song_folder] = True
                elif dta_found:
                    dta_dirs[song_folder] = False
                ftp.cwd("/")
        logger.info("Found .dta files")
        return dta_dirs
    except Exception as e:
        logger.error(f"Error finding .dta files: {e}, retry...")
        raise RetryError(e)

def run(ps3_ip:str, root_game_path:str="/dev_hdd0/game"):
    game_folders = get_game_folders(ps3_ip, root_game_path)
    usr_dirs = get_usr_dirs(game_folders, ps3_ip)
    song_folders = get_song_folders(usr_dirs, ps3_ip)
    return find_dta_files(song_folders, ps3_ip)