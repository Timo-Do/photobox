#!/home/pi/venvs/photobox/bin/python
import requests
import os
import time
import sys

import assets.config
import assets.tools

logger = assets.tools.get_logger("ImageLoader")

class SDCARD:

    handler = lambda f: None
    
    def __init__(self, dir, hostname = "flashair", path = "DCIM/101MSDCF"):
        logger.debug("Initializing SD Card downloader.")
        logger.debug("Using SD Card at {hn}".format(hn = hostname))
        self.hostname = hostname
        logger.debug("Setting target directory to {p}.".format(p = dir))
        self.path = path
        if(os.path.isdir(dir)):
            self.dir = dir
        else:
            raise NotADirectoryError(dir)
        
    def request(self, r, attempts = 3, timeout = 3):
        response = False
        attempt = 1
        if(attempts == 0):
            attempts = float("inf")
        while(attempt <= attempts):
            try:
                response = requests.get(r, timeout = timeout)
            except:
                attempt = attempt + 1
                logger.warning("HTTP Request to SD Card failed. Retrying attempt {a} of {ats}.".format(a = attempt, ats = attempts))
            else:
                break
        else:
            logger.error("HTTP Request to SD Card failed. No attempts left.")

        return response
        
    def getList(self):
        flist = []     
        logger.debug("Requesting image list from SD Card.")
        response = self.request("http://"+ self.hostname +"/command.cgi?op=100&DIR=" + self.path)
        if(response):
            for line in response.text.split("\n")[1:-1]:
                file = {}
                file["name"] = line.split(",")[1]
                file["size"] = int(line.split(",")[2])
                flist.append(file)
        return flist

            
    def download(self, fname):
        logger.info("Starting to download {f}.".format(f = fname))
        response = self.request("http://"+ self.hostname + "/" + self.path + "/" + fname)
        if(response):
            logger.info("Download finished successfully.")
            with open(os.path.join(self.dir, fname), "wb") as f:
                f.write(response.content)


    def diff(self, flist):
        dir_list = []
        diff_list = []
        with os.scandir(self.dir) as it:
            for entry in it:
                if entry.is_file():
                    file = {}
                    file["name"] = entry.name
                    file["size"] = entry.stat().st_size
                    dir_list.append(file)
        for file in flist:
            if(file not in dir_list):
                diff_list.append(file)
        
        return diff_list

def is_mounted(mountpoint):
    return os.path.ismount(mountpoint)

def on_dismount():
    logger.error("Device is not mounted.")
    sys.exit()


config = assets.config.load()
logger.debug("Starting up SD Card image loader.")
mountpoint = config["SDCard"]["MountPoint"]
if(is_mounted(mountpoint)):
    logger.info("Using device mounted at {mp}".format(mp = mountpoint))
else:
    on_dismount()
dirname = os.path.join(mountpoint, config["SDCard"]["DirName"])
os.makedirs(dirname, exist_ok=True)
card = SDCARD(dirname, hostname = "192.168.0.99", path = "DCIM/101MSDCF")
logger.debug("Starting main loop.")
while(True):
    file_list = card.getList()
    diff_list = card.diff(file_list)
    jpg_list = [image for image in diff_list if image["name"].upper().endswith("JPG")]
    for image in jpg_list:
        if(is_mounted(mountpoint)):
            card.download(image["name"])
        else:
            on_dismount()
    time.sleep(config["SDCard"]["Reaction_Time"])
