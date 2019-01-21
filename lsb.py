#!/usr/bin/env python3
# Module for processing images, audios and the least significant bits.

import numpy
from PIL import Image
from crypt import encrypt_info, decrypt_info

MAGIC_NUMBER = b'stegv2'

def get_host(host_path):
    ''' Returns a numpy array of a host file so that one can access values[x][y]. '''
    if host_path[-3:].lower() == 'wav':
        sound = numpy.fromfile(host_path, dtype=numpy.uint8)
        header = sound[:180]
        data = sound[180:]
        return [header, data]
    else:
        image = Image.open(host_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return numpy.array(image)


def save_host(array, host_path, wav_header = None):
    ''' Saves the host. '''
    if host_path[-3:].lower() == 'wav':
        array = numpy.concatenate((wav_header, array))
        array.tofile(host_path)
    else:
        image = Image.fromarray(array)
        image.save(host_path)

def insert_message(message, host_path, bits, filename = None, password = None):
    ''' Creates a similar file with the encoded message.
    There is an 11-byte header. 6 bytes for the magic number, 4 bytes for the length
    of the message as a 32-bit big endian unsigned integer and 1 byte for the length
    of the filename. The output file's first byte is also used to tell whether it was
    encoded with 1, 2 or 4 bits per byte. '''

    raw_message_len = len(message).to_bytes(4, 'big')
    formatted_message = format_message(message, raw_message_len, filename)

    if(password != None):
        formatted_message = encrypt_info(password, formatted_message)

    host_data = get_host(host_path)

    extension = host_path[-3:]
    wav_header = None
    if extension.lower() == 'wav':
        wav_header = host_data[0]
        host_data = host_data[1]

    elif extension.lower() not in ['png', 'bmp']:
        print("Host has a lossy format and will be converted to PNG.")
        host_path = host_path[:-3] + 'png'
   
    host_path = '_' + host_path    
    host_data = encode_message(host_data, formatted_message, bits)
    save_host(host_data, host_path, wav_header)
    print("Message encoded succesfully in {}".format(host_path))

def format_message(message, msg_len, filename=None):
    ''' Adds header message to the message so that it can be inserted in an image. '''
    if(filename == None): # text
        message = MAGIC_NUMBER + msg_len + (0).to_bytes(1, 'big') + message
    else:
        filename = filename.encode('utf-8')
        filename_len = len(filename).to_bytes(1, 'big')
        message = MAGIC_NUMBER + msg_len + filename_len + filename + message
    return message;

def encode_message(host_data, message, bits):
    ''' Encodes the byte array in the image numpy array. '''
    shape = host_data.shape
    host_data.shape = -1, # convert to 1D
    uneven = 0
    divisor = 8 // bits

    print("Host dimension: {:,} bytes".format(host_data.size))
    print("Message size: {:,} bytes".format(len(message)))
    print("Maximum size: {:,} bytes".format(host_data.size // divisor))

    check_message_space(host_data.size // divisor, len(message))
 
    if(host_data.size % divisor != 0): # Hacky way to deal with pixel arrays that cannot be divided evenly
        uneven = 1
        original_size = host_data.size
        host_data = numpy.resize(host_data, host_data.size + (divisor - host_data.size % divisor))

    msg = numpy.zeros(len(host_data) // divisor, dtype=numpy.uint8)

    msg[:len(message)] = list(message)

    host_data[:divisor*len(message)] &= 256 - 2 ** bits # clear last bit(s)
    for i in range(divisor):
        host_data[i::divisor] |= msg >> bits*i & (2 ** bits - 1) # copy bits to host_data

    operand = (0 if (bits == 1) else (16 if (bits == 2) else 32))
    host_data[0] = (host_data[0] & 207) | operand # 5th and 6th bits = log_2(bits)

    if uneven:
        host_data = numpy.resize(host_data, original_size)
    
    host_data.shape = shape # restore the 3D shape
    
    return host_data

def check_message_space(max_message_len, message_len):
    ''' Checks if there's enough space to write the message. '''
    if(max_message_len < message_len):
        print('You have too few colors to store that message. Aborting.')
        exit(-1)
    else:
        print('Ok.')

def read_message(host_path, password=None):
    ''' Reads inserted message. '''
    host_data = get_host(host_path)
        
    extension = host_path[-3:]
 
    if extension.lower() == 'wav':
        host_data = host_data[1]

    host_data.shape = -1, # convert to 1D
    bits = 2 ** ((host_data[0] & 48) >> 4) # bits = 2 ^ (5th and 6th bits)
    msg = decode_message(host_data, bits)

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

    with open(filename, 'wb') as f:
        f.write(bytes(msg[start:end]))

    print('File {} succesfully extracted from {}'.format(filename, host_path))

def decode_message(host_data, bits):
    ''' Decodes the image numpy array into a byte array. '''
    
    divisor = 8 // bits

    if(host_data.size % divisor != 0):
        host_data = numpy.resize(host_data, host_data.size + (divisor - host_data.size % divisor))

    msg = numpy.zeros(len(host_data) // divisor, dtype=numpy.uint8)

    for i in range(divisor):
        msg |= (host_data[i::divisor] & (2 ** bits - 1)) << bits*i

    return msg

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
