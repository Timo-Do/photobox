import tflite_runtime.interpreter as tflite
import cv2
import numpy as np
import time

face_detection = cv2.CascadeClassifier("face_detection.xml")

interpreter = tflite.Interpreter("model_32_lite")
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
interpreter.allocate_tensors()


camera = cv2.VideoCapture(0)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

last_frame = time.time()
while True:
    # grab the current frame
    (grabbed, frame) = camera.read()
    #frame = imutils.resize(frame, width=300)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frameClone = frame.copy()

    rects = face_detection.detectMultiScale(gray, scaleFactor=1.2, 
        minNeighbors=5, minSize=(32, 32),
        flags=cv2.CASCADE_SCALE_IMAGE)

    for (fX, fY, fW, fH) in rects:
        roi = gray[fY:fY + fH, fX:fX + fW]
        roi = cv2.resize(roi, (32, 32))
        roi = roi.astype("float32") / 255.0
        
        #roi = tf.keras.preprocessing.image.img_to_array(roi)
        roi = np.array([np.expand_dims(roi, axis=2)])

        interpreter.set_tensor(input_details[0]['index'], roi)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])

        smile = output_data[0][0]
        
        if(smile > 0):
            label = "smiling"
            color = (0, 255, 0)
        else:
            label = "not_smiling"
            color = (0, 0, 255)
        
        cv2.putText(frameClone, label + " ({:.4f})".format(smile), (fX, fY - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
        cv2.rectangle(frameClone, (fX, fY), (fX + fW, fY + fH),
            color, 2)
        fps = 1/(time.time() - last_frame)
        print(np.round(fps,3), end="\r")
    # show our detected faces along with smiling/not smiling labels
    #cv2.imshow("Face", frameClone)
    # if the 'q' key is pressed, stop the loop
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# cleanup the camera and close any open windows
camera.release()
cv2.destroyAllWindows()
