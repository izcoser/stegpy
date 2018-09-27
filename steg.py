import sys
from lsb import insert_message, read_message, get_image
from getpass import getpass
import time

def start_message():
    print('''
    steg.py v2
        Usage: python3 steg.py <command> <switch> <information> <image_name> <switch> <switch>
        Example: python3 steg.py write -f archive.7z image.png -p -b=4

<Commands>
  write: Add information to image
  read: Read information from image
<Switches>
  These are optional.
  -f: File input
  -b: Bits to encode per byte (1, 2 or 4. Default is 2)
  -p: Set password
    ''')

def main():
    password = None
    filename = None
    bits = 2

    if(len(sys.argv) == 1):
        start_message()
        return

    else:

        if(sys.argv[1] == 'write'):
            if(sys.argv[2] == '-f'):
                filename = sys.argv[3]
                with open(filename, 'rb') as myfile:
                    message = myfile.read()
                image_path = sys.argv[4]
            else:
                message = sys.argv[2].encode('utf-8')
                image_path = sys.argv[3]
            if('-p' in sys.argv):
                while True:
                    password = getpass('Enter password (will not be echoed) :')
                    password_2 = getpass('Verify password (will not be echoed) :')
                    if password == password_2:
                        break;
            if('-b=1' in sys.argv):
                bits = 1
            elif('-b=4' in sys.argv):
                bits = 4

            insert_message(message, image_path, bits, filename, password)

        elif(sys.argv[1] == 'read'):
            image_path = sys.argv[2]
            if('-p' in sys.argv):
                password = getpass('Enter password (will not be echoed) :')
            read_message(image_path, password)

if __name__== "__main__":
    main()
