# Module for processing images and the last significant bits.

import textwrap
import numpy
from PIL import Image

def is_alpha(word):
     try:
         return word.encode('ascii').isalpha() or word == ' '
     except:
         return False

def get_image(image_path):
    """Get a numpy array of an image so that one can access values[x][y]."""
    image = Image.open(image_path, 'r')
    width, height = image.size
    pixel_values = list(image.getdata())
    if image.mode == 'RGB':
        channels = 3
    elif image.mode == 'L':
        channels = 1
    else:
        print("Unknown mode: %s" % image.mode)
        return None
    pixel_values = numpy.array(pixel_values).reshape((width, height, channels))
    return pixel_values

def getLast2Digits(binary):
    return binary[6:8]

def getMessageBinaries(message):
    binaries = []
    for character in message:
        binaries.append(bin(ord(character))[2:].zfill(8))
    return binaries

def getPixelsBinaries(pixels):
    binaries = []
    for pixel_column in pixels:
        for pixel in pixel_column:
            for color in pixel:
                binaries.append(bin(color)[2:].zfill(8))
    return binaries

def changeLeastSignificantBit(pixels_binaries, message_binaries):
    i = 0
    new_pixels_binaries = []

    for binary in pixels_binaries:
        new_pixels_binaries.append(list(binary))

    #print(new_pixels_binaries)
    #print(new_pixels_binaries[0][8])

    #print(pixels_binaries)
    #print(message_binaries)

    for binary in message_binaries:
        for j in range(0, 7, 2):
            #print(i)
            #print(new_pixels_binaries[i])
            #print(binary);
            #print("Changing " + new_pixels_binaries[i][6] + " to " + binary[j])
            new_pixels_binaries[i][6] = binary[j]
            #print("Changing " + new_pixels_binaries[i][7] + " to " + binary[j + 1])
            new_pixels_binaries[i][7] = binary[j + 1]
            i += 1

    return new_pixels_binaries



def insertMessage(message, image_path):
    pixels = get_image(image_path)

    number_of_pixels = len(pixels) * len(pixels[0])
    number_of_characters = len(message)
    ratio = number_of_pixels / float(number_of_characters)

    print("Number of pixels: %d" % number_of_pixels)
    print("Number of characters: %d" % number_of_characters)
    print("Maximum character storage: %d" % (number_of_pixels * 3/float(4)))

    if(ratio < 4/float(3)):
        print('You have too few pixels to store that information. Aborting.')
        exit(1)
    else:
        print('Ok.')

    message_binaries = getMessageBinaries(message)
    pixels_binaries = getPixelsBinaries(pixels)

    new_pixels_binaries = changeLeastSignificantBit(pixels_binaries, message_binaries)

    for i in range(0, number_of_pixels * 3):
        new_pixels_binaries[i] = ''.join(new_pixels_binaries[i])

    new_pixels = []
    new_pixel = []

    for i in range(0, len(new_pixels_binaries), 3):
        new_pixel.append(int(new_pixels_binaries[i], 2))
        new_pixel.append(int(new_pixels_binaries[i + 1], 2))
        new_pixel.append(int(new_pixels_binaries[i + 2], 2))
        new_pixels.append(new_pixel)
        new_pixel = []

    new_pixels = list(tuple(x) for x in new_pixels)
    im = Image.new('RGB', (len(pixels), len(pixels[0])))
    im.putdata(new_pixels)
    #im.save('stego_' + image_path)
    im.save(image_path + '.png') #Can't seem to insert messages if I save this as .jpg



def readInsertedMessage(image_path, write_to_file = 0):
    pixels = get_image(image_path)
    pixels_binaries = getPixelsBinaries(pixels)

    values = []
    for binary in pixels_binaries:
        values.append(getLast2Digits(binary))

    values = ''.join(values)
    values = textwrap.wrap(values, 8)
    read_message = []
    for value in values:
        character = chr(int(value, 2))
        #if(is_alpha(character)):
        #    read_message.append(character)
        read_message.append(character)

    if(write_to_file):
        with open(image_path + ".txt", "w") as text_file:
            print(''.join(read_message), file=text_file)
    else:
        print(''.join(read_message))

#with open('data_2.txt', 'r') as myfile:
#    message = myfile.read()
