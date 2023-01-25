# photobox
Hi y'all,

this piece of code is going to be a photobox software package. The main feature is a smile based trigger which is based on the dataset of [Hromada, 2010](https://github.com/hromi/SMILEsmileD). I'm extending that tho.

For face detection I use YuNet from https://github.com/opencv/opencv_zoo. It works like a charm :)

Work is still in progress and I have not cleaned up my code in a while, but I'll get to that eventually.

Timo :)


In case you are serious about installing this piece of software, here are a couple of things you might want to install:

cv2 (duh)
tflite_runtime
unclutter (for removing the cursor, put that into your crontab)


## config

raspi: visudo -> mount no passwd
udev: udev rule to add usbtop