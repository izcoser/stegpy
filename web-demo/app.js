"use strict";

const SUPPORTED_HOSTS = new Set(["png", "bmp", "gif", "webp", "wav", "jpg", "jpeg"]);
const MAX_HOST_BYTES = 20 * 1024 * 1024;
const MAX_PAYLOAD_BYTES = 20 * 1024 * 1024;

function extensionFor(file) {
  return extensionForName(file?.name || "");
}

function extensionForName(name) {
  return (name.split(".").pop() || "").toLowerCase();
}

function isImageExtension(extension) {
  return ["png", "bmp", "gif", "webp", "jpg", "jpeg"].includes(extension);
}

function isImageHost(file) {
  return isImageExtension(extensionFor(file));
}

function isPreviewableImage(blob, filename) {
  return blob.type.startsWith("image/") || isImageExtension(extensionForName(filename));
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
    return file?.size || 0;
  }
  return new TextEncoder().encode(text).length;
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
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
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
  const decodedTextField = document.getElementById("decoded-text-field");
  const decodedOutput = document.getElementById("decoded-output");
  const statusOutput = document.getElementById("status-output");
  const encodeTab = document.getElementById("encode-tab");
  const decodeTab = document.getElementById("decode-tab");
  const encodePanel = document.getElementById("encode-panel");
  const decodePanel = document.getElementById("decode-panel");
  const encodeResult = document.getElementById("encode-result");
  const encodeResultSummary = document.getElementById("encode-result-summary");
  const encodedUseButton = document.getElementById("encoded-use-button");
  const encodedDownloadButton = document.getElementById("encoded-download-button");
  const originalResultImage = document.getElementById("original-result-image");
  const originalResultFile = document.getElementById("original-result-file");
  const originalResultName = document.getElementById("original-result-name");
  const originalResultMeta = document.getElementById("original-result-meta");
  const encodedResultImage = document.getElementById("encoded-result-image");
  const encodedResultFile = document.getElementById("encoded-result-file");
  const encodedResultName = document.getElementById("encoded-result-name");
  const encodedResultMeta = document.getElementById("encoded-result-meta");
  const decodeResult = document.getElementById("decode-result");
  const decodeResultSummary = document.getElementById("decode-result-summary");
  const decodedDownloadButton = document.getElementById("decoded-download-button");
  const decodedFilePreview = document.getElementById("decoded-file-preview");
  const decodedResultImage = document.getElementById("decoded-result-image");
  const decodedResultFile = document.getElementById("decoded-result-file");
  const decodedResultName = document.getElementById("decoded-result-name");
  const decodedResultMeta = document.getElementById("decoded-result-meta");
  let currentHost = null;
  let capacityRequestId = 0;
  let capacityEncrypted = false;
  let encodedBlob = null;
  let encodedFilename = "";
  let decodedBlob = null;
  let decodedFilename = "";
  let encodePreviewUrls = [];
  let decodePreviewUrls = [];

  const originalSlot = {
    image: originalResultImage,
    file: originalResultFile,
    name: originalResultName,
    meta: originalResultMeta,
  };
  const encodedSlot = {
    image: encodedResultImage,
    file: encodedResultFile,
    name: encodedResultName,
    meta: encodedResultMeta,
  };
  const decodedSlot = {
    image: decodedResultImage,
    file: decodedResultFile,
    name: decodedResultName,
    meta: decodedResultMeta,
  };

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

  function revokePreviewUrls(urls) {
    for (const url of urls) {
      URL.revokeObjectURL(url);
    }
    urls.length = 0;
  }

  function trackedUrl(blob, urls) {
    const url = URL.createObjectURL(blob);
    urls.push(url);
    return url;
  }

  function resetMediaSlot(slot) {
    slot.image.hidden = true;
    slot.image.removeAttribute("src");
    slot.image.alt = "";
    slot.file.hidden = true;
    slot.name.textContent = "";
    slot.meta.textContent = "";
  }

  function mediaMeta(blob, filename) {
    const extension = extensionForName(filename).toUpperCase();
    const kind = extension || blob.type || "file";
    return `${kind} · ${formatBytes(blob.size)}`;
  }

  function renderMediaSlot(slot, blob, filename, urls) {
    resetMediaSlot(slot);
    slot.name.textContent = filename;
    slot.meta.textContent = mediaMeta(blob, filename);

    if (isPreviewableImage(blob, filename)) {
      slot.image.src = trackedUrl(blob, urls);
      slot.image.alt = filename;
      slot.image.hidden = false;
      return;
    }

    slot.file.hidden = false;
  }

  function clearEncodeResult() {
    revokePreviewUrls(encodePreviewUrls);
    encodedBlob = null;
    encodedFilename = "";
    encodeResult.hidden = true;
    encodeResultSummary.textContent = "";
    encodedUseButton.disabled = true;
    encodedDownloadButton.disabled = true;
    resetMediaSlot(originalSlot);
    resetMediaSlot(encodedSlot);
  }

  function clearDecodeResult() {
    revokePreviewUrls(decodePreviewUrls);
    decodedBlob = null;
    decodedFilename = "";
    decodeResult.hidden = true;
    decodeResultSummary.textContent = "";
    decodedDownloadButton.hidden = true;
    decodedDownloadButton.disabled = true;
    decodedFilePreview.hidden = true;
    decodedTextField.hidden = false;
    resetMediaSlot(decodedSlot);
  }

  function showEncodeResult(blob, filename) {
    clearEncodeResult();
    encodedBlob = blob;
    encodedFilename = filename;
    renderMediaSlot(originalSlot, currentHost, currentHost.name, encodePreviewUrls);
    renderMediaSlot(encodedSlot, blob, filename, encodePreviewUrls);
    encodeResultSummary.textContent = (
      `Created ${filename} (${formatBytes(blob.size)}). ` +
      "Compare it with the original, then download when ready."
    );
    encodedUseButton.disabled = false;
    encodedDownloadButton.disabled = false;
    encodeResult.hidden = false;
    encodeResult.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showDecodeText(message) {
    clearDecodeResult();
    decodedOutput.value = message;
    decodeResultSummary.textContent = "Decoded a text payload from the selected host.";
    decodeResult.hidden = false;
    decodeResult.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showDecodeFile(blob, filename) {
    clearDecodeResult();
    decodedBlob = blob;
    decodedFilename = filename;
    decodedOutput.value = "";
    decodedTextField.hidden = true;
    renderMediaSlot(decodedSlot, blob, filename, decodePreviewUrls);
    decodedFilePreview.hidden = false;
    decodedDownloadButton.hidden = false;
    decodedDownloadButton.disabled = false;
    decodeResultSummary.textContent = (
      `Decoded ${filename} (${formatBytes(blob.size)}). ` +
      "Preview it here, then download when ready."
    );
    decodeResult.hidden = false;
    decodeResult.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
    formData.append("mode", selectedMode());
    formData.append("filename", payloadInput.files[0]?.name || "");
    formData.append("encrypted", String(Boolean(encodePasswordInput.value)));
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
    clearEncodeResult();
    clearDecodeResult();
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
  payloadModeInput.addEventListener("change", () => {
    clearEncodeResult();
    updatePayloadMode();
    refreshCapacity();
  });
  messageInput.addEventListener("input", () => {
    clearEncodeResult();
    updateStats();
  });
  payloadInput.addEventListener("change", () => {
    clearEncodeResult();
    const payload = payloadInput.files[0];
    if (payload?.size > MAX_PAYLOAD_BYTES) {
      setStatus("Payload files are limited to 20 MB.", true);
    }
    updateStats();
    refreshCapacity();
  });
  bitsInput.addEventListener("change", () => {
    clearEncodeResult();
    refreshCapacity();
  });
  encodePasswordInput.addEventListener("input", () => {
    clearEncodeResult();
    const encrypted = Boolean(encodePasswordInput.value);
    if (encrypted !== capacityEncrypted) {
      capacityEncrypted = encrypted;
      refreshCapacity();
    }
  });
  decodePasswordInput.addEventListener("input", clearDecodeResult);
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
      clearEncodeResult();
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
      showEncodeResult(blob, filename);
      setStatus(`Encoded ${filename}. Review it below before downloading.`, false, true);
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      updateStats();
    }
  });

  decodeButton.addEventListener("click", async () => {
    try {
      clearDecodeResult();
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
        showDecodeText(data.message);
        setStatus("Decoded text payload.", false, true);
      } else {
        const blob = await response.blob();
        const filename = filenameFromDisposition(
          response.headers.get("content-disposition"),
          "payload.bin"
        );
        showDecodeFile(blob, filename);
        setStatus(`Decoded embedded file ${filename}.`, false, true);
      }
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      updateStats();
    }
  });

  encodedDownloadButton.addEventListener("click", () => {
    if (encodedBlob) {
      downloadBlob(encodedBlob, encodedFilename || `_${currentHost.name}`);
    }
  });

  encodedUseButton.addEventListener("click", () => {
    if (!encodedBlob) {
      return;
    }

    const filename = encodedFilename || `_${currentHost.name}`;
    const file = new File([encodedBlob], filename, {
      type: encodedBlob.type || currentHost.type || "application/octet-stream",
    });
    switchMode("decode");
    loadHost(file);
    setStatus(`Loaded ${filename} for decoding.`, false, true);
  });

  decodedDownloadButton.addEventListener("click", () => {
    if (decodedBlob) {
      downloadBlob(decodedBlob, decodedFilename || "payload.bin");
    }
  });

  updatePayloadMode();
  updateStats();
  clearEncodeResult();
  clearDecodeResult();
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", setupDemo);
}
