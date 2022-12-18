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
        self.camera = cv2.VideoCapture(CAMERA_URL, cv2.CAP_DSHOW)
        print('VideoCapture created')

        # self.camera.set(cv2.CAP_PROP_SETTINGS, 1)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        self.camera.set(cv2.CAP_PROP_FPS, 60)
        self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

        # self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        # self.camera.set(cv2.CAP_PROP_FOCUS, 255)
        print(f'{ self.camera.get(cv2.CAP_PROP_AUTOFOCUS)=}')
        print(f'{ self.camera.get(cv2.CAP_PROP_FOCUS)=}')

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

    def supported_capture_properties(self) -> list:
        """
        List the properties supported by the capture device.
        """
        cap = self.camera
        supported = []
        for attr in dir(cv2):
            if attr.startswith('CAP_PROP'):
                if cap.get(getattr(cv2, attr)) != -1:
                    supported.append(attr)
        return supported


class ClientApp:
    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.title('VideoCaptureStreamDemo')
        self.main_window.geometry('800x600')
        self.main_window.protocol('WM_DELETE_WINDOW', self.stop)

        # 狀態列
        self.status_text = tk.StringVar()
        self.status_text.set('Ready')
        status_bar = tk.Label(self.main_window, textvariable=self.status_text, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        button_frame = tk.Frame(self.main_window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)

        show_settings_button = tk.Button(button_frame, text='Settings', command=self.show_settings)
        show_settings_button.pack(side=tk.LEFT)

        self.message_text = tk.StringVar()
        message_label = tk.Label(self.main_window, textvariable=self.message_text, justify=tk.LEFT)
        message_label.pack(side=tk.RIGHT, anchor=tk.N)

        self.preview_label = tk.Label(text='Starting...')
        self.preview_label.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        self.video_looper = self.VideoLooper(app=self)

        self.supported_capture_properties = self.video_looper.camera.supported_capture_properties()
        # 顯示設定視窗
        self.video_looper.camera.camera.set(cv2.CAP_PROP_SETTINGS, 1)

    def run(self) -> None:
        self.main_window.mainloop()

    def stop(self) -> None:
        self.video_looper.stop()
        self.main_window.destroy()

    def show_settings(self) -> None:
        self.video_looper.camera.camera.set(cv2.CAP_PROP_SETTINGS, 1)

    class VideoLooper(threading.Thread):
        stop_event = threading.Event()
        camera = None

        def __init__(self, app: 'ClientApp'):
            threading.Thread.__init__(self)
            self.app = app
            self.daemon = True
            self.camera = Camera()
            self.start()

        def run(self) -> None:
            if self.stop_event.is_set():
                return
            self.video_loop()
            threading.Timer(0, self.run).start()

        def video_loop(self) -> None:
            preview_label = self.app.preview_label
            ret, img = self.camera.read()
            if not ret and not self.stop_event.is_set():
                preview_label.img_tk = None
                preview_label.config(image='', text='Disconnected. Trying to reconnect...')
                self.camera.reconnect()
                return

            self.refresh_info()

            limit_width = preview_label.winfo_width()
            limit_height = preview_label.winfo_height()
            img = resize_image(img, limit_width, limit_height)

            cv2image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            current_image = Image.fromarray(cv2image)

            img_tk = ImageTk.PhotoImage(image=current_image)
            preview_label.config(image=img_tk)
            preview_label.img_tk = img_tk

        def refresh_info(self) -> None:
            self.app.status_text.set(f'FPS={self.camera.fps:.2f}')

            message = 'Supported properties:\n'
            for property_name in self.app.supported_capture_properties:
                value = self.camera.camera.get(getattr(cv2, property_name))
                message += f'- {property_name}:\t\t {value}\n'

            self.app.message_text.set(message)

        def stop(self) -> None:
            self.stop_event.set()
            self.camera.release()
            self.join()
            print('CameraLooper stopped')


if __name__ == "__main__":
    app = ClientApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print('KeyboardInterrupt detected, exiting...')
        app.stop()
