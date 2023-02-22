#!/home/pi/venvs/photobox/bin/python

import zmq
import time
import threading

from assets.tools import get_logger

logger = get_logger("IPC")

context = zmq.Context()
SUB_SOCKET = "/tmp/SUB"
PUB_SOCKET = "/tmp/PUB"
ENCODING = "ascii"
DELIMITER = ":"

class Messenger():
    def __init__(self):
        self.publisher = context.socket(zmq.PUB)
        self.publisher.connect("ipc://" + SUB_SOCKET)

    def publish(self, topic, message, local = False):
        mode = "G"
        if(local):
            mode = "L"
        transmit = mode + DELIMITER + topic + DELIMITER + message
        self.send(transmit.encode(ENCODING))
        
    def send(self, transmit):
        self.publisher.send(transmit)


    def _waiter_thread(self, topic, callback, loc, glob):
        subscriber = context.socket(zmq.SUB)
        subscriber.connect("ipc://" + PUB_SOCKET)
        if(loc):
            topic_local = "L" + DELIMITER + topic
            subscriber.setsockopt(zmq.SUBSCRIBE, topic_local.encode(ENCODING))
        if(glob):
            topic_global = "G" + DELIMITER + topic
            subscriber.setsockopt(zmq.SUBSCRIBE, topic_global.encode(ENCODING))
        while True:
            transmit = subscriber.recv().decode(ENCODING)
            # transmit consists of:
            # M : TOPIC : MESSAGE
            # with M = {L/G} (local or global mode)
            idx_start = 2   # start looking after the first Delimiter (":")
            delim_index = transmit.find(DELIMITER, idx_start) + 1
            callback(transmit[delim_index:])


    def subscribe(self, topic, callback, mode = "both"):
        if(mode == "both"):
            loc = True
            glob = True
        elif(mode == "local"):
            loc = True
            glob = False
        elif(mode == "global"):
            loc = False
            glob = True
        else:
            raise ValueError("Argument 'mode' was set to {m} but can only take on 'both', 'local' or 'global'.".format(
                m = mode
            ))

        thread = threading.Thread(target = self._waiter_thread, args = (topic, callback, loc, glob), daemon = True)
        thread.start()
        return thread

def relais():
    """
    Sets up a ZeroMQ forwarding device that receives messages on a SUB socket and forwards them on a PUB socket.
    """
    try:
        # Create a ZeroMQ context with one I/O thread.
        context = zmq.Context(1)

        sub_socket = context.socket(zmq.SUB)
        sub_socket.bind("ipc://" + SUB_SOCKET)
        
        # Subscribe to all messages received by the SUB socket.
        sub_socket.setsockopt(zmq.SUBSCRIBE, "".encode(ENCODING))
        

        pub_socket = context.socket(zmq.PUB)
        pub_socket.bind("ipc://" + PUB_SOCKET)

        # Create a ZeroMQ forwarding device that receives messages on the SUB socket and forwards them on the PUB socket.
        zmq.device(zmq.FORWARDER, sub_socket, pub_socket)

    except Exception as e:
        # Print any exceptions that occur during execution.
        print(e)

    finally:
        # Close the sockets and terminate the ZeroMQ context when the device is shut down.
        sub_socket.close()
        pub_socket.close()
        context.term()

if __name__ == "__main__":
    # Call the main function when this script is executed.
    relais()

        
