import sys
from lsb import insert_message, read_message, get_image
from getpass import getpass
import time

def start_message():
    print('''
    steg.py v2
        Usage: steg.py <command> <switch> <information> <image_name> <switch>

<Commands>
  write: Add information to image
  read: Read information from image
<Switches>
  -f: File input
  -p: Set password
    ''')

def main():
    password = None
    args = None
    filename = None

    if(len(sys.argv) == 1):
        start_message()
        return

    else:

        if(sys.argv[1] == 'write'):
            if(sys.argv[2] == '-f'):
                filename = sys.argv[3]
                if(filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))):
                    input_image = get_image(filename)
                    args = input_image.shape
                    message = bytes(input_image)
                else:
                    with open(filename, 'rb') as myfile:
                        message = myfile.read()
                image_path = sys.argv[4]
            else:
                message = sys.argv[2].encode('utf-8')
                image_path = sys.argv[3]
            if(sys.argv[-1] == '-p'):
                while True:
                    password = getpass('Enter password (will not be echoed) :')
                    password_2 = getpass('Verify password (will not be echoed) :')
                    if password == password_2:
                        break;

            insert_message(message, image_path, filename, password, args)
            print('Done.')

        elif(sys.argv[1] == 'read'):
            image_path = sys.argv[2]
            if(sys.argv[-1] == '-p'):
                while True:
                    password = getpass('Enter password (will not be echoed) :')
                    password_2 = getpass('Verify password (will not be echoed) :')
                    if password == password_2:
                        break;

            read_message(image_path, password)

if __name__== "__main__":
    main()
