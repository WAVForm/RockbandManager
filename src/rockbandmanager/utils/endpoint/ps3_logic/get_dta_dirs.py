from rockbandmanager.utils.retry import retryable
import logging
from ftplib import FTP
import os.path as osp
from rockbandmanager.models.endpoint import PS3ConnectionInfo

logger = logging.getLogger("Utilities")

def _treat_nlst_as_mlsd(ftp: FTP) -> list[tuple[str,dict[str,str]]]:
    """Helper function to enumerate directories and determine whether entry is a file or directory

    Args:
        ftp (FTP):

    Returns:
        list[tuple[str,dict[str,str]]]: list in the style of that returned by mlsd(): list[(name,type)]
    """
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
def _get_game_folders(ps3_connection_info:PS3ConnectionInfo, root_game_path:str) -> list[str]:
    """Helper function to find game folders

    Args:
        ps3_connection_info (PS3ConnectionInfo): PS3 connection information
        root_game_path (_type_): root directory where PS3 game data can be found

    Returns:
        list[str]: list of possible game directories found inside game data folder
    """
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
                ls = _treat_nlst_as_mlsd(ftp)

            for game_folder, t in ls:
                if game_folder == "." or game_folder == "..":
                    continue
                elif t["type"] == "dir":
                    game_folders.append(osp.join(root_game_path,game_folder))
        logger.info("Found game folders")
        return game_folders
    except Exception as e:
        logger.error(f"Error finding game folders: {e}, retry...")
        raise
    
@retryable()
def _get_usr_dirs(ps3_connection_info:PS3ConnectionInfo, game_folders:list[str]) -> list[str]: 
    """Helper function to find 'USRDIR' folders within possible game folders

    Args:
        ps3_connection_info (PS3ConnectionInfo): PS3 connection information 
        game_folders (list[str]): list of directories for possible game folders

    Returns:
        list[str]: list of USRDIR directories, marking more plausible game folders
    """
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
                    ls = _treat_nlst_as_mlsd(ftp)

                for in_game_folder, t in ls:
                    if in_game_folder == "USRDIR":
                        usr_dirs.append(osp.join(game_folder, "USRDIR"))
                ftp.cwd("/")
        logger.info("Found game folders containing 'USRDIR'")
        return usr_dirs
    except Exception as e:
        logger.error(f"Error finding USRDIRs: {e}, retry...")
        raise

@retryable()
def _get_song_folders(ps3_connection_info:PS3ConnectionInfo, usr_dirs:list[str]) -> list[str]:
    """Helper function to find song folders within USRDIR directories

    Args:
        ps3_connection_info (PS3ConnectionInfo): PS3 connection information
        usr_dirs (list[str]): list of directories containing USRDIR folders

    Returns:
        list[str]: list of 'songs' directories within USRDIR folders
    """
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
                    ls1 = _treat_nlst_as_mlsd(ftp)

                for in_usr_dir,t in ls1:
                    if in_usr_dir == "." or in_usr_dir == "..":
                        continue
                    if t["type"] == "dir" and in_usr_dir != "gen":
                        path = osp.join(usr_dir, in_usr_dir)
                        ftp.cwd(in_usr_dir)

                        if ps3_connection_info.ls_style == "mlsd":
                            ls2 = ftp.mlsd()
                        elif ps3_connection_info.ls_style == "nlst":
                            ls2 = _treat_nlst_as_mlsd(ftp)

                        for song_folder,t in ls2:
                            if song_folder == "songs":
                                song_folders.append(osp.join(path, "songs"))
                        ftp.cwd("..")
                ftp.cwd("/")                    
        logger.info("Found song folders")
        return song_folders
    except Exception as e:
        logger.error(f"Error finding song folders: {e}, retry...")
        raise

@retryable()
def _find_dta_files(ps3_connection_info:PS3ConnectionInfo, song_folders:list[str]) -> dict[str,bool]:
    """Helper function to find .dta files

    Args:
        ps3_connection_info (PS3ConnectionInfo): PS3 connection information
        song_folders (list[str]): list of directories containing 'songs' folder

    Returns:
        dict[str,bool]: key is directory .dta/ab file was found, value is if .dtab was found
    """
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
                    ls = _treat_nlst_as_mlsd(ftp)
                
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
        raise

@retryable()
def run(ps3_connection_info:PS3ConnectionInfo, root_game_path:str) -> dict[str,bool]:
    """Attempts to get directories where .dta/.dtab files are found

    Args:
        ps3_connection_info (PS3ConnectionInfo): PS3 connection info
        root_game_path (str, optional): Directory where game data folders are found.
    Returns:
        dict[str,bool]: key is the directory, value is if a .dtab was found
    """
    try:
        game_folders = _get_game_folders(ps3_connection_info, root_game_path)
        usr_dirs = _get_usr_dirs(ps3_connection_info,game_folders)
        song_folders = _get_song_folders( ps3_connection_info, usr_dirs)
        return _find_dta_files(ps3_connection_info,song_folders)
    except Exception as e:
        logger.debug(f"Error getting DTA directories from PS3: {e}")
        raise