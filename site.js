(function () {
  var d = document;
  d.documentElement.classList.add('js');

  // repassa utm_* (e src/sck da Kiwify) da URL do anúncio pro link de checkout
  var q = new URLSearchParams(location.search), extra = [];
  ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'src', 'sck'].forEach(function (k) {
    var v = q.get(k); if (v) extra.push([k, v]);
  });
  var compra = Array.prototype.slice.call(d.querySelectorAll('a[data-compra]'));
  compra.forEach(function (a) {
    if (extra.length) {
      try { var u = new URL(a.href); extra.forEach(function (p) { if (!u.searchParams.has(p[0])) u.searchParams.set(p[0], p[1]); }); a.href = u.toString(); } catch (e) {}
    }
    a.addEventListener('click', function () {
      if (window.fbq) window.fbq('track', 'InitiateCheckout', { value: parseFloat(a.dataset.valor) || 0, currency: 'BRL' });
    });
  });

  // barra fixa: aparece quando o botão do topo sai da tela, some na seção de compra
  // e some também quando o botão do fim da página está na tela (nunca dois botões de compra juntos)
  var barra = d.getElementById('barra'), cta = d.getElementById('cta-hero'), fim = d.getElementById('comprar'), fim2 = d.getElementById('comprar-fim');
  if (barra && cta && fim && 'IntersectionObserver' in window) {
    var heroFora = false, dentro = { a: false, b: false };
    var atualiza = function () { barra.classList.toggle('on', heroFora && !dentro.a && !dentro.b); };
    new IntersectionObserver(function (e) { heroFora = !e[0].isIntersecting && e[0].boundingClientRect.top < 0; atualiza(); }).observe(cta);
    new IntersectionObserver(function (e) { dentro.a = e[0].isIntersecting; atualiza(); }).observe(fim);
    if (fim2) new IntersectionObserver(function (e) { dentro.b = e[0].isIntersecting; atualiza(); }).observe(fim2);
  } else if (barra) { barra.classList.add('on'); }

  // carrossel no celular: contador 1/6 e pontinhos
  var trilho = d.getElementById('trilho'), num = d.getElementById('pig-n');
  if (trilho && num) {
    var pontos = d.querySelectorAll('.pig-pontos i'), ultimo = 0;
    trilho.addEventListener('scroll', function () {
      var i = Math.round(trilho.scrollLeft / Math.max(1, trilho.clientWidth));
      if (i === ultimo) return; ultimo = i;
      num.textContent = i + 1;
      for (var k = 0; k < pontos.length; k++) pontos[k].classList.toggle('on', k === i);
    }, { passive: true });
  }

  // tela cheia das artes
  var luz = d.getElementById('luz');
  if (!luz || !luz.showModal) return;
  var abre = Array.prototype.slice.call(d.querySelectorAll('main a.abre:not(.hero-capa)'));
  var capa = d.querySelector('main a.hero-capa');
  if (capa) capa.addEventListener('click', function (ev) {
    var alvo = abre.map(function (a) { return a.getAttribute('href'); }).indexOf(capa.getAttribute('href'));
    if (alvo < 0) return;
    ev.preventDefault(); mostra(alvo); luz.showModal();
  });
  var img = d.getElementById('luz-img'), cap = d.getElementById('luz-cap'), atual = 0;
  function mostra(i) {
    atual = (i + abre.length) % abre.length;
    var a = abre[atual], fonte = a.querySelector('img');
    img.src = a.getAttribute('href');
    img.alt = fonte ? fonte.alt : '';
    cap.textContent = (a.dataset.cap || '') + '  ·  ' + (atual + 1) + ' de ' + abre.length;
  }
  abre.forEach(function (a, i) {
    a.addEventListener('click', function (ev) { ev.preventDefault(); mostra(i); luz.showModal(); });
  });
  luz.addEventListener('click', function (ev) {
    var acao = ev.target.dataset && ev.target.dataset.acao;
    if (acao === 'fechar' || ev.target === luz) luz.close();
    if (acao === 'ant') mostra(atual - 1);
    if (acao === 'prox') mostra(atual + 1);
  });
  luz.addEventListener('keydown', function (ev) {
    if (ev.key === 'ArrowLeft') mostra(atual - 1);
    if (ev.key === 'ArrowRight') mostra(atual + 1);
  });
  var x0 = null;
  luz.addEventListener('touchstart', function (ev) { x0 = ev.touches[0].clientX; }, { passive: true });
  luz.addEventListener('touchend', function (ev) {
    if (x0 === null) return;
    var dx = ev.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 50) mostra(atual + (dx < 0 ? 1 : -1));
  });
})();
