from dta_processor import DTAProcessor
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import os
import shutil


class Song:
    '''
    Store the name and artist of a song, it's location on the PS3, and the content
    '''
    def __init__(self):
        self.name = "" #name of song
        self.artist = "" #artist of song
        self.nested = [] #song data from DTA as nested list
        self.content = "" #all the text for the song
        self.excluded = False #should the song be excluded
        self.reason = "" #why

    def __eq__(self, other:'Song')->bool:
        return (self.name == other.name) and (self.artist == other.artist)
    def __hash__(self)->int:
        return hash(self.name, self.artist, self.content)
    def __str__(self)->str:
        return ("| " + self.name + " by " + self.artist + (("| Excluded because: " + self.reason) if self.excluded else ""))

class SongManager:
    '''
    Manage processing of song data locally
    '''
    def __init__(self):
        self.logger = logging.getLogger("RBManager")
        self.dta_processor = DTAProcessor()
        self.songs = {} #all the songs that program can recognize, path is key, all songs in that file is value
        self.kept = [] #which songs to keep
        self.excluded = [] #which songs to exclude
        self.dtas = {} #where .dta contents will be held before and after modification until file write, path is key, entire file content is value
        self.whitelist = {} #whitelist, key is artist, value is song name

    def read_dtas(self):
        '''Open each .dta that was downloaded and process it'''
        try:
            for dir in self.dtas.keys():
                path = os.path.join(dir, "songs.dtab")
                self.logger.info(f"[SongManager] Processing {path}")
                self.songs[dir] = self.process_dta(path)
                self.logger.debug(f"[SongManager] Found {len(self.songs[dir])} songs")
            self.logger.info(f"[SongManager] {len([song for songs in self.songs.values() for song in songs])} total songs found.")
            return True
        except Exception as e:
            self.logger.error(f"[SongManager] Error reading .dtas: {e}")
            return False

    def __process_dta_old__(self, file_str):
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

    def process_dta(self, file_path):
        '''
        Read the file, parse its content and return list of songs in file.
        '''
        try:
            self.dta_processor = DTAProcessor()
            song_list = []
            nested = self.dta_processor.dta_to_nested_list(open(file_path, 'r').read())
            self.logger.debug(f"[SongManager] Got back a nested list from {file_path}")
            for each in nested:
                if not isinstance(each,list) or (isinstance(each,list) and len(each) < 2) or (isinstance(each,list) and len(each) >= 2 and ((not isinstance(each[1],list) or not isinstance(each[2],list)))):
                    continue
                s = Song()
                if each[1][0] == 'name':
                    s.name = each[1][1] if isinstance(each[1][1], str) else str(each[1][1])
                if each[2][0] == 'artist':
                    s.artist = each[2][1] if isinstance(each[2][1], str) else str(each[2][1])
                s.nested = each
                song_list.append(s)
            return song_list
        except Exception as e:
            self.logger.debug(f"[SongManager] Error processing .dta: {e}")

    def exclude_from_whitelist(self):
        '''
        Sets up whitelist exclusion with concurrency
        '''
        try:
            self.logger.info("[SongManager] Excluding songs not on whitelist")
            failed = False
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.process_exclusion, song_set) for song_set in self.songs.values()]
                for future in as_completed(futures):
                    if not future.result():
                        failed = True
            self.logger.info(f"[SongManager] {len(self.excluded)} total songs excluded")
            return not failed
        except Exception as e:
            self.logger.debug(f"[SongManager] Error excluding by whitelist: {e}")

    def process_exclusion(self, songs):
        '''Check each song against whitelists, exclude if not on whitelist'''
        try:
            wl_artists = self.whitelist.keys()
            wl_names = self.whitelist.values()
            for song in songs:
                in_artists = song.artist in wl_artists
                in_names = song.name in wl_names
                if in_artists or in_names:
                    if in_artists:
                        self.logger.debug("Whitelisted: " + (str)(f"{song.name} by {song.artist} for artist name"))
                    elif in_names:
                        self.logger.debug("Whitelisted: " + (str)(f"{song.name} by {song.artist} for song name"))
                    self.kept.append(song)
                else:
                    song.reason = "whitelist Exclusion"
                    self.excluded.append(song)

            self.logger.info((str)(len(self.excluded))+ " songs excluded")
            return True
        except Exception as e:
            self.logger.debug(f"[SongManager] Error processing exclusion: {e}")
            return False

    def manual_elimination(self):
        '''Allow the user to eliminate songs manually. Has 2 stage confirmation.'''
        logger.info((str)(len(self.excluded))+ " songs left for elimination...")
        try:
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
        except Exception as e:
            self.logger.debug(f"[SongManager] Error during elimination: {e}")

    def finalize(self):
        '''Finalize changes and create the files'''
        self.logger.info("[SongManager] finalizing .dta files to send back")
        try:
            failed = False
            with ThreadPoolExecutor() as executor:
                dirs = self.songs.keys()
                self.logger.info("[SongManager] Creating new .dta trings to write to files")
                create_futures = [ executor.submit(self.create_modified_dta, dir) for dir in dirs]
                for future in as_completed(create_futures):
                    if not future.result():
                        input()
                        failed = True
                
                self.logger.info("[SongManager] Writing new .dta strings to files")
                write_futures = [executor.submit(self.write_modified_dta, dir) for dir in dirs]
                for future in as_completed(write_futures):
                    if not future.result():
                        input()
                        failed = True

            self.logger.info("[SongManager] files finalized")
            return not failed
        except Exception as e:
            self.logger.debug(f"[SongManager] Error finalizing .dtas: {e}")
            return False

    def create_modified_dta(self,dir):
        try:
            self.logger.debug("Finalizing "+ (str)(len(self.songs[dir])) + " songs at:" + dir)
            processor = DTAProcessor()
            modified = ""
            for song in self.songs[dir]:
                if song not in self.excluded: #if the song is to be excluded
                    self.logger.debug("Adding " + song.name + " by " +  song.artist)
                    modified += processor.nested_list_to_dta(song.nested) + "\n"
            self.dtas[dir] = modified
            return True
        except Exception as e:
            self.logger.debug(f"[SongManager] Error creating modified .dta strings: {e}")
            return False

    def write_modified_dta(self, dir):
        try:
            destination = dir.replace("FROM", "TO")
            if not os.path.exists(destination): #if the path for the song in the TO directory doesn't exist
                self.logger.debug(f"Created directory {destination}")
                os.makedirs(destination, exist_ok=True) #make the directories recursively
            
            self.logger.debug("Finalizing "+(str)(destination+"\\songs.dtab")+ " ...")
            shutil.copy(dir+"/songs.dtab", destination+"/songs.dtab")
            
            self.logger.debug("Finalizing "+(str)(destination+"\\songs.dta")+ " ...")
            with open(destination+"/songs.dta", "w") as dta: #make the dta
                dta.write(self.dtas[dir])
            self.logger.debug("Done writing "+(str)(destination+"\\songs.dta")+ " ...")
            return True
        except Exception as e:
            self.logger.debug(f"[SongManager] Error writing modified .dta: {e}")
            return False
