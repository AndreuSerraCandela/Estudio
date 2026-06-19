(() => {
  const tbody = document.getElementById("documentos-tbody");
  const previewPanel = document.getElementById("document-preview");
  if (!tbody || !previewPanel) return;

  const titleEl = document.getElementById("preview-title");
  const emptyEl = document.getElementById("preview-empty");
  const viewerEl = document.getElementById("preview-viewer");
  const fallbackEl = document.getElementById("preview-fallback");
  const iframeEl = document.getElementById("preview-iframe");
  const imageEl = document.getElementById("preview-image");
  const openEl = document.getElementById("preview-open");
  const fallbackLinkEl = document.getElementById("preview-fallback-link");

  let lockedRow = null;

  function rows() {
    return Array.from(tbody.querySelectorAll(".doc-preview-row"));
  }

  function hideAllViewers() {
    if (iframeEl) {
      iframeEl.hidden = true;
      iframeEl.removeAttribute("src");
    }
    if (imageEl) {
      imageEl.hidden = true;
      imageEl.removeAttribute("src");
    }
    if (viewerEl) viewerEl.hidden = true;
    if (fallbackEl) fallbackEl.hidden = true;
  }

  function showPreview(row) {
    if (!row) return;

    const nombre = row.dataset.docNombre || "Documento";
    const url = row.dataset.docUrl || "#";
    const kind = row.dataset.previewKind || "other";
    const src = row.dataset.previewSrc || url;

    rows().forEach((item) => item.classList.toggle("is-active", item === row));

    if (titleEl) titleEl.textContent = nombre;
    if (openEl) {
      openEl.href = url;
      openEl.hidden = false;
    }

    hideAllViewers();
    if (emptyEl) emptyEl.hidden = true;

    if (kind === "image") {
      if (viewerEl) viewerEl.hidden = false;
      if (imageEl) {
        imageEl.src = src;
        imageEl.hidden = false;
      }
      return;
    }

    if (kind === "pdf" || kind === "mail") {
      if (viewerEl) viewerEl.hidden = false;
      if (iframeEl) {
        iframeEl.src = kind === "pdf" ? `${src}#view=FitH` : src;
        iframeEl.hidden = false;
      }
      return;
    }

    if (fallbackEl) fallbackEl.hidden = false;
    if (fallbackLinkEl) fallbackLinkEl.href = url;
  }

  function bindRow(row) {
    row.addEventListener("mouseenter", () => {
      if (!lockedRow) showPreview(row);
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

  rows().forEach(bindRow);

  tbody.addEventListener("mouseleave", (event) => {
    if (lockedRow) {
      showPreview(lockedRow);
      return;
    }
    if (event.relatedTarget && previewPanel.contains(event.relatedTarget)) return;
    rows().forEach((item) => item.classList.remove("is-active"));
    hideAllViewers();
    if (emptyEl) emptyEl.hidden = false;
    if (titleEl) titleEl.textContent = "Selecciona un documento";
    if (openEl) openEl.hidden = true;
  });

  document.addEventListener("document-preview:row-added", (event) => {
    const row = event.detail && event.detail.row;
    if (!row) return;
    bindRow(row);
    lockedRow = row;
    showPreview(row);
  });

  const firstRow = rows()[0];
  if (firstRow) {
    lockedRow = firstRow;
    showPreview(firstRow);
  }
})();
