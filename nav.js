document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.nav-menu-toggle');
  var links = document.querySelector('.nav-links');
  if (!toggle || !links) return;

  toggle.addEventListener('click', function () {
    links.classList.toggle('open');
  });

  links.querySelectorAll('.nav-link').forEach(function (link) {
    link.addEventListener('click', function () {
      links.classList.remove('open');
    });
  });
});
