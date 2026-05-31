"use strict";

const MAGIC = new Uint8Array([115, 116, 101, 103, 118, 51]);
const HEADER_SIZE = 11;
const BITS_TO_MARKER = new Map([
  [1, 0],
  [2, 16],
  [4, 32],
]);
const MARKER_TO_BITS = new Map([
  [0, 1],
  [1, 2],
  [2, 4],
]);

function rgbCarrierCount(imageData) {
  return (imageData.data.length / 4) * 3;
}

function capacityBytes(imageData, bits) {
  return Math.floor(rgbCarrierCount(imageData) / (8 / bits));
}

function formatTextPayload(text) {
  const body = new TextEncoder().encode(text);
  if (body.length > 0xffffffff) {
    throw new Error("Message is too large.");
  }

  const payload = new Uint8Array(HEADER_SIZE + body.length);
  payload.set(MAGIC, 0);
  payload[6] = (body.length >>> 24) & 0xff;
  payload[7] = (body.length >>> 16) & 0xff;
  payload[8] = (body.length >>> 8) & 0xff;
  payload[9] = body.length & 0xff;
  payload[10] = 0;
  payload.set(body, HEADER_SIZE);
  return payload;
}

function isAlphaOffset(offset) {
  return offset % 4 === 3;
}

function nextRgbOffset(offset, dataLength) {
  while (offset < dataLength && isAlphaOffset(offset)) {
    offset += 1;
  }
  return offset;
}

function encodeTextIntoImageData(sourceImageData, text, bits) {
  const payload = formatTextPayload(text);
  const maxBytes = capacityBytes(sourceImageData, bits);
  if (payload.length > maxBytes) {
    throw new Error(`Message needs ${payload.length} bytes, but this PNG can hold ${maxBytes} bytes at ${bits} bit.`);
  }

  const encoded = new ImageData(
    new Uint8ClampedArray(sourceImageData.data),
    sourceImageData.width,
    sourceImageData.height
  );
  const data = encoded.data;
  const mask = (1 << bits) - 1;
  const clearMask = 256 - (1 << bits);
  const chunksPerByte = 8 / bits;
  let offset = 0;

  for (const byte of payload) {
    for (let chunk = 0; chunk < chunksPerByte; chunk += 1) {
      offset = nextRgbOffset(offset, data.length);
      data[offset] = (data[offset] & clearMask) | ((byte >> (bits * chunk)) & mask);
      offset += 1;
    }
  }

  data[0] = (data[0] & 207) | BITS_TO_MARKER.get(bits);
  return encoded;
}

function decodeBytesFromImageData(imageData) {
  const data = imageData.data;
  const marker = (data[0] & 48) >> 4;
  const bits = MARKER_TO_BITS.get(marker) || 2;
  const mask = (1 << bits) - 1;
  const chunksPerByte = 8 / bits;
  const maxBytes = capacityBytes(imageData, bits);
  const bytes = new Uint8Array(maxBytes);
  let offset = 0;

  for (let byteIndex = 0; byteIndex < maxBytes; byteIndex += 1) {
    let byte = 0;

    for (let chunk = 0; chunk < chunksPerByte; chunk += 1) {
      offset = nextRgbOffset(offset, data.length);
      byte |= (data[offset] & mask) << (bits * chunk);
      offset += 1;
    }

    bytes[byteIndex] = byte;
  }

  return { bytes, bits };
}

function decodeTextFromImageData(imageData) {
  const { bytes, bits } = decodeBytesFromImageData(imageData);
  for (let index = 0; index < MAGIC.length; index += 1) {
    if (bytes[index] !== MAGIC[index]) {
      throw new Error("No stegpy text payload was found in this PNG.");
    }
  }

  const filenameLength = bytes[10];
  if (filenameLength !== 0) {
    throw new Error("This payload contains an embedded file. Use the Python package to extract it.");
  }

  const messageLength =
    bytes[6] * 0x1000000 +
    (bytes[7] << 16) +
    (bytes[8] << 8) +
    bytes[9];
  const start = HEADER_SIZE;
  const end = start + messageLength;
  if (end > bytes.length) {
    throw new Error(`The payload header says ${messageLength} bytes, but the PNG only has ${bytes.length - HEADER_SIZE} readable bytes at ${bits} bit.`);
  }

  return new TextDecoder("utf-8", { fatal: true }).decode(bytes.slice(start, end));
}

function downloadCanvasPng(canvas, filename, onError) {
  canvas.toBlob((blob) => {
    if (!blob) {
      onError("Could not create a PNG download.");
      return;
    }

    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }, "image/png");
}

function setupDemo() {
  const imageInput = document.getElementById("image-input");
  const dropZone = document.getElementById("drop-zone");
  const canvas = document.getElementById("preview-canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  const messageInput = document.getElementById("message-input");
  const bitsInput = document.getElementById("bits-input");
  const capacityOutput = document.getElementById("capacity-output");
  const payloadOutput = document.getElementById("payload-output");
  const encodeButton = document.getElementById("encode-button");
  const decodeButton = document.getElementById("decode-button");
  const decodedOutput = document.getElementById("decoded-output");
  const statusOutput = document.getElementById("status-output");
  const encodeTab = document.getElementById("encode-tab");
  const decodeTab = document.getElementById("decode-tab");
  const encodePanel = document.getElementById("encode-panel");
  const decodePanel = document.getElementById("decode-panel");
  let currentImageData = null;
  let currentFilename = "encoded.png";

  function setStatus(message, isError = false, isSuccess = false) {
    statusOutput.textContent = message;
    statusOutput.classList.toggle("is-error", isError);
    statusOutput.classList.toggle("is-success", isSuccess);
  }

  function selectedBits() {
    return Number.parseInt(bitsInput.value, 10);
  }

  function updateStats() {
    const payloadSize = formatTextPayload(messageInput.value).length;
    payloadOutput.textContent = `${payloadSize.toLocaleString()} bytes`;

    if (!currentImageData) {
      capacityOutput.textContent = "No image";
      encodeButton.disabled = true;
      decodeButton.disabled = true;
      return;
    }

    const capacity = capacityBytes(currentImageData, selectedBits());
    capacityOutput.textContent = `${capacity.toLocaleString()} bytes`;
    encodeButton.disabled = payloadSize > capacity;
    decodeButton.disabled = false;
  }

  function drawImageToCanvas(image) {
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    currentImageData = context.getImageData(0, 0, canvas.width, canvas.height);
    updateStats();
  }

  function loadPng(file) {
    if (!file || file.type !== "image/png") {
      setStatus("Choose a PNG file.", true);
      return;
    }

    currentFilename = file.name.replace(/\.png$/i, "") || "encoded";
    const image = new Image();
    const url = URL.createObjectURL(file);

    image.addEventListener("load", () => {
      URL.revokeObjectURL(url);
      drawImageToCanvas(image);
      decodedOutput.value = "";
      setStatus(`Loaded ${file.name}.`, false, true);
    });
    image.addEventListener("error", () => {
      URL.revokeObjectURL(url);
      setStatus("The selected PNG could not be loaded.", true);
    });
    image.src = url;
  }

  function switchMode(mode) {
    const isEncode = mode === "encode";
    encodeTab.classList.toggle("is-active", isEncode);
    decodeTab.classList.toggle("is-active", !isEncode);
    encodeTab.setAttribute("aria-selected", String(isEncode));
    decodeTab.setAttribute("aria-selected", String(!isEncode));
    encodePanel.classList.toggle("is-active", isEncode);
    decodePanel.classList.toggle("is-active", !isEncode);
    encodePanel.hidden = !isEncode;
    decodePanel.hidden = isEncode;
  }

  imageInput.addEventListener("change", () => loadPng(imageInput.files[0]));
  messageInput.addEventListener("input", updateStats);
  bitsInput.addEventListener("change", updateStats);
  encodeTab.addEventListener("click", () => switchMode("encode"));
  decodeTab.addEventListener("click", () => switchMode("decode"));

  dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("is-dragging"));
  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
    loadPng(event.dataTransfer.files[0]);
  });

  encodeButton.addEventListener("click", () => {
    try {
      const encoded = encodeTextIntoImageData(currentImageData, messageInput.value, selectedBits());
      context.putImageData(encoded, 0, 0);
      currentImageData = context.getImageData(0, 0, canvas.width, canvas.height);
      downloadCanvasPng(canvas, `_${currentFilename}.png`, (message) => setStatus(message, true));
      setStatus("Encoded PNG is ready for download.", false, true);
      updateStats();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  decodeButton.addEventListener("click", () => {
    try {
      decodedOutput.value = decodeTextFromImageData(currentImageData);
      setStatus("Decoded text payload.", false, true);
    } catch (error) {
      decodedOutput.value = "";
      setStatus(error.message, true);
    }
  });

  updateStats();
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", setupDemo);
}

if (typeof module !== "undefined") {
  module.exports = {
    capacityBytes,
    decodeTextFromImageData,
    encodeTextIntoImageData,
    formatTextPayload,
    rgbCarrierCount,
  };
}
