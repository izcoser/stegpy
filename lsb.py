# Module for processing images and the last significant bits.

import numpy
import codecs
from PIL import Image

''' Returns a numpy array of an image so that one can access values[x][y]. '''
def getImage(image_path):
    image = Image.open(image_path, 'r')
    width, height = image.size
    pixel_values = list(image.getdata())
    if image.mode == 'RGB':
        channels = 3
    else:
        print("Image mode not supported yet: %s\nAborting." % image.mode)
        exit(1)
    pixel_values = numpy.array(pixel_values).reshape((width, height, channels))
    return pixel_values

''' Returns the message as a list of binaries. '''
def getMessageBinaries(message):
    binaries = []
    for character in message:
        binaries.append(bin(ord(character))[2:].zfill(8))
    return binaries

''' Returns the pixels as a list of binaries. '''
def getPixelsBinaries(pixels):
    binaries = []
    for pixel_column in pixels:
        for pixel in pixel_column:
            for color in pixel:
                binaries.append(bin(color)[2:].zfill(8))
    return binaries

''' Returns the pixels with encoded message and terminator zeroes as a list of binaries. '''
def changeLeastSignificantBit(pixels_binaries, message_binaries):
    i = 0
    new_pixels_binaries = []

    for binary in pixels_binaries:
        new_pixels_binaries.append(list(binary))

    for binary in message_binaries:
        for j in range(0, 7, 2):
            new_pixels_binaries[i][6] = binary[j]
            new_pixels_binaries[i][7] = binary[j + 1]
            i += 1

    k = i
    for k in range(i, i + 100):
        new_pixels_binaries[k][6] = '0'
        new_pixels_binaries[k][7] = '0'

    return new_pixels_binaries


''' Creates a similar image with the encoded message. '''
def insertMessage(message, image_path):
    pixels = getImage(image_path)

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
    im.save('steg_' + image_path, 'PNG')


''' Reads inserted message. '''
def readInsertedMessage(image_path, write_to_file = 0):
    pixels = getImage(image_path)
    pixels_binaries = getPixelsBinaries(pixels)

    values = []
    for binary in pixels_binaries:
        values.append(binary[6:8])

    read_message = []
    i = 0
    terminator_count = 0
    binary = []

    for value in values:
        if(value == '00'):
            terminator_count += 1
            if(terminator_count == 100):
                break
        else:
            terminator_count = 0

        i += 1
        binary += value
        if(i == 4):
            character = chr(int(''.join(binary), 2))
            i = 0
            binary = []
            read_message.append(character)

    if(write_to_file):
        with codecs.open(image_path + ".txt", "w", 'utf-8-sig') as text_file:
            print(''.join(read_message[:-24]), file=text_file)
        print("Information written to " + image_path + ".txt")
    else:
        print(''.join(read_message[:-24]))
