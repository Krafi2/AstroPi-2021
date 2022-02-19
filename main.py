from sense_hat import SenseHat
from picamera import PiCamera
from datetime import datetime, timedelta
from logzero import logger, logfile
from pathlib import Path
from PIL import Image
import os


def setup():
    sense = SenseHat()

    dir = Path(__file__).parent.resolve()
    logfile(dir / "kkkm.log")

    return sense


dt = timedelta(seconds=1)  # Time between measurements
runtime = timedelta(minutes=178)  # Runtime of the program
sense = setup()

camera = PiCamera()
camera.resolution = (4056, 3040)
camera.start_preview()
sleep(2)
# camera setup
minval = 0
# mininum value to save photo, choose after experiments
n = 0
max_space = 3000000000
# number of photos taken
photo_quality = {}
# dict


def get_size():
    size = 0
    for path, dirs, files in os.walk(dir):
        for f in files:
            fp = os.path.join(path, f)
            size += os.path.getsize(fp)
        return size


def crop_photo(image):
    return image


def take_photo(n):
    current_size = get_size()
    while current_size >= max_space:
        min_val = min(photo_quality.itervalues())
        lowest = [k for k, v in photo_quality.iteritems() if v == min_val]
        remaining = photo_quality.viewkeys() - lowest
        for name in lowest:
            os.remove(name)
    camera.capture(stream, format='jpeg')
    stream.seek(0)
    image = Image.open(stream)
    image = crop_photo(image)
    quality = eval_photo(image)

    if quality >= minval:
        img_name = "photo_{}.jpg".format(str(n).zfill(3))
        image.save(img_name)
        n += 1
        photo_quality[img_name] = quality


def eval_photo(image):
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

    # Sampling factor
    sample = 16
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

    return round(sum({count * weights[name] for (name, count) in counts.items()})) * sample ** 2


def main():
    now_time = datetime.now()
    # The end of the allocated time window
    end_time = now_time + runtime
    next_time = now_time

    while now_time < end_time:
        try:
            now_time = datetime.now()
            if now_time > next_time:
                next_time = now_time + dt
                take_photo(n)
                # Check if we are late
                if datetime.now() > next_time:
                    logger.warn("Measurement took too long")

        except Exception as e:
            logger.error("{}: {}".format(e.__class__.__name__, e))


if __name__ == "__main__":
    main()
