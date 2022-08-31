# stegpy

<p align="middle">
    <img src="https://files.catbox.moe/4t5f8u.gif"/>
</p>

A program for encoding information in image and audio files through steganography. Any type of data can be encoded, from raw strings to files, as shown below:

<p align="middle">
  <img src="https://github.com/kamihfkjkf/stegpy/blob/master/images/house.png?raw=true"/>
  <img src="https://github.com/kamihfkjkf/stegpy/blob/master/images/_cat.jpeg?raw=true"/>
</p>

On the left, a house with a steganographically hidden image. On the right, the extracted hidden image of a cat. It is revealed by removing all but the least significant bit of each color component in the host image.

***
## Supported host formats
* PNG
* BMP
* GIF
* WebP
* WAV

Images in a different format are automatically converted to PNG. Different audio formats are not supported at all.

***
## Dependencies
* numpy
* cryptography
* Pillow (PIL fork)
***
## Installation
```sh
 pip3 install stegpy
```
***
## Usage:
### Hide a message or file:
```sh
 stegpy "Hello World!" image.png
```
### Extract it:
```sh
 stegpy _image.png
```

Data is encoded without any protection by default, but it can be encrypted with the ```-p``` flag:

### Encrypt:
```sh
 stegpy "Hello World!" image.png -p
Enter password (will not be echoed):
Verify password (will not be echoed):
 stegpy _image.png -p
Enter password (will not be echoed):
Hello World!
```
### More options:
```sh
 stegpy -h
```
***
## To do
* Add docstrings
* Allow encoding across multiple files
* Support JPEG & FLAC as hosts

