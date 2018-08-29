#!/usr/bin/env python3
# Module for processing images and the last significant bits.

import numpy
import codecs
from PIL import Image
from itertools import chain

def getImage(image_path):
    ''' Returns a numpy array of an image so that one can access values[x][y]. '''
    image = Image.open(image_path)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    return numpy.array(image)

def getMessageBinaries(message):
    ''' Returns the message as a list of binaries. '''
    return ['{:0>8b}'.format(ord(character)) for character in message]

def getPixelsBinaries(pixels):
    ''' Returns the pixels as a list of binaries. '''
    return ['{:0>8b}'.format(pixel) for pixel in chain(*chain(*pixels))]

def changeLeastSignificantBit(pixels_binaries, message_binaries):
    ''' Returns the pixels with encoded message and terminator zeroes as a list of binaries. '''
    i = 0
    new_pixels_binaries = list(map(list, pixels_binaries))

    for binary in message_binaries:
        for j in range(0, 7, 2): # 0, 2, 4, 6
            new_pixels_binaries[i][6] = binary[j]
            new_pixels_binaries[i][7] = binary[j + 1]
            i += 1

    for k in range(i, i + 100):
        new_pixels_binaries[k][6] = '0'
        new_pixels_binaries[k][7] = '0'

    return new_pixels_binaries

def insertMessage(message, image_path):
    ''' Creates a similar image with the encoded message. '''
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
    im = Image.new('RGB', (len(pixels[0]), len(pixels)))
    im.putdata(new_pixels)
    im.save('steg_' + image_path, 'PNG')

def readInsertedMessage(image_path, write_to_file = 0):
    ''' Reads inserted message. '''
    pixels = getImage(image_path)
    pixels_binaries = getPixelsBinaries(pixels)

    values = [binary[6:8] for binary in pixels_binaries]
    values = ''.join(values)

    terminator = '00'*100
    idx = values.index(terminator) # find the terminator
    if idx%8:
        idx += 8-idx%8 # set to the 8-byte boundary
    values = values[:idx]

    read_message = []
    for binary in [values[i:i+8] for i in range(0, len(values), 8)]:
        character = chr(int(binary, 2))
        read_message.append(character)

    if(write_to_file):
        with codecs.open(image_path + ".txt", "w", 'utf-8-sig') as text_file:
            print(''.join(read_message), file=text_file)
        print("Information written to " + image_path + ".txt")
    else:
        print(''.join(read_message))

if __name__ == "__main__":
    print(getPixelsBinaries([[(1,2,3), (4,5,6)]]))
