(() => {
  const panel = document.getElementById("documentos-panel");
  const dropZone = document.getElementById("document-drop-zone");
  const tbody = document.getElementById("documentos-tbody");
  const table = document.getElementById("documentos-table");
  const scrollPanel = document.getElementById("documentos-scroll");
  const emptyState = document.getElementById("documentos-empty");
  const statusEl = document.getElementById("document-upload-status");

  if (!panel || !dropZone || !tbody) return;

  const uploadUrl = panel.dataset.uploadUrl;
  let dragDepth = 0;

  function setStatus(message, isError = false) {
    if (!statusEl) return;
    statusEl.hidden = !message;
    statusEl.textContent = message;
    statusEl.classList.toggle("is-error", isError);
  }

  function showTable() {
    if (scrollPanel) scrollPanel.hidden = false;
    if (table) table.hidden = false;
    if (emptyState) emptyState.hidden = true;
  }

  function appendDocumentRow(doc) {
    const tr = document.createElement("tr");
    tr.className = "doc-preview-row";
    tr.tabIndex = 0;
    tr.draggable = true;
    tr.dataset.docId = String(doc.id);
    tr.dataset.docNombre = doc.nombre;
    tr.dataset.docTipo = doc.tipo || "";
    tr.dataset.docUrl = doc.url;
    tr.dataset.previewKind = doc.preview_kind || "other";
    tr.dataset.previewSrc = doc.preview_src || doc.url;

    const desc = doc.descripcion
      ? `<br><small class="muted">${escapeHtml(doc.descripcion)}</small>`
      : "";

    tr.innerHTML = `
      <td>
        <span class="doc-name">${escapeHtml(doc.nombre)}</span>
        ${desc}
      </td>
      <td><span class="badge">${escapeHtml(doc.tipo_label)}</span></td>
      <td>
        <form method="post" action="${escapeHtml(doc.delete_url)}"
              onsubmit="return confirm('¿Eliminar este documento?')">
          <button type="submit" class="btn btn-sm btn-danger">Eliminar</button>
        </form>
      </td>
    `;
    tbody.prepend(tr);
    showTable();
    document.dispatchEvent(new CustomEvent("document-preview:row-added", { detail: { row: tr } }));
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  async function uploadFile(file) {
    const formData = new FormData();
    formData.append("archivo", file, file.name);

    const response = await fetch(uploadUrl, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `Error al subir ${file.name}`);
    }
    return data;
  }

  async function uploadFiles(files) {
    const list = Array.from(files).filter((file) => file && file.size > 0);
    if (!list.length) {
      setStatus("No se detectaron archivos válidos.", true);
      return;
    }

    setStatus(`Subiendo ${list.length} archivo(s)...`);

    let ok = 0;
    const errors = [];

    for (const file of list) {
      try {
        const doc = await uploadFile(file);
        appendDocumentRow(doc);
        ok += 1;
      } catch (error) {
        errors.push(`${file.name}: ${error.message}`);
      }
    }

    if (errors.length) {
      setStatus(
        `${ok} subido(s). Error: ${errors.join(" · ")}`,
        errors.length === list.length,
      );
    } else {
      setStatus(`${ok} documento(s) subido(s) correctamente.`);
      window.setTimeout(() => setStatus(""), 4000);
    }
  }

  function extractFiles(dataTransfer) {
    if (dataTransfer.files && dataTransfer.files.length) {
      return Array.from(dataTransfer.files);
    }
    return [];
  }

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      event.stopPropagation();
      dragDepth += 1;
      dropZone.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (eventName === "dragleave") {
        dragDepth -= 1;
        if (dragDepth <= 0) {
          dragDepth = 0;
          dropZone.classList.remove("is-dragover");
        }
        return;
      }
      dragDepth = 0;
      dropZone.classList.remove("is-dragover");
      uploadFiles(extractFiles(event.dataTransfer));
    });
  });

  document.addEventListener("dragover", (event) => event.preventDefault());
})();
