import os
from ftplib import FTP
from shutil import copy
import logging

class RBManager:
    '''
    Manage transfering of data between data source and data processor
    '''
    def __init__(self):
        self.logger = logging.getLogger("RBManager")
        self.cwd = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir)) #keep track of the CWD
        self.dta_dirs = {} #dirs containing .dta/.dtabs on PS3, path is key, value is true if dtab is found, false otherwise
        self.make_buffers()
        self.ps3_ip = None
        self.emu_path = None

    def make_buffers(self):
        '''
        Creates the buffer directories where files will be stores after download for processing and before upload afterwards
        '''
        try:
            self.logger.info("Creating buffer directories...")
            os.makedirs(os.path.join(self.cwd, "FROM"), exist_ok=True)
            os.makedirs(os.path.join(self.cwd, "TO"), exist_ok=True)
        except Exception as e:
            self.logger.debug(f"Error making buffers: {e}")

    def get_dta_dirs(self):
        '''
        Looks for the directories containing .dta files
        '''
        #TODO add retry decorator
        def ps3():
            '''
            Helper function to seperate PS3 logic
            '''
            def get_game_folders():
                '''
                Helper function to find game folders
                '''
                try:
                    game_folders = []
                    with FTP(self.ps3_ip, encoding="latin-1", timeout=60) as ftp:
                        self.logger.info("Connected to PS3, logging in and finding game folders...")
                        ftp.login()
                        ftp.cwd("/dev_hdd0/game")
                        for game_folder, t in ftp.mlsd():
                            if game_folder == "." or game_folder == "..":
                                continue
                            elif t["type"] == "dir":
                                game_folders.append(os.path.join("/dev_hdd0/game",game_folder))
                    self.logger.info("Found game folders")
                    return game_folders
                except Exception as e:
                    self.logger.error(f"Error finding game folders: {e}")

            def get_usr_dirs(game_folders):
                '''
                Helper function to find 'USRDIR' folders
                '''
                try:
                    usr_dirs = []
                    with FTP(self.ps3_ip, encoding="latin-1", timeout=60) as ftp:
                        self.logger.info("Connected to PS3, logging in and finding USRDIRs...")
                        ftp.login()
                        for game_folder in game_folders:
                            ftp.cwd(self.to_ps3_dir(game_folder))
                            for in_game_folder, t in ftp.mlsd():
                                if in_game_folder == "USRDIR":
                                    usr_dirs.append(os.path.join(game_folder, "USRDIR"))
                            ftp.cwd("/")
                    self.logger.info("Found game folders containig 'USRDIR'")
                    return usr_dirs
                except Exception as e:
                    self.logger.error(f"Error finding USRDIRs: {e}")
            
            def get_song_folders(usr_dirs):
                '''
                Helper function to find song folders
                '''
                try:
                    song_folders = []
                    with FTP(self.ps3_ip, encoding="latin-1", timeout=60) as ftp:
                        self.logger.info("Connected to PS3, logging in and finding song folders...")
                        ftp.login()
                        for usr_dir in usr_dirs:
                            ftp.cwd(self.to_ps3_dir(usr_dir))
                            for in_usr_dir,t in ftp.mlsd():
                                if in_usr_dir == "." or in_usr_dir == "..":
                                    continue
                                if t["type"] == "dir" and in_usr_dir != "gen":
                                    path = os.path.join(usr_dir, in_usr_dir)
                                    ftp.cwd(self.to_ps3_dir(path))
                                    for song_folder,t in ftp.mlsd():
                                        if songs == "songs":
                                            song_folders.append(os.path.join(usr_dir, in_usr_dir, "songs"))
                                            ftp.cwd("/")
                                            break
                                ftp.cwd("/")
                            ftp.cwd("/")                              
                    self.logger.info("Found song folders")
                    return usr_dirs
                except Exception as e:
                    self.logger.error(f"Error finding song folders: {e}")

            def find_dta_files(song_folders):
                '''
                Helper function to find .dta files
                '''
                try:
                    dta_dirs = {}
                    with FTP(self.ps3_ip, encoding="latin-1", timeout=60) as ftp:
                        self.logger.info("Connected to PS3, logging in and finding .dta files...")
                        ftp.login()
                        for song_folder in song_folders:
                            ftp.cwd(self.to_ps3_dir(song_folder))
                            dta_found = False
                            dtab_found = False
                            for file,t in ftp.mlsd():
                                if t["type"] == "file":
                                    if file.endswith(".dtab"):
                                        dtab_found = True
                                        break
                                    elif file.endswith(".dta"):
                                        dta_found = True
                                        break
                            if dtab_found:
                                dta_dirs[song_folder] = True
                                ftp.cwd("/")
                                break
                            elif dta_found:
                                dta_dirs[song_folder] = False
                            ftp.cwd("/")
                    self.logger.info("Found .dta files")
                    return usr_dirs
                except Exception as e:
                    self.logger.error(f"Error finding .dta files: {e}")

            game_folders = get_game_folders()
            usr_dirs = get_usr_dirs(game_folders)
            song_folders = get_song_folders(usr_dirs)
            return find_dta_files(song_folders)

        #TODO add retry decorator
        def emu():
            '''
            Helper function to seperate emulator logic
            '''
            def get_game_folders():
                '''
                Helper function to find game folders
                '''
                self.logger.info("Looking for game folders...")
                try:
                    game_folders = []
                    path = os.path.join(self.emu_path, "dev_hdd0/game")
                    for game_folder in os.listdir(path):
                        game_folders.append(os.path.join(path, game_folder))
                    self.logger.info("Found game folders")
                    return game_folders
                except Exception as e:
                    self.logger.error(f"Error finding game folders: {e}")

            def get_usr_dirs(game_folders):
                '''
                Helper function to find game folders
                '''
                self.logger.info("Looking for 'USRDIR' folders...")
                try:
                    usr_dirs = []
                    for game_folder in game_folders:
                        path = os.path.join(game_folder, "USRDIR")
                        if os.path.isdir(path):
                            usr_dirs.append(path)
                    self.logger.info("Found game folders containig 'USRDIR'")
                    return usr_dirs
                except Exception as e:
                    self.logger.error(f"Error finding USRDIRs: {e}")
            
            def get_song_folders(usr_dirs):
                '''
                Helper function to find game folders
                '''
                self.logger.info("Looking for song folders...")
                try:
                    song_folders = []
                    for usr_dir in usr_dirs:
                        for in_usr_dir in os.listdir(usr_dir):
                            if in_usr_dir == 'gen':
                                continue
                            songs_path = os.path.join(usr_dir, in_usr_dir, "songs")
                            if os.path.isdir(songs_path):
                                song_folders.append(songs_path)
                    self.logger.info("Found song folders")
                    return usr_dirs
                except Exception as e:
                    self.logger.error(f"Error finding song folders: {e}")

            def find_dta_files(song_folders):
                '''
                Helper function to find .dta files
                '''
                self.logger.info("Looking for .dta files...")
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
                            dta_dirs[os.path.relpath(song_folder, self.emu_path)] = True
                            break
                        elif dta_found:
                            dta_dirs[os.path.relpath(song_folder, self.emu_path)] = False
                    self.logger.info("Found .dta files")
                    return usr_dirs
                except Exception as e:
                    self.logger.error(f"Error finding .dta files: {e}")
    
            game_folders = get_game_folders()
            usr_dirs = get_usr_dirs(game_folders)
            song_folders = get_song_folders(usr_dirs)
            return find_dta_files(song_folders)
            
        self.logger.info("Getting .dta directories...")
        try:
            if self.ps3_ip != None:
                self.dta_dirs = ps3()
            elif self.emu_path != None:
                self.dta_dirs = emu()
            else:
                raise ValueError("PS3 IP and Emulator path not defined")
            return True
        except Exception as e:
            self.logger.error(f"Error getting .dta dirs: {e}")
            return False

    def download_dtas(self):
        '''
        Downloads/copies .dta files from target source
        '''
        def ps3():
            '''
            Helper function to seperate PS3 logic
            '''
            dtas = {}
            with FTP(self.ps3_ip, encoding="latin-1", timeout=60) as ftp:
                self.logger.info("Connected to PS3, logging in and downloading .dta/dtab...")
                ftp.login()
                for dir in self.dta_dirs.keys():
                    ftp.cwd(self.to_ps3_dir(dir))
                    downloaded_dta_path = os.path.join(self.cwd, "FROM", dir)
                    if not os.path.exists(downloaded_dta_path):
                        self.logger.info("Making dir for .dta download")
                        os.makedirs(downloaded_dta_path)
                    extension = "songs.dtab" if self.dta_dirs[dir] else "songs.dta"
                    with open(os.path.join(downloaded_dta_path, "songs.dta"), "wb") as dta_f:
                        ftp.retrbinary(f"RETR {extension}", dta_f.write)
                        dtas[downloaded_dta_path] = ""
                    ftp.cwd("/")
            return dtas

        def emu():
            '''
            Helper function to seperate emulator logic
            '''
            dtas = {}
            self.logger.info("Copying .dta...")
            for dir in self.dta_dirs.keys():
                downloaded_dta_path = os.path.join(self.cwd, "FROM", dir)
                emu_path = os.path.join(self.emu_path, dir)
                os.makedirs(downloaded_dta_path, exist_ok=True)
                extension = "songs.dtab" if os.path.exists(os.path.join(emu_path, "songs.dtab")) else "songs.dta"
                copy(os.path.join(emu_path, extension), os.path.join(downloaded_dta_path, "songs.dta"))
                dtas[downloaded_dta_path] = ""
            return dtas

        try:
            dtas = {}
            if self.ps3_ip != None:
                dtas = ps3()
            elif self.emu_path != None:
                dtas = emu()
            else:
                raise ValueError("PS3 IP and Emulator path not defined")
            return (True, dtas)
        except Exception as e:
            self.logger.error(f"Error downloading .dtas: {e}")
            return False

    def upload(self):
        '''
        Uploads modified .dta files back to target source
        '''
        def ps3():
            '''
            Helper function to seperate PS3 logic
            '''
            with FTP(self.ps3_ip, encoding='latin-1', timeout=60) as ftp:
                ftp.login()
                for dir in self.dta_dirs.keys():
                    path = os.path.join(self.cwd, "TO", dir)
                    self.logger.info(f"Uploading .dta at {path}, to {dir}")
                    ftp.cwd(self.to_ps3_dir(dir))
                    with open(os.path.join(path, "songs.dta")) as dta_f:
                        ftp.storbinary("STOR songs.dta", dta_f)
                    with open(os.path.join(path, "songs.dtab")) as dtab_f:
                        ftp.storbinary("STOR songs.dtab", dtab_f)
                    ftp.cwd("/")

        def emu():
            '''
            Helper function to seperate emulator logic
            '''
            for dir in self.dta_dirs.keys():
                path = os.path.join(self.cwd, "TO", dir)
                emu_path = os.path.join(self.emu_path, dir)
                self.logger.info(f"Copying .dta at {path}, to {emu_path}")
                copy(os.path.join(path, "songs.dta"), os.path.join(emu_path, "songs.dta"))
                copy(os.path.join(path, "songs.dtab"), os.path.join(emu_path, "songs.dtab"))

        try:
            if self.ps3_ip != None:
                ps3()
            elif self.emu_path != None:
                emu()
            else:
                raise ValueError("PS3 IP and Emulator path not defined")
            return True
        except Exception as e:
            self.logger.error(f"Error uploading .dtas: {e}")
            return false

    def restore_dtas(self):
        '''
        Reuploads available unmodified .dta files back to target source. Used in cases where reverting to a backup is needed (corruption, error, etc.) 
        '''
        def ps3():
            '''
            Helper function to seperate PS3 logic
            '''
            with FTP(self.ps3_ip, encoding='latin-1', timeout=60) as ftp:
                ftp.login()
                for dir in self.dta_dirs.keys():
                    path = os.path.join(self.cwd, "FROM", dir, "songs.dta")
                    if not os.path.exists(path):
                        continue
                    ftp.cwd(self.to_ps3_dir(dir))
                    with open(path, 'rb') as dta_f:
                        ftp.storbinary(f"STOR songs.dta", dta_f)
                    ftp.cwd("/")            
        
        def emu():
            '''
            Helper function to seperate emulator logic
            '''
            for dir in self.dta_dirs.keys():
                path = os.join(self.cwd, "FROM", dir, "songs.dta")
                if not os.path.exists(path):
                    continue
                copy(path, os.path.join(self.emu_path, dir, "songs.dta"))
        
        try:
            if self.ps3_ip != None:
                ps3()
            elif self.emu_path != None:
                emu()
            else:
                raise ValueError("PS3 IP and Emulator path not defined")
            return True
        except Exception as e:
            self.logger.error(f"Error reuploading .dtas: {e}")
            return False

    def to_ps3_dir(self, dir: str):
        '''Helper function for converting Windows path schema to PS3 schema'''
        return dir.replace('\\','/')

    def get_ps3_connection(self):
        '''
        Attempts to get valid PS3 connection details from user
        '''
        from ipaddress import ip_address
        try:
            ip = ip_address(input("Please enter the IP of the PS3\n>: "))
            with FTP(ip, encoding='latin-1', timeout=60) as ftp:
                self.logger.info("PS3 Connection Validated")
                self.ps3_ip = ip
            if self.ps3_ip is None:
                raise Exception("Connection could not be established with provided IP")
            return True
        except Exception as e:
            self.logger.debug(f"Error getting PS3 connection: {e}")
            return False

    def get_emulator_path(self):
        '''
        Attempts to get valid PS3 emulator path
        '''
        try:
            path = input("Please enter the root path to the emulator (i.e. the folder with 'dev_hdd0' in it)\n>: ")
            if os.path.isdir(path) and 'dev_hdd0' in os.listdir(path):
                self.emu_path = path
                return True
        except Exception as e:
            self.logger.debug(f"Error getting emulator path: {e}")
            return False