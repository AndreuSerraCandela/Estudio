(() => {
  function setupBcAutocomplete(config) {
    const input = document.getElementById(config.inputId);
    const hiddenId = document.getElementById(config.hiddenId);
    const list = document.getElementById(config.listId);
    const hint = config.hintId ? document.getElementById(config.hintId) : null;

    if (!input || !hiddenId || !list) return;

    let timer = null;
    let lastQuery = "";

    function setHint(text) {
      if (hint) hint.textContent = text;
    }

    function clearSuggestions() {
      list.innerHTML = "";
      list.hidden = true;
    }

    function selectItem(item) {
      input.value = config.getLabel(item);
      hiddenId.value = config.getValue(item);
      setHint(`Vinculado a BC: ${config.getValue(item)}`);
      clearSuggestions();
    }

    function renderSuggestions(items) {
      list.innerHTML = "";
      if (!items.length) {
        list.hidden = true;
        return;
      }

      items.forEach((item) => {
        const li = document.createElement("li");
        li.className = "autocomplete-item";
        if (config.renderRow) {
          li.appendChild(config.renderRow(item));
        } else {
          li.innerHTML = config.renderItem(item);
        }
        li.addEventListener("mousedown", (event) => {
          if (event.target.closest("[data-ficha]")) return;
          event.preventDefault();
          selectItem(item);
        });
        list.appendChild(li);
      });
      list.hidden = false;
    }

    async function searchItems(query) {
      const response = await fetch(`${config.apiUrl}?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Error al buscar en Business Central");
      }
      return data;
    }

    input.addEventListener("input", () => {
      hiddenId.value = "";
      setHint(config.searchHint);

      const query = input.value.trim();
      if (query.length < 2) {
        clearSuggestions();
        return;
      }

      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(async () => {
        if (query === lastQuery) return;
        lastQuery = query;
        try {
          const items = await searchItems(query);
          renderSuggestions(items);
        } catch (error) {
          clearSuggestions();
          setHint(error.message);
        }
      }, 300);
    });

    input.addEventListener("blur", () => {
      window.setTimeout(clearSuggestions, 150);
    });
  }

  setupBcAutocomplete({
    inputId: "cliente",
    hiddenId: "bc_cliente_id",
    listId: "cliente-suggestions",
    hintId: "cliente-bc-hint",
    apiUrl: "/expedientes/api/clientes",
    searchHint: "Escribe al menos 2 caracteres para buscar en Business Central",
    getLabel: (item) => item.name,
    getValue: (item) => item.no,
    renderItem: (item) =>
      `<strong>${item.name}</strong><span>${item.no}${item.vat ? " · " + item.vat : ""}</span>`,
  });

  setupBcAutocomplete({
    inputId: "comercial",
    hiddenId: "bc_comercial_id",
    listId: "comercial-suggestions",
    hintId: "comercial-bc-hint",
    apiUrl: "/expedientes/api/vendedores",
    searchHint: "Buscar vendedor en Business Central o escribir manualmente",
    getLabel: (item) => item.name.trim(),
    getValue: (item) => item.code,
    renderItem: (item) =>
      `<strong>${item.name.trim()}</strong><span>${item.code}</span>`,
  });

  function fechaCorta(iso) {
    if (!iso) return "—";
    const [anio, mes, dia] = iso.split("-");
    return `${dia}/${mes}/${anio}`;
  }

  function campoFicha(etiqueta, valor) {
    const fila = document.createElement("div");
    fila.className = "ficha-campo";
    const etiquetaEl = document.createElement("span");
    etiquetaEl.className = "ficha-etiqueta";
    etiquetaEl.textContent = etiqueta;
    const valorEl = document.createElement("span");
    valorEl.className = "ficha-valor";
    valorEl.textContent = valor || "";
    fila.appendChild(etiquetaEl);
    fila.appendChild(valorEl);
    return fila;
  }

  const fichaDialogo = document.getElementById("ficha-proyecto");

  async function abrirFicha(item) {
    if (!fichaDialogo) return;
    const cuerpo = fichaDialogo.querySelector(".ficha-cuerpo");
    fichaDialogo.querySelector(".ficha-titulo").textContent = `${item.no} · ${item.description || ""}`;
    cuerpo.textContent = "Cargando ficha…";
    fichaDialogo.showModal();
    const params = new URLSearchParams({ empresa: item.empresa || "", numero: item.no || "" });
    let ficha;
    try {
      const respuesta = await fetch(`/expedientes/api/proyectos/ficha?${params.toString()}`);
      ficha = await respuesta.json();
      if (!respuesta.ok) throw new Error(ficha.error || "No se pudo cargar la ficha.");
    } catch (error) {
      cuerpo.textContent = "";
      const aviso = document.createElement("p");
      aviso.className = "flash flash-error";
      aviso.textContent = error.message;
      cuerpo.appendChild(aviso);
      return;
    }
    cuerpo.textContent = "";
    const general = document.createElement("div");
    general.className = "ficha-general";
    const izquierda = document.createElement("div");
    [
      ["Nº", ficha.numero],
      ["Empresa", ficha.empresa],
      ["Nº proyecto antiguo", ficha.proyecto_antiguo],
      ["Proyecto original", ficha.proyecto_original],
      ["Proyecto origen", ficha.proyecto_origen],
      ["Renovado", ficha.renovado ? "Sí" : "No"],
      ["Descripción", ficha.descripcion],
      ["Anunciante", ficha.anunciante],
      ["Nombre del cliente", ficha.nombre_cliente],
    ].forEach(([etiqueta, valor]) => izquierda.appendChild(campoFicha(etiqueta, valor)));
    const derecha = document.createElement("div");
    [
      ["Fija/Papel", ficha.fija_papel],
      ["Fecha creación", fechaCorta(ficha.fecha_creacion)],
      ["Fecha inicial", fechaCorta(ficha.fecha_inicio)],
      ["Fecha final", fechaCorta(ficha.fecha_final)],
      ["Estado contrato", ficha.estado_contrato],
      ["Facturar a", ficha.facturar_a],
    ].forEach(([etiqueta, valor]) => derecha.appendChild(campoFicha(etiqueta, valor)));
    general.appendChild(izquierda);
    general.appendChild(derecha);
    cuerpo.appendChild(general);
    const titulo = document.createElement("h3");
    titulo.textContent = "Líneas";
    cuerpo.appendChild(titulo);
    if (!ficha.lineas.length) {
      const vacio = document.createElement("p");
      vacio.className = "muted";
      vacio.textContent = "El proyecto no tiene líneas.";
      cuerpo.appendChild(vacio);
      return;
    }
    const tabla = document.createElement("table");
    tabla.className = "table ficha-lineas";
    tabla.innerHTML = "<thead><tr><th>Tipo</th><th>Nº</th><th>Descripción</th><th>Fecha</th></tr></thead><tbody></tbody>";
    ficha.lineas.forEach((linea) => {
      const tr = document.createElement("tr");
      [linea.tipo, linea.numero, linea.descripcion, fechaCorta(linea.fecha)].forEach((valor) => {
        const td = document.createElement("td");
        td.textContent = valor || "";
        tr.appendChild(td);
      });
      tabla.querySelector("tbody").appendChild(tr);
    });
    cuerpo.appendChild(tabla);
  }

  if (fichaDialogo) {
    fichaDialogo.querySelector(".ficha-cerrar").addEventListener("click", () => fichaDialogo.close());
    fichaDialogo.addEventListener("click", (event) => {
      if (event.target === fichaDialogo) fichaDialogo.close();
    });
  }

  setupBcAutocomplete({
    inputId: "proyecto",
    hiddenId: "bc_proyecto_id",
    listId: "proyecto-suggestions",
    hintId: "proyecto-bc-hint",
    apiUrl: "/expedientes/api/proyectos",
    searchHint: "Buscar proyecto en Business Central o escribir manualmente",
    getLabel: (item) => item.description || item.no,
    getValue: (item) => item.no,
    renderRow: (item) => {
      const fila = document.createElement("div");
      fila.className = "autocomplete-proyecto";
      const texto = document.createElement("div");
      const titulo = document.createElement("strong");
      titulo.textContent = `${item.no} — ${item.description || "Sin descripción"}`;
      const detalle = document.createElement("span");
      detalle.textContent = `Anunciante: ${item.anunciante || "—"} · Cliente: ${item.nombre_cliente || "—"}`;
      const inicio = document.createElement("span");
      inicio.textContent = `Inicio: ${fechaCorta(item.fecha_inicio)} · ${item.empresa || ""}`;
      texto.appendChild(titulo);
      texto.appendChild(detalle);
      texto.appendChild(inicio);
      const ver = document.createElement("button");
      ver.type = "button";
      ver.className = "btn btn-secondary btn-sm";
      ver.dataset.ficha = "1";
      ver.textContent = "Ver ficha";
      ver.addEventListener("mousedown", (event) => {
        event.preventDefault();
        event.stopPropagation();
      });
      ver.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        abrirFicha(item);
      });
      fila.appendChild(texto);
      fila.appendChild(ver);
      return fila;
    },
  });
})();
