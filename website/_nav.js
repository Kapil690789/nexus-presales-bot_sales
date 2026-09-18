document.write(`<header class="site-header"><div class="wrap header-inner"><a class="brand" href="/">DevConsult</a><nav>
<a href="/">Home</a>
<a href="/web-app-development.html">Website</a>
<a href="/mobile-app-development.html">Mobile apps</a>
<a href="/ai-development.html">AI solutions</a>
<a href="/ui-ux-design.html">UI/UX</a>
<a href="/staff-augmentation.html">Staff aug</a>
<a href="/work.html">Work</a>
<a href="/contact.html">Contact</a>
</nav></div></header>`);

(function () {
  var path = location.pathname;
  document.querySelectorAll(".site-header nav a").forEach(function (link) {
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
  });
})();
