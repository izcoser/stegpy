#!/usr/bin/env python3

import sys
import argparse
import os.path
from getpass import getpass

from . import lsb

def main():
    parser = argparse.ArgumentParser(description='Simple steganography program based on the LSB method.')
    parser.add_argument('a', help='file or message to encode (if none, will read host)', nargs='*')
    parser.add_argument('b', help='host file')
    parser.add_argument('-p', '--password', help='set password to encrypt or decrypt a hidden file', action='store_true')
    parser.add_argument('-b', '--bits', help='number of bits per byte (default is 2)', nargs='?', default=2, choices=['1', '2', '4'])
    parser.add_argument('-c', '--check', help='check free space of argument files', action='store_true')
    args = parser.parse_args()

    bits = int(args.bits)
    
    if args.check:
        for arg in args.a + [args.b]:
            if os.path.isfile(arg):
                lsb.HostElement(arg).print_free_space(bits)
        return

    password = filename = None
    host_path = args.b
    host = lsb.HostElement(host_path)

    if args.a:
        args.a = args.a[0]
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
 
        host.insert_message(message, bits, filename, password)
        host.save()
    else:
       if args.password:
            password = getpass('Enter password (will not be echoed):')
       host.read_message(password)

if __name__== "__main__":
    main()

