import assets.config
import assets.tools

import cv2
import os
import random
import glob
import sys
import networking
import time
import threading

logger = assets.tools.get_logger("SLIDESHOW")
config = assets.config.load()
DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
REACTION_TIME = 0.1

class Slideshow():

    # SCREEN_TIME = 5000
    # FPS = 30
    # TRANSITION_SPEED = 0.02
    # SCREEN_WIDTH = 1920
    # SCREEN_HEIGHT = 1080
    IMAGE_PATH = os.path.join(config["Slideshow"]["ImagePath"], "*.JPG")
    SCREEN_TIME = int(config["Slideshow"]["ScreenTime"] * 1000)
    FPS = config["Slideshow"]["FPS"]
    TRANSITION_SPEED = config["Slideshow"]["TRANSITION_SPEED"] / 50
    SCREEN_WIDTH = config["Slideshow"]["SCREEN_WIDTH"]
    SCREEN_HEIGHT = config["Slideshow"]["SCREEN_HEIGHT"]

    DEFAULT_IMAGE = os.path.join(DIR, "assets", "DEFAULT.png")
    SCREEN_RATIO = SCREEN_WIDTH / SCREEN_HEIGHT
    SCREEN_NAME = "Slideshow"
    
    index = 0
    running = True

    def load_image(self, src):
        img = cv2.imread(src)
        h, w = img.shape[:2]
        new_h = round(self.SCREEN_WIDTH * h / w)
        img = cv2.resize(img, (self.SCREEN_WIDTH, new_h), interpolation=cv2.INTER_LINEAR)
    
        if(new_h > self.SCREEN_HEIGHT):
            crop_upper = round((new_h - self.SCREEN_HEIGHT)/2)
            crop_lower = new_h - crop_upper - self.SCREEN_HEIGHT
            img = img[crop_upper:-crop_lower, :]
        return img

    def get_image_list(self):
        image_list = glob.glob(self.IMAGE_PATH)
        random.shuffle(image_list)
        self.image_list = image_list

    def update_image_list(self):
        new_image_list = glob.glob(self.IMAGE_PATH)
        new_images = [im for im in new_image_list if im not in self.image_list]
        for idx, new_image in enumerate(new_images):
            self.image_list.insert(self.index + idx + 1, new_image)

    def next_image(self, new_image):
        next_image = self.load_image(new_image)
        current_alpha = 0
        while(current_alpha < 1 and self.running):
            transition_image = cv2.addWeighted(
                self.current_image, 1 - current_alpha,
                next_image, current_alpha, 0)
            current_alpha += self.TRANSITION_SPEED
            cv2.imshow(self.SCREEN_NAME, transition_image)
            cv2.waitKey(int(1000/self.FPS))
        self.current_image = next_image
        if(self.running):
            cv2.imshow(self.SCREEN_NAME, self.current_image)
            cv2.waitKey(self.SCREEN_TIME)

    def display_default(self):
        default = self.load_image(self.DEFAULT_IMAGE)
        cv2.imshow(self.SCREEN_NAME, default)
        self.current_image = default
        cv2.waitKey(1)

    def Watcher(self):
        while(True):
            if(networking.get_command("TOGGLESCREEN")):
                logger.debug("New TOGGLESCREEN command received.")
                self.running = not self.running
                if(not self.running):
                    logger.debug("Switching off display")
                else:
                    logger.debug("Switching on display")
            time.sleep(REACTION_TIME)

    def __init__(self):
        logger.info("Starting up.")
        logger.debug("Initializing window.")
        cv2.namedWindow(self.SCREEN_NAME)
        cv2.setWindowProperty(self.SCREEN_NAME,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
        logger.debug("Loading image list.")
        self.images = self.get_image_list()
        logger.debug("Starting up Screensaver.")
        self.display_default()
        cv2.waitKey(self.SCREEN_TIME)
        logger.debug("Starting up Watcher.")
        watcher_thread = threading.Thread(target=self.Watcher, args=())
        watcher_thread.start()
        self._main_loop()

    def _main_loop(self):
        logger.info("Starting main loop.")
        while(True):
            if(not self.running):
                self.display_default()
                cv2.waitKey(1)
                time.sleep(REACTION_TIME)
            else:
                self.index += 1
                logger.debug("Updating image list.")
                self.update_image_list()
                if(self.index == len(self.image_list)):
                    logger.debug("Loading new set of images.")
                    self.index = 0
                    self.get_image_list()
                logger.debug("Displaying image #{i}".format(i = self.index))
                self.next_image(self.image_list[self.index])

Slideshow()