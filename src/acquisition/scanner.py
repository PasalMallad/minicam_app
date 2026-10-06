# src/acquisition/scanner.py

from concurrent.futures import ThreadPoolExecutor
import time

class MiniCamScanner:

    def __init__(
        self,
        adc,
        camera
    ):

        self.adc = adc

        self.camera = camera

        self.executor = (
            ThreadPoolExecutor(
                max_workers=2
            )
        )

    # ========================================================
    # ADC AVERAGE
    # ========================================================

    def measure_average(
        self,
        num_measurements=16
    ):

        accumulated = [
            0
            for _ in range(24)
        ]

        for _ in range(
            num_measurements
        ):

            measurement = (
                self.adc
                .read_all_channels()
            )

            for i in range(24):

                accumulated[i] += (
                    measurement[i]
                )

        average = [

            value //
            num_measurements

            for value in accumulated
        ]

        return average

    # ========================================================
    # PHOTO + SCAN
    # ========================================================

    def scan(self):

        camera_future = (
            self.executor.submit(
                self.camera.capture
            )
        )

        adc_future = (
            self.executor.submit(
                self.measure_average
            )
        )

        image_filename = (
            camera_future.result()
        )

        values = (
            adc_future.result()
        )

        return {

            "values":
                values,

            "image":
                image_filename
        }

    # ========================================================
    # STREAM
    # ========================================================

    def stream_once(self):

        camera_future = (
            self.executor.submit(
                self.camera.capture_frame
            )
        )

        adc_future = (
            self.executor.submit(
                self.measure_average
            )
        )

        frame = (
            camera_future.result()
        )

        values = (
            adc_future.result()
        )

        return {

            "values":
                values,

            "frame":
                frame
        }

    #=======================================================
    # 30S FRAME BURST
    # ========================================================

    def stream_burst(
        self,
        duration_seconds=30,
        fps=2
    ):
        if duration_seconds <= 0:
            return []

        if fps <= 0:
            raise ValueError("fps must be greater than zero")

        interval = 1.0 / fps
        start_time = time.monotonic()
        end_time = start_time + duration_seconds
        next_capture = start_time
        frames = []

        while next_capture < end_time:
            wait_seconds = next_capture - time.monotonic()
            if wait_seconds > 0:
                time.sleep(wait_seconds)

            if time.monotonic() >= end_time:
                break

            frames.append(self.stream_once())
            next_capture += interval

            # Skip missed slots instead of running scans back-to-back.
            now = time.monotonic()
            if next_capture < now:
                missed_slots = int((now - next_capture) / interval) + 1
                next_capture += missed_slots * interval

        return frames
        

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self.executor.shutdown(
            wait=True
        )