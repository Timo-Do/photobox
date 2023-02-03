#!/home/pi/venvs/photobox/bin/python
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

os.environ["DISPLAY"] = ":0.0"

logger = assets.tools.get_logger("SLIDESHOW")
config = assets.config.load()
DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
REACTION_TIME = 0.1

def subtract_lists(list1, list2):
    return list(set(list1) - set(list2))

class Slideshow():

    # SCREEN_TIME = 5000
    # FPS = 30
    # TRANSITION_SPEED = 0.02
    # SCREEN_WIDTH = 1920
    # SCREEN_HEIGHT = 1080
    IMAGE_PATH = config["Slideshow"]["ImagePath"]
    SCREEN_TIME = config["Slideshow"]["Screen_Time"]
    TRANSIT_TIME = config["Slideshow"]["Transit_Time"]
    FPS = config["Slideshow"]["FPS"]
    SCREEN_WIDTH = config["Slideshow"]["SCREEN_WIDTH"]
    SCREEN_HEIGHT = config["Slideshow"]["SCREEN_HEIGHT"]
    TRANSIT_SPEED = 1 / (TRANSIT_TIME * FPS)
    DEFAULT_IMAGES = os.path.join(DIR, "assets", "SCREENSAVER")
    SCREEN_RATIO = SCREEN_WIDTH / SCREEN_HEIGHT
    SCREEN_NAME = "Slideshow"
    
    index = 0
    running = True
    current_image = None
    images = []
    seen_image_list= []
    last_image_list = []

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

    def get_list(self, path):
        image_list = []
        for search_term in ["*.JPG", "*.jpg", "*.PNG", "*.png"]:
            image_list.extend(glob.glob(os.path.join(path, search_term)))
        return image_list

    def get_image_list(self):
        return self.get_list(self.IMAGE_PATH)

    def get_default_image_list(self):
        return self.get_list(self.DEFAULT_IMAGES)

    def transit_to_image(self, image, state):
        if(self.current_image is not None):
            current_alpha = 0
            transit_start = self.current_image
            while(current_alpha < 1 and (self.running == state)):
                transition_image = cv2.addWeighted(
                    transit_start, 1 - current_alpha,
                    image, current_alpha, 0)
                current_alpha += self.TRANSIT_SPEED
                self.current_image = transition_image
                cv2.imshow(self.SCREEN_NAME, transition_image)
                cv2.waitKey(int(1000/self.FPS))

    def show_image(self, image, state):
        if(self.running == state):
            self.current_image = image
            cv2.imshow(self.SCREEN_NAME, self.current_image)
            cv2.waitKey(1)
        tshown = 0
        while(tshown < self.SCREEN_TIME and (self.running == state)):
            time.sleep(REACTION_TIME)
            tshown += REACTION_TIME

    def get_random_default_image_path(self):
        default = random.choice(os.listdir(self.DEFAULT_IMAGES))
        return os.path.join(self.DEFAULT_IMAGES, default)

    def get_list_to_pick_from(self, state):
        if(state):
            new_image_list = self.get_image_list()
            if(not new_image_list):
                logger.debug("No images found in directory.")
                list_to_pick_from = self.get_default_image_list()
            else: 
                brand_new_images = subtract_lists(new_image_list, self.last_image_list)
                if(not brand_new_images):
                    logger.debug("Found no new images in directory.")
                    list_to_pick_from = new_image_list
                else:
                    logger.debug("Found new images in directory.")
                    list_to_pick_from = brand_new_images
        else:
            list_to_pick_from = self.get_default_image_list()

        self.last_image_list = new_image_list
        
        return list_to_pick_from

    def Watcher(self):
        while(True):
            if(networking.get_command("TOGGLESCREEN")):
                logger.debug("New TOGGLESCREEN command received.")
                if(self.running):
                    logger.debug("Switching off display")
                else:
                    logger.debug("Switching on display")
                self.running = not self.running
            time.sleep(REACTION_TIME)

    def __init__(self):
        logger.info("Starting up.")
        logger.debug("Initializing window.")
        cv2.namedWindow(self.SCREEN_NAME, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(self.SCREEN_NAME,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
        logger.debug("Loading image list.")
        logger.debug("Starting up initial Screensaver.")
        default_image_path = self.get_random_default_image_path()
        default_image = self.load_image(default_image_path)
        self.show_image(default_image, self.running)
        logger.debug("Starting up Watcher.")
        watcher_thread = threading.Thread(target=self.Watcher, args=(), daemon=True)
        watcher_thread.start()
        self._main_loop()

    def _main_loop(self):
        logger.info("Starting main loop.")
        while(True):
            state = self.running
            list_to_pick_from = self.get_list_to_pick_from(state = state)
            unseen_images = subtract_lists(list_to_pick_from, self.seen_image_list)
            if(not unseen_images):
                logger.debug("All pictures have been shown, beginning new set.")
                self.seen_image_list = []
                unseen_images = list_to_pick_from
            image_path = random.choice(unseen_images)
            logger.debug("Picked {img} for display.".format(img = image_path))
            try:
                image = self.load_image(image_path)
            except Exception as e:
                logger.error("Could not load image {img}: {err}".format(img = image_path, err = e.msg))
                image = self.load_image(self.get_random_default_image_path())
            
            self.seen_image_list.append(image_path)
            self.transit_to_image(image, state)
            self.show_image(image, state)

Slideshow()