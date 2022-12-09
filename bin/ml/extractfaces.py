import cv2
import numpy as np
from matplotlib import pyplot as plt
import pathlib
import glob
import os

from assets.face_detection.yunet import YuNet

SET = "kaggle"
SOURCE = "../data/full/"
TARGET = "../data/new/"
SIZE = 64

dir = os.path.dirname(__file__)
model = os.path.join(dir, "assets", "face_detection", "face_detection_yunet_2022mar.onnx")

model = YuNet(modelPath=model,
                  confThreshold=0.9,
                  nmsThreshold=0.3,
                  topK=5000,
                  backendId=cv2.dnn.DNN_BACKEND_OPENCV,
                  targetId=cv2.dnn.DNN_TARGET_CPU)


source_dir = os.path.join(dir, SOURCE, SET)
target_dir = os.path.join(dir, TARGET, SET)

num_file = 0
for path in pathlib.Path(source_dir).glob("*.*"):
    num_file += 1
    print("Reading image {n:5d} ({im})...".format(n = num_file, im = path))
    if(len(glob.glob(os.path.join(target_dir, path.stem + "*"))) > 0):
        print("File {im} has already been processed.".format(im = path))
    else:
        frame = cv2.imread(str(path))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
        model.setInputSize(frame.shape[1::-1])
        results = model.infer(frame)

        #for (fX, fY, fW, fH) in rects:
        if(results is None): results = []
        faces = 0
        smiles = 0
        for result in results:
            fX, fY, fW, fH = result[0:4].astype(np.int32)
            roi = frame[fY:fY + fH, fX:fX + fW]
            if(fW > SIZE and fH > SIZE and fX > 0 and fY > 0):
                roi = gray[fY:fY + fH, fX:fX + fW]
                roi = cv2.resize(roi, (SIZE, SIZE))
                filename = path.stem + "_{:02d}".format(faces) + ".jpg"
                save_path = os.path.join(target_dir, filename)
                cv2.imwrite(save_path, roi)
                faces += 1




