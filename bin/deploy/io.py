import RPi.GPIO as GPIO
import time
import networking
import assets.config

class Functionality():
    enabled = True
    ticks = 10

    def __init__(self, action, GPIOs, **kwargs):
        self.__dict__.update(kwargs)
        self.GPIOs = GPIOs
        self.action = action
    
    def disable(self):
        self.enabled = False
    
    def enable(self):
        self.enabled = True

logger = assets.tools.get_logger("IO")
config = assets.config.load()

input_funcs = {}

if(config["IO"]["Slideshow_Toggle"]):
    input_funcs["Slideshow Toggle"] = Functionality(
        lambda : networking.command("TOGGLESCREEN"),
        [config["GPIOs"]["Slideshow_Toggle"]])

if(config["IO"]["Shutdown"]):   
    input_funcs["Shutdown"] = Functionality(
            lambda : networking.command("SHUTDOWN"),
            [config["GPIOs"]["Shutdown_left"], config["GPIOs"]["Shutdown_right"]],
            ticks = 30)

output_funcs = {}

GPIO.setmode(GPIO.BCM)

gpios_in = []

for name, func in input_funcs.items():
    for gpio in func.GPIOs:
        logger.debug("Adding GPIO {g} for {n} functionality.".format(g = gpio, n = name))
        gpios_in.append(gpio)

gpios_in = set(gpios_in)
state = {}
try:
    for gpio in gpios_in:
        logger.debug("Setting up GPIO {g} as input.".format(g = gpio))
        GPIO.setup(gpio, GPIO.IN)
        state[gpio] = 0

    # Main Loop
    while(True):
        for gpio in gpios_in:
            if(GPIO.input(gpio)):
                state[gpio] += 1
            else:
                state[gpio] = 0
    
        # Inputs
        for name, func in input_funcs.items():
            if(func.enabled and all(state[gpio] > func.ticks for gpio in func.GPIOs)):
                logger.info("{n} triggered.".format(n = name))
                func.action()
                func.disable()
            elif(not func.enabled and all(state[gpio] == 0 for gpio in func.GPIOs)):
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