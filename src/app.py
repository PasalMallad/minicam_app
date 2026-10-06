# src/app.py

from flask import (
    Flask,
    render_template,
    jsonify,
    send_from_directory,
    Response,
    request,
)

import threading
import time
import base64
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from config import (
    HOST,
    PORT,
    CAPTURE_DIR,
)

from hardware.adc import MCP3208
from hardware.camera import Camera
from acquisition.scanner import MiniCamScanner


app = Flask(__name__)


# ============================================================
# HARDWARE
# ============================================================

adc = MCP3208()

camera = Camera()

scanner = MiniCamScanner(
    adc,
    camera
)


# ============================================================
# STREAM STATE
# ============================================================

stream_running = False

stream_thread = None

stream_lock = threading.Lock()

latest_stream_data = {
    "values": None,
    "image": None,
}


# ============================================================
# MAIN PAGE
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# PHOTO + SCAN
# ============================================================

@app.route(
    "/api/scan",
    methods=["POST"]
)
def scan():

    try:

        result = scanner.scan()

        print(
            "Scan values:",
            result["values"]
        )

        print(
            "Image:",
            result["image"]
        )

        return jsonify({

            "success": True,

            "values":
                result["values"],

            "image":
                f"/captures/{result['image']}"
        })

    except Exception as e:

        print(
            "SCAN ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "error":
                str(e)
        }), 500


# ============================================================
# SERVE SAVED IMAGES
# ============================================================

@app.route(
    "/captures/<path:filename>"
)
def captured_image(filename):

    return send_from_directory(
        str(CAPTURE_DIR),
        filename
    )


@app.route(
    "/api/burst",
    methods=["POST"]
)
def burst():
    try:
        data = request.get_json(silent=True) or {}
        duration = float(data.get("duration", 30))
        fps = float(data.get("fps", 2))

        frames = scanner.stream_burst(
            duration_seconds=duration,
            fps=fps,
        )
        saved_files = save_burst_results(frames, fps)

        return jsonify({
            "success": True,
            **saved_files,
        })

    except Exception as e:
        print("BURST ERROR:", e)
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


# ============================================================
# STREAM WORKER
# ============================================================

def stream_worker():

    global stream_running
    global latest_stream_data

    print("Constant stream started")

    while True:

        # ----------------------------------------------------
        # Check whether stream should continue
        # ----------------------------------------------------

        with stream_lock:

            if not stream_running:

                break

        try:

            # ------------------------------------------------
            # Acquire camera + ADC
            # ------------------------------------------------

            result = scanner.stream_once()

            # ------------------------------------------------
            # Convert image to Base64
            # ------------------------------------------------

            image_base64 = base64.b64encode(
                result["frame"]
            ).decode("utf-8")

            # ------------------------------------------------
            # Store latest result
            # ------------------------------------------------

            with stream_lock:

                latest_stream_data = {

                    "values":
                        result["values"],

                    "image":
                        image_base64,
                }

        except Exception as e:

            print(
                "STREAM ERROR:",
                e
            )

            with stream_lock:

                latest_stream_data = {

                    "values": None,

                    "image": None,

                    "error": str(e)
                }

            break

    with stream_lock:

        stream_running = False

    print("Constant stream stopped")


# ============================================================
# START STREAM
# ============================================================

@app.route(
    "/api/stream/start",
    methods=["POST"]
)
def start_stream():

    global stream_running
    global stream_thread

    with stream_lock:

        if stream_running:

            return jsonify({

                "success": True,

                "message":
                    "Stream already running"
            })

        stream_running = True

        stream_thread = threading.Thread(
            target=stream_worker,
            daemon=True
        )

        stream_thread.start()

    return jsonify({

        "success": True,

        "message":
            "Stream started"
    })


# ============================================================
# STOP STREAM
# ============================================================

@app.route(
    "/api/stream/stop",
    methods=["POST"]
)
def stop_stream():

    global stream_running

    with stream_lock:

        stream_running = False

    return jsonify({

        "success": True,

        "message":
            "Stream stopping"
    })


# ============================================================
# GET LATEST STREAM RESULT
# ============================================================

@app.route(
    "/api/stream/data"
)
def stream_data():

    with stream_lock:

        data = dict(
            latest_stream_data
        )

        running = stream_running

    return jsonify({

        "running":
            running,

        "values":
            data.get("values"),

        "image":
            data.get("image"),

        "error":
            data.get("error")
    })


# ============================================================
# HELPER FUNCTION
# ============================================================

def save_burst_results(frames, fps):
    capture_dir = Path(CAPTURE_DIR)
    burst_id = datetime.now().strftime("burst_%Y%m%d_%H%M%S_%f")
    burst_dir = capture_dir / burst_id
    burst_dir.mkdir(parents=True, exist_ok=True)

    records = []
    video_writer = None
    video_path = burst_dir / f"{burst_id}.mp4"
    video_error = None

    try:
        import cv2
        import numpy as np

        for index, item in enumerate(frames, start=1):
            frame_bytes = item["frame"]
            image_name = f"{burst_id}_{index:04d}.jpg"
            (burst_dir / image_name).write_bytes(frame_bytes)

            record = {
                "frame": index,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "values": item["values"],
                "image": image_name,
            }
            records.append(record)

            decoded = cv2.imdecode(
                np.frombuffer(frame_bytes, dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )
            if decoded is None:
                continue

            height, width = decoded.shape[:2]

            if video_writer is None:
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                video_writer = cv2.VideoWriter(
                    str(video_path),
                    fourcc,
                    fps,
                    (width, height),
                )
                if not video_writer.isOpened():
                    video_writer.release()
                    video_writer = None
                    video_error = "No se pudo crear el archivo de video."
                    continue

            video_writer.write(decoded)

    except ImportError:
        video_error = (
            "OpenCV o NumPy no están instalados; "
            "se guardaron los JPEG, CSV y JSON."
        )
    finally:
        if video_writer is not None:
            video_writer.release()

    value_count = max(
        (len(record["values"]) for record in records),
        default=0,
    )
    csv_path = burst_dir / f"{burst_id}.csv"
    json_path = burst_dir / f"{burst_id}.json"

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["frame", "captured_at", "image"]
            + [f"value_{i}" for i in range(value_count)]
        )
        for record in records:
            writer.writerow([
                record["frame"],
                record["captured_at"],
                record["image"],
                *record["values"],
            ])

    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    burst_url = f"/captures/{burst_id}"
    result = {
        "frames_saved": len(records),
        "csv": f"{burst_url}/{csv_path.name}",
        "json": f"{burst_url}/{json_path.name}",
        "images": [
            f"{burst_url}/{record['image']}"
            for record in records
        ],
    }

    if video_writer is not None and video_path.exists():
        result["video"] = f"{burst_url}/{video_path.name}"
    if video_error:
        result["video_warning"] = video_error

    return result


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        app.run(
            host=HOST,
            port=PORT,
            debug=False,
            threaded=True
        )

    finally:

        with stream_lock:

            stream_running = False

        scanner.close()

        camera.close()

        adc.close()