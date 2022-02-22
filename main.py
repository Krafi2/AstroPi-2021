from picamera import PiCamera
from datetime import datetime, timedelta
from logzero import logger, logfile
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
import io
import os
from time import sleep


# Timing
dt = timedelta(seconds=1.1)  # Time between measurements
runtime = timedelta(minutes=180)  # Runtime of the program

# Camera setup
camera = PiCamera()
camera.resolution = (2028, 1520)  # Half the maximum resolution
camera.start_preview()

# Photo setup
min_quality = 0  # Minimum rating required to save a photo
n = 0
max_space = 2_990_000_000  # Maximum available data size
sample = 30  # Image quality sampling factor
quality = 100  # Jpeg encoding quality
bias = 427_861  # Bias added to the image quality

# Window mask
circle_bb_topleft_corner = (322, 36)
circle_diameter = 1412
# A circular mask applied to the image to cover the window
circle_mask = Image.new("RGB", (circle_diameter, circle_diameter), (0, 0, 0))
ImageDraw.Draw(circle_mask).ellipse(
    [(0, 0), (circle_diameter, circle_diameter)], fill=(255, 255, 255))

# Logging
dir = Path(__file__).parent.resolve()
logfile(dir / "log.log")


def data_size():
    "Get the size of data accumulated by the experiment so far."

    size = 0
    for path, _, files in os.walk(dir):
        for f in files:
            fp = os.path.join(path, f)
            size += os.path.getsize(fp)
    return size


def eval_photo(image):
    """Evaluate a Pillow Image to see how certain we are in its quality. A
    positive values means that the image is good, while a negative rating means
    that there might be just clouds."""

    # The colors of the buckets and their weights (r, g, b, w)
    # These colors are chosen to be conservative and let an image pass more
    # often than not, because we should hopefully have enough space.
    palette = {
        "night": (0, 0, 0, -1.),
        "blue_ocean": (32, 95, 113, -0.5),
        "turqoise_ocean": (35, 118, 152, -0.5),
        "green_ocean": (111, 158, 150, -0.3),
        "cloud": (240, 240, 240, -1.),
        "ground1": (122, 116, 104, 1.),
        "ground2": (100, 118, 118, 1.),
        "ground3": (150, 150, 150, 1.),
        "desert": (233, 215, 195, 1.),
        "grass": (97, 160, 140, 0.5)
    }
    counts = {name: 0 for name in palette.keys()}

    # Sample pixels of the image and sort them into buckets.
    # Sampling is necessary because python isn't fast enough.
    for x in range(image.width // sample):
        for y in range(image.height // sample):
            pix = image.getpixel((x * sample, y * sample))

            min = 99999
            color = None
            # Iterate through the buckets and find the "closest" one
            for name, col in palette.items():
                # Use squared euclidean distance as a metric
                dist = (col[0] - pix[0]) ** 2 + (col[1] -
                                                 pix[1]) ** 2 + (col[2] - pix[2]) ** 2
                # Find the minimum
                if dist < min:
                    min = dist
                    color = name

            counts[color] += 1

    # Rating is the weighted sum of pixel counts multiplied by samples squared
    # in an attempt to somewhat normalize it.
    rating = sum({count * palette[name][3]
                 for (name, count) in counts.items()}) * sample ** 2 + bias
    return round(rating)


def crop_photo(image):
    """Crop the area around the ISS's window and cover the remaining region
    with a black mask."""

    # Crop around the ISS's window
    image = image.crop((circle_bb_topleft_corner[0], circle_bb_topleft_corner[1],
                        circle_bb_topleft_corner[0] + circle_diameter, circle_bb_topleft_corner[1] + circle_diameter))
    # Mask everything except the viewport
    image = ImageChops.multiply(image, circle_mask)
    return image


def take_photo():
    """Take a photo, crop it and mask the window. Return the image and exif
    data."""

    stream = io.BytesIO()
    camera.capture(stream, format="jpeg")
    stream.seek(0)
    image = Image.open(stream)
    # Exctract the exif data so we can preserve it
    exif = image.info["exif"]
    image = crop_photo(image)
    return image, exif


def measure():
    """Try to process a measurement. Return false when continuing isn't
    possible."""

    if data_size() < max_space:
        image, exif = take_photo()
        quality = eval_photo(image)

        # If the quality is higher than minimum, save the photo
        if quality >= min_quality:
            global n
            logger.info("Photo is good")
            img_name = dir / f"photo_{n:04d}.jpg"
            # Save the image with the original exif data
            image.save(img_name, "JPEG", quality=quality, exif=exif)
            n += 1
        else:
            logger.info("Photo is bad")
        return True
    else:
        return False


def main():
    """
    The program spins until it's time to take a measurement, and then it takes
    a photo. This photo is evaluated using some simple heuristics in order to
    sort out images with little terrain. If it passes and there's space left,
    it gets saved, otherwise we prematurely exit.
    """

    logger.info("Warming up camera")
    sleep(2)  # Camera warmup
    logger.info("Started!")

    now_time = datetime.now()  # The time is now
    end_time = now_time + runtime  # End of the program's runtime
    next_time = now_time  # The end of the allocated time window

    # Loop until experiment end
    while now_time < end_time:
        try:
            now_time = datetime.now()
            # Check if we should take a measurement
            if now_time > next_time:
                # The next measurement
                next_time = now_time + dt

                # Take a measurement and exit if we can't
                if not measure():
                    logger.info("Ending prematurely")
                    break

                # Check if we are late
                now = datetime.now()
                if now > next_time:
                    # Let's hope that we can catch up. In our testing that
                    # wasn't a problem.
                    logger.warning(
                        f"Measurement took too long ({now - now_time} > {dt})")

        except Exception as e:
            logger.error("{}: {}".format(e.__class__.__name__, e))
    logger.info("Finished!")


if __name__ == "__main__":
    main()
