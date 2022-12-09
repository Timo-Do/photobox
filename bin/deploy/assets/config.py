import configparser
import os
import tools
import shutil

logger = tools.get_logger("CONFIG")

PATH = "/home/timo/Projects/photobox/CONFIG"

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

config["Slideshow"] = {}
config["Slideshow"]["Enabled"] = bool
config["Slideshow"]["ImagePath"] = str
config["Slideshow"]["ScreenTime"] = float
config["Slideshow"]["FPS"] = int
config["Slideshow"]["TRANSITION_SPEED"] = float
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
if __name__ == "__main__":
    # Init Config
    logger.debug("Initializing new Config.")
    new_config  = configparser.ConfigParser()
    for section in config:
        new_config[section] = {}
        for key, value in config[section].items():
            new_config[section][key] = init_values[value]
    with open(PATH, "w") as configfile:
        new_config.write(configfile)


