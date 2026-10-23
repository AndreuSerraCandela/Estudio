(() => {
  const tbody = document.getElementById("documentos-tbody");
  const previewPanel = document.getElementById("document-preview");
  const iframeEl = document.getElementById("preview-iframe");
  if (!tbody || !previewPanel || !iframeEl) return;

  const titleEl = document.getElementById("preview-title");
  const openEl = document.getElementById("preview-open");
  const statusEl = document.getElementById("preview-status");
  const viewerOrigin = previewPanel.dataset.viewerOrigin || "";
  const uploadUrl = previewPanel.dataset.uploadUrl || "";
  const sessionCache = new Map();

  let lockedRow = null;
  let viewerReady = false;
  let pendingRow = null;
  let hoverTimer = null;

  function rows() {
    return Array.from(tbody.querySelectorAll(".doc-preview-row")).filter((row) => !row.hidden);
  }

  function setStatus(message, isError = false) {
    if (!statusEl) return;
    statusEl.hidden = !message;
    statusEl.textContent = message || "";
    statusEl.classList.toggle("is-error", isError);
  }

  function callViewer(method, args) {
    if (!viewerReady || !iframeEl.contentWindow) return;
    iframeEl.contentWindow.postMessage({ method, args }, viewerOrigin || "*");
  }

  function fileType(row) {
    const mime = row.dataset.docMime || "";
    if (mime) return mime;
    const tipo = row.dataset.docTipo || "";
    if (tipo === "imagen") return "image/jpeg";
    if (tipo === "pdf") return "application/pdf";
    if (tipo === "mail") return "message/rfc822";
    return row.dataset.docNombre || "application/octet-stream";
  }

  function loadsByUrl(row) {
    const mime = (row.dataset.docMime || "").toLowerCase();
    const tipo = row.dataset.docTipo || "";
    const url = (row.dataset.docUrl || "").toLowerCase();
    return tipo === "imagen" || mime.startsWith("image/") || /\.(jpg|jpeg|png|gif|webp|bmp|tif|tiff)(\?|$)/.test(url);
  }

  function mark(row) {
    rows().forEach((item) => item.classList.toggle("is-active", item === row));
    const index = rows().indexOf(row);
    if (titleEl) titleEl.textContent = row.dataset.docNombre || "Documento";
    if (openEl) {
      openEl.href = row.dataset.docUrl || "#";
      openEl.hidden = !row.dataset.docUrl;
    }
    callViewer("Ficheros", [rows().length || 1]);
    callViewer("Fichero", [index + 1]);
  }

  async function sessionFor(row) {
    const sessionUrl = row.dataset.viewerSessionUrl;
    if (!sessionUrl) throw new Error("Este documento no se puede abrir en el visor.");
    if (sessionCache.has(sessionUrl)) return sessionCache.get(sessionUrl);
    const response = await fetch(sessionUrl, {
      method: "POST",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || "No se pudo abrir el documento en el visor.");
    sessionCache.set(sessionUrl, payload);
    return payload;
  }

  async function showPreview(row) {
    if (!row) return;
    mark(row);
    if (!viewerReady) {
      pendingRow = row;
      return;
    }
    setStatus("");
    if (loadsByUrl(row)) {
      callViewer("LoadOtros", [fileType(row), "", row.dataset.docUrl || ""]);
      return;
    }
    setStatus("Cargando en el visor...");
    try {
      const payload = await sessionFor(row);
      callViewer("loadSession", [payload.previewId]);
      if (openEl && payload.expandedUrl) openEl.href = payload.expandedUrl;
      setStatus("");
    } catch (error) {
      setStatus(error.message || "No se pudo cargar el documento.", true);
    }
  }

  function move(step) {
    const list = rows();
    if (!list.length) return;
    const current = list.indexOf(lockedRow);
    const next = list[Math.min(list.length - 1, Math.max(0, (current < 0 ? 0 : current) + step))];
    if (!next || next === lockedRow) return;
    lockedRow = next;
    showPreview(next);
    next.scrollIntoView({ block: "nearest" });
  }

  function bindRow(row) {
    row.addEventListener("mouseenter", () => {
      if (lockedRow || !loadsByUrl(row)) return;
      if (hoverTimer) window.clearTimeout(hoverTimer);
      hoverTimer = window.setTimeout(() => showPreview(row), 200);
    });
    row.addEventListener("click", (event) => {
      if (event.target.closest("form, button")) return;
      lockedRow = row;
      showPreview(row);
    });
    row.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      lockedRow = row;
      showPreview(row);
    });
  }

  function fileFromBase64(name, content) {
    const binary = atob(content || "");
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return new File([bytes], name || "archivo", { type: "application/octet-stream" });
  }

  async function saveUploaded(files) {
    if (!uploadUrl || !files.length) return;
    setStatus("Guardando en el expediente...");
    const saved = [];
    for (const file of files) {
      const formData = new FormData();
      formData.append("archivo", file, file.name);
      const response = await fetch(uploadUrl, { method: "POST", body: formData, credentials: "same-origin" });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || `No se pudo guardar ${file.name}`);
      saved.push(payload);
    }
    document.dispatchEvent(new CustomEvent("document-preview:files-saved", { detail: { documents: saved } }));
    setStatus("");
  }

  rows().forEach(bindRow);

  function mostrarSeccion() {
    const lista = rows();
    lockedRow = lista[0] || null;
    pendingRow = lockedRow;
    if (lockedRow) {
      showPreview(lockedRow);
      return;
    }
    if (titleEl) titleEl.textContent = "Selecciona un documento";
    if (openEl) openEl.hidden = true;
    callViewer("ClearFiles", []);
  }

  iframeEl.addEventListener("load", () => {
    viewerReady = true;
    const row = pendingRow || lockedRow || rows()[0];
    if (row) showPreview(row);
  });

  window.addEventListener("hashchange", () => {
    window.setTimeout(mostrarSeccion, 0);
  });

  window.addEventListener("message", (event) => {
    if (event.source !== iframeEl.contentWindow) return;
    if (viewerOrigin && event.origin !== viewerOrigin) return;
    const data = event.data;
    if (!data || data.source !== "malla-doc-viewer") return;
    if (data.event === "OnSiguiente") {
      move(1);
      return;
    }
    if (data.event === "OnAnterior") {
      move(-1);
      return;
    }
    if (data.event !== "FileUploaded") return;
    let uploaded = [];
    try {
      uploaded = JSON.parse((data.args && data.args[0]) || "[]");
    } catch (_error) {
      return;
    }
    const files = uploaded
      .filter((item) => item && item.name && item.content)
      .map((item) => fileFromBase64(item.name, item.content));
    saveUploaded(files).catch((error) => {
      setStatus(error.message || "No se pudieron guardar los archivos.", true);
    });
  });

  document.addEventListener("document-preview:row-added", (event) => {
    const row = event.detail && event.detail.row;
    if (!row) return;
    bindRow(row);
  });
})();
