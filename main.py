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
