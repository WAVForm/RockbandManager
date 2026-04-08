from retry import retryable, RetryError
import logging
from ftplib import FTP
import os.path as osp
from .models import PS3ConnectionInfo

logger = logging.getLogger("RBManager")

'''
Due to stability issues with connecting to PS3, all functions automatically retry and a new FTP connection is made each step.
'''

def treat_nlst_as_mlsd(ftp: FTP):
    '''
    Helper function to enumerate directories and determine whether entry is a file or directory
    '''
    ret = []

    lines = []
    ftp.retrlines('LIST', lines.append)

    for line in lines:
        parts = line.split()
        name = parts[-1] # Usually the last element
        
        if line.startswith('d'):
            ret.append((name,{"type":"dir"}))
        else:
            ret.append((name,{"type":"file"}))

    return ret

@retryable()
def get_game_folders(ps3_connection_info:PS3ConnectionInfo, root_game_path):
    '''
    Helper function to find game folders
    '''
    try:
        game_folders = []
        with FTP(encoding="latin-1", timeout=60) as ftp:
            ftp.connect(host=ps3_connection_info.ip,port=ps3_connection_info.port)
            logger.info("Connected to PS3, logging in and finding game folders...")
            ftp.login()
            ftp.cwd(root_game_path)

            if ps3_connection_info.ls_style == "mlsd":
                ls = ftp.mlsd()
            elif ps3_connection_info.ls_style == "nlst":
                ls = treat_nlst_as_mlsd(ftp)

            for game_folder, t in ls:
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
def get_usr_dirs(ps3_connection_info:PS3ConnectionInfo, game_folders): 
    '''
    Helper function to find 'USRDIR' folders
    '''
    try:
        usr_dirs = []
        with FTP(encoding="latin-1", timeout=60) as ftp:
            ftp.connect(host=ps3_connection_info.ip, port=ps3_connection_info.port)
            logger.info("Connected to PS3, logging in and finding USRDIRs...")
            ftp.login()
            for game_folder in game_folders:
                ftp.cwd(game_folder)

                if ps3_connection_info.ls_style == "mlsd":
                    ls = ftp.mlsd()
                elif ps3_connection_info.ls_style == "nlst":
                    ls = treat_nlst_as_mlsd(ftp)

                for in_game_folder, t in ls:
                    if in_game_folder == "USRDIR":
                        usr_dirs.append(osp.join(game_folder, "USRDIR"))
                ftp.cwd("/")
        logger.info("Found game folders containing 'USRDIR'")
        return usr_dirs
    except Exception as e:
        logger.error(f"Error finding USRDIRs: {e}, retry...")
        raise RetryError(e)

@retryable()
def get_song_folders(ps3_connection_info:PS3ConnectionInfo, usr_dirs):
    '''
    Helper function to find song folders
    '''
    try:
        song_folders = []
        with FTP(encoding="latin-1", timeout=60) as ftp:
            ftp.connect(host=ps3_connection_info.ip, port=ps3_connection_info.port)
            logger.info("Connected to PS3, logging in and finding song folders...")
            ftp.login()
            for usr_dir in usr_dirs:
                ftp.cwd(usr_dir)

                if ps3_connection_info.ls_style == "mlsd":
                    ls1 = ftp.mlsd()
                elif ps3_connection_info.ls_style == "nlst":
                    ls1 = treat_nlst_as_mlsd(ftp)

                for in_usr_dir,t in ls1:
                    if in_usr_dir == "." or in_usr_dir == "..":
                        continue
                    if t["type"] == "dir" and in_usr_dir != "gen":
                        path = osp.join(usr_dir, in_usr_dir)
                        ftp.cwd(in_usr_dir)

                        if ps3_connection_info.ls_style == "mlsd":
                            ls2 = ftp.mlsd()
                        elif ps3_connection_info.ls_style == "nlst":
                            ls2 = treat_nlst_as_mlsd(ftp)

                        for song_folder,t in ls2:
                            if song_folder == "songs":
                                song_folders.append(osp.join(path, "songs"))
                        ftp.cwd("..")
                ftp.cwd("/")                    
        logger.info("Found song folders")
        return song_folders
    except Exception as e:
        logger.error(f"Error finding song folders: {e}, retry...")
        raise RetryError(e)

@retryable()
def find_dta_files(ps3_connection_info:PS3ConnectionInfo, song_folders):
    '''
    Helper function to find .dta files
    '''
    try:
        dta_dirs = {}
        with FTP(encoding="latin-1", timeout=60) as ftp:
            ftp.connect(host=ps3_connection_info.ip, port=ps3_connection_info.port)
            logger.info("Connected to PS3, logging in and finding .dta files...")
            ftp.login()
            for song_folder in song_folders:
                ftp.cwd(song_folder)
                dta_found = False
                dtab_found = False

                if ps3_connection_info.ls_style == "mlsd":
                    ls = ftp.mlsd()
                elif ps3_connection_info.ls_style == "nlst":
                    ls = treat_nlst_as_mlsd(ftp)
                
                for file,t in ls:
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

def run(ps3_connection_info:PS3ConnectionInfo, root_game_path:str="/dev_hdd0/game"):
    game_folders = get_game_folders(ps3_connection_info, root_game_path)
    usr_dirs = get_usr_dirs(ps3_connection_info,game_folders)
    song_folders = get_song_folders( ps3_connection_info, usr_dirs)
    return find_dta_files(ps3_connection_info,song_folders)