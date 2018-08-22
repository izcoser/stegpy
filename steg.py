import sys
from lsb import insertMessage, readInsertedMessage

'''

    Usage:
    python3 steg.py [option] [message] [filename]
    Examples:
    python3 steg.py write "Hello World!" image.jpg
    python3 steg.py read image.jpg

'''

def main():
    if(sys.argv[1] == 'write'):
        message = sys.argv[2]
        image_path = sys.argv[3]

        insertMessage(message, image_path)
        print('Done.')

    elif(sys.argv[1] == 'read'):
        image_path = sys.argv[2]

        readInsertedMessage(image_path, 1)

if __name__== "__main__":
    main()
