(() => {
  const buttons = Array.from(document.querySelectorAll(".peticion-adjunto-preview"));
  const viewer = document.getElementById("peticiones-viewer");
  const title = document.getElementById("peticiones-viewer-title");
  const empty = document.getElementById("peticiones-viewer-empty");
  const status = document.getElementById("peticiones-viewer-status");
  const frame = document.getElementById("peticiones-viewer-frame");
  const openLink = document.getElementById("peticiones-viewer-open");

  if (!viewer || !title || !empty || !status || !frame || !openLink || !buttons.length) return;

  const sessionCache = new Map();

  function setStatus(message, isError = false) {
    status.hidden = !message;
    status.textContent = message || "";
    status.classList.toggle("is-error", isError);
  }

  function setActive(button) {
    buttons.forEach((item) => item.classList.toggle("is-active", item === button));
  }

  function withFactbox(url) {
    if (!url) return "";
    return url + (url.includes("?") ? "&" : "?") + "factbox=1";
  }

  async function loadSession(button) {
    const sessionUrl = button.dataset.viewerSessionUrl;
    if (!sessionUrl) throw new Error("No hay URL de sesión del visor.");
    if (sessionCache.has(sessionUrl)) return sessionCache.get(sessionUrl);

    const response = await fetch(sessionUrl, {
      method: "POST",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const text = await response.text();
    let payload = {};
    try {
      payload = text ? JSON.parse(text) : {};
    } catch (_error) {
      const preview = text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 180);
      throw new Error(
        `Respuesta inesperada del servidor (${response.status}). ${preview || "No se recibió JSON."}`,
      );
    }
    if (!response.ok) {
      throw new Error(payload.error || "No se pudo preparar la vista previa.");
    }
    sessionCache.set(sessionUrl, payload);
    return payload;
  }

  async function preview(button) {
    setActive(button);
    title.textContent = button.dataset.name || "Adjunto";
    empty.hidden = true;
    frame.hidden = true;
    openLink.hidden = true;
    setStatus("Cargando vista previa...");

    try {
      const payload = await loadSession(button);
      frame.src = withFactbox(payload.embedUrl);
      frame.hidden = false;
      openLink.href = payload.expandedUrl || payload.embedUrl || button.dataset.originalUrl || "#";
      openLink.hidden = !openLink.href || openLink.href.endsWith("#");
      setStatus("");
    } catch (error) {
      frame.removeAttribute("src");
      frame.hidden = true;
      empty.hidden = false;
      setStatus(error.message || "No se pudo cargar la vista previa.", true);
    }
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => preview(button));
  });

  preview(buttons[0]);
})();
