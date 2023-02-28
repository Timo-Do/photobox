#!/home/pi/venvs/photobox/bin/python
import threading
import time

import RPi.GPIO as GPIO

import ipc
import assets.config
import assets.tools as tools


class Functionality():
    enabled = True
    ticks = 10
    topic = None

    def __init__(self, action, GPIOs, **kwargs):
        self.__dict__.update(kwargs)
        self.GPIOs = GPIOs
        self.action = action
    
    def disable(self):
        self.enabled = False
    
    def enable(self):
        self.enabled = True
    
class OutputManager():
    GPIOs = {}
    _blinking = {}

    def __init__(self):
        self.GPIOs["StatusLED"] = config["GPIOs"]["Status_LED"]
        self._blinking[self.GPIOs["StatusLED"]] = False

    def _blink(self, gpio):
        self._blinking[gpio] = True
        while(self._blinking[gpio]):
            GPIO.output(gpio, not GPIO.input(gpio))
            time.sleep(0.5)
        GPIO.output(gpio, GPIO.LOW)
            
    def StatusLED(self, message):
        gpio = self.GPIOs["StatusLED"]
        if(message == "STARTBLINKING"):   
            if(not self._blinking[gpio]):
                thread = threading.Thread(target = self._blink, args=(gpio, ), daemon = True)
                thread.start()
        elif(message == "STOPBLINKING"):
            self._blinking[gpio] = False


logger = tools.get_logger("io")
config = assets.config.load()
messenger = ipc.Messenger()
output = OutputManager()


input_funcs = {}

if(config["io"]["Slideshow_Toggle"]):
    input_funcs["Slideshow Toggle"] = Functionality(
        lambda : messenger.publish("TOGGLESCREEN", "Button"),
        [config["GPIOs"]["Slideshow_Toggle"]])

if(config["io"]["Shutdown"]):   
    input_funcs["Shutdown"] = Functionality(
        lambda : messenger.publish("SHUTDOWN", "Button"),
        [config["GPIOs"]["Shutdown_left"], config["GPIOs"]["Shutdown_right"]],
        ticks = 30)

output_funcs = {}

if(config["io"]["Status_LED"]):
    output_funcs["Status_LED"] = Functionality(
        lambda msg : output.StatusLED(msg),
        [config["GPIOs"]["Status_LED"]],
        topic = "STATUSLED")




GPIO.setmode(GPIO.BCM)

gpios_in = []
gpios_out = []

for name, func in input_funcs.items():
    for gpio in func.GPIOs:
        gpios_in.append(gpio)

for name, func in output_funcs.items():
    for gpio in func.GPIOs:
        gpios_out.append(gpio)



gpios_in = set(gpios_in)
gpios_out = set(gpios_out)
input_state = {}
try:
    for gpio in gpios_in:
        logger.debug("Setting up GPIO {g} as input.".format(g = gpio))
        GPIO.setup(gpio, GPIO.IN)
        input_state[gpio] = 0

    for gpio in gpios_out:
        logger.debug("Setting up GPIO {g} as output.".format(g = gpio))
        GPIO.setup(gpio, GPIO.OUT)

    for name, func in output_funcs.items():
        messenger.subscribe(func.topic, func.action)
    # Main Loop
    while(True):
        for gpio in gpios_in:
            if(GPIO.input(gpio)):
                input_state[gpio] += 1
            else:
                input_state[gpio] = 0
    
        # Inputs
        for name, func in input_funcs.items():
            if(func.enabled and all(input_state[gpio] > func.ticks for gpio in func.GPIOs)):
                logger.info("{n} triggered.".format(n = name))
                func.action()
                func.disable()
            elif(not func.enabled and all(input_state[gpio] == 0 for gpio in func.GPIOs)):
                logger.debug("Resetting {n}.".format(n = name))
                func.enable()
        

        time.sleep(0.01)
finally:
    GPIO.cleanup()


# GPIO.setup(22, GPIO.OUT)
# while True:

#     if(int(time.time()) % 2 == 0):
#         GPIO.output(22, GPIO.HIGH)
#     else:
#         GPIO.output(22, GPIO.LOW)

#     time.sleep(0.2)