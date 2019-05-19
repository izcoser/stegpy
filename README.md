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
* GIF
* WebP
* WAV

Images in a different format are automatically converted to PNG. Different audio formats are not supported at all.

***
Dependencies:
* numpy
* cryptography
* Pillow (PIL fork)
***
Install:
```sh
$ pip3 install stegpy
```
***
How to use:
* Hide a message or file:
```sh
$ stegpy "Hello World!" image.png
```
* Extract it:
```sh
$ stegpy _image.png
```
* Encrypt:
```sh
$ stegpy "Hello World!" image.png -p
Enter password (will not be echoed):
Verify password (will not be echoed):
$ stegpy _image.png -p
Enter password (will not be echoed):
Hello World!
```
* More options:
```sh
$ stegpy -h
```
***
To do:
* Add docstrings
* Allow encoding across multiple files
* Support JPEG & FLAC as hosts
