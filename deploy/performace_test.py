import tflite_runtime.interpreter as tflite
import cv2
import numpy as np
import time
import imutils

HEADLESS = False

from yunet import YuNet
model = YuNet(modelPath="face_detection_yunet_2022mar.onnx",
                  inputSize=[320, 320],
                  confThreshold=0.9,
                  nmsThreshold=0.3,
                  topK=5000,
                  backendId=cv2.dnn.DNN_BACKEND_OPENCV,
                  targetId=cv2.dnn.DNN_TARGET_CPU)

interpreter = tflite.Interpreter(model_path = "model_32_lite")
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
interpreter.allocate_tensors()



camera = cv2.VideoCapture(2)

#camera.set(cv2.CAP_PROP_FRAME_WIDTH, 426)
#camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

w = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
model.setInputSize([w, h])
last_frame = time.time()
while True:
    # grab the current frame
    (grabbed, frame) = camera.read()
    
    #frame = imutils.resize(frame, width=900)
    
    frameClone = frame.copy()

    #rects = face_detection.detectMultiScale(gray, scaleFactor=1.2, 
    #    minNeighbors=5, minSize=(32, 32),
    #    flags=cv2.CASCADE_SCALE_IMAGE)
    results = model.infer(frame)

    #for (fX, fY, fW, fH) in rects:
    if(results is None): results = []
    faces = 0
    smiles = 0
    for result in results:
        faces = faces + 1
        fX, fY, fW, fH = result[0:4].astype(np.int32)
        
        roi = frame[fY:fY + fH, fX:fX + fW]
        if(np.prod(roi.shape) > 0):
            roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            #roi = tf.keras.preprocessing.image.img_to_array(roi)
            roi = cv2.resize(roi, (32, 32))
            roi = roi.astype("float32") / 255.0
            roi = np.array([np.expand_dims(roi, axis=2)])

            interpreter.set_tensor(input_details[0]['index'], roi)
            interpreter.invoke()
            output_data = interpreter.get_tensor(output_details[0]['index'])

            smile = output_data[0][0]
            
            if(smile > 0):
                label = "smiling"
                smiles = smiles + 1
                color = (0, 255, 0)
            else:
                label = "not_smiling"
                color = (0, 0, 255)
            if(not HEADLESS):
                cv2.putText(frameClone, label + " ({:.4f})".format(smile), (fX, fY - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
                cv2.rectangle(frameClone, (fX, fY), (fX + fW, fY + fH),
                    color, 2)
    curr_time = time.time()
    fps = 1/(curr_time - last_frame)
    last_frame = curr_time
        
    # show our detected faces along with smiling/not smiling labels
    if(not HEADLESS):
        cv2.imshow("Face", frameClone)
    print("FPS: {fps} FACES: {faces} SMILING: {smiles}".format(
        fps = "{:.2f}".format(fps),
        faces = faces,
        smiles = smiles), end="\r")
    # if the 'q' key is pressed, stop the loop
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# cleanup the camera and close any open windows
camera.release()
cv2.destroyAllWindows()
