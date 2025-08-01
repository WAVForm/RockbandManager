import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from shutil import copy
from webbrowser import open as web_open
from retry import retryable, RetryError

from dta_processor import DTAProcessor

class Song:
    '''
    Store the name and artist of a song, if it was excluded and why, and all the text content
    '''
    def __init__(self):
        self.name = "" #name of song
        self.artist = "" #artist of song
        self.content = [] #song data from DTA as nested list
        self.excluded = False #should the song be excluded

    def __eq__(self, other:'Song')->bool:
        return (self.name == other.name) and (self.artist == other.artist)
    def __hash__(self)->int:
        return hash((self.name, self.artist))
    def __str__(self)->str:
        return (f"|{self.name} by {self.artist}|{f"Excluded" if self.excluded else ""}")

class SongManager:
    '''
    Manage processing of song data locally
    '''
    def __init__(self):
        self.logger = logging.getLogger("SongManager")
        self.songs = {} #all the songs that program can recognize, path is key, all songs in that file is value
        self.kept = [] #which songs to keep
        self.excluded = [] #which songs to exclude
        self.whitelist = [] #TODO self.whitelist needed, list of tuples [(artist,song_name)...]

    def read_dtas(self, dta_dirs):
        '''
        Open each .dta that was downloaded and process it
        '''
        @retryable()
        def process_dta(file_path):
            '''
            Helper function that sends .dta to be processed and return list of songs.
            '''
            try:
                self.logger.debug(f"Processing .dta file at {file_path}")
                processor = DTAProcessor()
                song_list = []
                with open(os.path.join(file_path, "songs.dta"), 'r') as dta_f:
                    nested = processor.dta_to_nested_list(dta_f.read())
                self.logger.debug(f"Got back a nested list from {file_path}, extracting songs")
                for each in nested:
                    #checks if every song returned is in a valid format
                    if not isinstance(each,list) or (isinstance(each,list) and len(each) < 2) or (isinstance(each,list) and len(each) >= 2 and ((not isinstance(each[1],list) or not isinstance(each[2],list)))):
                        self.logger.debug(f"Item of nested list not in expected format: {each}")
                        continue
                    if not isinstance(each[1][1], str):
                        self.logger.debug(f"{str(each[1][1])} processed as {type(each[1][1])}")
                    if not isinstance(each[2][1], str):
                        self.logger.debug(f"{str(each[2][1])} processed as {type(each[2][1])}")
                    s = Song()
                    s.name = each[1][1].strip('"') if each[1][0] == "name" else ""
                    s.artist = each[2][1].strip('"') if each[2][0] == "artist" else ""
                    s.content = each
                    song_list.append(s)
                self.songs[file_path] = song_list
                return True
            except Exception as e:
                self.logger.debug(f"Error processing .dta: {e}, retry...")
                raise RetryError(e)
                
        self.logger.info("Processing downloaded .dtas")
        try:
            with ThreadPoolExecutor() as executor:
                dta_process_futures = [executor.submit(process_dta, dir) for dir in dta_dirs]
                for future in as_completed(dta_process_futures):
                    if not future.result():
                        raise Exception("Failed processing .dtas")
                amount_of_songs = len([song for songs in self.songs.values() for song in songs])
                self.logger.info(f"{amount_of_songs} total songs found.")
            return True
        except Exception as e:
            self.logger.error(f"Error reading .dtas: {e}")
            return False

    def exclude_blacklisted(self):
        '''
        Excludes not wanted songs
        '''
        @retryable()
        def process_exclusion(songs):
            '''
            Helper function to make exclusion multithreaded
            '''
            try:
                for song in songs:
                    if (song.artist, song.name) in self.whitelist:
                        self.logger.debug(f"Whitelisted {song}")
                        song.excluded = False
                        self.kept.append(song)
                    else:
                        self.logger.debug(f"Excluded {song}")
                        song.excluded = True
                        self.excluded.append(song)
                self.logger.debug(f"Finished processing exclusion of {len(songs)} songs")
                return True
            except Exception as e:
                self.logger.debug(f"Error processing exclusion: {e}")
                raise RetryError(e)

        try:
            self.logger.info("Excluding blacklisted songs")
            with ThreadPoolExecutor() as executor:
                exclusion_futures = [executor.submit(process_exclusion, song_set) for song_set in self.songs.values()]
                for future in as_completed(exclusion_futures):
                    if not future.result():
                        raise Exception("Failed excluding a set of songs")
            self.logger.info(f"{len(self.excluded)} total songs excluded")
            return True
        except Exception as e:
            self.logger.debug(f"Error during automatic exclusion: {e}")
            return False

    def manual_confirmation(self):
        '''
        Allow the user to keep excluded songs or confirm exclusion of songs manually.
        '''
        def handle_single_song_choice(index, song):
            '''
            Handles user input for manual confirmation
            '''
            print("q to quit\nr to return to previous\nz to search YouTube for song\nx to confirm exclusion\nc to keep")
            while True:
                user_input = input(":> ").lower()[0]
                match user_input:
                    case 'q':
                        exit()
                    case 'r':
                        return -1 #go back 1
                    case 'z':
                        web_open(f"https://www.youtube.com/results?search_query={song.artist.replace("&","and")}+-+{song.name.replace("&", "and")}+song") #opens the user's browser and searches for the song
                    case 'x':
                        return 0 #not wanted
                    case 'c':
                        return 1 #wanted
                    case _:
                        pass

        self.logger.info("Starting manual confirmation of excluded songs...")
        try:
            print(f"{len(self.excluded)} songs left for confirmation...")
            index = 0
            manually_wanted = []
            while index < len(self.excluded):
                song = self.excluded[index]
                if song in manually_wanted:
                    manually_wanted.remove(song)
                print(f"{index+1}. {song}")
                proceed = handle_single_song_choice(index, song)
                index += -1 if proceed == -1 else 1
                if proceed == 1:
                    manually_wanted.append(song)
                if index >= len(self.excluded):
                    user_input = input("You reached the end of manual confirmation, 'r' to return or nothing to continue\n:> ").lower()[0]
                    match user_input:
                        case 'r':
                            index -= 1
                        case _:
                            for wanted_song in manually_wanted:
                                self.excluded.remove(wanted_song)
                                self.kept.append(wanted_song)
            self.logger.info(f"{len(self.excluded)} exclusions confirmed")
            return True
        except Exception as e:
            self.logger.error(f"Error during exclusion confirmation: {e}")
            return False

    def finalize(self):
        '''
        Finalize changes and create the files
        '''
        modified_dtas = {}#temporary dictionary, key is path value is modifed contents
        @retryable()
        def create_modified_dta(dir):
            '''
            Helper function to create modified .dta file strings before writing them
            '''
            try:
                self.logger.debug(f"Finalizing {len(self.songs[dir])} songs at {dir}")
                processor = DTAProcessor()
                modified_content = ""
                for song in self.songs[dir]:
                    if song in self.kept:
                        self.logger.debug(f"Adding {song} back to .dta at {dir}")
                        modified_content += processor.nested_list_to_dta(song.content) + "\n"
                modified_dtas[dir] = modified_content
                return True
            except Exception as e:
                self.logger.debug(f"Error creating modified .dta strings from {dir}: {e}")
                raise RetryError(e)

        @retryable()
        def write_modified_dta(dir):
            '''
            Helper function to write modified .dta file string
            '''
            try:
                destination_path = dir.replace("FROM", "TO")
                os.makedirs(destination_path, exist_ok=True) #make path if doesn't exist
                copy(os.path.join(dir, "songs.dta"), os.path.join(destination_path, "songs.dtab")) #create backup .dta
                self.logger.debug(f"Writing modified content to {destination_path}")
                with open(os.path.join(destination_path, "songs.dta"), "w") as dta_f: #make the dta
                    dta_f.write(modified_dtas[dir])
                self.logger.debug(f"Done writing to {destination_path}")
                return True
            except Exception as e:
                self.logger.debug(f"Error writing modified .dta originally from {dir}: {e}")
                raise RetryError(e)

        self.logger.info("finalizing .dta files to send back")
        try:
            with ThreadPoolExecutor() as executor:
                dirs = self.songs.keys()
                self.logger.info("Creating new .dta strings to write to files")
                create_futures = [executor.submit(create_modified_dta, dir) for dir in dirs]
                for future in as_completed(create_futures):
                    if not future.result():
                        raise Exception("a .dta file string failed to be created")

                self.logger.info("Writing new .dta strings to files")
                write_futures = [executor.submit(write_modified_dta, dir) for dir in dirs]
                for future in as_completed(write_futures):
                    if not future.result():
                        raise Exception("a .dta file string failed to be writted")

            self.logger.info("Modified .dta files finalized")
            return True
        except Exception as e:
            self.logger.debug(f"Error finalizing modified .dtas: {e}")
            return False
