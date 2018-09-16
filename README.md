# stegpy

A script for embedding information in image files through steganography.

Dependencies:
* numpy
* cryptography
* PIL
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
* ???
