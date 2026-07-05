# stegpy

<p align="middle">
    <img src="https://files.catbox.moe/4t5f8u.gif"/>
</p>

A program for encoding information in image, audio, and video files through steganography. Any type of data can be encoded, from raw strings to files, as shown below:

<p align="middle">
  <img src="https://github.com/izcoser/stegpy/blob/master/images/house.png?raw=true"/>
  <img src="https://github.com/izcoser/stegpy/blob/master/images/_cat.jpeg?raw=true"/>
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
* MP4
* M4V
* MOV
* MKV
* WebM
* AVI

JPEG hosts use DCT-coefficient embedding. On the CLI, other Pillow-readable image
formats are converted to PNG when saved. The web API accepts only the formats
listed above. WAV is the only supported audio format.

Video hosts are decoded with FFmpeg, embedded frame-by-frame with a robust DCT
signal, and written back as MP4/H.264. The video decoder is intended for files
created by stegpy's video encoder; arbitrary videos without a stegpy payload will
not decode useful data. Video processing is intentionally disabled on the hosted
public web demo because it can be CPU intensive; use the CLI or run the web app
locally for video hosts.

***
## Dependencies
* numpy
* cryptography
* Pillow (PIL fork)
* jpeglib
* FastAPI
* python-multipart
* Uvicorn

Video support also requires the `ffmpeg` and `ffprobe` command-line tools.
***
## Installation

Install the current release from PyPI as a command-line tool with `uv`:

```sh
 uv tool install stegpy
 stegpy -h
```

Upgrade an existing install with:

```sh
 uv tool upgrade stegpy
```

For development, clone the repository and create the environment with `uv`:

```sh
 git clone https://github.com/izcoser/stegpy.git
 cd stegpy
 uv sync --dev
 uv run stegpy -h
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

### Hide data in a video:
```sh
 stegpy "Hello video!" clip.mp4
 stegpy _clip.mp4
```

Video inputs can be any supported FFmpeg-readable container listed above. stegpy
always writes encoded video output as MP4/H.264.

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
## Live demo

A live demo backed by the Python package is available at
<https://stegpy.coseri.xyz>.

Run the FastAPI application and browser demo locally from the repository:

```sh
 uv run uvicorn stegpy.web:app --reload
```

Then open <http://127.0.0.1:8000>. The static files in `web-demo/` require the
FastAPI `/api/*` backend and do not work by opening `index.html` directly.

The hosted demo supports PNG, BMP, GIF, WebP, WAV, and JPEG hosts, text or file
payloads, and optional password encryption. Image/audio host and file payload
uploads are limited to 20 MB, and text messages are limited to 1 MB. Its capacity
display shows usable payload bytes after the stegpy header, embedded filename,
and encryption overhead.

Video hosts are available in the web UI only when running on localhost because
video processing can keep a small server CPU busy for minutes. The local web UI
accepts video hosts up to 5 MB.

The API also exposes `GET /api/health`, `POST /api/capacity`,
`POST /api/encode`, and `POST /api/decode`. Interactive API documentation is
available at <http://127.0.0.1:8000/docs> when running locally.

***
## Support

Donations are appreciated if you find this project useful.

Ethereum / EVM: `0xfE1039ba2d4973eb6F6dd1cF3BDAF24aa6cbff96`
