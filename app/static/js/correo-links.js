(() => {
  const MIME_TYPE = "application/x-estudio-document";
  const dropZone = document.getElementById("correo-document-drop");
  const list = document.getElementById("correo-document-links");

  if (!dropZone || !list) return;

  const selected = new Set();

  function documentFromRow(row) {
    const id = row.dataset.docId;
    const nombre = row.dataset.docNombre;
    const url = row.dataset.docUrl;
    if (!id || !nombre || !url) return null;
    return { id, nombre, url };
  }

  function markRowsDraggable(root = document) {
    root.querySelectorAll(".doc-preview-row").forEach((row) => {
      row.draggable = true;
    });
  }

  function hasDocumentPayload(dataTransfer) {
    return Array.from(dataTransfer?.types || []).includes(MIME_TYPE);
  }

  function addDocument(doc) {
    if (selected.has(doc.id)) return;
    selected.add(doc.id);
    list.hidden = false;

    const item = document.createElement("li");
    item.className = "correo-link-item";
    item.dataset.docId = doc.id;

    const hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = "documento_ids";
    hiddenInput.value = doc.id;

    const linkText = document.createElement("span");
    linkText.className = "correo-link-name";
    linkText.textContent = doc.nombre;

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "btn btn-sm btn-secondary";
    removeButton.textContent = "Quitar";
    removeButton.addEventListener("click", () => {
      selected.delete(doc.id);
      item.remove();
      list.hidden = selected.size === 0;
    });

    item.append(hiddenInput, linkText, removeButton);
    list.appendChild(item);
  }

  document.addEventListener("dragstart", (event) => {
    const row = event.target.closest?.(".doc-preview-row");
    if (!row || !event.dataTransfer) return;

    const doc = documentFromRow(row);
    if (!doc) return;

    event.dataTransfer.effectAllowed = "copy";
    event.dataTransfer.setData(MIME_TYPE, JSON.stringify(doc));
    event.dataTransfer.setData("text/plain", `${doc.nombre}\n${doc.url}`);
    row.classList.add("is-dragging");
  });

  document.addEventListener("dragend", (event) => {
    event.target.closest?.(".doc-preview-row")?.classList.remove("is-dragging");
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      if (!hasDocumentPayload(event.dataTransfer)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
      dropZone.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      if (!hasDocumentPayload(event.dataTransfer)) return;
      event.preventDefault();
      dropZone.classList.remove("is-dragover");

      if (eventName !== "drop") return;

      try {
        const doc = JSON.parse(event.dataTransfer.getData(MIME_TYPE));
        addDocument(doc);
      } catch (_error) {
        // Si el navegador no conserva el payload personalizado, simplemente ignoramos el drop.
      }
    });
  });

  document.addEventListener("document-preview:row-added", (event) => {
    if (event.detail?.row) {
      markRowsDraggable(event.detail.row.parentElement || document);
    }
  });

  markRowsDraggable();
})();
