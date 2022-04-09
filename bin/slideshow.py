#!/usr/bin/python

import pi3d
import time
import sys
import random

from PIL import Image # these are needed for getting exif data from images
from threading import Thread

class Slideshow():
    FPS = 30
    FADE_TIME = 1
    TIME_PER_SLIDE = 5
    
    last_dir_change = 0
    last_dir_update = 0
    last_slide_change = 0
    slide = None
    
    im_current = None
    
    def get_pic_list(self):       
        flist = ["01.jpg","02.jpg","03.jpg"]
        self.last_dir_update = time.time()
        random.shuffle(flist)
        return flist
    
    def get_pic(self):
        files = self.get_pic_list()
        while(True):
            if(len(files) == 0 or self.last_dir_change > self.last_dir_update):
                files = self.get_pic_list()
            yield files.pop()
        
    def load_pic(self,fname):
        im = Image.open(fname)
        im.putalpha(255) # this will convert to RGBA and set alpha to opaque
        tex = pi3d.Texture(im, blend=True, m_repeat=True, automatic_resize=True, free_after_load=True)
        return tex
        
                   
    def __init__(self):
            
        sys.path.insert(1,'/home/pi/pi3d')
        self.DISPLAY = pi3d.Display.create(x=0, y=0,frames_per_second=self.FPS,
                                           display_config=pi3d.DISPLAY_CONFIG_HIDE_CURSOR,
                                           background=(0.2, 0.2, 0.2, 1.0))
        CAMERA = pi3d.Camera(is_3d=False)
        shader = pi3d.Shader("/home/pi/pi3d_demos/shaders/blend_new")
        
        self.slide = pi3d.Sprite(camera=CAMERA, w=self.DISPLAY.width, h=self.DISPLAY.height, z=5.0)
        self.slide.set_shader(shader)

        self.run()
        
        self.DISPLAY.destroy()
        
    def run(self):
        pic_gen = self.get_pic()
        delta_alpha = 1.0 / (self.FPS * self.FADE_TIME)
        while(self.DISPLAY.loop_running()):
            if(time.time() - self.last_slide_change > self.TIME_PER_SLIDE):
                self.show(next(pic_gen))
                alpha = 0
                self.last_slide_change = time.time()
            if(alpha < 1):
                self.slide.unif[44] = alpha
                alpha = alpha + delta_alpha
            self.slide.draw()
            
    def show(self,fname):
        im_next = self.load_pic(fname)
        im_current = self.im_current
        if(self.im_current is None):
            im_current = im_next
        #self.slide.set_textures([im_next, im_current])
        self.slide.set_textures([im_next])
        self.slide.unif[45:47] = self.slide.unif[42:44] # transfer front width and height factors to back
        self.slide.unif[51:53] = self.slide.unif[48:50] # transfer front width and height offsets
        wh_rat = (self.DISPLAY.height * im_next.ix) / (self.DISPLAY.width * im_next.iy) 
        self.slide.unif[43] = wh_rat
        self.slide.unif[42] = 1.0
        self.slide.unif[49] = (wh_rat - 1.0) * 0.5
        self.slide.unif[48] = 0.0
        self.im_current = im_next

        
        
ss = Slideshow()

