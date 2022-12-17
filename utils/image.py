import cv2
import numpy as np


def resize_image(img: np.ndarray, limit_width: int, limit_height: int) -> np.ndarray:
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
