import requests
import os

class SDCARD:

    handler = lambda f: None
    
    def __init__(self, dir, hostname = "flashair", path = "DCIM/101MSDCF"):
        self.hostname = hostname
        self.path = path
        if(os.path.isdir(dir)):
            self.dir = dir
        else:
            raise NotADirectoryError(dir)
        
    def request(self, r, attempts = 0, timeout = 3):
        response = False
        attempt = 1
        if(attempts == 0):
            attempts = float("inf")
        while(attempt <= attempts):
            try:
                response = requests.get(r, timeout = timeout)
            except:
                print("> Flashair nicht auffindbar, versuche erneut")
                attempt = attempt + 1
            else:
                break
        else:
            print("> Flashair nicht auffindbar, beende Anfrage")

        return response
        
    def getList(self):
        flist = []     
        response = self.request("http://"+ self.hostname +"/command.cgi?op=100&DIR=" + self.path)
        if(response):
            for line in response.text.split("\n")[1:-1]:
                file = {}
                file["name"] = line.split(",")[1]
                file["size"] = int(line.split(",")[2])
                flist.append(file)
        else:
            print("Es konnte keine List geladen werden")
        return flist

            
    def download(self, fname):
        print("Beginne Download...")
        response = self.request("http://"+ self.hostname + "/" + self.path + "/" + fname)
        if(response):
            print("Download erfolgreich!")
            with open(os.path.join(self.dir, fname), "wb") as f:
                f.write(response.content)
        else:
            print("Download gescheitert")

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



card = SDCARD("dldir", hostname = "192.168.178.88", path = "DCIM/101MSDCF")
print("Starte ...")
flist = card.getList()
print(card.diff(flist))

#f.download(flist[0],"/home/timo/Pictures")

