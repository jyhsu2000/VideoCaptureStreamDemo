import os
import threading
import time
from collections import deque
from tkinter import *

import cv2
from PIL import ImageTk, Image

from config import CAMERA_URL
from utils.common import Singleton, synchronized


class Camera(metaclass=Singleton):
    camera = None
    prev_frame_time = 0
    recent_frame_count = 10
    recent_frame_time = deque([0], maxlen=recent_frame_count)

    def __init__(self):
        self.connect()

    @synchronized
    def read(self):
        # Capture frame-by-frame

        ret, frame = self.camera.read()

        # if video finished or no Video Input
        if not ret:
            return ret, frame

        # font which we will be using to display FPS
        font = cv2.FONT_HERSHEY_SIMPLEX
        # time when we finish processing for this frame
        new_frame_time = time.time()

        # Calculating the fps

        # fps will be number of frame processed in given time frame
        # since their will be most of time error of 0.001 second
        # we will be subtracting it to get more accurate result
        fps = 1 / ((new_frame_time - self.recent_frame_time[0]) / self.recent_frame_count)
        self.recent_frame_time.append(new_frame_time)
        self.prev_frame_time = new_frame_time

        # putting the FPS count on the frame
        cv2.putText(frame, f'{fps:.2f}', (7, 70), font, 3, (100, 255, 0), 3, cv2.LINE_AA)

        return ret, frame

    @synchronized
    def connect(self):
        self.camera = cv2.VideoCapture(CAMERA_URL)
        print('VideoCapture created')

        # self.camera.set(cv2.CAP_PROP_SETTINGS, 1)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        self.camera.set(cv2.CAP_PROP_FPS, 60)

        width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = self.camera.get(cv2.CAP_PROP_FPS)
        print(f'Resolution: {width} * {height}')
        print(f'FPS: {fps}')

    @synchronized
    def reconnect(self):
        self.camera.release()
        self.connect()


def resize_image(img, limit_width, limit_height):
    if limit_width <= 0:
        limit_width = 20
    if limit_height <= 0:
        limit_height = 20
    height, width = img.shape[:2]
    if limit_width / width < 1 or limit_height / height < 1:
        ratio = min(limit_width / width, limit_height / height)
        width, height = max(int(width * ratio), 1), max(int(height * ratio), 1)
        img = cv2.resize(img, (width, height))
    return img


class ClientApp:
    def __init__(self):
        self.main_window = Tk()
        self.main_window.title('VideoCaptureStreamDemo')
        self.main_window.geometry('800x600')
        self.main_window.protocol('WM_DELETE_WINDOW', lambda: os._exit(0))

        self.preview_label = Label(text='Starting...')
        self.preview_label.pack(fill=BOTH, expand=YES)

        self.VideoLooper(app=self)

    def run(self):
        self.main_window.mainloop()

    class VideoLooper(threading.Thread):
        camera = None

        def __init__(self, app):
            threading.Thread.__init__(self)
            self.app = app
            self.daemon = True
            self.camera = Camera()
            self.start()

        def run(self):
            self.video_loop()
            threading.Timer(0, self.run).start()

        def video_loop(self):
            preview_label = self.app.preview_label
            ret, img = self.camera.read()
            if not ret:
                preview_label.img_tk = None
                preview_label.config(
                    image='', text='Disconnected. Trying to reconnect...')
                self.camera.reconnect()
                return

            limit_width = preview_label.winfo_width()
            limit_height = preview_label.winfo_height()
            img = resize_image(img, limit_width, limit_height)

            cv2image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            current_image = Image.fromarray(cv2image)

            img_tk = ImageTk.PhotoImage(image=current_image)
            preview_label.config(image=img_tk)
            preview_label.img_tk = img_tk


if __name__ == "__main__":
    app = ClientApp()
    app.run()
