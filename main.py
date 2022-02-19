from sense_hat import SenseHat
from picamera import PiCamera
from datetime import datetime, timedelta
from logzero import logger, logfile
from pathlib import Path


def setup():
    sense = SenseHat()

    dir = Path(__file__).parent.resolve()
    logfile(dir/"kkkm.log")

    return sense


dt = timedelta(seconds=1)  # Time between measurements
runtime = timedelta(minutes=178)  # Runtime of the program
sense = setup()


def take_photo():
    pass


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
                take_photo()

                # Check if we are late
                if datetime.now() > next_time:
                    logger.warn("Measurement took too long")

        except Exception as e:
            logger.error("{}: {}".format(e.__class__.__name__, e))


if __name__ == "__main__":
    main()
