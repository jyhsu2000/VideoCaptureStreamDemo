import functools
import os
import threading
from tkinter import *

import cv2
from PIL import ImageTk, Image

camera_url = 'http://127.0.0.1:56000/mjpeg'


class Singleton(type):
    __instances = {}
    __lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            with cls.__lock:
                if cls not in cls.__instances:
                    cls.__instances[cls] = super(
                        Singleton, cls).__call__(*args, **kwargs)
        return cls.__instances[cls]


def synchronized(wrapped):
    lock = threading.Lock()

    @functools.wraps(wrapped)
    def _wrap(*args, **kwargs):
        with lock:
            return wrapped(*args, **kwargs)

    return _wrap


class Camera(metaclass=Singleton):
    camera = None

    def __init__(self):
        global camera_url
        self.camera = cv2.VideoCapture(camera_url)
        print('Create VideoCapture')
        fps = self.camera.get(cv2.CAP_PROP_FPS)
        print(f'FPS: {fps}')

    @synchronized
    def read(self):
        return self.camera.read()

    @synchronized
    def reconnect(self):
        self.camera.release()
        self.camera = cv2.VideoCapture(camera_url)


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
