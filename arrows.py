import cv2 as cv
from matplotlib import cm
from matplotlib import pyplot as plt
import numpy as np
import math 
 
path1 = r'/home/eg/Downloads/astropi/0002.jpg'
path2 = r'/home/eg/Downloads/astrotest/0002.png'
 
image = cv.imread(path1)
vectors = cv.imread(path2) # BGR!
vectors = cv.cvtColor(vectors, cv.COLOR_BGR2RGB)

half = vectors.shape[0] / 2

for y in range(0, vectors.shape[0]):
    for x in range(0, vectors.shape[1]):
        if (x - half)**2 + (y - half)**2 > half**2:
            vectors[y, x] = 255

def mag(x):
    return np.sqrt(x.dot(x))

baseline = [28,7,0]

max_vec = 0
for y in range(0, vectors.shape[0]):
    for x in range(0, vectors.shape[1]):
        vec = vectors[y, x]
        max_vec = max(max_vec, mag(vec - baseline))

ratiox = image.shape[1] / vectors.shape[1]
ratioy = image.shape[0] / vectors.shape[0]

viridis = cm.get_cmap('viridis')

for y in range(0, vectors.shape[0]):
    for x in range(0, vectors.shape[1]):
        vec = vectors[y, x, 0:2]
        if vec[0] != 255:
            vec = vec - baseline[0:2]
        else:
            vec = np.array([0,0])

        start = np.array([(x + 0.5) * ratiox, (y + 0.5) * ratioy]); 

        le = max(mag(vec), 0.001)
        if le < 3:
            vec = 0
        leg = math.log(le)

        end = start + (vec / le) * leg * 15
        color = viridis(leg / math.log(max_vec)) * np.array([255])
        
        start = np.array([int(start[0]), int(start[1])])
        end = np.array([int(end[0]), int(end[1])])
        image = cv.arrowedLine(image, start, end, color, 2, tipLength=10/max(mag(start-end), 0.01))
 
# Displaying the image
plt.imshow(image)
plt.show()