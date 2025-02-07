import logging
import webbrowser
import os
import ftplib
import shutil
import threading

logger = logging.getLogger(__name__)

class Song:
    '''
    Store the name and artist of a song, it's location on the PS3, and the content
    '''
    def __init__(self):
        self.name = "" #name of song
        self.artist = "" #artist of song
        self.content = "" #all the text for the song
        self.excluded = False #should the song be excluded
        self.reason = "" #why

    def __eq__(self, other:'Song')->bool:
        return (self.name == other.name) and (self.artist == other.artist) and (self.content == other.content)
    def __hash__(self)->int:
        return hash(self.name, self.artist, self.content)
    def __str__(self)->str:
        return ("| " + self.name + " by " + self.artist + (("| Excluded because: " + self.reason) if self.excluded else ""))
    
class SongManager:
    '''
    Manage processing of song data locally
    '''
    def __init__(self):
        self.songs = {} #all the songs that program can recognize, path is key, all songs in that file is value
        self.kept = [] #which songs to keep
        self.excluded = [] #which songs to exclude
        self.cwd = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir)) #keep track of the CWD
        self.dtas = {} #where .dta contents will be held before and after modification until file write, path is key, entire file content is value
        self.rb_manager = None #reference to RManager which manages all the remote operations
        #from config
        self.whitelist_names = []
        self.whitelist_artist = []
        self.missing_artists = []
        self.ip = None #ip of PS3
        self.emupath = None #path to emulator root
        self.elimination = False #should manual elimination be enabled
        self.restore = False #restore original files (in case of catastrophic failure)


    def to_ps3_dir(self, dir: str):
        '''Helper function for converting Windows path schema to PS3 schema'''
        return dir.replace('\\','/')

    def to_win_dir(self, dir: str):
        '''Helper function for converting PS3 path schema to Windows schema'''
        return dir.replace('/', '\\')

    def read_config(self):
        '''
        Reads dta.config file for IP and other optional information
        '''
        with open(self.to_win_dir(self.cwd+"/dta.config")) as config:
            file_lines = config.readlines()

        for i,line in enumerate(file_lines):
            if line.startswith("ip="):
                self.ip = line[3:].replace("\"", "").replace("\n", "")
                if self.ip == "":
                    print("No IP to FTP of PS3 was provided...assuming switch to local emulator mode (quit now if this is not the case)...")
                    self.emupath = input("Please enter the full path to root of local emulated PS3 filesystem: ")
            elif line.startswith("rb_dirs="): 
                self.rb_manager.rb_dirs = line[9:].replace("\"", "").replace("\n", "").split(",")
            elif line.startswith("name_whitelist="):
                self.whitelist_names = line[15:].replace("\"", "").replace("\n", "").split(",")
            elif line.startswith("artist_whitelist="):
                self.whitelist_artist = line[17:].replace("\"", "").replace("\n", "").split(",")
            elif line.startswith("missing_artists="):
                self.missing_artists = line[16:].replace("\"", "").replace("\n", "").split(",")
            elif line.startswith("elimination="):
                self.elimination = eval(line[12:].replace("\"", "").replace("\n", ""))
            elif line.startswith("restore="):
                self.restore = eval(line[8:].replace("\"", "").replace("\n", ""))
            elif line.startswith("export_excluded="):
                self.export_excluded = eval(line[16:].replace("\"", "").replace("\n", ""))
            else:
                logger.warning("Unknown config field found: line " + (str)(i))
        if self.rb_manager.rb_dirs is None:
            logger.error("No Rockband paths found in config...")
            exit("!CHECK LOG!")

    def read_dtas(self):
        '''Open each .dta that was downloaded and process it'''
        for dir in self.dtas.keys():
            lines = []
            with open(self.to_win_dir(dir+"/songs.dtab"), "r") as file:
                lines = file.readlines()
            file.close()
            logger.debug("File at "+ (str)(self.to_win_dir(dir))+ " read.")
            self.dtas[dir] = "".join(lines)
            self.songs[dir] = self.process_dta(self.dtas[dir])

    def process_dta(self, file_str):
        '''Read the file, parse its content and return list of songs in file. Flawed since some .dta formats cannot be parsed.'''
        song_list = []
        paran_counter = 0
        in_single_quotes = False
        in_double_quotes = False
        name_found = False
        artist_found = False
        name_stored = False
        artist_stored = False
        wait_for_open = True
        buffer = ""
        content_buffer = ""
        copy_content = False
        song = None

        for i,char in enumerate(file_str):
            if (copy_content):
                content_buffer += char

            if(wait_for_open):
                if char == '(':
                    wait_for_open = False
                    song = Song()
                    content_buffer = char
                    copy_content = True
                    name_stored = False
                    artist_stored = False
                    paran_counter += 1
            else:
                if paran_counter == 0:
                    if song is not None:
                        content_buffer += char
                        copy_content = False
                        song.content = content_buffer
                        content_buffer = ""
                        song_list.append(song)
                        song = None
                        wait_for_open = True
                
                if i == len(file_str)-1:
                    if song is not None:
                        content_buffer += char
                        copy_content = False
                        song.content = content_buffer
                        content_buffer = ""
                        song_list.append(song)

                if char == '(':
                    paran_counter += 1
                elif char == ')':
                    paran_counter -= 1
                elif char == '\'':
                    if not in_double_quotes:
                        in_single_quotes = not in_single_quotes
                    if in_single_quotes:
                        buffer = ""
                elif char == '\"':
                    if not in_single_quotes:
                        in_double_quotes = not in_double_quotes
                    if in_double_quotes:
                        buffer = ""

                if (name_stored and artist_stored) and paran_counter > 0:
                    continue

                if (not in_single_quotes and not in_double_quotes) and (char == '\'' or char == '\"'):
                    if buffer == "name"  and not name_stored:
                        name_found = True
                        buffer = ""
                    elif buffer == "artist" and not artist_stored:
                        artist_found = True
                        buffer = ""
                    else:
                        if name_found:
                            song.name = buffer
                            name_found = False
                            name_stored = True
                            buffer = ""
                        elif artist_found:
                            song.artist = buffer
                            artist_found = False
                            artist_stored = True
                            buffer = ""
                else:
                    if (in_single_quotes and char != '\'') or (in_double_quotes and char != '\"'):
                        buffer += char
        return song_list

    def exclude_from_whitelists(self):
        '''Check each song against whitelists, exclude if not on whitelist'''
        for song in [song for songs in self.songs.values() for song in songs]:
            if (song.artist in self.whitelist_artist) or (song.name in self.whitelist_names):
                if(song.artist in self.whitelist_artist):
                    logger.debug("Whitelisted: " + (str)(f"{song.name} by {song.artist} for artist name"))
                else:
                    logger.debug("Whitelisted: " + (str)(f"{song.name} by {song.artist} for song name"))
                self.kept.append(song)
            else:
                song.reason = "Whitelist Exclusion"
                self.excluded.append(song)

        logger.info((str)(len(self.excluded))+ " songs excluded")

    def manual_elimination(self):
        '''Allow the user to eliminate songs manually. Has 2 stage confirmation.'''
        logger.info((str)(len(self.excluded))+ " songs left for elimination...")
        print(((str)(len(self.excluded))+ " songs left for elimination..."))
        if(not self.elimination):
            return
        for i, song in enumerate(self.excluded):
            while True:
                print(f"{i+1}. {song.name} by {song.artist}")
                user_input = input("q to quit\nz to search youtube\nx to delete\nc to keep\n> ").lower()
                if user_input == 'q':
                    exit()
                elif user_input == 'z':
                    webbrowser.open(f"https://www.youtube.com/results?search_query={song.artist.replace("&","and")}+-+{song.name.replace("&", "and")}+song") #opens the user's browser and searches for the song
                elif user_input == 'x':
                    confirmed = False
                    while True:
                        confirm = input("Please confirm elimination (y/n): ").lower()
                        if confirm.lower() == 'y':
                            confirmed = True
                            break
                        elif confirm.lower() == 'n':
                            break
                    if not confirmed:
                        song.reason = ""
                        self.excluded.remove(song)
                        self.kept.append(song)
                    break
                elif user_input == 'c':
                    song.reason = ""
                    self.excluded.remove(song)
                    self.kept.append(song)
                    break
        
        while True: #confirm elimination
            logger.info((str)(len(self.excluded))+ " songs to confirm elimination...")
            print((str)(len(self.excluded))+ " songs to confirm elimination...")
            for i, song in enumerate(self.excluded): #double check in case a song was accidentally marked for deletion
                print(f"{i}. {song.name} - {song.artist}")
            print("The following songs will be deleted.")
            user_input = input("Press c to continue, a number if you wish to re-include a song, or q to quit.\n>")
            if user_input == 'q':
                exit()
            elif user_input == 'c':
                break
            elif user_input.isdigit() and 0 <= int(user_input) < len(self.excluded):
                song = self.excluded[int(user_input)]
                print(f"{song.name} by {song.artist}")
                user_input = input("q to quit\nz to search youtube\nx to delete\nc to keep\n> ")
                if user_input == 'q':
                    exit()
                elif user_input == 'z':
                    webbrowser.open(f"https://www.youtube.com/results?search_query={song.artist}+-+{song.name}+song+rock+band")
                elif user_input == 'x':
                    break
                elif user_input == 'c':
                    song.reason = ""
                    self.excluded.remove(song)
                    self.kept.append(song)
                    break
        logger.info((str)(len(self.excluded)) + " eliminations confirmed.")

    def finalize(self):
        '''Finalize changes and create the files'''
        threads = {}
        for dir in self.songs.keys():
            threads[dir] = threading.Thread(target=self.create_modified_dta, args=(dir,))
        for dir in self.songs.keys():
            threads[dir].start()
        for dir in self.songs.keys():
            threads[dir].join()
            self.write_modified_dta(dir)

    def create_modified_dta(self,dir):
        logger.debug("Finalizing "+ (str)(len(self.songs[dir])) + " songs at:" + dir)
        modified = ""
        for song in self.songs[dir]:
            if song not in self.excluded: #if the song is to be excluded
                logger.debug("Adding " + song.name + " by " +  song.artist)
                modified += song.content
        self.dtas[dir] = modified

    def write_modified_dta(self, dir):
        if not os.path.exists(self.to_win_dir(dir.replace("FROM", "TO"))): #if the path for the song in the TO directory doesn't exist
            os.makedirs(self.to_win_dir(dir.replace("FROM", "TO")), exist_ok=True) #make the directories recursively
        
        logger.debug("Finalizing "+(str)(dir.replace("FROM", "TO")+"\\songs.dtab")+ " ...")
        shutil.copy(dir+"/songs.dtab", dir.replace("FROM", "TO")+"/songs.dtab")
        
        logger.debug("Finalizing "+(str)(dir.replace("FROM", "TO")+"\\songs.dta")+ " ...")
        with open(self.to_win_dir(dir.replace("FROM", "TO")+"/songs.dta"), "w") as dta: #make the dta
            dta.write(self.dtas[dir])
        logger.debug("Done writing "+(str)(dir.replace("FROM", "TO")+"\\songs.dta")+ " ...")

    def excluded_to_csv(self):
        csv_content = "!$Artist$!,!$Song Name$!\n"
        for song in self.excluded:
            csv_content += "\""+song.artist+"\"" + "," + "\""+song.name+"\"" + "\n"
        with open(self.to_win_dir(self.cwd+"/excluded.csv"), "w") as csv_file:
            csv_file.write(csv_content)

class RManager:
    '''
    Manage processing of remote data
    '''
    def __init__(self, songManager:SongManager):
        self.rb_dirs = [] #parent RockBand dirs
        self.dta_dirs = {} #dirs containing .dta/.dtabs on PS3, path is key, value is true if dtab is found, false otherwise
        self.song_manager = songManager
        self.song_manager.rb_manager = self
        self.make_buffers()

    def make_buffers(self):
        logger.info("Checking for FTP buffer directories...")
        print("Checking for FTP buffer directories...")
        if not os.path.exists(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM")):
            logger.info("Making FROM directory.")
            os.mkdir(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM")) #create the dir that will hold ftp downloads
        if not os.path.exists(self.song_manager.to_win_dir(self.song_manager.cwd+"/TO")):
            logger.info("Making TO directory.")
            os.mkdir(self.song_manager.to_win_dir(self.song_manager.cwd+"/TO")) #create the dir that will hold ftp uploads

    def get_dta_dirs(self):
        if(self.song_manager.ip != ""):
            with ftplib.FTP(self.song_manager.ip, encoding='latin-1') as ftp:
                logger.info("Connected to PS3, logging in and searching...")
                ftp.login()
                for dir in self.rb_dirs:
                    dir = self.song_manager.to_ps3_dir(dir)
                    ftp.cwd(dir)
                    for name,type in ftp.mlsd():
                        if type['type'] == 'dir':
                            ftp.cwd(name)
                            for name_1,type_1 in ftp.mlsd():
                                if (type_1['type'] == 'dir' and name_1 == "songs"):
                                    dtab_found = False
                                    dta_found = False
                                    ftp.cwd("songs")
                                    for name_2,type_2 in ftp.mlsd():
                                        if type_2['type'] == 'file' and name_2.endswith(".dtab"):
                                            dtab_found = True
                                            path = ftp.pwd()
                                            logger.debug("Found a .dtab at: "+ (str)(path))
                                            self.dta_dirs[path] = True
                                        elif type_2['type'] == 'file' and name_2.endswith(".dta"):
                                            dta_found = True
                                            path = ftp.pwd()
                                            logger.debug("Found a .dta at: " + (str)(path))
                                    if not dtab_found and dta_found:
                                        path = ftp.pwd()
                                        logger.debug("No .dtab found at: " + (str)(path) +", using .dta.")
                                        self.dta_dirs[path] = False
                        ftp.cwd(dir)
                ftp.close()
                logger.info("Closed FTP connection with PS3. Returning directories.")
        else:
            os.chdir(self.song_manager.emupath)
            for dir in self.rb_dirs:
                ret = os.getcwd()
                os.chdir(ret+self.song_manager.to_win_dir(dir))
                pwd = dir
                for sub_dir in [f for f in os.scandir(os.getcwd()) if f.is_dir()]:
                    os.chdir(sub_dir.path)
                    pwd = dir+"/"+sub_dir.name
                    for sub_sub_dir in [ff for ff in os.scandir(os.getcwd()) if ff.is_dir() and ff.name == "songs"]:
                        dtab_found = False
                        dta_found = False
                        os.chdir(sub_sub_dir.path)
                        pwd = dir+"/"+sub_dir.name+"/"+"songs"
                        for sub_sub_sub_dir in [fff for fff in os.scandir(os.getcwd()) if fff.is_file() and (fff.name.endswith(".dta") or fff.name.endswith(".dtab"))]:
                            if sub_sub_sub_dir.name.endswith(".dtab"):
                                dta_found - True
                                path = pwd
                                logger.debug("Found a .dtab at: "+ (str)(path))
                                self.dta_dirs[path] = True
                            elif sub_sub_sub_dir.name.endswith(".dta"):
                                dta_found = True
                                path = pwd
                                logger.debug("Found a .dta at: " + (str)(path))
                        if not dtab_found and dta_found:
                            path = pwd
                            logger.debug("No .dtab found at: " + (str)(path) + ", using .dta.")
                            self.dta_dirs[path] = False
                os.chdir(ret)
            logger.info("Returning directories.")
    
    def download_dtas(self):
        if(self.song_manager.ip != ""):
            with ftplib.FTP(self.song_manager.ip, encoding='latin-1') as ftp:
                logger.info("Connected to PS3, logging in and downloading .dta/dtab...")
                ftp.login()
                for dir in self.dta_dirs:
                    ftp.cwd(dir)
                    if not os.path.exists(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir)):
                        os.makedirs(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir))
                        logger.debug("Downloading to "+ (str)(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab")))
                        dta_f = open(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab"), "wb")
                        ftp.retrbinary("RETR songs.dta", dta_f.write)
                        dta_f.close()
                    self.song_manager.dtas[self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir)] = "" #tell song manager where the dtas are
                    ftp.cwd("/")
                ftp.close()
        else:
            for dir in self.dta_dirs:
                if not os.path.exists(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir)):
                    os.makedirs(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir))
                    logger.debug("Copying to "+ (str)(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab")))
                    if(os.path.exists(self.song_manager.emupath+"/"+dir+"/songs.dtab")):
                        shutil.copy(self.song_manager.emupath+"/"+dir+"/songs.dtab",self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab"))
                    else:
                        shutil.copy(self.song_manager.emupath+"/"+dir+"/songs.dta",self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab"))
                self.song_manager.dtas[self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir)] = "" #tell song manager where the dtas are, let it read the file

    def upload(self):
        if (self.song_manager.ip != ""):
            with ftplib.FTP(self.song_manager.ip, encoding='latin-1') as ftp:
                ftp.login()
                for dir in self.dta_dirs:
                    logger.debug("Uploading .dta/.dtab at: "+ (str)(self.song_manager.cwd+"/TO"+dir)+", to:" + (str)(dir))
                    ftp.cwd(self.song_manager.to_ps3_dir(dir))
                    ftp.storbinary("STOR songs.dta", open(self.song_manager.to_win_dir(self.song_manager.cwd+"/TO"+dir+"/songs.dta"), 'rb'))
                    ftp.storbinary("STOR songs.dtab", open(self.song_manager.to_win_dir(self.song_manager.cwd+"/TO"+dir+"/songs.dtab"), 'rb'))
                    ftp.cwd("/")
                ftp.close()
        else:
            for dir in self.dta_dirs:
                logger.debug("Copying .dta/.dtab at: "+ (str)(self.song_manager.cwd+"/TO"+dir)+", to:" + (str)(dir))
                shutil.copy(self.song_manager.to_win_dir(self.song_manager.cwd+"/TO"+dir+"/songs.dta"),self.song_manager.emupath+"/"+dir+"/songs.dta")
                shutil.copy(self.song_manager.to_win_dir(self.song_manager.cwd+"/TO"+dir+"/songs.dtab"),self.song_manager.emupath+"/"+dir+"/songs.dtab")

    def find_dtas_for_reupload(self, dir=None):
        paths = []
        if dir == None:
            dir = self.song_manager.cwd
        for root, dirs, files in os.walk(dir):
            for file in files:
                if file.lower().endswith("dtab"):
                    paths.append(self.song_manager.to_win_dir(dir+"/songs.dtab"))
                    return paths
            for file in files:
                if file.lower().endswith("dta"):
                    paths.append(self.song_manager.to_win_dir(dir+"/songs.dta"))
                    return paths
            
            for each_dir in dirs:
                paths.extend(self.find_dtas_for_reupload(dir+"/"+each_dir))
            
            return paths

    def reuploaddtas(self):
        dtas = self.find_dtas_for_reupload()
        if (self.song_manager.ip != ""):
            with ftplib.FTP(self.song_manager.ip, encoding='latin-1') as ftp:
                ftp.login()
                ftp.cwd("/")
                for dir in dtas:
                    if(dir.endswith(".dtab")):
                        logger.debug("Uploading .dta at: "+ (str)(dir)+", back to:" + (str)(self.song_manager.to_ps3_dir(dir.replace(self.song_manager.cwd+"\\FROM",""))))
                        path = self.song_manager.to_ps3_dir(dir.replace(self.song_manager.cwd+"\\FROM",""))
                        path = path.replace("/songs.dtab", "")
                        ftp.cwd(path)
                        ftp.storbinary("STOR songs.dta", open(self.song_manager.to_win_dir(dir), 'rb'))
                    else:
                        logger.debug("Uploading .dta at: "+ (str)(dir)+", back to:" + (str)(self.song_manager.to_ps3_dir(dir.replace(self.song_manager.cwd+"\\FROM",""))))
                        path = self.song_manager.to_ps3_dir(dir.replace(self.song_manager.cwd+"\\FROM",""))
                        path = path.replace("/songs.dta", "")
                        ftp.cwd(path)
                        ftp.storbinary("STOR songs.dta", open(self.song_manager.to_win_dir(dir), 'rb'))
                    ftp.cwd("/")
                ftp.close()
        else:
            for dir in self.dta_dirs:
                logger.debug("Copying .dta/.dtab at: "+ (str)(self.song_manager.cwd+"/FROM"+dir)+", to:" + (str)(dir))
                shutil.copy(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab"),self.song_manager.emupath+"/"+dir+"/songs.dta")
                shutil.copy(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab"),self.song_manager.emupath+"/"+dir+"/songs.dtab")

def main():
    #logging.basicConfig(filename='dta.log', encoding="utf-8", level=logging.INFO,format='%(asctime)s - %(message)s')
    #normal()
    logging.basicConfig(filename='dta.log', encoding="utf-8", level=logging.DEBUG,format='%(asctime)s - %(message)s')
    debug()

def normal():
    #USE to_win_dir WHEN CHECKING LOCAL DIRS, USE to_ps3_dir WHEN CHECKING REMOTE DIRS
    #CONFIG
    song_manager = SongManager()
    rb_manager = RManager(song_manager)

    logger.info("Reading config...")
    print("Reading config...")
    song_manager.read_config()
    logger.info("IP: "+song_manager.ip)
    logger.info("RB Dirs: "+(str)(rb_manager.rb_dirs))
    logger.info("Names Whitelist: "+(str)(song_manager.whitelist_names))
    logger.info("Artists Whitelist: "+(str)(song_manager.whitelist_artist))
    logger.info("Successfully read config.")
    print("Successfully read config.")

    #DTA/DTAB DOWNLOAD
    logger.info("Getting directories of .dta/.dtab from PS3...")
    print("Getting directories of .dta/.dtab from PS3...")
    rb_manager.get_dta_dirs()
    logger.info("Successfully got directories.")
    print("Successfully got directories.")
    logger.info("Downloading .dta/.dtab from PS3 and storing their location locally...")
    print("Downloading .dta/.dtab from PS3 and storing their location locally...")
    rb_manager.download_dtas()
    logger.info("Successfully downloaded .dta/.dtab.")
    print("Successfully downloaded .dta/.dtab.")

    #RESTORE
    if(song_manager.restore):
        rb_manager.reuploaddtas()
        exit()

    #READ DTA/DTAB
    logger.info("Starting .dta/.dtab reading...")
    print("Starting .dta/.dtab reading...")
    song_manager.read_dtas()
    logger.info("Successfully read .dta/.dtab.")
    print("Successfully read .dta/.dtab.")

    #EXCLUSION
    logger.info(f"{len([song for songs in song_manager.songs for song in songs])} songs found!")
    print(f"{len([song for songs in song_manager.songs for song in songs])} songs found!")
    logger.info("Excluding songs not in whitelists...")
    print("Excluding songs not in whitelists...")
    song_manager.exclude_from_whitelists()
    logger.info("Successfully excluded songs not in whitelists.")
    print("Successfully excluded songs not in whitelists.")

    #MANUAL ELIMINATION
    logger.info("Starting manual elimination...")
    print("Starting manual elimination...")
    song_manager.manual_elimination()
    logger.info("Successfully finished manual elimination.")
    print("Successfully finished manual elimination.")

    #FINALIZING
    logger.info("Storing updated .dta/.dtab...")
    print("Storing updated .dta/.dtab...")
    song_manager.finalize()
    logger.info("Successfully made new .dta/.dtab.")
    print("Successfully made new .dta/.dtab.")

    #UPLOAD
    logger.info("Uploading new files to PS3...")
    print("Uploading new files to PS3...")
    rb_manager.upload()
    logger.info("Successfully uploaded new files to PS3.")
    print("Successfully uploaded new files to PS3.")

def debug():
    #USE to_win_dir WHEN CHECKING LOCAL DIRS, USE to_ps3_dir WHEN CHECKING REMOTE DIRS
    #CONFIG
    song_manager = SongManager()
    rb_manager = RManager(song_manager)

    logger.info("Reading config...")
    print("Reading config...")
    song_manager.read_config()
    logger.info("IP: "+song_manager.ip)
    logger.info("RB Dirs: "+(str)(rb_manager.rb_dirs))
    logger.info("Names Whitelist: "+(str)(song_manager.whitelist_names))
    logger.info("Artists Whitelist: "+(str)(song_manager.whitelist_artist))
    logger.info("Successfully read config.")
    print("Successfully read config.")

    #DTA/DTAB DOWNLOAD
    logger.info("Getting directories of .dta/.dtab from PS3...")
    print("Getting directories of .dta/.dtab from PS3...")
    rb_manager.get_dta_dirs()
    logger.info("Successfully got directories.")
    print("Successfully got directories.")
    logger.info("Downloading .dta/.dtab from PS3 and storing their location locally...")
    print("Downloading .dta/.dtab from PS3 and storing their location locally...")
    rb_manager.download_dtas()
    logger.info("Successfully downloaded .dta/.dtab.")
    print("Successfully downloaded .dta/.dtab.")

    #RESTORE
    if(song_manager.restore):
        rb_manager.reuploaddtas()
        exit()

    #READ DTA/DTAB
    logger.info("Starting .dta/.dtab reading...")
    print("Starting .dta/.dtab reading...")
    song_manager.read_dtas()
    logger.info("Successfully read .dta/.dtab.")
    print("Successfully read .dta/.dtab.")

    #EXCLUSION
    logger.info(f"{len([song for songs in song_manager.songs for song in songs])} songs found!")
    print(f"{len([song for songs in song_manager.songs for song in songs])} songs found!")
    logger.info("Excluding songs not in whitelists...")
    print("Excluding songs not in whitelists...")
    song_manager.exclude_from_whitelists()
    logger.info("Successfully excluded songs not in whitelists.")
    print("Successfully excluded songs not in whitelists.")

    if(song_manager.export_excluded):
        song_manager.excluded_to_csv()
        exit()

    #FINALIZE
    logger.info("Storing updated .dta/.dtab...")
    print("Storing updated .dta/.dtab...")
    song_manager.finalize()
    logger.info("Successfully made new .dta/.dtab.")
    print("Successfully made new .dta/.dtab.")

main()