# stegpy

A script for embedding information in media files through steganography.

<p align="middle">
  <img src="https://github.com/kamihfkjkf/stegpy/blob/master/images/house.png?raw=true"/>
  <img src="https://github.com/kamihfkjkf/stegpy/blob/master/images/_cat.jpeg?raw=true"/> 
</p>

On the left, a house with a steganographically hidden image. On the right, the extracted hidden image of a cat. It is revealed by removing all but the last significant bit of each color component in the host image.

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
