import sys
import argparse
import os.path
from lsb import HostElement
from getpass import getpass

def main():
    parser = argparse.ArgumentParser(description='Simple steganography program based on the LSB method.')
    parser.add_argument('a', help='file or message to encode (if none, will read host)', nargs='?')
    parser.add_argument('b', help='host image')
    parser.add_argument('-p', '--password', help='encrypt/decrypt hidden file', action='store_true')
    parser.add_argument('-b', '--bits', help='number of bits per byte (default is 2)', action='store_true')
    args = parser.parse_args()
    
    password = filename = None
    bits = 2
    host_path = args.b
    host = HostElement(host_path)

    if args.a:
        if os.path.isfile(args.a):
            filename = args.a
            with open(filename, 'rb') as myfile:
                message = myfile.read()
        else:
            message = args.a.encode('utf-8')
        if args.password:
            while 1:
                password = getpass('Enter password (will not be echoed):')
                password_2 = getpass('Verify password (will not be echoed):')
                if password == password_2:
                    break
        if args.bits:
            bits = int(input('Number of LSB bits to encode in each byte (1, 2, 4):'))
            if bits not in [1, 2, 4]:
                bits = 2
        
        host.insert_message(message, bits, filename, password)
        host.save()
    else:
        if args.password:
            password = getpass('Enter password (will not be echoed):')
        host.read_message(password)

if __name__== "__main__":
    main()

