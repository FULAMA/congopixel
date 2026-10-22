(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var toArray = function (list) { return Array.prototype.slice.call(list); };

  // Ombre de l'en-tête au défilement
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () { header.classList.toggle("scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // Apparition au défilement
  var targets = toArray(document.querySelectorAll(".card, .section-title, .summary, .form-card, .cart-line"));
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        var el = entry.target;
        el.classList.add("in");
        io.unobserve(el);
        setTimeout(function () {
          el.classList.remove("reveal", "in");
          el.style.transitionDelay = "";
        }, 900);
      });
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.05 });
    targets.forEach(function (el) {
      var index = el.parentNode ? Array.prototype.indexOf.call(el.parentNode.children, el) : 0;
      el.style.transitionDelay = (index % 4) * 70 + "ms";
      el.classList.add("reveal");
      io.observe(el);
    });
  }

  // Notifications : disparition automatique (les erreurs restent jusqu'au clic)
  toArray(document.querySelectorAll(".toasts .msg")).forEach(function (msg, i) {
    var close = function () {
      msg.classList.add("hide");
      setTimeout(function () { if (msg.parentNode) { msg.parentNode.removeChild(msg); } }, 400);
    };
    msg.addEventListener("click", close);
    if (!msg.classList.contains("error")) { setTimeout(close, 4500 + i * 600); }
  });

  // Rebond du bouton panier quand le nombre d'articles augmente
  var cart = document.querySelector(".cart-btn");
  if (cart) {
    var now = parseInt(cart.getAttribute("data-count"), 10) || 0;
    var before = 0;
    try { before = parseInt(sessionStorage.getItem("cp_cart") || "0", 10) || 0; } catch (e) {}
    if (now > before && !reduce) { cart.classList.add("bump"); }
    try { sessionStorage.setItem("cp_cart", String(now)); } catch (e) {}
  }

  // « Mon Pixel » : envoi automatique du choix
  toArray(document.querySelectorAll(".pixel-picker select")).forEach(function (select) {
    select.addEventListener("change", function () { select.form.submit(); });
  });

  // Galerie : changer l'image principale
  var main = document.getElementById("main-img");
  var thumbs = toArray(document.querySelectorAll("[data-thumb]"));
  thumbs.forEach(function (thumb) {
    thumb.addEventListener("click", function (event) {
      if (!main) { return; }
      event.preventDefault();
      var src = thumb.getAttribute("href");
      main.classList.add("swap");
      var probe = new Image();
      probe.onload = probe.onerror = function () { main.src = src; main.classList.remove("swap"); };
      probe.src = src;
      thumbs.forEach(function (t) { t.classList.remove("active"); });
      thumb.classList.add("active");
    });
  });

  // Quantité : boutons - et +
  toArray(document.querySelectorAll("[data-qty]")).forEach(function (box) {
    var input = box.querySelector("input");
    toArray(box.querySelectorAll("button")).forEach(function (button) {
      button.addEventListener("click", function () {
        var step = parseInt(button.getAttribute("data-step"), 10) || 0;
        var min = parseInt(input.min || "1", 10);
        var max = parseInt(input.max || "10", 10);
        var value = (parseInt(input.value, 10) || min) + step;
        input.value = Math.max(min, Math.min(max, value));
      });
    });
  });

  // Quantité maximale selon le stock de la variante choisie
  var variant = document.getElementById("variant");
  var qty = document.getElementById("qty");
  if (variant && qty) {
    var syncMax = function () {
      var option = variant.options[variant.selectedIndex];
      var stock = parseInt(option.getAttribute("data-stock"), 10) || 10;
      var max = Math.min(10, stock);
      qty.max = max;
      if ((parseInt(qty.value, 10) || 1) > max) { qty.value = max; }
    };
    variant.addEventListener("change", syncMax);
    syncMax();
  }

  // Anti double-clic sur les formulaires importants
  var forms = toArray(document.querySelectorAll("form[data-loading]"));
  var setBusy = function (form, busy) {
    var buttons = toArray(form.querySelectorAll("button[type=submit]"));
    if (form.id) { buttons = buttons.concat(toArray(document.querySelectorAll('button[form="' + form.id + '"]'))); }
    buttons.forEach(function (button) {
      if (busy) {
        if (!button.getAttribute("data-label")) { button.setAttribute("data-label", button.textContent); }
        button.textContent = form.getAttribute("data-busy-text") || "Patientez…";
        button.disabled = true;
        button.classList.add("busy");
      } else {
        if (button.getAttribute("data-label")) { button.textContent = button.getAttribute("data-label"); }
        button.disabled = false;
        button.classList.remove("busy");
      }
    });
  };
  forms.forEach(function (form) {
    form.addEventListener("submit", function () { setBusy(form, true); });
  });
  window.addEventListener("pageshow", function (event) {
    if (event.persisted) { forms.forEach(function (form) { setBusy(form, false); }); }
  });
})();