#!/home/pi/venvs/photobox/bin/python

import zmq
import time
import threading

from assets.tools import get_logger

logger = get_logger("IPC")


class CHANNELS():
    INBOUND = "I"
    OUTBOUND = "O"
    LOCAL = "L"
    ALL = INBOUND + OUTBOUND + LOCAL
    INTERNAL = LOCAL + OUTBOUND

context = zmq.Context()
SUB_SOCKET = "/tmp/SUB"
PUB_SOCKET = "/tmp/PUB"
ENCODING = "ascii"
DELIMITER = ":"

class Messenger():
    def __init__(self):
        self.publisher = context.socket(zmq.PUB)
        self.publisher.connect("ipc://" + SUB_SOCKET)

    def publish(self, topic, message, channel = CHANNELS.OUTBOUND):
        if(len(channel) != 1):
            raise ValueError("Argument 'channel' can only take character.")
        transmit = channel + topic + DELIMITER + message
        self.publish_raw(transmit.encode(ENCODING))

    def publish_raw(self, transmit):
        self.publisher.send(transmit)


    def _waiter_thread(self, topic, callback, channels, return_raw):
        subscriber = context.socket(zmq.SUB)
        subscriber.connect("ipc://" + PUB_SOCKET)
        for channel in channels:
            subscriber.setsockopt(zmq.SUBSCRIBE, (channel + topic).encode(ENCODING))
        while True:
            transmit = subscriber.recv()
            if(return_raw):
                callback(transmit)
            else:
                transmit = transmit.decode(ENCODING)
                delim_index = transmit.find(DELIMITER) + 1
                callback(transmit[delim_index:])


    def subscribe(self, topic, callback, channels = CHANNELS.ALL, return_raw = False):
        thread = threading.Thread(target = self._waiter_thread,
            args = (topic, callback, channels, return_raw), daemon = True)
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

        
