#!/home/pi/venvs/photobox/bin/python
import time
import socket
import struct
import assets.tools
import threading
import ipc

MULTICAST_IP = "224.1.1.1"
MULTICAST_PORT = 10000
MULTICAST = (MULTICAST_IP, MULTICAST_PORT)
BUFFER_SIZE = 1024
WAIT_BEFORE_RETRY = 10
REFRESH_RATE = 0.01

logger = assets.tools.get_logger("MULTICAST")

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((MULTICAST_IP, MULTICAST_PORT))
    ip = s.getsockname()[0]
    s.close()
    return ip

class Multicaster:
    def _get_MultiCastSocket(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ttl = struct.pack('b', 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            sock.bind(("", MULTICAST_PORT))
            group = socket.inet_aton(MULTICAST_IP)
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except OSError as e:
            if(e.args[0] == 19):
                # Network unreachable
                logger.error("Cannot setup MultiCastSocket. Network is unreachable.")
                return None
            else:
                raise e
        return sock

    def _operate_MultiCastSocket(self, send = False):
        success = False
        received = bytes()
        try:
            if(send):
                logger.debug("Sending \"{msg}\" to MultiCast.".format(msg = send.decode("ascii")))
                self.sock.sendto(send, MULTICAST)
            else:
                received = self.sock.recvfrom(BUFFER_SIZE)
                logger.debug("Received \"{msg}\" from MultiCast.".format(msg = received[0].decode("ascii")))
            success = True
        except OSError as e:
            if(e.args[0] == 101):
                success = False
            else:
                raise e
        if(send):
            return success
        else:
            return success, received

    def multicast(self, transmit):
        print("sending ...." + transmit.decode("ascii"))
        success = self._operate_MultiCastSocket(transmit)
        if(not success):
            logger.error("Failed to write to Multicast socket.")

    def __init__(self):
        interface_ip = get_ip()
        self.sock = None
        try:
            logger.debug("Trying to setup MultiCastSocket.")
            while(self.sock is None):
                self.sock = self._get_MultiCastSocket()
                if(self.sock is None):
                    logger.warning("MultiCastSocket setup failed. Starting next try in {w} s".format(
                        w = WAIT_BEFORE_RETRY
                    ))
                    time.sleep(WAIT_BEFORE_RETRY)
            logger.info("MultiCastSocket setup successfully.")
            messenger = ipc.Messenger()
            messenger.subscribe("", self.multicast, channels = ipc.CHANNELS.OUTBOUND, return_raw = True)
            while(True):
                success, received = self._operate_MultiCastSocket()
                sender_ip = received[1][0]
                if(success and sender_ip != interface_ip):
                    messenger.publish_raw(ipc.CHANNELS.INBOUND + received[0][1:])
        except Exception as e:
            if(self.sock is not None):
                self.sock.close()
            raise e

if __name__ == "__main__":
    m = Multicaster()
