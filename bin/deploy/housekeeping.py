#!/home/pi/venvs/photobox/bin/python

import ipc
import subprocess

import assets.tools
import time
from xmlrpc.client import ServerProxy

logger = assets.tools.get_logger("HOUSEKEEPING")
server = ServerProxy("http://localhost:9001/RPC2")

def run_bash(cmd):
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode("ascii")

def shutdown():
    #run_bash("sudo shutdown now")
    logger.error("Shutdown deactivated ... for now")

def supervisor_get_process_info(proc = None):
    if(proc is None):
        return server.supervisor.getAllProcessInfo()
    else:
        return server.supervisor.getProcessInfo(proc)

def supervsior_get_log(name):
    return server.supervisor.readProcessStderrLog(name, 0, 0)


if __name__ == "__main__":
    #networking.on_command("SHUTDOWN", shutdown)
    #print(supervsior_get_log("flask"))

    handler = print
    messenger = ipc.Messenger()
    messenger.subscribe("test", handler)
    while(True):
        messenger.publish("test", str(time.time()))
        time.sleep(1)