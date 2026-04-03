import os
from ftplib import FTP
from shutil import copy
import logging
from retry import retryable, RetryError
import ps3_logic as ps3
import emu_logic as emu

class RBManager:
    '''
    Manage transfering of data between data source and data processor
    '''
    def __init__(self):
        self.logger = logging.getLogger("RBManager")
        self.cwd = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir)) #keep track of the CWD
        self.remote_dta_dirs = {} #dirs containing .dta/.dtabs on PS3, path is key, value is true if dtab is found, false otherwise 
        self.ps3_ip = None
        self.emu_path = None

    def get_dta_dirs(self):
        '''
        Looks for the directories containing .dta files, stores results in 'RBManager.dta_dirs'
        '''
        self.logger.info("Getting .dta directories...")
        try:
            if self.ps3_ip != None:
                self.dta_dirs = ps3.get_dta_dirs.run(ps3_ip=, root_game_path=)
            elif self.emu_path != None:
                self.dta_dirs = emu.get_dta_dirs.run(emu_path=, root_game_path=)
            else:
                raise ValueError("PS3 IP and Emulator path not defined")
        except Exception as e:
            self.logger.error(f"Error getting .dta dirs: {e}")
            raise

    def download_dtas(self):
        '''
        Downloads/copies .dta files from target source
        '''
        try:
            if self.ps3_ip != None:
                ps3.download_dtas.run(ps3_ip=, dl_cache_path=, dta_dirs=)
            elif self.emu_path != None:
                emu.download_dtas.run(ps3_ip=, dl_cache_path=, dta_dirs=)
            else:
                raise ValueError("PS3 IP and Emulator path not defined")
        except Exception as e:
            self.logger.error(f"Error downloading .dtas: {e}")
            raise

    def upload(self):
        '''
        Uploads modified .dta files back to target source
        '''
        try:
            if self.ps3_ip != None:
                ps3.upload_dtas.run(ps3_ip=, ul_cache_path=, dta_dirs=)
            elif self.emu_path != None:
                emu.upload_dtas.run(ps3_ip=, ul_cache_path=, dta_dirs=)
            else:
                raise ValueError("PS3 IP and Emulator path not defined")
        except Exception as e:
            self.logger.error(f"Error uploading .dtas: {e}")
            raise

    def restore_dtas(self):
        '''
        Reuploads available unmodified .dta files back to target source. Used in cases where reverting to a backup is needed (corruption, error, etc.) 
        '''
        try:
            if self.ps3_ip != None:
                ps3.restore_dtas.run(ps3_ip=, dl_cache_path=, dta_dirs=)
            elif self.emu_path != None:
                emu.restore_dtas.run(ps3_ip=, dl_cache_path=, dta_dirs=)
            else:
                raise ValueError("PS3 IP and Emulator path not defined")
        except Exception as e:
            self.logger.error(f"Error reuploading .dtas: {e}")
            raise

    

    def get_ps3_connection(self):
        '''
        Attempts to get valid PS3 connection details from user
        '''
        from ipaddress import ip_address
        try:
            pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})"
            res = match(pattern, input("Please enter the IP and port (x.x.x.x:xxxxx)>: "))
            if not res:
                raise Exception()
            ip, port = res.groups()
            octets = list(map(int, ip.split('.')))
            if any(o <0 or o > 255 for o in octets):
                raise Exception()

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