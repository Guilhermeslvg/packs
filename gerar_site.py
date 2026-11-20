"""Gera o site de vendas dos packs (GitHub Pages).
uso: python3 gerar_site.py   → index.html + <slug>/index.html + ebooks
Os links de checkout da Kiwify ficam em links.json ({"dentista": "https://pay.kiwify.com.br/...", ...}).
"""
import html, json, pathlib, re, shutil

AQUI = pathlib.Path(__file__).parent
PACKS = AQUI.parent / "packs-fim-de-ano"
EBOOKS = AQUI.parent / "ebooks"
links = json.loads((AQUI / "links.json").read_text()) if (AQUI / "links.json").exists() else {}

CSS = """
:root{--bg:#120e0c;--card:#1d1714;--txt:#f4ece2;--apag:#b8a999;--linha:#33291f;--dest:#EBD6A8;--tinta:#2B201C;
--serif:"Instrument Serif",Georgia,serif;--sans:Inter,system-ui,sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--txt);font:400 17px/1.6 var(--sans)}
a{color:inherit}
.wrap{max-width:1180px;margin:0 auto;padding-left:max(20px,env(safe-area-inset-left,0px));padding-right:max(20px,env(safe-area-inset-right,0px))}
header.top{display:flex;justify-content:space-between;align-items:center;padding-block:22px;font:600 13px var(--sans);letter-spacing:.2em;text-transform:uppercase;color:var(--apag)}
header.top a{text-decoration:none}
.hero{display:grid;grid-template-columns:1.05fr .95fr;gap:48px;align-items:center;padding-block:30px 70px}
.hero h1{font:italic 400 clamp(52px,7vw,96px)/.95 var(--serif);margin:10px 0 18px;color:var(--dest);text-wrap:balance}
.olho{font:600 13px var(--sans);letter-spacing:.22em;text-transform:uppercase;color:var(--apag)}
.hero p.sub{font-size:20px;color:#e2d6c8;max-width:34ch;margin:0 0 26px}
.preco{display:flex;align-items:baseline;gap:14px;margin-bottom:22px}
.preco b{font:italic 400 64px/1 var(--serif)}.preco span{color:var(--apag)}
.btn{display:inline-block;background:var(--dest);color:var(--tinta);font:600 18px var(--sans);text-decoration:none;padding:17px 30px;border-radius:10px;transition:transform .15s}
.btn:hover{transform:translateY(-2px)}.btn:focus-visible{outline:2px solid var(--txt);outline-offset:3px}
.btn.off{opacity:.55;pointer-events:none}
.seg{font-size:14px;color:var(--apag);margin-top:14px}
.leque{position:relative;height:540px}
.leque img{position:absolute;width:56%;border-radius:10px;box-shadow:0 30px 60px rgba(0,0,0,.55)}
.leque .a{left:0;top:60px;transform:rotate(-7deg)}.leque .b{left:22%;top:0;z-index:2;width:58%}.leque .c{right:0;top:60px;transform:rotate(7deg)}
section{padding-block:56px;border-top:1px solid var(--linha)}
h2{font:italic 400 clamp(38px,5vw,58px)/1 var(--serif);margin:0 0 10px}
.desc{color:var(--apag);max-width:60ch;margin:0 0 28px}
.grade{display:grid;gap:12px}
.g6{grid-template-columns:repeat(6,1fr)}.g4{grid-template-columns:repeat(4,1fr)}
.grade img{width:100%;border-radius:6px;display:block}
.lista{display:grid;grid-template-columns:repeat(2,1fr);gap:14px 40px;padding:0;list-style:none;max-width:900px}
.lista li{padding-left:28px;position:relative}.lista li::before{content:"✦";position:absolute;left:0;color:var(--dest)}
.passos{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;counter-reset:p}
.passo{background:var(--card);border:1px solid var(--linha);border-radius:12px;padding:22px}
.passo b{display:block;font:italic 400 40px/1 var(--serif);color:var(--dest);margin-bottom:8px}
details{border-bottom:1px solid var(--linha);padding-block:16px;max-width:800px}
summary{cursor:pointer;font-weight:600}
.final{text-align:center}.final h2{margin-bottom:18px}
footer{padding-block:40px;color:var(--apag);font-size:14px;border-top:1px solid var(--linha)}
.cat{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:18px}
.cat a{text-decoration:none;background:var(--card);border:1px solid var(--linha);border-radius:12px;overflow:hidden;display:block;transition:border-color .15s}
.cat a:hover{border-color:var(--dest)}
.cat img{width:100%;display:block;aspect-ratio:1;object-fit:cover}
.cat div{padding:14px 16px}.cat b{font:italic 400 28px/1.1 var(--serif);display:block}.cat span{color:var(--apag);font-size:14px}
@media (max-width:860px){.hero{grid-template-columns:1fr}.leque{height:380px}.g6{grid-template-columns:repeat(3,1fr)}.g4{grid-template-columns:repeat(2,1fr)}.lista,.passos{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto}}
"""

HEAD = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:image" content="{og}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}estilo.css"></head><body>"""


def venda(slug):
    t = (PACKS / "packs" / slug / "venda.md").read_text()
    sub = re.search(r"^\*\*(.+?)\*\*", t, re.M)
    bullets = re.findall(r"^- (.+)$", t, re.M)
    paras = [l for l in t.split("\n\n") if l.strip() and not l.lstrip().startswith(("#", "-", "**", "Preço"))]
    return (sub.group(1) if sub else ""), bullets, (paras[0].strip() if paras else "")


def botao(slug, txt="Quero o pack por R$ 27"):
    url = links.get(slug)
    return f'<a class="btn" href="{html.escape(url)}">{txt}</a>' if url else f'<a class="btn off" aria-disabled="true">Em breve</a>'


def pagina_pack(slug, pack):
    nicho = pack.get("titulo", slug).split("·")[-1].strip()
    sub, bullets, para = venda(slug)
    img = lambda n: f"../img/{slug}/{n}.jpg"
    car = "".join(f'<img src="{img(d["id"])}" alt="Tela {i} do carrossel" loading="lazy">' for i, d in enumerate(pack["carrossel"], 1))
    posts = "".join(f'<img src="{img(d["id"])}" alt="Post" loading="lazy">' for d in pack["posts"])
    sts = "".join(f'<img src="{img(d["id"])}" alt="Story" loading="lazy">' for d in pack["stories"])
    lista = "".join(f"<li>{html.escape(b)}</li>" for b in bullets)
    return HEAD.format(title=f"Pack de Fim de Ano · {nicho}", desc=html.escape(sub), og=f"../img/{slug}/capa-kiwify.jpg", base="../") + f"""
<div class="wrap"><header class="top"><a href="../">Packs de Fim de Ano</a><span>R$ 27</span></header>
<div class="hero"><div><span class="olho">Pack de fim de ano</span><h1>{html.escape(nicho)}</h1>
<p class="sub">{html.escape(sub)}</p><div class="preco"><b>R$ 27</b><span>pagamento único · acesso imediato</span></div>
{botao(slug)}<p class="seg">Compra segura pela Kiwify. Você recebe o acesso por email na hora.</p></div>
<div class="leque" aria-hidden="true"><img class="a" src="{img('c2')}" alt=""><img class="b" src="{img('c1')}" alt=""><img class="c" src="{img('c6')}" alt=""></div></div></div>
<section><div class="wrap"><h2>O carrossel</h2><p class="desc">6 telas pra postar em dezembro, com conteúdo útil pro seu cliente e o convite pra janeiro no final.</p><div class="grade g6">{car}</div></div></section>
<section><div class="wrap"><h2>Posts e stories</h2><p class="desc">4 posts de feed e 4 stories com espaço pros stickers de pergunta e enquete.</p>
<div class="grade g4">{posts}</div><div class="grade g4" style="margin-top:12px">{sts}</div></div></section>
<section><div class="wrap"><h2>O que vem no pack</h2><p class="desc">{html.escape(para)}</p><ul class="lista">{lista}</ul></div></section>
<section><div class="wrap"><h2>Como funciona</h2><div class="passos">
<div class="passo"><b>1</b>Você compra pela Kiwify e recebe por email o login da área de membros.</div>
<div class="passo"><b>2</b>Lá você baixa as 14 artes em PNG e os PDFs pra editar no Canva.</div>
<div class="passo"><b>3</b>Troca nome, registro, @ e foto, e posta. Se preferir, pede a versão já personalizada.</div></div></div></section>
<section><div class="wrap"><h2>Dúvidas</h2>
<details><summary>Preciso saber design?</summary><p>Não. No Canva é só clicar no texto e trocar. As artes já vêm no tamanho certo do Instagram.</p></details>
<details><summary>As fotos são minhas?</summary><p>As fotos de exemplo são de banco de imagem com licença livre. O ideal é trocar por fotos suas pra ficar com a cara do seu negócio.</p></details>
<details><summary>Como recebo?</summary><p>Na hora, por email, com o acesso à área de membros da Kiwify.</p></details>
<details><summary>E se eu não gostar?</summary><p>Você tem 7 dias de garantia pela Kiwify.</p></details></div></section>
<section class="final"><div class="wrap"><h2>Seu dezembro pronto por R$ 27</h2>{botao(slug)}</div></section>
<footer><div class="wrap">Packs de Fim de Ano · Fotos de exemplo: Unsplash (licença livre)</div></footer></body></html>"""


AQUI.joinpath("estilo.css").write_text(CSS)
cards = []
for pj in sorted((PACKS / "packs").glob("*/pack.json")):
    slug = pj.parent.name
    pack = json.loads(pj.read_text())
    d = AQUI / slug; d.mkdir(exist_ok=True)
    (d / "index.html").write_text(pagina_pack(slug, pack))
    nicho = pack.get("titulo", slug).split("·")[-1].strip()
    cards.append(f'<a href="{slug}/"><img src="img/{slug}/capa-kiwify.jpg" alt="Pack {html.escape(nicho)}" loading="lazy"><div><b>{html.escape(nicho)}</b><span>14 artes · R$ 27</span></div></a>')

# e-books
eb_cards = []
for e in sorted(EBOOKS.glob("*/venda.md")):
    slug = e.parent.name
    dst = AQUI / "img" / "ebooks"; dst.mkdir(parents=True, exist_ok=True)
    if (e.parent / "capa-quadrada.png").exists():
        shutil.copy(e.parent / "capa-quadrada.png", dst / f"{slug}.png")
    t = e.read_text(); titulo = re.search(r"^#\s*(.+)$", t, re.M); preco = re.search(r"R\$\s*[\d,]+", t)
    url = links.get(slug, "")
    sub = re.search(r"^\*\*(.+?)\*\*", t, re.M); bullets = re.findall(r"^- (.+)$", t, re.M)
    paras = [l for l in t.split("\n\n") if l.strip() and not l.lstrip().startswith(("#", "-", "**", "Preço"))]
    if (e.parent / "capa-vertical.png").exists(): shutil.copy(e.parent / "capa-vertical.png", dst / f"{slug}-vertical.png")
    pd = AQUI / "ebooks" / slug; pd.mkdir(parents=True, exist_ok=True)
    ttl = titulo.group(1) if titulo else slug; pr = preco.group(0) if preco else ""
    btn = f'<a class="btn" href="{html.escape(url)}">Quero o e-book por {pr}</a>' if url else '<a class="btn off" aria-disabled="true">Em breve</a>'
    (pd / "index.html").write_text(HEAD.format(title=ttl, desc=html.escape(sub.group(1) if sub else ""), og=f"../../img/ebooks/{slug}.png", base="../../") + f"""
<div class="wrap"><header class="top"><a href="../../">Packs de Fim de Ano</a><span>{pr}</span></header>
<div class="hero"><div><span class="olho">E-book</span><h1>{html.escape(ttl)}</h1><p class="sub">{html.escape(sub.group(1) if sub else "")}</p>
<div class="preco"><b>{pr}</b><span>PDF · acesso imediato</span></div>{btn}<p class="seg">Compra segura pela Kiwify. Você recebe o acesso por email na hora.</p></div>
<div><img src="../../img/ebooks/{slug}-vertical.png" alt="Capa do e-book" style="width:100%;border-radius:10px"></div></div></div>
<section><div class="wrap"><h2>O que tem dentro</h2><p class="desc">{html.escape(paras[0].strip() if paras else "")}</p><ul class="lista">{''.join(f"<li>{html.escape(b)}</li>" for b in bullets)}</ul></div></section>
<section class="final"><div class="wrap"><h2>{html.escape(ttl)}</h2>{btn}</div></section>
<footer><div class="wrap">Packs de Fim de Ano · E-books</div></footer></body></html>""")
    url = f"ebooks/{slug}/"
    eb_cards.append(f'<a href="{html.escape(url) if url else "#"}"><img src="img/ebooks/{slug}.png" alt="" loading="lazy"><div><b>{html.escape(titulo.group(1) if titulo else slug)}</b><span>E-book · {preco.group(0) if preco else ""}</span></div></a>')

AQUI.joinpath("index.html").write_text(HEAD.format(title="Packs de Fim de Ano", desc="30 packs de artes de Instagram prontas pro fim de ano, um pra cada profissão. R$ 27 cada.", og="img/dentista/capa-kiwify.jpg", base="") + f"""
<div class="wrap"><header class="top"><span>Packs de Fim de Ano</span><span>R$ 27 cada</span></header>
<div style="padding-block:40px 30px"><span class="olho">Dezembro pronto em 5 minutos</span><h1 style="font:italic 400 clamp(56px,8vw,110px)/.92 var(--serif);color:var(--dest);margin:12px 0 16px;text-wrap:balance">O Instagram do seu negócio no fim de ano</h1>
<p class="sub" style="font-size:20px;max-width:40ch;color:#e2d6c8">14 artes prontas por profissão: carrossel, posts e stories de Natal, recesso e Ano Novo. Escolha a sua.</p></div>
<div class="cat">{''.join(cards)}</div>
{'<h2 style="margin-top:70px">E-books</h2><div class="cat">' + ''.join(eb_cards) + '</div>' if eb_cards else ''}
</div><footer><div class="wrap" style="margin-top:60px">Packs de Fim de Ano · Fotos de exemplo: Unsplash (licença livre)</div></footer></body></html>""")
print("site gerado:", len(cards), "packs,", len(eb_cards), "e-books")
