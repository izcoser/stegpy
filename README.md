# stegpy

A script for embedding information in media files through steganography.

![alt text](https://github.com/kamihfkjkf/stegpy/blob/master/images/house.png?raw=true)
Image of a house with a steganographically hidden image. The hidden image is revealed by removing all but the last significant bit of each color component.
![alt text](https://raw.githubusercontent.com/kamihfkjkf/stegpy/master/images/_cat.jpeg)
A cat extracted from the house above.
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
$ python3 steg.py write "Hello World!" "image.png"
$ python3 steg.py read "_image.png"
```
* Hide a file:
```sh
$ python3 steg.py write -f "file.whatever" "image.png"
$ python3 steg.py read "_image.png"
```
* Encrypt:
```sh
$ python3 steg.py write "Hello World!" "image.png" -p
$ Enter password (will not be echoed) :
$ Verify password (will not be echoed) :
$ Done.
$ python3 steg.py read "_image.png" -p
$ Enter password (will not be echoed) :
$ Verify password (will not be echoed) :
$ Hello World!
```
***
To do:
* ~Fix some types of images not working~
* ~Improve reading speed~
* ~Add image support~
* ~Add audio support~
* ~Support all kinds of files~
* ~Encrypt information~
* Find a way to use JPEG as host
