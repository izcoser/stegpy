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
* JPEG
* PNG
* BMP
* GIF
* WebP
* WAV

JPEG hosts use DCT-coefficient embedding. Unsupported image formats are automatically converted to PNG. Different audio formats are not supported at all.

***
## Dependencies
* numpy
* cryptography
* Pillow (PIL fork)
* jpeglib
***
## Installation
```sh
 pip3 install stegpy
```

To run from a local checkout instead of installing from PyPI:

```sh
 git clone https://github.com/dhsdshdhk/stegpy.git
 cd stegpy
 uv sync --dev
 uv run stegpy -h
```

You can also install the checkout into your current Python environment:

```sh
 pip install .
 stegpy -h
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
## Browser demo

A small client-side demo is available at
https://izcoser.github.io/stegpy/.

You can also run it locally by opening `web-demo/index.html`.

It runs entirely in the browser and supports PNG text payloads only. For JPEG,
GIF, WebP, WAV, encrypted payloads, and embedded files, use the Python package.
***
## To do
* Add docstrings
* Allow encoding across multiple files
* Support FLAC as a host

***
## Support

Donations are appreciated if you find this project useful.

Ethereum / EVM: `0xfE1039ba2d4973eb6F6dd1cF3BDAF24aa6cbff96`
