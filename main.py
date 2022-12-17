import threading
import time
import tkinter as tk
from collections import deque

import cv2
import numpy as np
from PIL import ImageTk, Image

from config import CAMERA_URL
from utils.common import Singleton, synchronized
from utils.image import resize_image


class Camera(metaclass=Singleton):
    camera = None
    prev_frame_time = 0
    recent_frame_count = 10
    recent_frame_time = deque([0.0], maxlen=recent_frame_count)
    fps = 0

    def __init__(self):
        self.connect()

    @synchronized
    def read(self) -> tuple[bool, np.ndarray]:
        # Capture frame-by-frame

        ret, frame = self.camera.read()

        # if video finished or no Video Input
        if not ret:
            return ret, frame

        # time when we finish processing for this frame
        new_frame_time = time.perf_counter()

        # Calculating the fps

        # fps will be number of frame processed in given time frame
        # since their will be most of time error of 0.001 second
        # we will be subtracting it to get more accurate result
        self.fps = 1 / ((new_frame_time - self.recent_frame_time[0]) / self.recent_frame_count)
        self.recent_frame_time.append(new_frame_time)
        self.prev_frame_time = new_frame_time

        return ret, frame

    @synchronized
    def connect(self) -> None:
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
    def reconnect(self) -> None:
        self.camera.release()
        self.connect()

    @synchronized
    def release(self) -> None:
        print('Camera releasing...')
        self.camera.release()


class ClientApp:
    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.title('VideoCaptureStreamDemo')
        self.main_window.geometry('800x600')
        self.main_window.protocol('WM_DELETE_WINDOW', lambda: self.main_window.destroy())

        # 狀態列
        self.status_text = tk.StringVar()
        self.status_text.set('Ready')
        status_bar = tk.Label(self.main_window, textvariable=self.status_text, relief=tk.SUNKEN, anchor='w', width=1)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.preview_label = tk.Label(text='Starting...')
        self.preview_label.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        self.video_looper = self.VideoLooper(app=self)

    def run(self) -> None:
        self.main_window.mainloop()

    def stop(self) -> None:
        self.video_looper.stop()
        # 正常離開時，已 destroy，若再次呼叫，會拋出 TclError: can't invoke "destroy" command: application has been destroyed，故以 try...except 的方式忽略
        try:
            self.main_window.destroy()
        except tk.TclError:
            pass

    class VideoLooper(threading.Thread):
        is_running: bool = False
        camera = None

        def __init__(self, app: 'ClientApp'):
            self.is_running = True
            threading.Thread.__init__(self)
            self.app = app
            self.daemon = True
            self.camera = Camera()
            self.start()

        def run(self) -> None:
            if not self.is_running:
                return
            self.video_loop()
            threading.Timer(0, self.run).start()

        def video_loop(self) -> None:
            preview_label = self.app.preview_label
            ret, img = self.camera.read()
            if not ret and self.is_running:
                preview_label.img_tk = None
                preview_label.config(image='', text='Disconnected. Trying to reconnect...')
                self.camera.reconnect()
                return

            self.app.status_text.set(f'FPS: {self.camera.fps:.2f}')

            limit_width = preview_label.winfo_width()
            limit_height = preview_label.winfo_height()
            img = resize_image(img, limit_width, limit_height)

            cv2image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            current_image = Image.fromarray(cv2image)

            img_tk = ImageTk.PhotoImage(image=current_image)
            preview_label.config(image=img_tk)
            preview_label.img_tk = img_tk

        def stop(self) -> None:
            self.is_running = False
            self.camera.release()
            self.join()
            print('CameraLooper stopped')


if __name__ == "__main__":
    app = ClientApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print('KeyboardInterrupt detected, exiting...')
    finally:
        app.stop()
