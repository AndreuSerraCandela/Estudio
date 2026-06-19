(() => {
  const table = document.getElementById("documentos-table");
  const tbody = document.getElementById("documentos-tbody");
  const noMatchEl = document.getElementById("documentos-no-match");
  if (!table || !tbody) return;

  let sortCol = null;
  let sortDir = 1;
  const activeFilters = {
    nombre: null,
    tipo: null,
  };

  function allRows() {
    return Array.from(tbody.querySelectorAll(".doc-preview-row"));
  }

  function rowValue(row, field) {
    if (field === "nombre") {
      return row.dataset.docNombre || "";
    }
    return (row.dataset.docTipo || "").replaceAll("_", " ");
  }

  function normalized(value) {
    return String(value || "").trim().toLowerCase();
  }

  function uniqueValues(field) {
    const values = new Map();
    allRows().forEach((row) => {
      const value = rowValue(row, field);
      values.set(normalized(value), value || "—");
    });
    return Array.from(values.entries()).sort((a, b) =>
      a[1].localeCompare(b[1], "es", { sensitivity: "base" }),
    );
  }

  function updateHeaderState() {
    table.querySelectorAll(".excel-filter").forEach((filter) => {
      const field = filter.dataset.excelFilter;
      const button = filter.querySelector(".excel-filter-button");
      const isFiltered = activeFilters[field] !== null;
      const isSorted = sortCol === field;
      filter.classList.toggle("is-filtered", isFiltered);
      filter.classList.toggle("is-sorted-asc", isSorted && sortDir === 1);
      filter.classList.toggle("is-sorted-desc", isSorted && sortDir === -1);
      button?.setAttribute("aria-sort", isSorted ? (sortDir === 1 ? "ascending" : "descending") : "none");
    });
  }

  function applyFiltersAndSort() {
    const rows = allRows();
    let visibleCount = 0;

    rows.forEach((row) => {
      const visible = Object.entries(activeFilters).every(([field, selected]) => {
        if (selected === null) return true;
        return selected.has(normalized(rowValue(row, field)));
      });
      row.hidden = !visible;
      if (visible) visibleCount += 1;
    });

    if (noMatchEl) {
      noMatchEl.hidden = visibleCount > 0 || rows.length === 0;
    }

    if (sortCol) {
      const visible = rows.filter((row) => !row.hidden);
      visible.sort((a, b) => {
        const cmp = rowValue(a, sortCol).localeCompare(rowValue(b, sortCol), "es", {
          sensitivity: "base",
        });
        return sortDir * cmp;
      });
      visible.forEach((row) => tbody.appendChild(row));
      rows.filter((row) => row.hidden).forEach((row) => tbody.appendChild(row));
    }

    updateHeaderState();
  }

  function closeMenus(exceptMenu = null) {
    table.querySelectorAll(".excel-filter-menu").forEach((menu) => {
      if (menu === exceptMenu) return;
      menu.hidden = true;
      const field = menu.dataset.excelFilterMenu;
      table.querySelector(`[data-excel-filter-toggle="${field}"]`)?.setAttribute("aria-expanded", "false");
    });
  }

  function syncSelectAll(menu) {
    const visibleChecks = Array.from(menu.querySelectorAll("[data-filter-value]"))
      .filter((input) => !input.closest(".excel-filter-check").hidden);
    const selectAll = menu.querySelector("[data-select-all]");
    if (!selectAll) return;
    selectAll.checked = visibleChecks.length > 0 && visibleChecks.every((input) => input.checked);
    selectAll.indeterminate = visibleChecks.some((input) => input.checked) && !selectAll.checked;
  }

  function renderOptions(menu, field) {
    const optionsEl = menu.querySelector("[data-filter-options]");
    const searchEl = menu.querySelector(".excel-filter-search");
    if (!optionsEl) return;

    optionsEl.innerHTML = "";
    const selected = activeFilters[field];
    uniqueValues(field).forEach(([key, label]) => {
      const item = document.createElement("label");
      item.className = "excel-filter-check";
      item.dataset.optionLabel = normalized(label);
      item.innerHTML = `
        <input type="checkbox" data-filter-value="${escapeHtml(key)}">
        <span>${escapeHtml(label)}</span>
      `;
      const checkbox = item.querySelector("input");
      checkbox.checked = selected === null || selected.has(key);
      checkbox.addEventListener("change", () => syncSelectAll(menu));
      optionsEl.appendChild(item);
    });

    if (searchEl) {
      searchEl.value = "";
      searchEl.dispatchEvent(new Event("input"));
    }
    syncSelectAll(menu);
  }

  function selectedFromMenu(menu) {
    const checks = Array.from(menu.querySelectorAll("[data-filter-value]"));
    const checked = checks.filter((input) => input.checked).map((input) => input.dataset.filterValue || "");
    if (checked.length === checks.length) return null;
    return new Set(checked);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  table.querySelectorAll(".excel-filter").forEach((filter) => {
    const field = filter.dataset.excelFilter;
    const toggle = filter.querySelector(".excel-filter-button");
    const menu = filter.querySelector(".excel-filter-menu");
    const search = filter.querySelector(".excel-filter-search");
    const selectAll = filter.querySelector("[data-select-all]");
    if (!field || !toggle || !menu) return;

    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const willOpen = menu.hidden;
      closeMenus(menu);
      menu.hidden = !willOpen;
      toggle.setAttribute("aria-expanded", String(willOpen));
      if (willOpen) {
        renderOptions(menu, field);
        search?.focus();
      }
    });

    menu.addEventListener("click", (event) => event.stopPropagation());

    search?.addEventListener("input", () => {
      const query = normalized(search.value);
      menu.querySelectorAll(".excel-filter-check[data-option-label]").forEach((item) => {
        item.hidden = query && !item.dataset.optionLabel.includes(query);
      });
      syncSelectAll(menu);
    });

    selectAll?.addEventListener("change", () => {
      const visibleChecks = Array.from(menu.querySelectorAll("[data-filter-value]"))
        .filter((input) => !input.closest(".excel-filter-check").hidden);
      visibleChecks.forEach((input) => {
        input.checked = selectAll.checked;
      });
      syncSelectAll(menu);
    });

    menu.querySelectorAll("[data-sort-col]").forEach((button) => {
      button.addEventListener("click", () => {
        sortCol = button.dataset.sortCol;
        sortDir = button.dataset.sortDir === "desc" ? -1 : 1;
        applyFiltersAndSort();
        closeMenus();
      });
    });

    menu.querySelector("[data-clear-filter]")?.addEventListener("click", () => {
      activeFilters[field] = null;
      applyFiltersAndSort();
      closeMenus();
    });

    menu.querySelector("[data-apply-filter]")?.addEventListener("click", () => {
      activeFilters[field] = selectedFromMenu(menu);
      applyFiltersAndSort();
      closeMenus();
    });
  });

  document.addEventListener("click", () => closeMenus());
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenus();
  });

  document.addEventListener("document-preview:row-added", () => {
    applyFiltersAndSort();
    table.querySelectorAll(".excel-filter-menu:not([hidden])").forEach((menu) => {
      renderOptions(menu, menu.dataset.excelFilterMenu);
    });
  });

  updateHeaderState();
})();
