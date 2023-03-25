#!/home/pi/venvs/photobox/bin/python
import time
import imutils
import sys
import numpy as np
import cv2
import os
import ipc

import tflite_runtime.interpreter as tflite
from assets.yunet import YuNet

import assets.tools

os.environ["DISPLAY"] = ":0.0"

# --- CONFIG ---
# Show preview Window
DEPLOY = False
# Camera Resolution for Face Detection
FACE_DETECTION_RES_W = 400
FACE_DETECTION_RES_RATIO = 16/9
FACE_DETECTION_RES_H = int(np.round(FACE_DETECTION_RES_W / FACE_DETECTION_RES_RATIO))

# Maximum Index to look for devices
CAMERA_MAX_IDX = 10
# Face Resolution (model dependent!)
SMILE_EVALUATION_RES_W = 32
SMILE_EVALUATION_RES_H = 32
# Directory of script
DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
# ---
# --- Logging Config ---
logger = assets.tools.get_logger("SMILETRIGGER")
# ---
# --- IPC ---
messenger = ipc.Messenger()
# ---
logger.info("Starting up")
logger.info("Using {w}x{h} Resolution for Face Detection".format(
    w = FACE_DETECTION_RES_W,
    h = FACE_DETECTION_RES_H
))
# --- Loading ML Modules ---
# YuNet from opencv_zoo for face detection
modelPath = os.path.join(DIR, "assets", "face_detection_yunet_2022mar.onnx")
face_detection = YuNet(
    modelPath = modelPath,
    inputSize = [FACE_DETECTION_RES_W, FACE_DETECTION_RES_H],
    confThreshold = 0.9,
    nmsThreshold = 0.3,
    topK = 5000,
    backendId = cv2.dnn.DNN_BACKEND_OPENCV,
    targetId = cv2.dnn.DNN_TARGET_CPU)
logger.debug("Loaded YuNet for Face Detection successfully")
# Smile evaluation
modelPath = os.path.join(DIR, "assets", "model_32_lite")
smile_evaluation = tflite.Interpreter(model_path = modelPath)
smile_evaluation_input_details = smile_evaluation.get_input_details()
smile_evaluation_output_details = smile_evaluation.get_output_details()
smile_evaluation.allocate_tensors()
logger.debug("Loaded tflite Model for Smile Evaluation successfully")
# ---
# --- Finding the camera
# Looping over all camera devices, taking the first one which returns an image
bCamFound = False
idxCamera = 0
while(not bCamFound):
    camera = cv2.VideoCapture(idxCamera)
    (bCamFound, frame) = camera.read()
    if(not bCamFound):
        if(idxCamera < CAMERA_MAX_IDX):
            idxCamera += 1
        else:
            logger.error("No camera found (CAMERA_MAX_IDX = {idx} reached)".format(idx = idxCamera))
            sys.exit()


logger.info("Camera found on index {idx}".format(idx = idxCamera))
(input_height, input_width, _) = frame.shape
logger.debug("Camera Resolution: {w}x{h}".format(
    w = input_width, h = input_height
))
# Calculating "Zoom Level" for Smile Evaluation
w_zoom = FACE_DETECTION_RES_W / input_width
h_zoom = FACE_DETECTION_RES_H / input_height
logger.debug("Using Zoom level {w_z} (w) and {h_z} (h) for Smile Evaluation".format(
    w_z = np.round(1 / w_zoom, 2),
    h_z = np.round(1 / h_zoom, 2)
))
# --- Main Loop
bRun = True
logger.info("Starting image processing")
# Starting the clock for FPS measurement
last_frame = time.time()
while(bRun):
    # Get next image
    (grabbed, frame) = camera.read()
    # Shrink it for Face Detection
    frame_face_detection = imutils.resize(frame,
        width = FACE_DETECTION_RES_W, height = FACE_DETECTION_RES_H)
    # Make it Black and White for Smile Evaluation
    frame_smile_evaluation = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect Faces with YuNet
    faces = face_detection.infer(frame_face_detection)
    if(faces is None): faces = []
    num_faces = 0
    num_smiles = 0
    for face in faces:
        num_faces += 1
        fX, fY, fW, fH = face[0:4].astype(np.int32)
        # Make sure it is not a phantom face
        if(fW * fH > 0 and fX > 0 and fY > 0):
            # "Zoom" into the face
            fX_zoom = int(np.round(fX / w_zoom))
            fY_zoom = int(np.round(fY / h_zoom))
            fW_zoom = int(np.round(fW / w_zoom))
            fH_zoom = int(np.round(fH / h_zoom))
            # Extract Region of Interest (Face)
            roi = frame_smile_evaluation[
                fY_zoom:fY_zoom + fH_zoom,
                fX_zoom:fX_zoom + fW_zoom]
            # Resize Face for Input in Model
            roi = cv2.resize(roi, (SMILE_EVALUATION_RES_W, SMILE_EVALUATION_RES_H))
            # And make it fit for the model
            roi = roi.astype("float32") / 255.0
            roi = np.array([np.expand_dims(roi, axis=2)])
            # Infer Smile Evaluation
            smile_evaluation.set_tensor(smile_evaluation_input_details[0]['index'], roi)
            smile_evaluation.invoke()
            output_data = smile_evaluation.get_tensor(smile_evaluation_output_details[0]['index'])
            smile = output_data[0][0]
            # Check if smiling
            if(smile > 0):
                label = "smiling"
                num_smiles += 1
                color = (0, 255, 0)
            else:
                label = "not_smiling"
                color = (0, 0, 255)
            label += " ({:.4f})".format(smile)
            # Set up preview image
            if(not DEPLOY):
                cv2.rectangle(frame, (fX_zoom, fY_zoom),
                    (fX_zoom + fW_zoom, fY_zoom + fH_zoom),
                    color, 2)
                cv2.putText(frame, label, (fX_zoom, fY_zoom - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
    # Do FPS measurement
    this_frame = time.time()
    fps = 1/(this_frame - last_frame)
    last_frame = this_frame
    if(not DEPLOY):
        cv2.imshow("Debug View", frame)
        # Stop if ESC is pressed
        if cv2.waitKey(1) == 27: 
            bRun = False

        print("FACES: {faces} SMILING: {smiles} FPS: {fps} ".format(
            fps = "{:5.2f}".format(fps),
            faces = num_faces,
            smiles = num_smiles), end="\r")
        
    if(num_faces > 0 and num_smiles/num_faces >= 0.5):
        messenger.publish("SHUTTER", "SMILETRIGGER")

# ---