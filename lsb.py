#!/usr/bin/env python3
# Module for processing images and the least significant bits.

import numpy
import codecs
from PIL import Image
from crypt import encrypt_info, decrypt_info

MAGIC_NUMBER = b'stegv2'

def get_image(image_path):
    ''' Returns a numpy array of an image so that one can access values[x][y]. '''
    image = Image.open(image_path)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    return numpy.array(image)

def save_image(array, image_path):
    image = Image.fromarray(array)
    image.save(image_path, 'PNG')

def insert_message(message, image_path, filename = None, password = None, args = None, bits_to_use = 4):
    ''' Creates a similar image with the encoded message.
    Text is encoded in utf8. There is a 10-byte header. 6 bytes for the magic number and
    4 bytes for the length of the message as a 32-bit big endian unsigned integer.
    When encoding an image, 6 bytes are added to the end to store its dimensions.
    The output image's first byte is also used to tell whether it was encoded with 1, 2 or 4 bits per byte'''

    msg_len = len(message).to_bytes(4, 'big')

    if(filename == None): # text
        message = MAGIC_NUMBER + msg_len + (0).to_bytes(1, 'big') + message
    else:
        filename = filename.encode('utf-8')
        filename_len = len(filename).to_bytes(1, 'big')
        if(args == None): # any file that's not an image
            message = MAGIC_NUMBER + msg_len + filename_len + filename + message
        elif(args != None): # image
            width = args[0].to_bytes(3, 'big')
            height = args[1].to_bytes(3, 'big')
            message = MAGIC_NUMBER + msg_len + filename_len + filename + message + width + height

    if(password != None):
        message = encrypt_info(password, message)

    pixels = get_image(image_path)
    number_of_pixels = pixels.size
    number_of_characters = len(message)
    divisor = (8 if (bits_to_use == 1) else (4 if bits_to_use == 2 else 2))
    max_message_len = number_of_pixels // divisor

    print("Number of pixels: {:,}".format(number_of_pixels))
    print("Number of characters: {:,}".format(number_of_characters))
    print("Maximum character storage: {:,}".format(max_message_len))

    if(max_message_len < number_of_characters):
        print('You have too few pixels to store that information. Aborting.')
        exit(-1)
    else:
        print('Ok.')

    # start the work
    shape = pixels.shape
    pixels.shape = -1, # convert to 1D

    msg = numpy.zeros(max_message_len, dtype=numpy.uint8)
    msg[:len(message)] = list(message)

    pixels &= 256 - 2 ** bits_to_use # clear last bit(s)
    for i in range(divisor):
        pixels[i::divisor] |= msg >> bits_to_use*i & (2 ** bits_to_use - 1) # copy bits to pixels

    operand = (0 if (bits_to_use == 1) else (16 if (bits_to_use == 2) else 32))
    pixels[0] = (pixels[0] & 207) | operand # 5th and 6th bits = log_2(bits_to_use)

    pixels.shape = shape # restore the 3D shape
    save_image(pixels, '_' + image_path)
    print("Done encoding")

def read_message(image_path, password=None):
    ''' Reads inserted message. '''
    pixels = get_image(image_path)
    pixels.shape = -1, # convert to 1D
    number_of_pixels = pixels.size
    bits_to_use = 2 ** ((pixels[0] & 48) >> 4) # bits_to_use = 2 ^ (5th and 6th bits)
    divisor = (8 if (bits_to_use == 1) else (4 if bits_to_use == 2 else 2))
    max_message_len = number_of_pixels // divisor

    msg = numpy.zeros(max_message_len, dtype=numpy.uint8)

    for i in range(divisor):
        msg |= (pixels[i::divisor] & (2 ** bits_to_use - 1)) << bits_to_use*i

    if(password != None):
        try:
            msg = decrypt_info(password, bytes(msg))
        except:
            print("Wrong password.")
            return

    if bytes(msg[0:6]) != MAGIC_NUMBER:
        print('ERROR! No encoded info found!')
        exit(-1)

    msg_len = int.from_bytes(bytes(msg[6:10]), 'big')
    filename_len = int.from_bytes(bytes(msg[10:11]), 'big')

    start = filename_len + 11
    end = start + msg_len

    if(filename_len > 0):
        filename = '_' + bytes(msg[11:start]).decode('utf-8')
    else:
        text = bytes(msg[start:end]).decode('utf-8')
        print(text)
        return


    if(filename.lower().endswith(('.txt'))):
        text = bytes(msg[start:end]).decode('utf-8')
        with codecs.open(filename, "w", 'utf-8-sig') as text_file:
            print(''.join(text), file=text_file)

    elif(filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))):
        size = [int.from_bytes(bytes(msg[end+3:end+6]), 'big'), int.from_bytes(bytes(msg[end:end+3]), 'big')]
        image = Image.frombytes('RGB', size, bytes(msg[start:end]))
        image.save(filename)

    else:
        with open(filename, 'wb') as f:
            f.write(bytes(msg[start:end]))

if __name__ == "__main__":
    import time
    start = time.time()
    # Tested: text, text file, image, audio, video, 7z
    with open('testie.7z', 'rb') as myfile:
        message = myfile.read()
    insert_message(message, 'Iceland.png', 'testie.7z', '123')
    read_message('_Iceland.png', '123')
    end = time.time()
    print('program took {} seconds to run'.format(end-start))
