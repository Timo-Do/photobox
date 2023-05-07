#!/home/pi/venvs/photobox/bin/python

import ipc
import subprocess
from multicast import get_ip
import assets.tools
import assets.config
import time
from xmlrpc.client import ServerProxy

logger = assets.tools.get_logger("HOUSEKEEPING")
server = ServerProxy("http://localhost:9001/RPC2")
msg = ipc.Messenger()
config = assets.config.load()


def run_bash(cmd):
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode("ascii")

def shutdown():
    #run_bash("sudo shutdown now")
    logger.error("Shutdown deactivated ... for now")

def umntusbtop(payload):
    print("Start blinking")
    msg.publish("STATUSLED", "STARTBLINKING", ipc.CHANNELS.LOCAL)
    run_bash("/home/pi/photobox/bin/deploy/umntusbtop")
    print("Stop blinking")
    msg.publish("STATUSLED", "STOPBLINKING", ipc.CHANNELS.LOCAL)
    while(run_bash("ls -l /dev/usbtop") != 0):
        time.sleep(0.1)
    msg.publish("STATUSLED", "STOP", ipc.CHANNELS.LOCAL)
    print("LED OFF")

def supervisor_get_process_info(proc = None):
    if(proc is None):
        return server.supervisor.getAllProcessInfo()
    else:
        return server.supervisor.getProcessInfo(proc)
    
def supervisor_empty_log(proc):
    server.supervisor.clearProcessLogs(proc)
    return True


def supervisor_get_process_log(name):
    try:
        log = server.supervisor.readProcessStderrLog(name, 0, 0)
    except:
        log = "Kein Log vorhanden!"
    log = log.replace("\n", "<br />")
    return log

def supervisor_processcontrol(proc, cmd):
    ret = run_bash(f"supervisorctl {cmd} {proc}")
    ret = ret.split(": ")
    if(ret[0].startswith(proc) and ret[1].startswith(cmd)):
        return True
    return False

def get_wifi():
    ret = run_bash("iw dev wlan0 station dump")
    lines = ret.split("\n")
    info = {}
    for line in lines:
        if(line.startswith("\t")):
            line = line.replace("\t", "")
            key, value = line.split(":")
            info[key] = value.strip()
    return info


if __name__ == "__main__":
    msg.subscribe("UMNTUSB",umntusbtop)
    hostname = config["Basic"]["Name"]
    while(True):
        time.sleep(1)
