# AGENTS.md

## Scope
- This guide covers the Python project in this repository.
- Ignore `stegpy-rs/` unless the user explicitly asks about the Rust port. It is git-ignored and out of scope for normal work here.

## Project Summary
- `stegpy` is a small Python steganography CLI/library and FastAPI application for hiding text or file payloads inside images and WAV audio.
- PNG/BMP/GIF/WebP/WAV use the original least-significant-bit path.
- JPEG/JPG now use a separate DCT-coefficient embedding path via `jpeglib`.
- The original package is centered around NumPy for byte-level manipulation, Pillow for image I/O, and `cryptography` for optional password-based encryption.
- The public CLI entry point is `stegpy=stegpy.steg:main`.
- The FastAPI application is exposed as `stegpy.web:app` and serves both `/api/*` endpoints and the static browser demo.

## Repository Layout
- `README.md`: user-facing overview and CLI examples.
- `pyproject.toml`: package metadata, dependencies, console script registration, and pytest configuration.
- `setup.py`: minimal setuptools compatibility shim.
- `stegpy/steg.py`: command-line interface.
- `stegpy/lsb.py`: main host-file abstraction plus encode/decode logic.
- `stegpy/crypt.py`: password-based encryption/decryption helpers using PBKDF2 + Fernet.
- `stegpy/web.py`: FastAPI upload, capacity, encode, and decode endpoints.
- `web-demo/`: static HTML/CSS/JavaScript frontend served by the FastAPI application.
- `tests/`: pytest-based characterization and end-to-end coverage.
- `images/`: example assets used in the README/demo.

## Core Flow
1. CLI parsing happens in `stegpy/steg.py`.
2. `lsb.HostElement` loads the host file and normalizes it into a NumPy array.
3. Payload bytes are wrapped in a small custom header:
   - magic number: `b"stegv3"`
   - payload length: 4 bytes, big-endian
   - embedded filename length: 1 byte
   - optional embedded filename bytes
   - raw payload bytes
4. If `-p/--password` is used, the formatted payload is encrypted before embedding.
5. `encode_message()` writes payload bits into the host array using 1, 2, or 4 LSBs per host byte.
6. JPEG hosts dispatch to a DCT-coefficient path that writes directly into quantized AC coefficients.
7. Extraction reverses the process, then optionally decrypts and either prints text or writes a recovered file prefixed with `_`.

## Web Application
- Run the local application from a source checkout with:
  - `uv run uvicorn stegpy.web:app --reload`
- The application exposes:
  - `GET /api/health`
  - `POST /api/capacity`
  - `POST /api/encode`
  - `POST /api/decode`
- `web-demo/` is mounted at `/`; opening `web-demo/index.html` directly does not provide the required `/api/*` backend.
- Host and file payload uploads are limited to 20 MB, while text messages are limited to 1 MB.
- `/api/capacity` reports raw usable payload bytes after accounting for the payload header, embedded filename, and optional Fernet encryption expansion.
- The web API accepts only PNG, BMP, GIF, WebP, WAV, JPG, and JPEG hosts; unlike the CLI/library path, it does not accept arbitrary Pillow-readable image formats for conversion.
- Uploads and generated files are processed in temporary directories and removed by response background tasks.
- `web-demo/` is outside the `stegpy` package and is not currently included in built wheels.
- Host parsing, capacity calculation, encoding, and decoding are dispatched through Starlette's thread pool so CPU-bound image/audio work does not block the event loop.

## File Format Handling
- Images:
  - Non-GIF image hosts are opened with Pillow and converted to `RGB` if needed.
  - Supported save targets are effectively lossless image formats plus format-conversion to PNG when the original extension is unsupported.
- JPEG:
  - JPEG hosts are loaded and saved through `jpeglib`, not Pillow pixel arrays.
  - Payload bits live in quantized AC DCT coefficients rather than pixel bytes.
- GIF:
  - Each frame is loaded into a NumPy array and palettes/duration are preserved separately.
  - Save reconstructs the animation frame-by-frame.
- WAV:
  - The code reads raw bytes with NumPy and treats the first `10000` bytes as "header" and the remainder as mutable payload area.
  - This is a project-specific simplification, not a general WAV parser.

## Important Implementation Details
- `lsb.py` contains almost all behavior that matters.
- `HostElement.save()` always writes to a new filename by prefixing `_` to the original host path.
- `HostElement.read_message()` also prefixes extracted embedded filenames with `_`.
- Bit depth is stored inside bits 5 and 6 of the first host byte, allowing the decoder to recover whether 1, 2, or 4 LSBs were used.
- `encode_message()` flattens the NumPy array, writes the payload across interleaved positions, then restores the original shape.
- If the flattened host size is not divisible by `8 // bits`, the code pads with `numpy.resize()` and trims back afterward.

## Encryption Notes
- `crypt.py` derives a 32-byte key from the provided password using PBKDF2-HMAC-SHA256 with 100000 iterations.
- A random 16-byte salt is generated during encryption and prepended to the encrypted token.
- Decryption expects the first 16 bytes of the extracted payload to be the salt.

## CLI Behavior
- Main usage pattern:
  - Encode text: `stegpy "hello" image.png`
  - Encode file: `stegpy secret.bin image.png`
  - Decode: `stegpy _image.png`
  - Check capacity: `stegpy file1 file2 -c`
- `-b/--bits` accepts `1`, `2`, or `4` and defaults to `2`.
- `-p/--password` enables encryption on write and decryption on read using interactive password prompts.
- If the first positional argument is an existing file, the CLI embeds file contents; otherwise it treats it as a literal text message.

## Testing And Tooling
- The repo now has a `uv`-based workflow.
- Set up the environment with:
  - `uv sync --dev`
- Main test command:
  - `uv run pytest`
- The modern pytest suite covers:
  - low-level encode/decode behavior
  - payload formatting
  - encryption helpers
  - CLI smoke tests
  - end-to-end PNG, GIF, WAV, and JPEG host flows
  - FastAPI health, capacity, encode/decode, encryption, file payload, GIF, and upload-limit behavior

## Known Quirks / Risks
- The codebase uses broad `except:` imports and decryption error handling.
- `HostElement.print_free_space()` hardcodes the string `encoding: 4 bit` even though the method accepts other bit depths.
- `check_message_space()` and `check_magic_number()` call `exit(-1)` instead of raising structured exceptions.
- WAV support is simplistic because of the fixed `10000`-byte split.
- GIF palette/duration handling is intentionally basic and should stay covered by end-to-end tests.

## Practical Guidance For Future Agents
- Start in `stegpy/lsb.py` if behavior changes touch encoding, capacity, host parsing, or extraction.
- Start in `stegpy/steg.py` if the task is mostly about CLI UX or argument parsing.
- Start in `stegpy/web.py` and `tests/test_web.py` for API behavior, limits, temporary-file handling, or browser-demo integration.
- Preserve current output behavior unless the user asks for cleanup; this project prints status directly and uses underscore-prefixed output filenames.
- Be careful not to "improve" exception handling, path behavior, or file naming implicitly without checking for compatibility expectations.
- If you add features, strongly consider adding end-to-end tests around:
  - text payload round-trip
  - file payload round-trip
  - encrypted round-trip
  - each supported host type
