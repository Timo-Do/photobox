#!/home/pi/venvs/photobox/bin/python
import threading
import time

import RPi.GPIO as GPIO

import ipc
import assets.config
import assets.tools as tools

GPIO.setmode(GPIO.BCM)

class Functionality():
    enabled = True
    ticks = 10
    topic = None
    init = True
    default = GPIO.LOW
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
        self.GPIOs["Shutter"] = config["GPIOs"]["Shutter"]
        self._blinking[self.GPIOs["StatusLED"]] = False
        self.shutter_lock = threading.Lock()

    def _blink(self, gpio):
        self._blinking[gpio] = True
        while(self._blinking[gpio]):
            GPIO.output(gpio, not GPIO.input(gpio))
            time.sleep(0.2)
        GPIO.output(gpio, GPIO.LOW)
            
    def StatusLED(self, message):
        gpio = self.GPIOs["StatusLED"]
        if(message == "STARTBLINKING"):
            logger.debug("Status LED blinking on")   
            if(not self._blinking[gpio]):
                thread = threading.Thread(target = self._blink, args=(gpio, ), daemon = True)
                thread.start()
        elif(message == "STOPBLINKING"):
            self._blinking[gpio] = False
            logger.debug("Status LED blinking off")
            GPIO.output(gpio, GPIO.HIGH)
        elif(message == "STOP"):
            logger.debug("Status LED off")
            GPIO.output(gpio, GPIO.LOW)

    def _display(self, symbol):
        segments = ["o", "ol", "or", "m", "ul", "ur", "u"]
        on = []
        if(symbol == 1):
            on = ["or", "ur"]
        elif(symbol == 2):
            on = ["o", "or", "m", "ul", "u"]
        elif(symbol == 3):
            on = ["o", "or", "m", "ur", "u"]
        elif(symbol == None):
            pass
        else:
            raise ValueError("Invalid symbol given.")
        for segment in segments:
            # Watch out: Inverse Logic!
            state = GPIO.HIGH
            if(segment in on):
                state = GPIO.LOW
            GPIO.output(config["GPIOs"][f"cd_{segment}"], state)

    def Countdown(self, start):
        logger.info("Countdown activated")
        for i in range(start):
            self._display(start - i)
            time.sleep(1)
        self._display(None)

    def shutter(self, msg):
        if(msg == "NOW"):
            countdown = False
        else:
            countdown = True

        if(self.shutter_lock.acquire(False)):
            if(countdown):
                self.Countdown(3)
            gpio = self.GPIOs["Shutter"]
            logger.info("Shutter activated!")
            GPIO.output(gpio, GPIO.LOW)
            time.sleep(.45)
            GPIO.output(gpio, GPIO.HIGH)
            self.shutter_lock.release()
            
        


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
    
if(config["io"]["Taster"]):
    input_funcs["Taster"] = Functionality(
        lambda : messenger.publish("SHUTTER", "COUNTDOWN"),
        [config["GPIOs"]["Taster"]])

output_funcs = {}

if(config["io"]["Status_LED"]):
    output_funcs["Status_LED"] = Functionality(
        lambda msg : output.StatusLED(msg),
        [config["GPIOs"]["Status_LED"]],
        topic = "STATUSLED")

if(config["io"]["Shutter"]):
    output_funcs["Shutter"] = Functionality(
        lambda msg : output.shutter(msg),
        [config["GPIOs"]["Shutter"]],
        topic = "SHUTTER", default = GPIO.HIGH)

if(config["io"]["Countdown"]):
	output_funcs["Countdown"] = Functionality(
	lambda msg : output.shutter(msg),
	[
		config["GPIOs"]["cd_o"],
		config["GPIOs"]["cd_ol"],
		config["GPIOs"]["cd_or"],
		config["GPIOs"]["cd_m"],
		config["GPIOs"]["cd_ul"],
		config["GPIOs"]["cd_ur"],
		config["GPIOs"]["cd_u"]
	],
	topic = "SHUTTER", default = GPIO.HIGH)




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
    for name, func in output_funcs.items():
        for gpio in func.GPIOs:
            logger.debug(f"Setting GPIO {gpio} to {func.default}")
            GPIO.output(gpio, func.default)

    while(True):
        for gpio in gpios_in:
            if(GPIO.input(gpio)):
                input_state[gpio] += 1
            else:
                input_state[gpio] = 0
    
        # Inputs
        for name, func in input_funcs.items():
            if(func.enabled and all(input_state[gpio] > func.ticks for gpio in func.GPIOs)):
                if(func.init):
                    logger.info("{n} init passed.".format(n = name))
                    func.init = False
                else:
                    logger.info("{n} triggered.".format(n = name))
                    func.action()
                func.disable()
            elif(not func.enabled and all(input_state[gpio] == 0 for gpio in func.GPIOs)):
                logger.debug("Resetting {n}.".format(n = name))
                func.enable()
        

        time.sleep(0.01)
finally:
    GPIO.cleanup()
