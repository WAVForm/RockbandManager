import os
import ftplib
import time
import shutil
import logging

class RBManager:
    '''
    Manage processing of remote data
    '''
    def __init__(self):
        self.logger = logging.getLogger("RBManager")
        self.cwd = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir)) #keep track of the CWD
        self.dta_dirs = {} #dirs containing .dta/.dtabs on PS3, path is key, value is true if dtab is found, false otherwise
        self.make_buffers()
        self.ps3_ip = None
        self.emu_path = None

    def make_buffers(self):
        try:
            self.logger.info("Checking for FTP buffer directories...")
            from_buffer_path = os.path.join(self.cwd, "FROM")
            to_buffer_path = os.path.join(self.cwd, "TO")
            if not os.path.exists(from_buffer_path):
                self.logger.info("Making FROM directory.")
                os.mkdir(from_buffer_path) #create the dir that will hold ftp downloads
            if not os.path.exists(to_buffer_path):
                self.logger.info("Making TO directory.")
                os.mkdir(to_buffer_path) #create the dir that will hold ftp uploads
        except Exception as e:
            self.logger.debug(f"[RBManager] Error making buffers: {e}")

    def get_dta_dirs(self,max_retries=5,retry_delay=5):
        try:
            if self.ps3_ip != None:
                for attempt in range(max_retries):
                    try:
                        with ftplib.FTP(self.ps3_ip, encoding='latin-1') as ftp:
                            self.logger.info("[RBManager] Connected to PS3, logging in and searching...")
                            ftp.login()
                            ftp.cwd("/dev_hdd0/game")

                            game_folders = []
                            try:
                                for game_folder, t in ftp.mlsd():
                                    if game_folder == "." or game_folder == '..':
                                        continue
                                    if t['type'] == 'dir':
                                        game_folders.append(f"/dev_hdd0/game/"+game_folder)
                            except Exception as e:
                                self.logger.error(f"[RBManager] Error finding game folders: {e}")
                                return False
                            self.logger.info("[RBManager] Game folders found")

                            usrdirs = []
                            try:
                                for game_folder in gamefolders:
                                    ftp.cwd(game_folder)
                                    for in_game_folder,t in ftp.mlsd():
                                        if in_game_folder == "USRDIR":
                                            usrdirs.append(game_folder+"/USRDIR")
                            except Exception as e:
                                self.logger.error(f"[RBManager] error finding 'USRDIR': {e}")
                                return False
                            self.logger.info("[RBManager] Found game folders containing 'USRDIR'")

                            song_folders = []
                            try:
                                for usrdir in usrdirs:
                                    ftp.cwd(usrdir)
                                    for subfolder,t in ftp.mlsd():
                                        if subfolder == '.' or subfolder == '..':
                                            continue
                                        if t['type'] == 'dir' and subfolder != 'gen':
                                            path = usrdir+"/"+subfolder
                                            for songs,t in ftp.mlsd():
                                                if songs == "songs":
                                                    song_folders.append(usrdir+"/"+subfolder+"/songs")
                            except Exception as e:
                                self.logger.error(f"[RBManager] Error finding 'songs' folders: {e}")
                                return False
                            self.logger.info("[RBManager] Found game folders containing 'songs' folders")

                            try:
                                for song_folder in song_folders:
                                    ftp.cwd(song_folder)
                                    dtab_found = False
                                    dta_found = False
                                    for file, t in ftp.mlsd():
                                        if t['type'] == 'file':
                                            if file.endswith(".dtab"):
                                                dtab_found = True
                                                break
                                            elif file.endswith(".dta"):
                                                dta_found = True
                                    if dtab_found:
                                        self.dta_dirs[song_folder] = True
                                    elif dta_found:
                                        self.dta_dirs[song_folder] = False
                            except Exception as e:
                                self.logger.error(f"[RBManager] error finding .dtab/.dta file paths: {e}")
                                return False
                            self.logger.info("[RBManager] Found .dtab/.dta file paths")
                            return True
                    except ftplib.error_temp as e:
                        self.logger.warning(f"[RBManager] PS3 FTP attempt {attempt + 1} failed with error: {e}")
                        if attempt < max_retries - 1:
                            self.logger.info(f"[RBManager] PS3 FTP retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            self.logger.error("[RBManager] PS3 FTP max retries reached. Could not complete the operation.")
                            return False
            elif self.emu_path != None:
                for attempt in range(max_retries):
                    try:
                        self.logger.info("[RBManager] Starting emulator directory scan...")
                        base_path = os.path.join(self.emu_path, "dev_hdd0/game")
                        game_folders = []
                        try:
                            for game_folder in os.listdir(base_path):
                                full_path = os.path.join(base_path, game_folder)
                                if os.path.isdir(full_path):
                                    game_folders.append(full_path)
                        except Exception as e:
                            self.logger.error(f"[RBManager] Error finding game folders: {e}")
                            return False

                        self.logger.info("[RBManager] Game folders found")

                        usrdirs = []
                        try:
                            for game_folder in game_folders:
                                usrdir_path = os.path.join(game_folder, "USRDIR")
                                if os.path.isdir(usrdir_path):
                                    usrdirs.append(usrdir_path)
                        except Exception as e:
                            self.logger.error(f"[RBManager] Error finding 'USRDIR': {e}")
                            return False

                        self.logger.info("[RBManager] Found game folders containing 'USRDIR'")

                        song_folders = []
                        try:
                            for usrdir in usrdirs:
                                for subfolder in os.listdir(usrdir):
                                    if subfolder == 'gen':
                                        continue
                                    subfolder_path = os.path.join(usrdir, subfolder)
                                    if os.path.isdir(subfolder_path):
                                        songs_path = os.path.join(subfolder_path, "songs")
                                        if os.path.isdir(songs_path):
                                            song_folders.append(songs_path)
                        except Exception as e:
                            self.logger.error(f"[RBManager] Error finding 'songs' folders: {e}")
                            return False

                        self.logger.info("[RBManager] Found game folders containing 'songs' folders")

                        try:
                            for song_folder in song_folders:
                                dtab_found = False
                                dta_found = False
                                for file in os.listdir(song_folder):
                                    if file.endswith(".dtab"):
                                        dtab_found = True
                                        break
                                    elif file.endswith(".dta"):
                                        dta_found = True
                                if dtab_found:
                                    self.dta_dirs[os.path.relpath(song_folder, self.emu_path)] = True
                                elif dta_found:
                                    self.dta_dirs[os.path.relpath(song_folder, self.emu_path)] = False
                        except Exception as e:
                            self.logger.error(f"[RBManager] Error finding .dtab/.dta file paths: {e}")
                            return False

                        self.logger.info("[RBManager] Found .dtab/.dta file paths")
                        return True

                    except Exception as e:
                        self.logger.warning(f"[RBManager] PS3 Emulator scan attempt {attempt + 1} failed with error: {e}")
                        if attempt < max_retries - 1:
                            self.logger.info(f"[RBManager] PS3 Emulator scan retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            self.logger.error("[RBManager] PS3 Emulator scan max retries reached. Could not complete the operation.")
                            return False
        except Exception as e:
            self.logger.debug(f"[RBManager] Error getting .dta directories: {e}")
    
    def download_dtas(self):
        try:
            dtas = {}
            if self.ps3_ip != None:
                try:
                    with ftplib.FTP(self.ps3_ip, encoding='latin-1') as ftp:
                        self.logger.info("[RBManager] Connected to PS3, logging in and downloading .dta/dtab...")
                        ftp.login()
                        for dir in self.dta_dirs:
                            ftp.cwd(dir)
                            dl_path = os.path.join(self.cwd, "FROM", dir)
                            if not os.path.exists(dl_path):
                                os.makedirs(dl_path)
                                self.logger.info("[RBManager] Downloading to "+ dl_path+"/songs.dtab")
                                dta_f = open(dl_path+"/songs.dtab", "wb")
                                ftp.retrbinary("RETR songs.dta", dta_f.write)
                                dta_f.close()
                            else:
                                self.logger.info("[RBManager] " + dl_path +"/songs.dtab" + " already exists locally, delete and rerun to update")
                            dtas[dl_path] = ""
                            ftp.cwd("/")
                        ftp.close()
                except Exception as e:
                    return False
            elif self.emu_path != None:
                try:
                    for dir in self.dta_dirs.keys():
                        full_path = os.path.join(self.cwd, "FROM", dir)
                        emu_dl_path = os.path.join(self.emu_path, dir)
                        if not os.path.exists(full_path):
                            print("Path not exists:",full_path)
                            os.makedirs(full_path)
                            self.logger.info("[RBManager] Copying from " + emu_dl_path+"/songs.dtab" + " to "+ full_path)
                            if(os.path.exists(emu_dl_path+"/songs.dtab")):
                                shutil.copy(emu_dl_path+"/songs.dtab",self.to_win_dir(full_path+"/songs.dtab"))
                            else:
                                shutil.copy(emu_dl_path+"/songs.dta",self.to_win_dir(full_path+"/songs.dtab"))
                        else:
                            print("Path exists")
                            self.logger.info("[RBManager] " + full_path + " already exists locally, delete and rerun to update")
                        dtas[full_path] = "" #tell song manager where the dtas are, let it read the file
                except Exception as e:
                    return False
            return (True, dtas)
        except Exception as e:
            self.logger.debug(f"[RBManager] Error downloading .dtas: {e}")

    def upload(self):
        try:
            if (self.ps3_ip != None):
                with ftplib.FTP(self.ps3_ip, encoding='latin-1') as ftp:
                    ftp.login()
                    for dir in self.dta_dirs:
                        path = os.path.join(self.cwd, "TO", dir)
                        self.logger.info("Uploading .dta/.dtab at: "+ path +", to:" + (str)(dir))
                        ftp.cwd(self.to_ps3_dir(dir))
                        ftp.storbinary("STOR songs.dta", open(path+"/songs.dta"), 'rb')
                        ftp.storbinary("STOR songs.dtab", open(path+"/songs.dtab"), 'rb')
                        ftp.cwd("/")
                    ftp.close()
            else:
                for dir in self.dta_dirs:
                    path = os.path.join(self.cwd, "TO", dir)
                    emu_up_path = os.path.join(self.emu_path, dir)
                    self.logger.info("Copying .dta/.dtab at: "+ path +", to:" + emu_up_path)
                    shutil.copy(path+"/songs.dta",emu_up_path+"/songs.dta")
                    shutil.copy(path+"/songs.dtab",emu_up_path+"/songs.dtab")
            return True
        except Exception as e:
            self.logger.debug(f"[RBManager] Error uploading .dtas: {e}")
            return False

    def find_dtas_for_reupload(self, dir=None):
        try:
            paths = []
            if dir == None:
                dir = self.cwd
            for root, dirs, files in os.walk(dir):
                for file in files:
                    if file.lower().endswith("dtab"):
                        if "TO" in dir:
                            continue
                        paths.append(os.path.join(dir, "songs.dtab"))
                        return paths
                for file in files:
                    if file.lower().endswith("dta"):
                        if "TO" in dir:
                            continue
                        paths.append(os.path.join(dir, "songs.dtab"))
                        return paths
                
                for each_dir in dirs:
                    paths.extend(self.find_dtas_for_reupload(os.path.join(dir, each_dir)))
                
                return paths
        except Exception as e:
            self.logger.debug(f"[RBManager] Error finding .dtas for reupload: {e}")

    def reuploaddtas(self):
        try:
            dtas = self.find_dtas_for_reupload()
            if (self.ps3_ip != ""):
                with ftplib.FTP(self.ps3_ip, encoding='latin-1') as ftp:
                    ftp.login()
                    ftp.cwd("/")
                    for dir in dtas:
                        if(dir.endswith(".dtab")):
                            self.logger.info("Uploading .dta at: "+ (str)(dir)+", back to:" + (str)(self.to_ps3_dir(dir.replace(self.cwd+"\\FROM",""))))
                            path = self.to_ps3_dir(dir.replace(self.cwd+"\\FROM",""))
                            path = path.replace("/songs.dtab", "")
                            ftp.cwd(path)
                            ftp.storbinary("STOR songs.dta", open(self.to_win_dir(dir), 'rb'))
                        else:
                            self.logger.info("Uploading .dta at: "+ (str)(dir)+", back to:" + (str)(self.to_ps3_dir(dir.replace(self.cwd+"\\FROM",""))))
                            path = self.to_ps3_dir(dir.replace(self.cwd+"\\FROM",""))
                            path = path.replace("/songs.dta", "")
                            ftp.cwd(path)
                            ftp.storbinary("STOR songs.dta", open(self.to_win_dir(dir), 'rb'))
                        ftp.cwd("/")
                    ftp.close()
            else:
                for dir in self.dta_dirs:
                    self.logger.info("Copying .dta/.dtab at: "+ (str)(self.cwd+"/FROM"+dir)+", to:" + (str)(dir))
                    path = os.path.join(self.cwd, "FROM", dir)
                    shutil.copy(path+"/songs.dtab", self.emu_path+"/"+dir+"/songs.dta")
                    shutil.copy(path+"/songs.dtab", self.emu_path+"/"+dir+"/songs.dtab")
        except Exception as e:
            self.logger.debug(f"[RBManager] Error reuploading dtas: {e}")

    def to_ps3_dir(self, dir: str):
        '''Helper function for converting Windows path schema to PS3 schema'''
        return dir.replace('\\','/')

    def to_win_dir(self, dir: str):
        '''Helper function for converting PS3 path schema to Windows schema'''
        return dir.replace('/', '\\')

    def get_ps3_connection(self):
        '''
        Attempts to get valid PS3 connection details from user
        '''
        try:
            pattern = r"\b((?:\d{1,3}\.){3}\d{1,3})"
            res = match(pattern, input("Please enter the IP and port (x.x.x.x:xxxxx)>: "))
            if not res:
                raise Exception()
            ip, port = res.groups()
            octets = list(map(int, ip.split('.')))
            if any(o <0 or o > 255 for o in octets):
                raise Exception()

            with ftplib.FTP(ip, encoding='latin-1') as ftp:
                self.logger.info("[RBManager] PS3 Connection Validated")
                self.ps3_ip = ip
            if self.ps3_ip is None:
                raise Exception()
            return True
        except Exception as e:
            self.logger.debug(f"[RBManager] Error getting PS3 connection: {e}")
            return False

    def get_emulator_path(self):
        '''
        Attempts to get valid PS3 emulator path
        '''
        try:
            path = input("Please enter the root path to the emulator (i.e. the folder with 'dev_hdd0' in it)\n>: ")
            # Check if the provided path exists and is a directory
            if os.path.isdir(path):
                # List all entries in the directory
                entries = os.listdir(path)
                # Check if 'dev_hdd0' is one of the entries
                if 'dev_hdd0' in entries:
                    self.emu_path = path
                    return True
            return False
        except Exception as e:
            self.logger.debug(f"[RBManager] Error getting emulator path: {e}")