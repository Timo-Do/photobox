import configparser
import os
from assets import tools
import shutil

logger = tools.get_logger("CONFIG")

if("PWFB_CONFIG" in os.environ):
    PATH = os.environ["PWFB_CONFIG"]
else:
    PATH = os.path.join("/", "home", "pi", "photobox", "CONFIG")

bool2str = {
    True  : "yes",
    False : "no" 
}
init_values = {
    int   : "<int>",
    str   : "<str>",
    bool  : "<yes/no>",
    float : "<float>"
}


config = {}
config["Basic"] = {}
config["Basic"]["Name"] = str
config["Basic"]["Deployment"] = bool

config["io"] = {}
config["io"]["Slideshow_Toggle"] = bool
config["io"]["Shutdown"] = bool
config["io"]["Shutter"] = bool
config["io"]["Status_LED"] = bool
config["io"]["Taster"] = bool
config["io"]["Countdown"] = bool

config["GPIOs"] = {}
config["GPIOs"]["Slideshow_Toggle"] = int
config["GPIOs"]["Shutdown_left"] = int
config["GPIOs"]["Shutdown_right"] = int
config["GPIOs"]["Shutter"] = int
config["GPIOs"]["Status_LED"] = int
config["GPIOs"]["Taster"] = int
config["GPIOs"]["cd_o"] = int
config["GPIOs"]["cd_ol"] = int
config["GPIOs"]["cd_or"] = int
config["GPIOs"]["cd_m"] = int
config["GPIOs"]["cd_ul"] = int
config["GPIOs"]["cd_ur"] = int
config["GPIOs"]["cd_u"] = int

config["SDCard"] = {}
config["SDCard"]["Reaction_Time"] = float
config["SDCard"]["MountPoint"] = str
config["SDCard"]["DirName"] = str

config["Shutdown"] = {}
config["Shutdown"]["Enabled"] = bool

config["Slideshow"] = {}
config["Slideshow"]["Enabled"] = bool
config["Slideshow"]["ImagePath"] = str
config["Slideshow"]["Screen_Time"] = float
config["Slideshow"]["FPS"] = int
config["Slideshow"]["Transit_Time"] = float
config["Slideshow"]["SCREEN_WIDTH"] = int
config["Slideshow"]["SCREEN_HEIGHT"] = int

def restore():
    logger.debug("Reloading Config")
    shutil.copyfile(PATH + ".default", PATH)

def load():
    logger.debug("Loading Config")
    if(not os.path.exists(PATH)):
        raise FileNotFoundError("No config file found at {p}.".format(p = PATH))
    loaded_config = configparser.ConfigParser()
    loaded_config.read(PATH)
    output_config = {}
    for section in config:
        output_config[section] = {}
        for key, dtype in config[section].items():
            if(dtype == str):
                output_config[section][key] = loaded_config[section][key]
            elif(dtype == int):
                output_config[section][key] = loaded_config[section].getint(key)
            elif(dtype == float):
                output_config[section][key] = loaded_config[section].getfloat(key)
            elif(dtype == bool):
                output_config[section][key] = loaded_config[section].getboolean(key)

    return output_config
def init():
    logger.debug("Initializing new Config.")
    new_config  = configparser.ConfigParser()
    for section in config:
        new_config[section] = {}
        for key, value in config[section].items():
            new_config[section][key] = init_values[value]
    with open(PATH, "w") as configfile:
        new_config.write(configfile)



