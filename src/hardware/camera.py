# src/hardware/camera.py

from datetime import datetime
import io

from picamera2 import Picamera2
from PIL import Image

from config import (
    CAPTURE_DIR,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
)


class Camera:

    def __init__(self):

        CAPTURE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        self.picam2 = Picamera2()

        config = (
            self.picam2
            .create_still_configuration(
                main={
                    "size": (
                        CAMERA_WIDTH,
                        CAMERA_HEIGHT
                    )
                }
            )
        )

        self.picam2.configure(
            config
        )

        self.picam2.start()

    # ========================================================
    # SINGLE PHOTO
    # ========================================================

    def capture(self):

        timestamp = (
            datetime.now()
            .strftime(
                "%Y%m%d_%H%M%S_%f"
            )
        )

        filename = (
            f"minicam_{timestamp}.jpg"
        )

        filepath = (
            CAPTURE_DIR /
            filename
        )

        print(
            f"Capturing image: {filepath}"
        )

        self.picam2.capture_file(
            str(filepath)
        )

        print(
            f"Image captured: {filepath}"
        )

        return filename

    # ========================================================
    # STREAM FRAME
    # ========================================================

    def capture_frame(self):

        frame = (
            self.picam2
            .capture_array()
        )

        image = Image.fromarray(
            frame
        )

        buffer = io.BytesIO()

        image.save(
            buffer,
            format="JPEG",
            quality=80
        )

        return buffer.getvalue()

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self.picam2.stop()