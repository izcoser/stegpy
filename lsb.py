#!/usr/bin/env python3
# Module for processing images and the last significant bits.

import numpy
import codecs
from PIL import Image

MAGIC_NUMBER = 'steg'

def getImage(image_path):
    ''' Returns a numpy array of an image so that one can access values[x][y]. '''
    image = Image.open(image_path)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    return numpy.array(image)

def save_image(array, image_path):
    image = Image.fromarray(array)
    image.save(image_path)

def insert_message(message, image_path):
    ''' Creates a similar image with the encoded message. '''
    message = (MAGIC_NUMBER + message).encode()
    pixels = getImage(image_path)
    number_of_pixels = pixels.size
    number_of_characters = len(message)
    max_message_len = number_of_pixels // 8

    print("Number of pixels: {:,}".format(number_of_pixels))
    print("Number of characters: {:,}".format(number_of_characters))
    print("Maximum character storage: {:,}".format(max_message_len))

    if(number_of_pixels < number_of_characters//8):
        print('You have too few pixels to store that information. Aborting.')
        exit(-1)
    else:
        print('Ok.')

    # start the work
    shape = pixels.shape
    pixels.shape = -1, # convert to 1D
    
    msg = numpy.zeros(max_message_len, dtype=numpy.uint8)
    msg[:len(message)] = list(message)
    
    pixels &= 254 # clear the lsb bit for all bytes
    for i in range(8):
        pixels[i::8] |= msg >> i & 1

    pixels.shape = shape # restore the 3D shape
    save_image(pixels, 'steg_' + image_path)
    print("Done encoding")

def read_until_zero(array):
    for byte in array:
        if byte:
            yield byte
        else:
            return
            
def read_message(image_path, write_to_file=False):
    ''' Reads inserted message. '''
    pixels = getImage(image_path)
    pixels.shape = -1, # convert to 1D
    number_of_pixels = pixels.size
    max_message_len = number_of_pixels // 8
    
    msg = numpy.zeros(max_message_len, dtype=numpy.uint8)
    for i in range(8):
        msg |= (pixels[i::8] & 1) << i
    
    result = bytes(msg[:msg.argmin()]).decode()
    # ~ result = ''.join(chr(x) for x in msg[:msg.argmin()])

    if result.startswith(MAGIC_NUMBER):
        result = result[len(MAGIC_NUMBER):]
    else:
        print('ERROR! No encoded info found!')
        exit(-1)

    if write_to_file:
        with codecs.open(image_path + ".txt", "w", 'utf-8-sig') as text_file:
            print(''.join(result), file=text_file)
        print("Information written to " + image_path + ".txt")
    else:
        print(''.join(result))

if __name__ == "__main__":
    # test code
    import time
    start = time.time()
    # ~ insert_message('hello world'*15000, 'fig.png')
    insert_message('hello world', 'fig.png')
    read_message('steg_fig.png')
    end = time.time()
    print('program took {} seconds to run'.format(end-start))
