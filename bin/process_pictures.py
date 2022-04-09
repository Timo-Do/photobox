import cv2
import numpy as np
from matplotlib import pyplot as plt
import pathlib
import uuid

face_detection = cv2.CascadeClassifier("bin/face_detection.xml")

for path in pathlib.Path("data/full").rglob("*.*"):
    print("Reading image {im}...".format(im = path))

    frame = cv2.imread(str(path))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frameClone = gray.copy()

    rects = face_detection.detectMultiScale(gray, scaleFactor=1.3, 
        minNeighbors=5, minSize=(64, 64),
        flags=cv2.CASCADE_SCALE_IMAGE)

    for (fX, fY, fW, fH) in rects:
        roi = gray[fY:fY + fH, fX:fX + fW]
        roi = cv2.resize(roi, (64, 64))
        cv2.imwrite("data/new/" + str(uuid.uuid4()) + ".jpg",roi)
        
        color = (255, 0 ,0)
        cv2.rectangle(frameClone, (fX, fY), (fX + fW, fY + fH),
            color, 2)


    #plt.imshow(frameClone, cmap = "gray")
    #plt.show()
    

cv2.destroyAllWindows()
