# Import of the library
import face_recognition
import cv2
from onvif import ONVIFCamera
import zeep
import math
from time import sleep
from imutils.video import VideoStream
import imutils

# Функция для корректной работы onvif
def zeep_pythonvalue(self, xmlvalue):
	return xmlvalue
zeep.xsd.simple.AnySimpleType.pythonvalue = zeep_pythonvalue

# Camera connection
video_capture = VideoStream(src="rtsp://192.168.15.43:554/Streaming/Channels/1").start()

face_locations = []
i = 0
cam = ONVIFCamera('192.168.15.43', '80', 'admin', 'Supervisor')
media = cam.create_media_service()
ptz = cam.create_ptz_service()
token = media.GetProfiles()[0].token
print("token", token)

#Getting zoom parameters
zoomX = ptz.GetStatus(token)['Position']['Zoom']['x']
zoomMultiplier = round(1.01 - zoomX, 2) + 0.85
if zoomMultiplier > 1:
    zoomMultiplier = 1
zoomMultiplierY = round(1.15 - zoomX, 2) 
if zoomMultiplierY > 1:
    zoomMultiplierY = 1

# Confines of stable zones
req = {'Velocity': {'Zoom': {'space': '', 'x': '0'}, 'PanTilt': {'space': '', 'y': 0, 'x': 0}}, 'ProfileToken': token, 'Timeout': None}

sFrame = video_capture.read()
width = int(sFrame.shape[1])
height = int(sFrame.shape[0])


safeZx = int(width*0.08)
safeZy = int(height*0.2)

widthSafeL = int(width*0.33)
widthSafeR = int(width*0.66)
heightSafe = int(height*0.5)
widthSafeMin = int(width*0.33 - safeZx)
widthSafeMax = int(width*0.33 + safeZx)
widthSafeMinR = int(width*0.66 - safeZx)
widthSafeMaxR = int(width*0.66 + safeZx) 
heightSafeMin = int(height*0.5 - safeZy)
heightSafeMax = int(height*0.5 + safeZy)
a = ((widthSafeMin * 0.2) / (width - widthSafeMax)) 

# Camera motion function
# Функция рассчитывает движение камеры в зависимости от координат центра лица на полученном кадре
# ptz - объект-сервис камеры для ее движения
# request - переменная для значений скорости
# x, y - численные значения координат центра лица человека по x и y
# width - численное значение ширины всего кадра
# height - численное значение высоты всего кадра
# timeout - численное значение задержки после обработки одного кадра
def mov_to_face(ptz, request, x, y, width, height, speed_kof = 1, timeout=0):

    if (x <= (widthSafeMax) and x >= (widthSafeMin)):
        request['Velocity']['PanTilt']['x'] = 0
        print("no need to move, left!")
        if (y > heightSafeMin) and (y < heightSafeMax):
            request['Velocity']['PanTilt']['y'] = 0
            print('no need to move up or down = ', request['Velocity']['PanTilt']['y'])
        elif (y >= heightSafeMax):
            request['Velocity']['PanTilt']['y'] = -1 * zoomMultiplierY * (round(((y - heightSafe) / (height - heightSafe)), 2))
            print('need to move down = ', request['Velocity']['PanTilt']['y'])
        elif (y <= heightSafeMin):
            request['Velocity']['PanTilt']['y'] = zoomMultiplierY * (round(((heightSafe - y) / heightSafe), 2))
            print('need to move up = ', request['Velocity']['PanTilt']['y'])
    elif (x >= (widthSafeMinR) and x <= (widthSafeMaxR)):
        request['Velocity']['PanTilt']['x'] = 0
        print("no need to move, right!")
        if (y > heightSafeMin) and (y < heightSafeMax):
            request['Velocity']['PanTilt']['y'] = 0
            print('no need to move up or down = ', request['Velocity']['PanTilt']['y'])
        elif (y >= heightSafeMax):
            request['Velocity']['PanTilt']['y'] = -1 * zoomMultiplierY * (round(((y - heightSafe) / (height - heightSafe)), 2))
            print('need to move down = ', request['Velocity']['PanTilt']['y'])
        elif (y <= heightSafeMin):
            request['Velocity']['PanTilt']['y'] = zoomMultiplierY * (round(((heightSafe - y) / heightSafe), 2))
            print('need to move up = ', request['Velocity']['PanTilt']['y'])
    elif x>widthSafeMaxR:
        request['Velocity']['PanTilt']['x'] = 0.2 * zoomMultiplier * round(((x - widthSafeR) / (width - widthSafeR)), 2)
        print("right = ", request['Velocity']['PanTilt']['x'])
    elif x<widthSafeMin:
        request['Velocity']['PanTilt']['x'] = a * zoomMultiplier * round((x - widthSafeL) / widthSafeL, 2)
        print("left = ", request['Velocity']['PanTilt']['x'])
    elif x>widthSafeMax and x < widthSafeMinR:
        request['Velocity']['PanTilt']['x'] = 0.2 * zoomMultiplier * round(((x - widthSafeL) / (width - widthSafeL)), 2)
        print("between = ", request['Velocity']['PanTilt']['x'])
    ptz.ContinuousMove(request)
    sleep(timeout)
    

# Frame processing 
while True:
    frame = video_capture.read()
    # Resize frame of video to 1/4 size for faster face detection processing
    try:
        small_frame = imutils.resize(frame,  width=int(width/4))
    except:
        print("empty frame!")
    
    # Find face locations
    face_locations = face_recognition.face_locations(small_frame)
    
    print("face locations = ", str(face_locations))
    
    for top, right, bottom, left in face_locations:
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Extract the region of the image that contains the face

        x = int(left + (right - left) / 2)
        y = int(top + (bottom - top) / 2)
        mov_to_face(ptz, req, x, y, width, height, 0.5, 0)

        # Draw rectangle over the face
        cv2.rectangle(frame, (left, top), (right, bottom), (255,0,0), 2)
        
    if not face_locations:
        i += 1
    else:
        i = 0
    
    if i == 10:
        ptz.Stop(token)

    # Visualization of the confines of stable zones
    cv2.rectangle(frame, (widthSafeMin, heightSafeMin), (widthSafeMax, heightSafeMax), (0,255,0), 2)
    cv2.rectangle(frame, (widthSafeMinR, heightSafeMin), (widthSafeMaxR, heightSafeMax), (0,255,0), 2)
    
    # Display the resulting image
    cv2.imshow('Video', frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        ptz.Stop(token)
        break

video_capture.release()
cv2.destroyAllWindows()
