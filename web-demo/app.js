"use strict";

const SUPPORTED_HOSTS = new Set(["png", "bmp", "gif", "webp", "wav", "jpg", "jpeg"]);
const HEADER_SIZE = 11;
const MAX_HOST_BYTES = 20 * 1024 * 1024;
const MAX_PAYLOAD_BYTES = 20 * 1024 * 1024;

function extensionFor(file) {
  return (file?.name.split(".").pop() || "").toLowerCase();
}

function isImageHost(file) {
  return ["png", "bmp", "gif", "webp", "jpg", "jpeg"].includes(extensionFor(file));
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) {
    return "unknown";
  }

  const units = ["bytes", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toLocaleString(undefined, { maximumFractionDigits: unitIndex ? 1 : 0 })} ${units[unitIndex]}`;
}

function payloadEstimate(mode, text, file) {
  if (mode === "file") {
    return HEADER_SIZE + (file?.name.length || 0) + (file?.size || 0);
  }
  return HEADER_SIZE + new TextEncoder().encode(text).length;
}

async function postForm(url, formData) {
  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    const body = await response.text();

    if (body) {
      try {
        const error = JSON.parse(body);
        message = error.detail || message;
      } catch {
        if (response.status !== 413 && !body.trim().startsWith("<")) {
          message = body;
        }
      }
    }

    if (response.status === 413 && message === `${response.status} ${response.statusText}`) {
      message = "Upload is too large. Host and payload files are limited to 20 MB each.";
    }
    throw new Error(message);
  }

  return response;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function filenameFromDisposition(disposition, fallback) {
  const match = /filename="?([^"]+)"?/i.exec(disposition || "");
  return match ? match[1] : fallback;
}

function setupDemo() {
  const hostInput = document.getElementById("host-input");
  const dropZone = document.getElementById("drop-zone");
  const canvas = document.getElementById("preview-canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  const filePreview = document.getElementById("file-preview");
  const filePreviewName = document.getElementById("file-preview-name");
  const filePreviewMeta = document.getElementById("file-preview-meta");
  const payloadModeInput = document.getElementById("payload-mode-input");
  const messageField = document.getElementById("message-field");
  const payloadField = document.getElementById("payload-field");
  const messageInput = document.getElementById("message-input");
  const payloadInput = document.getElementById("payload-input");
  const bitsInput = document.getElementById("bits-input");
  const capacityOutput = document.getElementById("capacity-output");
  const payloadOutput = document.getElementById("payload-output");
  const encodePasswordInput = document.getElementById("encode-password-input");
  const decodePasswordInput = document.getElementById("decode-password-input");
  const encodeButton = document.getElementById("encode-button");
  const decodeButton = document.getElementById("decode-button");
  const decodedOutput = document.getElementById("decoded-output");
  const statusOutput = document.getElementById("status-output");
  const encodeTab = document.getElementById("encode-tab");
  const decodeTab = document.getElementById("decode-tab");
  const encodePanel = document.getElementById("encode-panel");
  const decodePanel = document.getElementById("decode-panel");
  let currentHost = null;
  let capacityRequestId = 0;

  function setStatus(message, isError = false, isSuccess = false) {
    statusOutput.textContent = message;
    statusOutput.classList.toggle("is-error", isError);
    statusOutput.classList.toggle("is-success", isSuccess);
  }

  function selectedBits() {
    return Number.parseInt(bitsInput.value, 10);
  }

  function selectedMode() {
    return payloadModeInput.value;
  }

  function updatePayloadMode() {
    const fileMode = selectedMode() === "file";
    messageField.hidden = fileMode;
    payloadField.hidden = !fileMode;
    updateStats();
  }

  function updateStats() {
    const estimate = payloadEstimate(selectedMode(), messageInput.value, payloadInput.files[0]);
    payloadOutput.textContent = formatBytes(estimate);
    encodeButton.disabled = !currentHost;
    decodeButton.disabled = !currentHost;

    if (!currentHost) {
      capacityOutput.textContent = "No host";
    }
  }

  async function refreshCapacity() {
    updateStats();
    if (!currentHost) {
      return;
    }

    const requestId = ++capacityRequestId;
    const formData = new FormData();
    formData.append("host", currentHost);
    formData.append("bits", String(selectedBits()));
    capacityOutput.textContent = "Checking...";

    try {
      const response = await postForm("/api/capacity", formData);
      const data = await response.json();
      if (requestId === capacityRequestId) {
        capacityOutput.textContent = formatBytes(data.capacityBytes);
      }
    } catch (error) {
      if (requestId === capacityRequestId) {
        capacityOutput.textContent = "Unavailable";
        setStatus(error.message, true);
      }
    }
  }

  function showFilePreview(file) {
    canvas.hidden = true;
    filePreview.hidden = false;
    filePreviewName.textContent = file.name;
    filePreviewMeta.textContent = `${extensionFor(file).toUpperCase()} host, ${formatBytes(file.size)}`;
  }

  function drawImagePreview(file) {
    const image = new Image();
    const url = URL.createObjectURL(file);

    image.addEventListener("load", () => {
      URL.revokeObjectURL(url);
      canvas.hidden = false;
      filePreview.hidden = true;
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
    });

    image.addEventListener("error", () => {
      URL.revokeObjectURL(url);
      showFilePreview(file);
    });

    image.src = url;
  }

  function loadHost(file) {
    if (!file) {
      return;
    }

    if (file.size > MAX_HOST_BYTES) {
      setStatus("Host files are limited to 20 MB.", true);
      return;
    }

    const extension = extensionFor(file);
    if (!SUPPORTED_HOSTS.has(extension)) {
      setStatus("Choose a PNG, BMP, GIF, WebP, WAV, JPG, or JPEG host file.", true);
      return;
    }

    currentHost = file;
    decodedOutput.value = "";
    if (isImageHost(file)) {
      drawImagePreview(file);
    } else {
      showFilePreview(file);
    }
    setStatus(`Loaded ${file.name}.`, false, true);
    refreshCapacity();
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

  hostInput.addEventListener("change", () => loadHost(hostInput.files[0]));
  payloadModeInput.addEventListener("change", updatePayloadMode);
  messageInput.addEventListener("input", updateStats);
  payloadInput.addEventListener("change", () => {
    const payload = payloadInput.files[0];
    if (payload?.size > MAX_PAYLOAD_BYTES) {
      setStatus("Payload files are limited to 20 MB.", true);
    }
    updateStats();
  });
  bitsInput.addEventListener("change", refreshCapacity);
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
    loadHost(event.dataTransfer.files[0]);
  });

  encodeButton.addEventListener("click", async () => {
    try {
      if (!currentHost) {
        throw new Error("Choose a host file first.");
      }
      if (selectedMode() === "file" && !payloadInput.files[0]) {
        throw new Error("Choose a payload file.");
      }
      if (payloadInput.files[0]?.size > MAX_PAYLOAD_BYTES) {
        throw new Error("Payload files are limited to 20 MB.");
      }

      encodeButton.disabled = true;
      setStatus("Encoding with stegpy...");

      const formData = new FormData();
      formData.append("host", currentHost);
      formData.append("mode", selectedMode());
      formData.append("message", messageInput.value);
      formData.append("bits", String(selectedBits()));
      formData.append("password", encodePasswordInput.value);
      if (selectedMode() === "file") {
        formData.append("payload", payloadInput.files[0]);
      }

      const response = await postForm("/api/encode", formData);
      const blob = await response.blob();
      const filename = filenameFromDisposition(
        response.headers.get("content-disposition"),
        `_${currentHost.name}`
      );
      downloadBlob(blob, filename);
      setStatus(`Encoded ${filename}.`, false, true);
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      updateStats();
    }
  });

  decodeButton.addEventListener("click", async () => {
    try {
      if (!currentHost) {
        throw new Error("Choose a host file first.");
      }

      decodeButton.disabled = true;
      decodedOutput.value = "";
      setStatus("Decoding with stegpy...");

      const formData = new FormData();
      formData.append("host", currentHost);
      formData.append("password", decodePasswordInput.value);

      const response = await postForm("/api/decode", formData);
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const data = await response.json();
        decodedOutput.value = data.message;
        setStatus("Decoded text payload.", false, true);
      } else {
        const blob = await response.blob();
        const filename = filenameFromDisposition(
          response.headers.get("content-disposition"),
          "payload.bin"
        );
        downloadBlob(blob, filename);
        setStatus(`Decoded embedded file ${filename}.`, false, true);
      }
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      updateStats();
    }
  });

  updatePayloadMode();
  updateStats();
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", setupDemo);
}
