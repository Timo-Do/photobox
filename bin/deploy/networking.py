import socket
import threading
import time
import select
import struct
import pickle
import uuid
import assets.tools

logger = assets.tools.get_logger("NETWORKING")

MULTICAST_IP = "224.1.1.1"
MULTICAST_PORT = 10000
MULTICAST = (MULTICAST_IP, MULTICAST_PORT)
TCP_PORT = 10001
BUFFER_SIZE = 1024
WAIT_BEFORE_RETRY = 10
QUEUE_PAUSE = 0.01
EVENT_LIFETIME = 10
MAX_NAME_LEN = 32
DELIMITER = ":"
ACK = "OK".encode("ascii")
ERR = "ERR".encode("ascii")
YES = "YES".encode("ascii")
NO = "NO".encode("ascii")
EOT = "EOT".encode("ascii")
HEARTBEAT = "PULSE"
CMD_PREFIX = "CMD"
NFY_PREFIX = "NFY"

class Event:
    def __init__(self, id, sender):
        self.id = id
        self.sender = sender
        self.birth = time.time()

def _encode_obj(event):
    return pickle.dumps(event)

def _decode_obj(event):
    return pickle.loads(event)        
        
def _is_event(id):
    if(_is_command(id) or _is_notification(id)):
        return True
    return False

def _is_command(id):
    if(id.startswith(CMD_PREFIX)):
        return True
    return False

def _is_notification(id):
    if(id.startswith(NFY_PREFIX)):
        return True
    return False

class RadioOperator:
    EVENTS = []
    OUTBOUND = []
    PEERS = {}

    THREADLIST = ["TRANSCEIVER", "AGENT", "HEART"]
    THREADS = {}

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

    def _operate_MultiCastSocket(self, sock, send = False):
        success = False
        received = bytes()
        try:
            if(send):
                logger.debug("Sending \"{msg}\" to MultiCast.".format(msg = send.decode("ascii")))
                sock.sendto(send, MULTICAST)
            else:
                received = sock.recvfrom(BUFFER_SIZE)
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

    
    def Transceiver(self):
        sock = None
        try:
            logger.debug("Trying to setup MultiCastSocket.")
            while(sock is None):
                sock = self._get_MultiCastSocket()
                if(sock is None):
                    logger.warning("MultiCastSocket setup failed. Starting next try in {w} s".format(
                        w = WAIT_BEFORE_RETRY
                    ))
                    time.sleep(WAIT_BEFORE_RETRY)
            logger.info("MultiCastSocket setup successfully.")
            while(self.RUN):
                time.sleep(QUEUE_PAUSE)
                ready_to_read, ready_to_write, in_error = \
                    select.select([sock],[sock],[sock],0)

                if(len(self.OUTBOUND) > 0):
                    message = self.OUTBOUND.pop(0)
                    for sock_write in ready_to_write:
                        success = self._operate_MultiCastSocket(sock_write, message)

                for sock_read in ready_to_read:
                    success, received = self._operate_MultiCastSocket(sock_read, send = False)
                    if(success):
                        msg = received[0].decode("ascii")
                        info = msg.split(DELIMITER)
                        sender = info[0]
                        sender_ip = received[1][0]
                        self.PEERS[sender] = sender_ip
                        id = info[1]
                        if(_is_event(id)):
                            # New Event #
                            if(sender != self.address):
                                self._add_evt(Event(id, sender))
                            else:
                                logger.debug("Rejected event \"{evt}\" because localhost was the sender.".format(
                                    evt = id
                                ))

        except Exception as e:
            self.RUN = False
            if(sock is not None):
                sock.close()
            raise e


    def _get_evt(self, id):
        evt_found = False
        idx_evt = None
        self.EVENTS_LOCK.acquire()
        for idx, evt in enumerate(self.EVENTS):
            if(evt.id == id):
                idx_evt = idx
                break
        if(idx_evt is not None):
            if(_is_command(id)):
                evt = self.EVENTS.pop(idx_evt)
            else:
                evt = self.EVENTS[idx_evt]
            lifetime = time.time() - evt.birth
            logger.debug("Acquired event \"{evt}\" after {lt} seconds.".format(
                evt = evt.id,
                lt = lifetime
            ))
            evt_found = True
        self.EVENTS_LOCK.release()
        return evt_found

    def _get_notifications(self):
        return [evt for evt in self.EVENTS if evt.id.startswith("NFY")]

    def _add_evt(self, evt):
        logger.debug("Adding event \"{evt}\" to EVENTS".format(evt = evt.id))
        self.EVENTS_LOCK.acquire()
        self.EVENTS.append(evt)
        self.EVENTS_LOCK.release()
    
    def _clean_evts(self):
        self.EVENTS_LOCK.acquire()
        num_events_before = len(self.EVENTS)
        self.EVENTS = [evt for evt in self.EVENTS if time.time() < evt.birth + EVENT_LIFETIME]
        num_event_diff = num_events_before - len(self.EVENTS)
        self.EVENTS_LOCK.release()
        if(num_event_diff > 0):
            logger.debug("Cleaned up {n} event(s) from queue.".format(n = num_event_diff))

    def Heart(self):
        while(True):
            notify(HEARTBEAT)
            time.sleep(EVENT_LIFETIME)

    def Agent(self):
        logger.debug("Trying to setup TCPSocket.")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", TCP_PORT))
            sock.listen()
            logger.info("TCPSocket setup successfully.")
            while(self.RUN):
                connection, _ = sock.accept()
                with connection:
                    # Clean up all old events
                    self._clean_evts()
                    while True:
                        data = connection.recv(BUFFER_SIZE)
                        if(not data):
                            break
                        data = data.decode("ascii")
                        logger.debug("Received \"{msg}\" from TCP.".format(msg = data))
                        info = data.split(DELIMITER)
                        header = info[0]
                        body = None
                        footer = None
                        if(len(info) > 1):
                            body = info[1]
                        if(len(info) > 2):
                            footer = info[2]
                        # # # # # # # # # # # #
                        if(header == "SND"):
                            # New Event #
                            # Append to Event List
                            self._add_evt(Event(body, sender = self.address))
                            # Notify the world
                            msg = self._build_transmit(body)
                            logger.debug("Appending \"{msg}\" to outbound queue".format(
                                msg = msg.decode("ascii")
                            ))
                            self.OUTBOUND.append(msg)
                            connection.sendall(ACK)
                        if(header == "CHK"):
                            # Event Command #
                            rmsg = NO
                            rval = self._get_evt(CMD_PREFIX + "_" + body)                            
                            if(rval): rmsg = YES
                            connection.sendall(rmsg)
                        if(header == "LIST"):
                            connection.sendall(_encode_obj(self._get_notifications()))
                        if(header == "PEERS"):
                            connection.sendall(_encode_obj(self.PEERS))

                        connection.sendall(EOT)
        except Exception as e:
            raise e
        finally:
            sock.close()
    
    def Watcher(self):
        while(True):
            time.sleep(QUEUE_PAUSE)
            for thread in self.THREADS:
                if(not self.THREADS[thread].is_alive()):
                    logger.warning("{thread} died. Restarting ...".format(thread = thread))
                    self.transceiver_thread = self._setup_threads(thread)
                    self.transceiver_thread.start()
                    logger.debug("{thread} restarted. Sleeping {w} s".format(w = WAIT_BEFORE_RETRY, thread = thread))
                    time.sleep(WAIT_BEFORE_RETRY)                 


    def _setup_threads(self, which):
        if(which == "AGENT"):
            return threading.Thread(target=self.Agent, args=())
        elif(which == "TRANSCEIVER"):
            return threading.Thread(target=self.Transceiver, args=())
        elif(which == "HEART"):
            return threading.Thread(target=self.Heart, args=())
        else:
            raise ValueError("Unknown thread name. Possible names: HEART, AGENT, TRANSCEIVER")

    def _build_transmit(self, message):
        transmit = DELIMITER.join([self.address, message]).encode("ascii")
        return transmit

    def __init__(self):
        self.address = str(uuid.uuid4())
        self.RUN = True
        self.EVENTS_LOCK = threading.Lock()

        for thread in self.THREADLIST:
            self.THREADS[thread] = self._setup_threads(thread)
        
        for thread in self.THREADS:
            logger.info("Starting {thread}.".format(thread = thread))
            self.THREADS[thread].start()

        logger.info("Starting Watcher.")
        watcher = threading.Thread(target=self.Watcher, args=())
        watcher.start()

def _send_bytes(bytes):
    try:
        if(len(bytes) > BUFFER_SIZE):
            raise ValueError("Argument \"bytes\" may not be bigger than the set BUFFER_SIZE ({bs})".format(
                bs = BUFFER_SIZE
            ))
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("127.0.0.1", TCP_PORT))
                s.sendall(bytes)
                response = s.recv(BUFFER_SIZE)
                while(response[-3:] != EOT):
                    response += s.recv(BUFFER_SIZE)
                response = response[:-3]
        except ConnectionRefusedError:
            logger.warning("Connection to TCPSocket refused")
            response = False
        return response
    except Exception as e:
        logger.error("Failed to send bytes: " + str(e))
        return None

def _check_validity(name):
    if(len(name) > MAX_NAME_LEN):
        raise ValueError(("Given name \"{name}\" has length {len}," + \
            " which is bigger than the allowed size ({max}).").format(
                name = name,
                len = len(name),
                max = MAX_NAME_LEN
            ))
    if(not name.isalnum()):
        raise ValueError(("Given name \"{name}\" may only contain alphanumerical characters").format(
                name = name
            ))
    return

def broadcast(event):
    msg = "SND" + DELIMITER + event.upper()
    response = _send_bytes(msg.encode("ascii"))
    if(not response == ACK):
        raise ValueError("No Acknowledgement has been received from server.")
    return

def notify(event):
    _check_validity(event)
    broadcast(NFY_PREFIX + "_" + event)

def command(event):
    _check_validity(event)
    broadcast(CMD_PREFIX + "_" + event)

def get_notifications():
    response = _send_bytes("LIST".encode("ascii"))
    return _decode_obj(response)

def get_peers():
    response = _send_bytes("PEERS".encode("ascii"))
    return _decode_obj(response)

def get_command(event):
    _check_validity(event)
    msg = "CHK" + DELIMITER + event.upper()
    response = _send_bytes(msg.encode("ascii"))
    if(response == YES):
        return True
    elif(response == NO):
        return False
    else:
        if(hasattr(response, "decode")):
            raise ValueError("Got unexpected response \"{r}\"".format(response.decode("ascii")))
        else:
            return response
if __name__ == "__main__":
    RadioOperator()
    while(True):
        match input().split():
            case ["command", cmd]:
                command(cmd)
            case ["notify", nfy]:
                notify(nfy)    
            case ["break"]:
                break
            case _:
                print("Unknown input.")