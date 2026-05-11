(() => {
  const shell = document.querySelector(".app-shell.topbar-layout");
  if (!shell) return;

  const sidebar = shell.querySelector(".side-taskbar");
  if (!sidebar) return;

  const body = document.body;
  const mobileWidth = 600;
  const isMobileViewport = () => window.innerWidth <= mobileWidth;

  const linkNodes = Array.from(sidebar.querySelectorAll(".side-link"));
  linkNodes.forEach((link) => {
    const labelNode = link.querySelector("span");
    const label = labelNode ? (labelNode.textContent || "").trim() : "";
    if (label && !link.dataset.label) {
      link.dataset.label = label;
    }
  });

  const hasActive = linkNodes.some((link) => link.classList.contains("active"));
  if (!hasActive) {
    const currentPath = ((window.location.pathname || "/").replace(/\/+$/, "") || "/");
    linkNodes.forEach((link) => {
      if (link.tagName !== "A") return;
      try {
        const hrefPath = ((new URL(link.href, window.location.origin).pathname || "/").replace(/\/+$/, "") || "/");
        if (hrefPath === currentPath) link.classList.add("active");
      } catch (_err) {
        // Ignore invalid links.
      }
    });
  }

  const sideGroups = Array.from(sidebar.querySelectorAll("details.side-group"));
  sideGroups.forEach((group, idx) => {
    const summary = group.querySelector("summary.side-group-toggle");
    if (!summary) return;
    if (!summary.id) summary.id = "side-group-toggle-" + (idx + 1);
    summary.setAttribute("role", "button");
    summary.setAttribute("aria-controls", "side-group-links-" + (idx + 1));
    const linksWrap = group.querySelector(".side-group-links");
    if (linksWrap && !linksWrap.id) linksWrap.id = "side-group-links-" + (idx + 1);
    const hasActiveChild = !!group.querySelector(".side-link.active");
    if (hasActiveChild) group.open = true;
    summary.setAttribute("aria-expanded", group.open ? "true" : "false");
    group.addEventListener("toggle", () => {
      summary.setAttribute("aria-expanded", group.open ? "true" : "false");
    });
  });

  // Mobile accordion mode for grouped nav sections that opt in.
  const accordionGroups = Array.from(sidebar.querySelectorAll("details.side-group[data-accordion-mobile='1']"));
  accordionGroups.forEach((group) => {
    group.addEventListener("toggle", () => {
      if (!group.open || !isMobileViewport()) return;
      const bucket = group.getAttribute("data-accordion-group") || "__default__";
      accordionGroups.forEach((other) => {
        if (other === group || !other.open) return;
        const otherBucket = other.getAttribute("data-accordion-group") || "__default__";
        if (otherBucket === bucket) other.open = false;
      });
    });
  });

  let overlay = document.querySelector(".rail-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "rail-overlay";
    body.appendChild(overlay);
  }

  let toggle = document.querySelector(".rail-toggle");
  if (!toggle) {
    toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "rail-toggle";
    toggle.setAttribute("aria-label", "Open menu");
    toggle.innerHTML = '<i class="fas fa-bars" aria-hidden="true"></i>';
    body.appendChild(toggle);
  }

  const isDesktop = () => window.innerWidth > mobileWidth;
  const toElement = (target) => (target && target.nodeType === 1 ? target : null);

  const expandRail = () => {
    if (isDesktop()) body.classList.add("rail-expanded");
  };

  const collapseRail = () => {
    body.classList.remove("rail-expanded");
  };

  const closeRail = () => {
    body.classList.remove("rail-open");
    body.classList.remove("rail-expanded");
    toggle.setAttribute("aria-label", "Open menu");
    toggle.innerHTML = '<i class="fas fa-bars" aria-hidden="true"></i>';
  };

  const openRail = () => {
    body.classList.add("rail-open");
    toggle.setAttribute("aria-label", "Close menu");
    toggle.innerHTML = '<i class="fas fa-times" aria-hidden="true"></i>';
  };

  toggle.addEventListener("click", () => {
    if (body.classList.contains("rail-open")) closeRail();
    else openRail();
  });

  overlay.addEventListener("click", closeRail);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeRail();
  });

  // Keep rail expanded on desktop dashboards.
  expandRail();

  linkNodes.forEach((link) => {
    link.addEventListener("click", () => {
      if (!isDesktop()) closeRail();
    });
  });

  window.addEventListener("resize", () => {
    if (isDesktop()) {
      body.classList.remove("rail-open");
      expandRail();
    } else {
      collapseRail();
    }
  });
})();
