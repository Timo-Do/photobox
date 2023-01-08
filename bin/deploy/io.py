import RPi.GPIO as GPIO
import time
import networking
import assets.config

class Functionality():
    def __init__(self, name, on_trigger, GPIOs, act_ticks = 10):
        self.name = name
        self.enabled = True
        self.GPIOs = GPIOs
        self.on_trigger = on_trigger
        self.act_ticks = act_ticks

logger = assets.tools.get_logger("IO")
config = assets.config.load()

funcs = []

if(config["IO"]["Slideshow_Toggle"]):
    funcs.append(
        Functionality("Slideshow Toggle", "TOGGLESCREEN",
        [config["Slideshow"]["GPIO_TOGGLE"]])
    )

if(config["IO"]["Shutdown"]):   
    funcs.append(
        Functionality("Shutdown", "SHUTDOWN",
            [config["Shutdown"]["GPIO_LEFT"], config["Shutdown"]["GPIO_RIGHT"]],
            act_ticks = 30)
    )


GPIO.setmode(GPIO.BCM)

gpios_in = []

for func in funcs:
    for gpio in func.GPIOs:
        logger.debug("Adding GPIO {g} for {n} functionality.".format(g = gpio, n = func.name))
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
        for func in funcs:
            if(all(state[gpio] > func.act_ticks for gpio in func.GPIOs)):
                if(func.enabled):
                    logger.info("{n} triggered.".format(n = func.name))
                    networking.command(func.on_trigger)
                    func.enabled = False
            elif(all(state[gpio] == 0 for gpio in func.GPIOs)):
                logger.debug("Resetting {n}.".format(n = func.name))
                func.enabled = True
        

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