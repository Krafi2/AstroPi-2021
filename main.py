from picamera import PiCamera
from datetime import datetime, timedelta
from logzero import logger, logfile
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
import io
import os
from time import sleep


# Timing
dt = timedelta(seconds=1)  # Time between measurements
runtime = timedelta(minutes=178)  # Runtime of the program

# Camera setup
camera = PiCamera()
camera.resolution = (4056, 3040)
camera.start_preview()

# Photo setup
minval = 0  # Minimum rating required to save a photo
n = 0
max_space = 2_990_000_000  # Maximum available data size
photo_quality = {}  # dict
sample = 16  # Image quality sampling factor


# Window mask
circle_bb_topleft_corner = (644, 72)
circle_diameter = 2825
circle_mask = Image.new("RGB", (circle_diameter, circle_diameter), (0, 0, 0))
ImageDraw.Draw(circle_mask).ellipse(
    [(0, 0), (circle_diameter, circle_diameter)], fill=(255, 255, 255))

# Logging
dir = Path(__file__).parent.resolve()
logfile(dir / "log.log")


def get_size():
    size = 0
    for path, _, files in os.walk(dir):
        for f in files:
            fp = os.path.join(path, f)
            size += os.path.getsize(fp)
    return size


def eval_photo(image):
    logger.info("Starting photo evaluation")
    palette = {
        "ocean": (35, 118, 152),
        "night": (0, 0, 0),
        "cloud": (255, 255, 255),
        "ground": (122, 116, 104),
    }
    weights = {
        "ocean": -0.1,
        "night": -1.,
        "cloud": -0.2,
        "ground": 1.,
    }
    counts = {
        "ocean": 0,
        "night": 0,
        "cloud": 0,
        "ground": 0,
    }

    for x in range(image.width // sample):
        for y in range(image.height // sample):
            pix = image.getpixel((x * sample, y * sample))

            min = 99999
            color = None
            for name, col in palette.items():
                dist = (col[0] - pix[0]) ** 2 + (col[1] -
                                                 pix[1]) ** 2 + (col[2] - pix[2]) ** 2
                if dist < min:
                    min = dist
                    color = name

            counts[color] += 1

    logger.info("Finished photo evaluation")
    return round(sum({count * weights[name] for (name, count) in counts.items()})) * sample ** 2


def crop_photo(image):
    image = image.crop((circle_bb_topleft_corner[0], circle_bb_topleft_corner[1],
                        circle_bb_topleft_corner[0] + circle_diameter, circle_bb_topleft_corner[1] + circle_diameter))
    image = ImageChops.multiply(image, circle_mask)
    return image


def take_photo():
    logger.info("Taking photo")
    stream = io.BytesIO()
    camera.capture(stream, format="jpeg")
    stream.seek(0)
    image = Image.open(stream)
    image = crop_photo(image)
    logger.info("Photo taken")
    return image


def measure():
    if get_size() < max_space:
        image = take_photo()

        quality = eval_photo(image)
        if quality >= minval:
            global n
            logger.info("Photo is good")
            img_name = dir / "photo_{}.jpg".format(str(n).zfill(3))
            image.save(img_name)
            n += 1
            photo_quality[img_name] = quality
        else:
            logger.info("Photo is bad")


def main():
    logger.info("Warming up camera")
    sleep(2)  # Camera warmup
    logger.info("Started")

    now_time = datetime.now()
    end_time = now_time + runtime
    # The end of the allocated time window
    next_time = now_time

    while now_time < end_time:
        try:
            now_time = datetime.now()
            if now_time > next_time:
                next_time = now_time + dt
                measure()
                # Check if we are late
                if datetime.now() > next_time:
                    logger.warn("Measurement took too long")

        except Exception as e:
            logger.error("{}: {}".format(e.__class__.__name__, e))
    logger.info("Finished")


if __name__ == "__main__":
    main()
