#!/home/pi/venvs/photobox/bin/python
import socket
import threading
import time
import struct
import pickle
import uuid
import assets.tools
import os
import sys

logger = assets.tools.get_logger("NETWORKING")

MULTICAST_IP = "224.1.1.1"
MULTICAST_PORT = 10000
MULTICAST = (MULTICAST_IP, MULTICAST_PORT)
TCP_PORT = 10001
BUFFER_SIZE = 1024
WAIT_BEFORE_RETRY = 10
REFRESH_RATE = 0.01
HEART_RATE = 1
MAX_NAME_LEN = 32
DELIMITER = ":"

DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
SOCKET_ADDRESS = os.path.join(DIR, "UD_SOCKET")

ACK = "OK".encode("ascii")
ERR = "ERR".encode("ascii")
YES = "YES".encode("ascii")
NO = "NO".encode("ascii")
EOT = "EOT".encode("ascii")
PULSE = "BEEP".encode("ascii")

class Event(threading.Event):
    def fire(self):
        self.set()
        self.clear()

def _encode_obj(event):
    return pickle.dumps(event)

def _decode_obj(event):
    return pickle.loads(event)        

class RadioOperator:
    EVENTS = {}
    OUTBOUND = []
    PEERS = {}

    THREADLIST = ["TRANSCEIVER", "AGENT"]
    THREADS = {}


    def get_event(self, name):
        with self.EVENTS_LOCK:
            if name not in self.EVENTS:
                self.EVENTS[name] = Event()
        return self.EVENTS[name]

    # # # # MULTI CAST # # # #

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

    def _writer_thread(self, sock):
        try:
            while(self.RUN):
                self.OUTBOUND_EVENT.wait()
                with self.OUTBOUND_LOCK:
                    while(len(self.OUTBOUND) > 0):
                        message = self.OUTBOUND.pop(0)
                        success = self._operate_MultiCastSocket(sock, message)
                        if(not success):
                            logger.error("Failed to write to Multicast socket.")
        except Exception as e:
            raise e
        finally:
            self.RUN = False
            if(sock is not None):
                sock.close()

    def _reader_thread(self, sock):
        try:
            while(self.RUN):
                success, received = self._operate_MultiCastSocket(sock, send = False)
                if(success):
                    msg = received[0].decode("ascii")
                    info = msg.split(DELIMITER)
                    sender = info[0]
                    sender_ip = received[1][0]
                    self.PEERS[sender] = sender_ip
                    event = info[1]
                    logger.debug("Received event {e} from {s}.".format(
                        e = event,
                        s = sender_ip 
                    ))
                    # New Event #
                    if(sender != self.address):
                        logger.debug("Firing event {n}.".format(n = event))
                        self.get_event(event).fire()
                    else:
                        logger.debug("Rejected event \"{evt}\" because localhost was the sender.".format(
                            evt = event
                        ))
        except Exception as e:
            raise e
        finally:
            self.RUN = False
            if(sock is not None):
                sock.close()

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
            writer_thread = threading.Thread(target=self._writer_thread, args=(sock,))
            reader_thread = threading.Thread(target=self._reader_thread, args=(sock,))
            writer_thread.start()
            reader_thread.start()
            while(self.RUN):
                time.sleep(REFRESH_RATE)
        except Exception as e:
            self.RUN = False
            if(sock is not None):
                sock.close()
            raise e

    # # # # UDS AGENT # # # #
    def _build_multicast_message(self, message):
        transmit = DELIMITER.join([self.address, message]).encode("ascii")
        return transmit

    def _process_uds_message(self, data):
        data = data.decode("ascii")
        logger.debug("Received \"{msg}\" from UDS.".format(msg = data))
        info = data.split(DELIMITER)
        header = info[0]
        body = None
        footer = None
        if(len(info) > 1):
            body = info[1]
        if(len(info) > 2):
            footer = info[2]
        return header, body, footer

    def _handle_connection(self, connection):
        with connection:
            try:
                data = connection.recv(BUFFER_SIZE)
                if(data):
                    header, body, footer = self._process_uds_message(data)
                    if(header.endswith("SND")):
                        # Either LOCAL ("LSND") or GLOBAL ("GSND")
                        # New Event #
                        # Append to Event List
                        logger.debug("Fired event {evt}".format(evt = body))
                        self.get_event(body).fire()
                        if(header.startswith("G")):
                            # Notify the world
                            msg = self._build_multicast_message(body)
                            logger.debug("Appending \"{msg}\" to outbound queue".format(
                                msg = msg.decode("ascii")
                            ))
                            with self.OUTBOUND_LOCK:
                                self.OUTBOUND.append(msg)
                            self.OUTBOUND_EVENT.fire()
                        connection.sendall(ACK + EOT)
                    if(header == "PEERS"):
                        connection.sendall(_encode_obj(self.PEERS) + EOT)
                    if(header == "WAIT"):
                        fired = False
                        while(not fired):
                            connection.sendall(PULSE)
                            fired = self.get_event(body).wait(timeout = HEART_RATE)
                        connection.sendall(ACK + EOT)      
            except:
               logger.error("Handling of connection failed. Connection might be lost.")


    def Agent(self):
        logger.debug("Trying to setup UNIX socket.")
        # Remove UNIX Socket if it exists
        try:
            os.unlink(SOCKET_ADDRESS)
        except OSError:
            if os.path.exists(SOCKET_ADDRESS):
                raise

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(SOCKET_ADDRESS)
            sock.listen()
            logger.info("UDS setup successfully.")
            while(self.RUN):
                connection, _ = sock.accept()
                client_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(connection,),
                    daemon=True)
                client_thread.start()
                   
        except Exception as e:
            self.RUN = False
            raise e
        finally:
            sock.close()
    
    def Watcher(self):
        while(True):
            time.sleep(REFRESH_RATE)
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
        else:
            raise ValueError("Unknown thread name. Possible names: AGENT, TRANSCEIVER")

    def __init__(self):
        self.address = str(uuid.uuid4())
        self.RUN = True
        self.EVENTS_LOCK = threading.Lock()
        self.OUTBOUND_EVENT = Event()
        self.OUTBOUND_LOCK = threading.Lock()

        for thread in self.THREADLIST:
            self.THREADS[thread] = self._setup_threads(thread)
        
        for thread in self.THREADS:
            logger.info("Starting {thread}.".format(thread = thread))
            self.THREADS[thread].start()

        logger.info("Starting Watcher.")
        watcher = threading.Thread(target=self.Watcher, args=())
        watcher.start()

def _send_bytes(bytestring, object = False):
    try:
        if(len(bytestring) > BUFFER_SIZE):
            raise ValueError("Argument \"bytes\" may not be bigger than the set BUFFER_SIZE ({bs})".format(
                bs = BUFFER_SIZE
            ))
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(2 * HEART_RATE)
                s.connect(SOCKET_ADDRESS)
                s.sendall(bytestring)
                received_bytes = bytes()
                response = bytes()
                while(received_bytes[-3:] != EOT):
                    received_bytes = s.recv(BUFFER_SIZE)
                    if(len(received_bytes) == 0):
                        logger.error("Connection broke.")
                        return False
                    if(object):
                        response += received_bytes
                    else:
                        if(response.find(ACK) < 0):
                            response = ACK

                if(object):
                    response = _decode_obj(response[:-len(EOT)] ) 
                
        except ConnectionRefusedError:
            logger.warning("Connection to UDS refused")
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

def publish(event, local = False):
    _check_validity(event)
    if(local):
        header = "LSND"
    else:
        header = "GSND"
    msg = header + DELIMITER + event.upper()
    response = _send_bytes(msg.encode("ascii"))
    if(not response == ACK):
        logger.error("No Acknowledgement has been received from server.")
    return

def get_peers():
    response = _send_bytes("PEERS".encode("ascii"), object = True)
    return response

def _run_on_event(evt, fun):
    header = "WAIT"
    msg = header + DELIMITER + evt.upper()
    msg = msg.encode("ascii")
    while(True):
        response = _send_bytes(msg)
        if(response == ACK):
            fun()
        else:
            time.sleep(HEART_RATE)



def subscribe(evt, fun):
    _check_validity(evt)
    logger.debug("Waiting for event {evt}.".format(evt = evt))
    wait_thread = threading.Thread(target=_run_on_event, args=(evt, fun), daemon = True)
    wait_thread.start()

if __name__ == "__main__":
    RadioOperator()
