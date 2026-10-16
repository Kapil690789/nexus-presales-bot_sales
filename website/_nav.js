document.write(`<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="/" aria-label="Nexus Home">
      <span class="brand-dot"></span>
      <span class="brand-text">Nexus</span>
      <span class="brand-pill">Studio</span>
    </a>
    <button class="mobile-toggle" type="button" aria-label="Toggle Navigation Menu" aria-expanded="false" onclick="window.__toggleNav&&window.__toggleNav(this)">
      <span class="toggle-bar"></span>
      <span class="toggle-bar"></span>
      <span class="toggle-bar"></span>
    </button>
    <nav id="site-nav" class="site-nav">
      <a href="/">Home</a>
      <a href="/web-app-development.html">Web Apps</a>
      <a href="/mobile-app-development.html">Mobile</a>
      <a href="/ai-development.html">AI Solutions</a>
      <a href="/ui-ux-design.html">UI/UX</a>
      <a href="/staff-augmentation.html">Staffing</a>
      <a href="/work.html">Work</a>
      <a href="/pricing.html">Pricing</a>
      <a href="/contact.html">Contact</a>
      <button type="button" class="nav-advisor-btn" onclick="if(window.NexusAdvisor&&window.NexusAdvisor.open){window.NexusAdvisor.open(true);}else{var l=document.querySelector('.ps-launcher');if(l)l.click();}">
        <span class="pulse-dot"></span>
        <span class="btn-text">⚡ Talk to Mike</span>
      </button>
    </nav>
  </div>
</header>`);

window.__toggleNav = function (btn) {
  var nav = document.getElementById("site-nav");
  if (!nav) return;
  var isOpen = nav.classList.toggle("is-open");
  if (btn) {
    btn.classList.toggle("active", isOpen);
    btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
  }
  document.body.classList.toggle("nav-open", isOpen);
};

(function () {
  var path = location.pathname;
  document.querySelectorAll(".site-nav a").forEach(function (link) {
    var href = link.getAttribute("href");
    var active = false;
    if (href === "/") {
      active = path === "/" || path === "/index.html";
    } else if (href === "/work.html") {
      active = path === "/work.html" || path.indexOf("/work/") === 0;
    } else {
      active = path === href;
    }
    if (active) link.classList.add("active");
    link.addEventListener("click", function () {
      var nav = document.getElementById("site-nav");
      var btn = document.querySelector(".mobile-toggle");
      if (nav && nav.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        document.body.classList.remove("nav-open");
        if (btn) {
          btn.classList.remove("active");
          btn.setAttribute("aria-expanded", "false");
        }
      }
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      var nav = document.getElementById("site-nav");
      var btn = document.querySelector(".mobile-toggle");
      if (nav && nav.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        document.body.classList.remove("nav-open");
        if (btn) {
          btn.classList.remove("active");
          btn.setAttribute("aria-expanded", "false");
        }
      }
    }
  });
})();
