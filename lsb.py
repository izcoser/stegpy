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

def save_image(array, image_path):
    image = Image.fromarray(array)
    image.save(image_path)

def write_byte(array, idx, char):
    for i in range(8):
        if char & 1 << i:
            array[idx+i] |= 1 # set the bit
        else:
            array[idx+i] &= ~1 # clear the bit

def read_byte(array, idx):
    data = 0
    for i in range(8):
        last_bit = array[idx+i] & 1
        data |= last_bit << i
    return data

def insert_message(message, image_path):
    ''' Creates a similar image with the encoded message. '''
    pixels = getImage(image_path)
    number_of_pixels = pixels.size
    number_of_characters = len(message)

    print("Number of pixels: %d" % number_of_pixels)
    print("Number of characters: %d" % number_of_characters)
    print("Maximum character storage: %d" % (number_of_pixels // 8))

    if(number_of_pixels < number_of_characters//8):
        print('You have too few pixels to store that information. Aborting.')
        exit(1)
    else:
        print('Ok.')

    # start the work
    shape = pixels.shape
    pixels.shape = -1, # convert to 1D

    i = 0
    for char in message:
        write_byte(pixels, i, ord(char))
        i += 8
    write_byte(pixels, i, 0) # write terminator; 0 is not a valid char, so it makes a good terminator.

    pixels.shape = shape # restore the 3D shape
    save_image(pixels, 'steg_' + image_path)

def read_message(image_path, write_to_file=False):
    ''' Reads inserted message. '''
    pixels = getImage(image_path)
    pixels.shape = -1, # convert to 1D

    values = []
    for i in range(0, len(pixels), 8):
        data = read_byte(pixels, i)
        if data:
            values.append(chr(data))
        else:
            break
    result = ''.join(values)

    if write_to_file:
        with codecs.open(image_path + ".txt", "w", 'utf-8-sig') as text_file:
            print(''.join(result), file=text_file)
        print("Information written to " + image_path + ".txt")
    else:
        print(''.join(result))

if __name__ == "__main__":
    # test code
    insert_message('hello world', 'fig.png')
    read_message('steg_fig.png')
