import webbrowser
import os
import ftplib
import logging #for debbuging

logging.basicConfig(filename='dta.log', encoding="utf-8", level=logging.DEBUG ,format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

#logger.info, logger.debug, logger.warning, logger.error

class RBSong:
    '''
    Store the name and artist of a song, it's location on the PS3, and what lines its in between
    '''
    def __init__(self):
        self.name = ""
        self.artist = ""
        self.dir = ""
        self.between = [0,0]
        self.reason = ""
    def __eq__(self, other):
        return (self.name == other.name) and (self.artist == other.artist) and (self.dir == other.dir)
    def __hash__(self):
        return hash(self.name, self.artist, self.dir)
    def __str__(self):
        return ("| " + self.name + " by " + self.artist + " @ " + self.dir + " | between: " + (str)(self.between[0]) + "-" + (str)(self.between[1]) + " | Reason: " + self.reason + " |")
class SongManager:
    '''
    Manage processing of song data locally
    '''
    def __init__(self):
        self.songs = []
        self.cwd = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir))
        self.rb_manager = None
        #config
        self.whitelist_names = []
        self.whitelist_artist = []
        self.missing_artists = []
        self.ip = None
        self.elimination = False
        #local
        self.dta_dirs = [] #where are .dtas/.dtabs stored locally
        #additional
        self.kept = []
        self.excluded = []


    def to_ps3_dir(self, dir: str):
        return dir.replace('\\','/')

    def to_win_dir(self, dir: str):
        return dir.replace('/', '\\')

    def read_config(self):
        '''
        Reads dta.config file for IP and other optional information
        '''

        with open(self.to_win_dir(self.cwd+"/dta.config")) as config:
            file_lines = config.readlines()
        config.close()

        for i,line in enumerate(file_lines):
            if line.startswith("ip="):
                self.ip = line[3:].replace("\"", "").replace("\n", "")
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
            else:
                logger.warning("Unknown config field found: line " + (str)(i))
        if self.rb_manager.rb_dirs is None:
            logger.error("No Rockband paths found in config...")
            self.rb_dirs = ["/dev_hdd0/game/BLUS30050/USRDIR","/dev_hdd0/game/BLUS30463/USRDIR"] #default locations
        if self.ip is None:
            logger.error("No IP found in config...")
            exit("!CHECK LOG!")

    def read_dtas(self):
        for dir in self.dta_dirs:
            lines = []
            with open(self.to_win_dir(dir+"/songs.dtab"), "r") as file:
                lines = file.readlines()
            file.close()
            logger.info("File at "+ (str)(self.to_win_dir(dir))+ " read.")
            file_str = ""
            for line in lines:
                file_str += line
            self.songs.extend(self.process_dta(file_str, dir))

    def process_dta(self, file_str, parent_dir):
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
        song = None

        for i,char in enumerate(file_str):
            if(wait_for_open):
                if char == '(':
                    wait_for_open = False
                    song = RBSong()
                    song.between[0] = i
                    song.dir = (self.to_win_dir(parent_dir))
                    name_stored = False
                    artist_stored = False
                    paran_counter += 1
            else:
                if paran_counter == 0:
                    if song is not None:
                        song.between[1] = i
                        song.reason = "!!!"
                        song_list.append(song)
                        song = None
                        wait_for_open = True
                
                if i == len(file_str)-1:
                    if song is not None:
                        song.between[1] = i
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
                    if buffer == "name":
                        name_found = True
                        buffer = ""
                    elif buffer == "artist":
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
        for song in self.songs:
            if (song.artist in self.whitelist_artist) or (song.name in self.whitelist_names):
                if(song.artist in self.whitelist_artist):
                    logger.debug("Whitelisted: " + (str)(f"{song.name} by {song.artist} for artist name"))
                    song.reason = "Artist Whitelist"
                else:
                    logger.debug("Whitelisted: " + (str)(f"{song.name} by {song.artist} for song name"))
                    song.reason = "Name Whitelist"
                self.kept.append(song)
            else:
                song.reason = "Whitelist Exclusion"
                self.excluded.append(song)

        logger.info((str)(len(self.excluded))+ " songs excluded")

    def manual_elimination(self):
        logger.info((str)(len(self.excluded))+ " songs left for elimination...")
        print(((str)(len(self.excluded))+ " songs left for elimination..."))
        if(not self.elimination):
            return
        for i, song in enumerate(self.excluded):
            while True:
                print(f"{i+1}. {song.name} by {song.artist}")
                user_input = input("q to quit\nz to search youtube\nx to delete\nc to keep\n> ")
                if user_input == 'q':
                    exit()
                elif user_input == 'z':
                    webbrowser.open(f"https://www.youtube.com/results?search_query={song.artist.replace("&","and")}+-+{song.name.replace("&", "and")}+song")
                elif user_input == 'x':
                    break
                elif user_input == 'c':
                    song.reason = "Kept at manual elimination"
                    self.excluded.remove(song)
                    self.kept.append(song)
                    break

        while True:
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
                    song.reason = "Kept at manual elimination"
                    self.excluded.remove(song)
                    self.kept.append(song)
                    break
        logger.info((str)(len(self.excluded)) + " eliminations confirmed.")

    def finalize(self):
        dirs = []
        songs_in_dir = []
        for song in self.excluded:
            if song in self.kept:
                continue #just in case
            if song.dir not in dirs: #if the current song's directory hasn't been accounted for
                dirs.append(song.dir) #add it
                songs_in_dir.append([song]) #and add the accompanying song
            else:
                songs_in_dir[dirs.index(song.dir)].extend([song]) #otherwise, add the song to the existing list

        for i,dir in enumerate(dirs):
            logger.info("Finalizing "+ (str)(len(songs_in_dir[i])) + " .songs at:" + dir)
            lines = []
            chars_to_exclude = [] #for .dta file, keep track of what chars to exclude
            for song in songs_in_dir[i]:
                if song in self.excluded: #if the song is to be excluded
                    logger.info("Removing " + song.name + " by " +  song.artist + " at " + song.dir)
                    chars_to_exclude.extend([x for x in range(song.between[0], song.between[1]+1)]) #exclude it's chars from the file
            with open(self.to_win_dir(dir+"/songs.dtab"), "r") as song_file: #now open dta in the FROM directory
                lines = song_file.readlines() #read it
                song_file.close()
            if not os.path.exists(self.to_win_dir(dir.replace("FROM", "TO"))): #if the path for the song in the TO directory doesn't exist
                os.makedirs(self.to_win_dir(dir.replace("FROM", "TO")), exist_ok=True) #make the directories recursively
            logger.info("Finalizing "+(str)(dir.replace("FROM", "TO")+"\\songs.dtab")+ " ...")
            with open(self.to_win_dir(dir.replace("FROM", "TO")+"/songs.dtab"), "w")as dtab: #make the dta backup by just writing the entire file
                for line in lines:
                    dtab.write(line)
                dtab.close()
            with open(self.to_win_dir(dir.replace("FROM", "TO")+"/songs.dta"), "w") as dta: #make the dta
                file_str_full = ""
                file_str_modi = ""
                for line in lines:
                    file_str_full += line
                for i,char in enumerate(file_str_full):
                    if i not in chars_to_exclude:
                        file_str_modi += char
                    dta.write(file_str_modi)
            song_file.close()

    def show_between(self, song:RBSong):
        between_str = ""
        with open(self.to_win_dir(song.dir+"/songs.dtab"), "r") as song_file: #now open dta in the FROM directory
            lines = song_file.readlines() #read it
            linestr = ""
            for line in lines:
                linestr += line
            for i,char in enumerate(linestr):
                if ((i >= song.between[0]) and (i <= song.between[1])):
                    between_str += char
            song_file.close()
        return between_str

class RBManager:
    '''
    Manage processing of data from PS3
    '''
    def __init__(self, songManager:SongManager):
        self.rb_dirs = [] #parent RockBand dirs
        self.dta_dirs = {} #dirs containing .dta/.dtabs on PS3
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
                                        logger.info("Found a .dtab at: "+ (str)(path))
                                        self.dta_dirs[path] = True
                                    elif type_2['type'] == 'file' and name_2.endswith(".dta"):
                                        dta_found = True
                                        path = ftp.pwd()
                                        logger.info("Found a .dta at: " + (str)(path))
                                if not dtab_found and dta_found:
                                    path = ftp.pwd()
                                    logger.info("No .dtab found at: " + (str)(path) +", using .dta.")
                                    self.dta_dirs[path] = False
                    ftp.cwd(dir)
            ftp.close()
            logger.info("Closed FTP connection with PS3. Returning directories.")
    
    def download_dtas(self):
        with ftplib.FTP(self.song_manager.ip, encoding='latin-1') as ftp:
            logger.info("Connected to PS3, logging in and downloading .dta/dtab...")
            ftp.login()
            for dir in self.dta_dirs:
                ftp.cwd(dir)
                if not os.path.exists(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab")):
                    os.makedirs(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir))
                    logger.info("Downloading to "+ (str)(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab")))
                    dta_f = open(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir+"/songs.dtab"), "wb")
                    ftp.retrbinary("RETR songs.dta", dta_f.write)
                    dta_f.close()
                self.song_manager.dta_dirs.append(self.song_manager.to_win_dir(self.song_manager.cwd+"/FROM"+dir)) #tell song manager where the dtas are
                ftp.cwd("/")
            ftp.close()

    def upload(self):
        with ftplib.FTP(self.song_manager.ip, encoding='latin-1') as ftp:
            ftp.login()
            for dir in self.dta_dirs:
                logger.info("Uploading .dta/.dtab at: "+ (str)(self.song_manager.cwd+"/TO"+dir)+", to:" + (str)(dir))
                ftp.cwd(self.song_manager.to_ps3_dir(dir))
                ftp.storbinary("STOR songs.dta", open(self.song_manager.to_win_dir(self.song_manager.cwd+"/TO"+dir+"/songs.dta"), 'rb'))
                ftp.storbinary("STOR songs.dtab", open(self.song_manager.to_win_dir(self.song_manager.cwd+"/TO"+dir+"/songs.dtab"), 'rb'))
                ftp.cwd("/")
            ftp.close()

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
        
        with ftplib.FTP(self.song_manager.ip, encoding='latin-1') as ftp:
            ftp.login()
            ftp.cwd("/")
            for dir in dtas:
                if(dir.endswith(".dtab")):
                    logger.info("Uploading .dta at: "+ (str)(dir)+", back to:" + (str)(self.song_manager.to_ps3_dir(dir.replace(self.song_manager.cwd+"\\FROM",""))))
                    path = self.song_manager.to_ps3_dir(dir.replace(self.song_manager.cwd+"\\FROM",""))
                    path = path.replace("/songs.dtab", "")
                    ftp.cwd(path)
                    ftp.storbinary("STOR songs.dta", open(self.song_manager.to_win_dir(dir), 'rb'))
                else:
                    logger.info("Uploading .dta at: "+ (str)(dir)+", back to:" + (str)(self.song_manager.to_ps3_dir(dir.replace(self.song_manager.cwd+"\\FROM",""))))
                    path = self.song_manager.to_ps3_dir(dir.replace(self.song_manager.cwd+"\\FROM",""))
                    path = path.replace("/songs.dta", "")
                    ftp.cwd(path)
                    ftp.storbinary("STOR songs.dta", open(self.song_manager.to_win_dir(dir), 'rb'))
                ftp.cwd("/")
            ftp.close()
        

def main():
    #USE to_win_dir WHEN CHECKING LOCAL DIRS, USE to_ps3_dir WHEN CHECKING REMOTE DIRS
    #CONFIG
    song_manager = SongManager()
    rb_manager = RBManager(song_manager)

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

    #READ DTA/DTAB
    logger.info("Starting .dta/.dtab reading...")
    print("Starting .dta/.dtab reading...")
    song_manager.read_dtas()
    logger.info("Successfully read .dta/.dtab.")
    print("Successfully read .dta/.dtab.")

    #EXCLUSION
    logger.info(f"{len(song_manager.songs)} songs found!")
    print(f"{len(song_manager.songs)} songs found!")
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
    rb_manager = RBManager(song_manager)

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

    #READ DTA/DTAB
    logger.info("Starting .dta/.dtab reading...")
    print("Starting .dta/.dtab reading...")
    song_manager.read_dtas()
    logger.info("Successfully read .dta/.dtab.")
    print("Successfully read .dta/.dtab.")

    #EXCLUSION
    logger.info(f"{len(song_manager.songs)} songs found!")
    print(f"{len(song_manager.songs)} songs found!")
    logger.info("Excluding songs not in whitelists...")
    print("Excluding songs not in whitelists...")
    song_manager.exclude_from_whitelists()
    logger.info("Successfully excluded songs not in whitelists.")
    print("Successfully excluded songs not in whitelists.")
    logger.info("Start of excluded song info.")
    print("Printing song info to log...")
    for song in song_manager.excluded:
        logger.debug(str(song))
        logger.debug(song_manager.show_between(song))
    logger.info("End of excluded song info.")
    print("Song info logging done.")

def reupload():
    song_manager = SongManager()
    rb_manager = RBManager(song_manager)
    song_manager.read_config()
    rb_manager.reuploaddtas()

main()
#debug()
#reupload()