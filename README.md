# stegpy

A program for encoding information in image and audio files through steganography.

<p align="middle">
  <img src="https://github.com/kamihfkjkf/stegpy/blob/master/images/house.png?raw=true"/>
  <img src="https://github.com/kamihfkjkf/stegpy/blob/master/images/_cat.jpeg?raw=true"/>
</p>

On the left, a house with a steganographically hidden image. On the right, the extracted hidden image of a cat. It is revealed by removing all but the last significant bit of each color component in the host image.

***
Supported host formats:
* PNG
* BMP
* WAV

Images in a different format are automatically converted to PNG. Different audio formats are not supported at all.

***
Dependencies:
* numpy
* cryptography
* Pillow (PIL fork)
```sh
$ sudo apt-get install python3-numpy python3-cryptography
$ sudo pip install Pillow
```
***
How to use:
* Hide a message:
```sh
$ python3 steg.py "Hello World!" image.png
```
* Hide a file:
```sh
$ python3 steg.py file.whatever image.png
```
* Encrypt:
```sh
$ python3 steg.py "Hello World!" image.png -p
Enter password (will not be echoed):
Verify password (will not be echoed):
$ python3 steg.py _image.png -p
Enter password (will not be echoed):
Hello World!
```
***
To do:
* ~Fix some types of images not working~
* ~Improve reading speed~
* ~Add image support~
* ~Add audio support~
* ~Support all kinds of files~
* ~Encrypt information~
* Support JPEG as host
