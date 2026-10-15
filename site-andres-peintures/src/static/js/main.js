/* Andres Peintures — interactions (menu mobile, en-tête, apparitions, formulaire, carte). */
(function () {
  "use strict";

  var doc = document.documentElement;
  doc.classList.add("js");

  /* ---------- Menu mobile ---------- */
  var burger = document.querySelector(".burger");
  var panneau = document.getElementById("panneau-mobile");

  function fermerMenu(rendreFocus) {
    if (!burger || !panneau) return;
    burger.setAttribute("aria-expanded", "false");
    burger.querySelector(".burger__texte").textContent = "Menu";
    panneau.classList.remove("est-ouvert");
    panneau.setAttribute("aria-hidden", "true");
    panneau.inert = true;
    document.body.classList.remove("menu-ouvert");
    if (rendreFocus) burger.focus();
  }

  function placerPanneau() {
    var entete = document.querySelector(".entete");
    if (entete) panneau.style.top = Math.max(0, entete.getBoundingClientRect().bottom) + "px";
  }

  function ouvrirMenu() {
    placerPanneau();
    burger.setAttribute("aria-expanded", "true");
    burger.querySelector(".burger__texte").textContent = "Fermer";
    panneau.classList.add("est-ouvert");
    panneau.setAttribute("aria-hidden", "false");
    panneau.inert = false;
    document.body.classList.add("menu-ouvert");
    var premier = panneau.querySelector("a, button");
    if (premier) premier.focus({ preventScroll: true });
  }

  if (burger && panneau) {
    panneau.inert = true;
    burger.addEventListener("click", function () {
      if (burger.getAttribute("aria-expanded") === "true") fermerMenu(false);
      else ouvrirMenu();
    });
    panneau.addEventListener("click", function (e) {
      if (e.target.closest("a")) fermerMenu(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && burger.getAttribute("aria-expanded") === "true") fermerMenu(true);
    });
    window.addEventListener("resize", function () {
      if (burger.getAttribute("aria-expanded") === "true") placerPanneau();
    });
    window.matchMedia("(min-width: 1180px)").addEventListener("change", function (mq) {
      if (mq.matches) fermerMenu(false);
    });
  }

  /* ---------- Ombre de l'en-tête au défilement ---------- */
  var entete = document.querySelector(".entete");
  if (entete) {
    var majEntete = function () {
      entete.classList.toggle("est-defile", window.scrollY > 8);
    };
    majEntete();
    window.addEventListener("scroll", majEntete, { passive: true });
  }

  /* ---------- Apparitions au défilement ---------- */
  var aReveler = document.querySelectorAll(".revele, .revele-groupe");
  if ("IntersectionObserver" in window && aReveler.length) {
    var obs = new IntersectionObserver(
      function (entrees) {
        entrees.forEach(function (entree) {
          if (entree.isIntersecting) {
            entree.target.classList.add("est-visible");
            obs.unobserve(entree.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );
    aReveler.forEach(function (el) {
      obs.observe(el);
    });
  } else {
    aReveler.forEach(function (el) {
      el.classList.add("est-visible");
    });
  }

  /* ---------- Formulaire de devis ---------- */
  var form = document.getElementById("form-devis");
  if (form) {
    // La validation est gérée ici pour afficher les messages dans le bon ordre.
    form.noValidate = true;
    // Pré-sélection du métier depuis l'adresse : contact.html?metier=facade
    var params = new URLSearchParams(window.location.search);
    var metier = params.get("metier");
    if (metier) {
      var caseMetier = form.querySelector('input[name="travaux[]"][value="' + metier.replace(/[^a-z]/g, "") + '"]');
      if (caseMetier) caseMetier.checked = true;
    }

    var erreur = form.querySelector(".formulaire__erreur");
    var bouton = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", function (e) {
      var coches = form.querySelectorAll('input[name="travaux[]"]:checked');
      if (!coches.length) {
        e.preventDefault();
        erreur.textContent = "Indiquez au moins un type de travaux : peinture, façade, plâtrerie ou sols.";
        erreur.classList.add("est-visible");
        form.querySelector('input[name="travaux[]"]').focus();
        return;
      }
      if (!form.checkValidity()) {
        e.preventDefault();
        erreur.textContent = "Merci de compléter les champs obligatoires signalés en rouge.";
        erreur.classList.add("est-visible");
        form.reportValidity();
        return;
      }
      erreur.classList.remove("est-visible");

      // Mode « courriel » : la demande est préparée dans la messagerie du visiteur.
      var destinataire = form.getAttribute("data-courriel");
      if (destinataire) {
        e.preventDefault();
        var travaux = Array.prototype.map
          .call(coches, function (c) {
            return c.getAttribute("data-libelle");
          })
          .join(", ");
        var val = function (nom) {
          var champ = form.elements[nom];
          return champ && champ.value ? champ.value.trim() : "";
        };
        var lignes = [
          "Travaux : " + travaux,
          "Type de bien : " + (val("bien") || "non précisé"),
          "Commune : " + (val("commune") || "non précisée"),
          "",
          val("message"),
          "",
          "Nom : " + val("nom"),
          "Téléphone : " + val("telephone"),
          "Courriel : " + (val("email") || "non renseigné"),
          "Disponibilités : " + (val("disponibilite") || "peu importe"),
        ];
        var sujet = "Demande de devis – " + travaux;
        window.location.href =
          "mailto:" +
          destinataire +
          "?subject=" +
          encodeURIComponent(sujet) +
          "&body=" +
          encodeURIComponent(lignes.join("\n"));
        return;
      }

      if (bouton) {
        bouton.disabled = true;
        bouton.querySelector(".btn__texte").textContent = "Envoi en cours…";
      }
    });

    form.addEventListener("change", function () {
      erreur.classList.remove("est-visible");
    });
  }

  /* ---------- Carte OpenStreetMap chargée à la demande ---------- */
  var boutonCarte = document.querySelector("[data-charger-carte]");
  if (boutonCarte) {
    boutonCarte.addEventListener("click", function () {
      var conteneur = boutonCarte.closest(".carte-osm");
      var iframe = document.createElement("iframe");
      iframe.src = boutonCarte.getAttribute("data-charger-carte");
      iframe.title = "Plan d'accès : " + (conteneur.getAttribute("data-adresse") || "notre entreprise");
      iframe.loading = "lazy";
      iframe.referrerPolicy = "no-referrer";
      conteneur.innerHTML = "";
      conteneur.appendChild(iframe);
    });
  }
})();
