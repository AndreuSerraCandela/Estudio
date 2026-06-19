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
        li.innerHTML = config.renderItem(item);
        li.addEventListener("mousedown", (event) => {
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

  setupBcAutocomplete({
    inputId: "proyecto",
    hiddenId: "bc_proyecto_id",
    listId: "proyecto-suggestions",
    hintId: "proyecto-bc-hint",
    apiUrl: "/expedientes/api/proyectos",
    searchHint: "Buscar proyecto en Business Central o escribir manualmente",
    getLabel: (item) => item.description || item.no,
    getValue: (item) => item.no,
    renderItem: (item) =>
      `<strong>${item.description || item.no}</strong><span>${item.no}</span>`,
  });
})();
