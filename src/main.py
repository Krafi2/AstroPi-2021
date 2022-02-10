from sense_hat import SenseHat

def setup():
    sense = SenseHat()
    
    # Recommended color gain
    sense.color.gain = 60

    return sense
