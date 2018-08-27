import sys
from lsb import insertMessage, readInsertedMessage

import time


'''

    Usage:
    python3 steg.py [option] [flag] [message] [filename]
    Examples:
    python3 steg.py write "Hello World!" image.jpg
    python3 steg.py write -f "data.txt" image.jpg
    python3 steg.py read steg_image.jpg
    python3 steg.py read -f steg_image.jpg

'''

def main():
    start_time = time.time()

    if(sys.argv[1] == 'write'):
        if(sys.argv[2] == '-f'):
            text_file = sys.argv[3]
            with open(text_file, 'r') as myfile:
                message = myfile.read()
            image_path = sys.argv[4]
        else:
            message = sys.argv[2]
            image_path = sys.argv[3]

        insertMessage(message, image_path)
        print('Done.')

    elif(sys.argv[1] == 'read'):
        if(sys.argv[2] == '-f'):
            flag = 1
            image_path = sys.argv[3]
        else:
            flag = 0
            image_path = sys.argv[2]

        readInsertedMessage(image_path, flag)
    print(time.time() - start_time)

if __name__== "__main__":
    main()
