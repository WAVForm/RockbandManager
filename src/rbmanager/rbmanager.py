import os
from ftplib import FTP
from shutil import copy
import logging
from retry import retryable, RetryError
from ps3_logic import download_dtas, get_dta_dirs, restore_dtas, upload_dtas
from re import match

class RBManager:
    '''
    Manage transfering of data between data source and data processor
    '''
    def __init__(self):
        self.logger = logging.getLogger("RBManager")
        self.cwd = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir)) #keep track of the CWD
        self.remote_dta_dirs = {} #dirs containing .dta/.dtabs on PS3, path is key, value is true if dtab is found, false otherwise 
        self.ps3_ip = None

    def get_dta_dirs(self):
        '''
        Looks for the directories containing .dta files, stores results in 'RBManager.dta_dirs'
        '''
        self.logger.info("Getting .dta directories...")
        try:
            if self.ps3_ip != None:
                self.dta_dirs = get_dta_dirs.run(ps3_ip=self.ps3_ip, root_game_path=)
            else:
                raise ValueError("PS3 IP not defined")
        except Exception as e:
            self.logger.error(f"Error getting .dta dirs: {e}")
            raise

    def download_dtas(self):
        '''
        Downloads/copies .dta files from target source
        '''
        try:
            if self.ps3_ip != None:
                download_dtas.run(ps3_ip=self.ps3_ip, dl_cache_path=, dta_dirs=)
            else:
                raise ValueError("PS3 IP not defined")
        except Exception as e:
            self.logger.error(f"Error downloading .dtas: {e}")
            raise

    def upload(self):
        '''
        Uploads modified .dta files back to target source
        '''
        try:
            if self.ps3_ip != None:
                upload_dtas.run(ps3_ip=self.ps3_ip, ul_cache_path=, dta_dirs=)
            else:
                raise ValueError("PS3 IP not defined")
        except Exception as e:
            self.logger.error(f"Error uploading .dtas: {e}")
            raise

    def restore_dtas(self):
        '''
        Reuploads available unmodified .dta files back to target source. Used in cases where reverting to a backup is needed (corruption, error, etc.) 
        '''
        try:
            if self.ps3_ip != None:
                restore_dtas.run(ps3_ip=self.ps3_ip, dl_cache_path=, dta_dirs=)
            else:
                raise ValueError("PS3 IP not defined")
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