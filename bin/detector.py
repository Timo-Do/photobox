import tensorflow as tf
import cv2
import numpy as np

face_detection = cv2.CascadeClassifier("bin/face_detection.xml")

smile_detection = tf.keras.models.load_model("bin/model_32")

camera = cv2.VideoCapture(0)

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
        roi = roi.astype("float") / 255.0
        roi = tf.keras.preprocessing.image.img_to_array(roi)
        roi = np.expand_dims(roi, axis=0)

        smile = tf.math.sigmoid(smile_detection.predict(roi)[0][0])
        smile = smile.numpy()
        
        if(smile > 0.5):
            label = "smiling"
            color = (0, 255, 0)
        else:
            label = "not_smiling"
            color = (0, 0, 255)
        
        cv2.putText(frameClone, label + " ({:.4f})".format(smile), (fX, fY - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
        cv2.rectangle(frameClone, (fX, fY), (fX + fW, fY + fH),
            color, 2)

    # show our detected faces along with smiling/not smiling labels
    cv2.imshow("Face", frameClone)
    # if the 'q' key is pressed, stop the loop
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# cleanup the camera and close any open windows
camera.release()
cv2.destroyAllWindows()