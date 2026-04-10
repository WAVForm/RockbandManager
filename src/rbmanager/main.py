import os
from ftplib import FTP
import logging
from retry import retryable
from .ps3_logic import download_dtas, get_dta_dirs, restore_dtas, upload_dtas
from re import match
from json import load as json_load
import multiprocessing
from .ps3_logic.models import PS3ConnectionInfo

class RBManager:
    '''
    Manage transfering of data between data source and data processor
    '''
    def __init__(self):
        self.logger = logging.getLogger("RBManager")
        self.cwd = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir)) #keep track of the CWD
        self.remote_dta_dirs:dict[str,bool] #dirs containing .dta/.dtabs on PS3, path is key, value is true if dtab is found, false otherwise 
        self.local_dta_dirs:set[str] #all locally downloaded dirs
        self.ps3_connection_info: PS3ConnectionInfo
        self.config = json_load(open("config.json", 'r'))["rbmanager"]
        self.config["dl_cache_path"] = os.path.join(self.cwd,self.config["dl_cache_path"])
        self.config["ul_cache_path"] = os.path.join(self.cwd, self.config["ul_cache_path"])


    def get_dta_dirs(self):
        '''
        Looks for the directories containing .dta files, stores results in 'RBManager.dta_dirs'
        '''
        self.logger.info("Getting .dta directories...")
        try:
            if self.ps3_connection_info is not None:
                self.remote_dta_dirs = get_dta_dirs.run(ps3_connection_info=self.ps3_connection_info, root_game_path=self.config["root_game_path"])
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
            if self.ps3_connection_info is not None:
                self.local_dta_dirs = download_dtas.run(ps3_connection_info=self.ps3_connection_info, dl_cache_path=os.path.join(self.cwd, self.config["dl_cache_path"]), dta_dirs=self.remote_dta_dirs)
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
            if self.ps3_connection_info is not None:
                upload_dtas.run(ps3_connection_info=self.ps3_connection_info, ul_cache_path=os.path.join(self.cwd, self.config["ul_cache_path"]), dta_dirs=self.remote_dta_dirs)
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
            if self.ps3_connection_info is not None:
                restore_dtas.run(ps3_connection_info=self.ps3_connection_info, dl_cache_path=os.path.join(self.cwd, "cache", "download"), dta_dirs=self.remote_dta_dirs)
            else:
                raise ValueError("PS3 IP not defined")
        except Exception as e:
            self.logger.error(f"Error reuploading .dtas: {e}")
            raise

    
    @retryable()
    def get_ps3_connection(self):
        '''
        Attempts to get valid PS3 connection details from user
        '''
        try:
            pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})"
            res = match(pattern, input("Please enter the IP and port (x.x.x.x:xxxxx)>: "))
            if not res:
                raise Exception("Input did not match pattern")
            ip, port = res.groups()
            port = int(port)
            octets = list(map(int, ip.split('.')))
            if any(o <0 or o > 255 for o in octets):
                raise Exception("IP Octet(s) value out of range")
            if port < 0 or port > 65535:
                raise Exception("Port value out of range")

            def try_mlsd():
                with FTP(encoding='latin-1', timeout=60) as ftp:
                    ftp.connect(host=ip,port=port)
                    ftp.login()
                    ftp.cwd(self.config["root_game_path"])
                    next(ftp.mlsd())

            def try_nlst():
                with FTP(encoding='latin-1', timeout=60) as ftp:
                    ftp.connect(host=ip,port=port)
                    ftp.login()
                    ftp.cwd(self.config["root_game_path"])
                    ftp.nlst()


            self.logger.debug("Determining 'ls' command style for connection")
            ls_style = None
            mlsd_process = multiprocessing.Process(target=try_mlsd)
            mlsd_process.start()
            mlsd_process.join(10)
            if mlsd_process.is_alive() or mlsd_process.exitcode != 0:
                self.logger.error("MLSD failed.")
                mlsd_process.terminate()
                nlst_process = multiprocessing.Process(target=try_nlst)
                nlst_process.start()
                nlst_process.join(10)
                if nlst_process.is_alive() or nlst_process.exitcode != 0:
                    self.logger.error("NLST failed.")
                    nlst_process.terminate()
                    raise Exception("Directory listing method unsupported")
                else:
                    self.logger.debug("NLST completed succssfully.")
                    ls_style = "nlst"
            else:
                self.logger.debug("MLSD completed successfully.")
                ls_style = "mlsd"

            self.logger.info("PS3 Connection Validated")
            self.ps3_connection_info = PS3ConnectionInfo(ip, port, ls_style)
            return True
        except Exception as e:
            self.logger.debug(f"Error getting PS3 connection: {e}")
            return False