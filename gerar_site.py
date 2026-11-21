"""Gera o site de vendas dos packs (GitHub Pages, publicado em /packs/).
uso: python3 gerar_site.py  ->  estilo.css + site.js + index.html + <slug>/index.html + ebooks/<slug>/index.html

Fontes de dados:
  ../packs-fim-de-ano/packs/<slug>/pack.json e venda.md   (texto e artes de cada pack)
  ../packs-fim-de-ano/saida/<slug>/canva-*.pdf           (conta as páginas dos PDFs de verdade)
  ../packs-fim-de-ano/kiwify-bumps.json                  (extras opcionais do checkout de cada pack)
  ../ebooks/<slug>/venda.md, ../kit-metas-2027, ../ferias-sem-tela
  links.json                                             (links de checkout da Kiwify; sem link = botão "Em breve")
Imagens das artes: img/<slug>/*.jpg (já exportadas). Capas e prévias dos e-books são copiadas pra img/ebooks/.
"""
import html, json, pathlib, re, shutil, subprocess, unicodedata

AQUI = pathlib.Path(__file__).parent
PACKS = AQUI.parent / "packs-fim-de-ano"
EBOOKS = AQUI.parent / "ebooks"
SITE = "https://guilhermeslvg.github.io/packs/"   # endereço público (og:image precisa de URL completa)
META_PIXEL_ID = ""   # cole aqui o ID do Pixel da Meta quando tiver; vazio = nada de pixel na página
# >>> GOOGLE SEARCH CONSOLE: cole aqui a tag de verificação que o Google mostrar, entre as aspas.
# Pode ser a linha inteira (<meta name="google-site-verification" content="abc123" />) ou só o código (abc123).
# Vazio = sem tag. Ela entra só na página inicial (/packs/), que é a que o Google confere.
GOOGLE_VERIFICACAO = ""
MARCA = "Atelier de Posts"   # nome da loja na Kiwify e na página do Facebook (vai no JSON-LD como marca e vendedor)

links = json.loads((AQUI / "links.json").read_text()) if (AQUI / "links.json").exists() else {}
bumps = json.loads((PACKS / "kiwify-bumps.json").read_text()) if (PACKS / "kiwify-bumps.json").exists() else []
# aspas retas em par viram curvas (“assim”) antes de escapar, igual ao calendário "Quando postar cada uma"
aspas = lambda s: re.sub(r'"([^"\n]+)"', "\u201c\\1\u201d", s)
esc = lambda s: html.escape(aspas(str(s or "")), quote=True)
NB = "\u00a0"                 # espaço que não quebra: "R$ 27" e "7 dias" nunca se separam
PRECO = f"R${NB}27"
GARANTIA = f"7{NB}dias de garantia"
CONFIA = f"Pix, cartão ou boleto · {GARANTIA}"   # sem "acesso na hora": no boleto não é

# nome de cada profissão na vitrine e no rótulo da página, sempre no plural de quem compra
NOMES = {
    "academia": "Academias", "advogado": "Advogados", "arquitetura-interiores": "Arquitetos e designers de interiores",
    "barbearia": "Barbearias", "cafeteria": "Cafeterias", "confeitaria": "Confeitarias", "contador": "Contadores",
    "corretor-de-imoveis": "Corretores de imóveis", "dentista": "Dentistas", "dermatologista": "Dermatologistas",
    "escola-de-idiomas": "Escolas de idiomas", "estetica": "Clínicas de estética", "fisioterapeuta": "Fisioterapeutas",
    "floricultura": "Floriculturas", "fotografo": "Fotógrafos", "hamburgueria": "Hamburguerias",
    "harmonizacao": "Profissionais de harmonização facial", "loja-de-roupas": "Lojas de roupas", "maquiadora": "Maquiadoras",
    "medico": "Médicos", "mentora": "Mentoras de negócios", "nail-designer": "Nail designers", "nutricionista": "Nutricionistas",
    "otica": "Óticas", "personal-trainer": "Personal trainers", "pet-shop": "Pet shops", "psicologa": "Psicólogas",
    "restaurante": "Restaurantes", "salao-de-beleza": "Salões de beleza", "sobrancelha": "Designers de sobrancelha",
}
# primeiro os nichos que têm extras no checkout, depois o resto em ordem alfabética
PRIMEIRO = ["dentista", "estetica", "salao-de-beleza", "barbearia", "nail-designer"]

# ----------------------------------------------------------------------------------------------
# SEO: como cada página aparece no Google. Termos tirados do jeito que as pessoas buscam
# ("pack de artes de natal para dentista", "posts prontos para confeitaria", "artes de natal para salão de beleza").
# BUSCA[slug] = (profissão no singular, como vai no título;  "pro Instagram ___";  o que tem de específico, tirado do venda.md)
# ----------------------------------------------------------------------------------------------
BUSCA = {
    "academia": ("academia", "da academia", "horário das festas, treino curto de 30 minutos e chamada pras matrículas de janeiro"),
    "advogado": ("advogado", "do escritório de advocacia", "dúvidas das festas e recesso com os prazos suspensos, dentro do Provimento 205/2021"),
    "arquitetura-interiores": ("arquitetura de interiores", "de arquitetura e interiores", "decoração de Natal sem bagunçar a casa, recesso e reforma de janeiro"),
    "barbearia": ("barbearia", "da barbearia", "barba e corte pras festas, horário de dezembro e chamada pra agendar"),
    "cafeteria": ("cafeteria", "da cafeteria", "bebida de Natal da casa, café pra presentear e horário das festas"),
    "confeitaria": ("confeitaria", "da confeitaria", "encomendas de Natal, prazo pra pedir, cardápio com seus sabores e retirada no dia 24"),
    "contador": ("contador", "do escritório de contabilidade", "13º salário, recibos pro IR 2027, o que o MEI precisa e recesso"),
    "corretor-de-imoveis": ("corretor de imóveis", "do corretor de imóveis", "casa nova em 2027, recesso e convite pras visitas de janeiro"),
    "dentista": ("dentista", "do consultório odontológico", "cuidados com o sorriso nas festas, recesso e convite pra revisão de janeiro"),
    "dermatologista": ("dermatologista", "do consultório de dermatologia", "protetor solar no verão, limão e sol, queimadura e recesso"),
    "escola-de-idiomas": ("escola de idiomas", "da escola de idiomas", "inglês pra viagem de férias, 15 minutos por dia e matrícula de janeiro"),
    "estetica": ("clínica de estética", "da clínica de estética", "cuidados de pele no calor e no pós-festa, agenda de dezembro e Feliz 2027"),
    "fisioterapeuta": ("fisioterapeuta", "do fisioterapeuta", "pausa na viagem de carro, peso das sacolas, como levantar a mala e recesso"),
    "floricultura": ("floricultura", "da floricultura", "arranjo da mesa de Natal, encomenda com tempo e horário das festas"),
    "fotografo": ("fotógrafo", "do fotógrafo", "dicas pra foto da ceia no celular, ensaio de Natal e recesso"),
    "hamburgueria": ("hamburgueria", "da hamburgueria", "delivery nos dias 25 e 1º, combo família e horário das festas"),
    "harmonizacao": ("harmonização facial", "de harmonização facial", "naturalidade, tempo de recuperação, recesso e Feliz 2027"),
    "loja-de-roupas": ("loja de roupas", "da loja de roupas", "looks de Natal e Réveillon, ideias de presente e horário de fim de ano"),
    "maquiadora": ("maquiadora", "da maquiadora", "maquiagem no calor, o que levar na bolsa, agenda e reserva pro dia 31"),
    "medico": ("médico", "do consultório médico", "bebida e desidratação, remédio na viagem, vacinas, recesso e Feliz 2027"),
    "mentora": ("mentora de negócios", "de mentora de negócios", "4 perguntas de balanço do ano, recesso e convite pra 2027"),
    "nail-designer": ("nail designer", "da nail designer", "unhas pras festas, agenda de dezembro e o que fazer se lascar"),
    "nutricionista": ("nutricionista", "do nutricionista", "água entre os brindes, prato da ceia, sobras no calor e recesso"),
    "otica": ("ótica", "da ótica", "óculos de sol UV400, lente depois da praia, vale-presente e recesso"),
    "personal-trainer": ("personal trainer", "do personal trainer", "treino nas festas, treino de viagem sem academia e metas de janeiro"),
    "pet-shop": ("pet shop", "do pet shop", "fogos que assustam, o que o pet não pode comer da ceia e horário das festas"),
    "psicologa": ("psicóloga", "da psicóloga", "saudade de quem falta, dizer não a convite, ansiedade antes da festa e recesso"),
    "restaurante": ("restaurante", "do restaurante", "reservas, ceia pra levar, mesas pra grupos e horário de 24, 25 e 31/12"),
    "salao-de-beleza": ("salão de beleza", "do salão de beleza", "sol e cloro na cor, penteado pras festas, agenda de dezembro e Feliz 2027"),
    "sobrancelha": ("designer de sobrancelha", "da designer de sobrancelha", "quando marcar, cuidados com henna, vale-design e agenda das festas"),
}
# nestes o rótulo "Pack de Natal e Ano Novo pra ..." quebraria em 2 linhas no celular de 390px (antes cabia em 1):
# fica só "Pack de Natal pra ...", pra hero não descer
ROTULO_CURTO = {"corretor-de-imoveis", "mentora", "sobrancelha"}
# título diferente do padrão quando a busca real usa outra palavra
TITULO_BUSCA = {
    "confeitaria": "Posts prontos de Natal para confeitaria | Instagram | R$ 27",
    "salao-de-beleza": "Artes de Natal para salão de beleza | Instagram | R$ 27",
}
# e-books, kits e os produtos novos (entram sozinhos quando a página for gerada com esse slug)
SEO_PRODUTO = {
    "ceia-sem-stress": ("Cardápio de ceia de Natal com lista de compras | R$ 14,90",
                        "Cardápio de ceia de Natal pra 8 a 10 pessoas: 8 receitas, lista de compras por seção do mercado e cronograma do dia 22 ao 24. E-book em PDF, R$ 14,90."),
    "2027-no-controle": ("Como organizar o dinheiro em 2027 | E-book | R$ 19,90",
                         "Plano de 30 dias pra saber pra onde vai o salário e começar 2027 com orçamento, reserva e metas. 39 páginas em PDF com planner financeiro. R$ 19,90."),
    "kit-metas-2027": ("Metas 2027 para imprimir: bingo e vision board | R$ 14,90",
                       "40 punch cards de metas, bingo de metas 2027, vision board em A4 e A3 e planner trimestral pra imprimir e marcar o ano inteiro. Kit em PDF, R$ 14,90."),
    "ferias-sem-tela": ("Atividades para imprimir nas férias, 3 a 8 anos | R$ 19,90",
                        "87 páginas de atividades pra imprimir: labirintos, caça-palavras, ligue os pontos, desenhos pra colorir e jogos pra crianças de 3 a 8 anos. PDF, R$ 19,90."),
    "dezembro-sem-tela": ("Atividades de Natal para imprimir, 3 a 9 anos | R$ 14,90",
                          "50 atividades de Natal pra imprimir, separadas por idade: labirinto, caça-palavras, colorir, carta pro Papai Noel e calendário de 1 a 24/12. PDF, R$ 14,90."),
    "familia-na-mesa": ("Brincadeiras para a ceia de Natal e Ano Novo | R$ 17,90",
                        "40 brincadeiras pra imprimir e jogar na ceia, na confraternização da firma e na virada: quiz, mímica, bingo natalino e amigo secreto. PDF, R$ 17,90."),
    "cardapio-natal-confeitaria": ("Cardápio de Natal para confeitaria no Canva | R$ 19,90",
                                   "Cardápio de Natal pro feed e pro story, tabela de encomendas P/M/G, etiquetas pra caixa e mensagens de WhatsApp. Editável no Canva, R$ 19,90."),
}

# quem fez: foto e Instagram de verdade do Guilherme
QUEM_FOTO = "img/guilherme.jpg"     # retrato 4:5 (recorte da foto do site pessoal dele)
QUEM_IG = "guiilhermesg_"
AVISOS = []


# ----------------------------------------------------------------------------------------------
# CSS
# ----------------------------------------------------------------------------------------------
CSS = r"""/* Packs de Fim de Ano · estilo gerado por gerar_site.py (não edite à mão)
   Paleta: chão quase preto quente, ouro claro das artes, creme das telas claras do carrossel. */
:root{
  --chao:#16110e;        /* fundo */
  --chao2:#211a15;       /* superfície um tom acima */
  --chao3:#2c231d;       /* superfície dentro de superfície */
  --tinta:#f4ece2;       /* texto */
  --apagado:#c2b4a3;     /* texto secundário: 8:1 sobre --chao */
  --rotulo:rgba(244,236,226,.62);
  --ouro:#ecd7a9;        /* destaque e ação */
  --ouro-tinta:#22180f;  /* texto sobre o ouro */
  --fio:rgba(236,214,163,.15);
  --borda-arte:rgba(236,214,163,.14);
  --creme:#f3eae0;
  --creme2:#e9dccd;
  --creme-tinta:#2b201c;
  --creme-apagado:#5f4e41;

  --serif:"Instrument Serif",Georgia,"Times New Roman",serif;
  --sans:"Hanken Grotesk",system-ui,-apple-system,"Segoe UI",sans-serif;

  --margem:16px;
  --secao:64px;
  --max:1344px;
  --ease-out:cubic-bezier(.23,1,.32,1);
  --ease-gaveta:cubic-bezier(.32,.72,0,1);
}

*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--chao);color:var(--tinta);font:400 17px/1.55 var(--sans);-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;-webkit-tap-highlight-color:transparent;overflow-x:clip}
img{display:block;max-width:100%;height:auto}
a{color:inherit}
h1,h2,h3{font-family:var(--serif);font-style:italic;font-weight:400;margin:0;letter-spacing:-.015em}
p{margin:0;text-wrap:pretty}
ol,ul{margin:0;padding:0;list-style:none}
:focus-visible{outline:2px solid var(--ouro);outline-offset:3px;border-radius:2px}
::selection{background:var(--ouro);color:var(--ouro-tinta)}

.pular{position:absolute;left:var(--margem);top:-60px;background:var(--ouro);color:var(--ouro-tinta);padding:10px 14px;z-index:50;text-decoration:none;font-weight:600}
.pular:focus{top:10px}

/* toda miniatura de arte ganha um fio claro, pra arte escura não sumir no fundo escuro */
.arte{outline:1px solid var(--borda-arte);outline-offset:-1px;border-radius:2px}

/* botão */
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:52px;padding:14px 26px;background:var(--ouro);color:var(--ouro-tinta);font:600 17px/1.2 var(--sans);text-decoration:none;border-radius:999px;transition:transform 160ms var(--ease-out),background-color 200ms ease;touch-action:manipulation;user-select:none;-webkit-user-select:none;text-align:center}
.btn:active{transform:scale(.97)}
@media (hover:hover){.btn:hover{background:#f5e4bd}}
.btn.off{background:var(--chao3);color:var(--apagado);cursor:default}

/* topo */
.topo{padding:8px var(--margem);padding-top:max(8px,env(safe-area-inset-top))}
.topo-in{max-width:calc(var(--max) - 2 * 48px);margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:16px}
.marca{font:italic 400 23px/1 var(--serif);text-decoration:none;min-height:44px;display:flex;align-items:center}
.topo-comprar{font-weight:600;font-size:15px;text-decoration:none;color:var(--ouro);min-height:44px;display:flex;align-items:center;text-underline-offset:4px}
@media (hover:hover){.topo-comprar:hover{text-decoration:underline}}
.topo-comprar.off{color:var(--apagado)}

/* hero */
.hero{padding:4px var(--margem) 0;max-width:var(--max);margin:0 auto;display:grid;gap:18px}
.rotulo{font:600 16px/1.35 var(--sans);color:var(--tinta)}
.hero h1{font-size:clamp(44px,12.4vw,60px);line-height:.95;color:var(--ouro);margin-top:10px;text-wrap:balance}
.hero h1.longo{font-size:clamp(40px,11vw,60px)}
/* o rótulo mora dentro do h1 (o Google lê "Pack de Natal... pra dentistas" como título), mas fica com a cara de antes:
   a margem negativa cancela a margem do h1, então o rótulo e a frase ficam na mesma posição de quando eram p + h1 */
h1>.rotulo{display:block;margin:-10px 0 10px;color:var(--tinta);letter-spacing:normal;text-wrap:pretty}
.hero-sub{font-size:18px;line-height:1.42;margin-top:14px;max-width:34ch;text-wrap:balance}
.hero-compra{display:grid;grid-template-columns:auto 1fr;align-items:center;column-gap:18px;row-gap:10px}
.preco-valor{font:italic 400 48px/1 var(--serif);color:var(--tinta);white-space:nowrap}
.hero-compra .btn{width:100%}
.seguro{grid-column:1/-1;color:var(--apagado);font-size:14px;line-height:1.4}

/* palco: capa e celular lado a lado. O celular nunca cobre a faixa de baixo da capa (nome, registro e @):
   a borda de baixo dele fica acima de 85% da altura da capa e ele invade a capa em no máximo 8px. */
.hero-palco{display:grid;grid-template-columns:63fr 37fr;align-items:start;margin-top:6px;container-type:inline-size}
.hero-capa{grid-column:1;grid-row:1;display:block;margin-top:24cqw}
.hero-capa img{width:100%}
.palco-lado{display:contents}
.celular{grid-column:2;grid-row:1;margin:0 -12px 0 -6px;z-index:2;position:relative;container-type:inline-size}
.palco-nota{grid-column:1/-1;grid-row:2;color:var(--apagado);font-size:14px;line-height:1.4;margin-top:12px;max-width:40ch}

/* celular em CSS: tudo dentro escala com a largura do aparelho */
.cel-tela{aspect-ratio:9/18.6;background:#000;border-radius:13cqw;border:2.4cqw solid #2e2620;overflow:hidden;position:relative;font-family:-apple-system,"Hanken Grotesk",system-ui,sans-serif;color:#f5f5f5;box-shadow:0 0 0 .6cqw #4a3e34,0 24px 60px rgba(0,0,0,.5)}
.cel-status{display:flex;justify-content:space-between;align-items:center;padding:3.6cqw 8cqw 0;font-size:4.2cqw;font-weight:600;height:11cqw}
.cel-ilha{width:28cqw;height:8cqw;background:#111;border-radius:99px;position:absolute;left:50%;top:2.4cqw;transform:translateX(-50%)}
.cel-bat{width:7.5cqw;height:3.6cqw;border-radius:1cqw;background:#f5f5f5}
.ig-topo{padding:2cqw 5cqw 3cqw;font-size:5.2cqw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ig-perfil{display:flex;gap:4.5cqw;align-items:center;padding:0 5cqw}
.ig-avatar{flex:none;width:20cqw;height:20cqw;border-radius:50%;display:grid;place-items:center;background:var(--chao3);color:var(--ouro);font:italic 400 8cqw/1 var(--serif);box-shadow:0 0 0 .8cqw #000,0 0 0 1.5cqw var(--ouro)}
.ig-nome{display:grid;font-size:3.7cqw;line-height:1.35;color:#cfcfcf;min-width:0}
.ig-nome>*{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ig-nome b{color:#f5f5f5;font-size:4cqw}
.ig-botoes{display:grid;grid-template-columns:1fr 1fr;gap:2cqw;padding:4cqw 5cqw 0}
.ig-botoes span{background:#363636;color:#fff;border-radius:2.4cqw;text-align:center;font-size:3.6cqw;font-weight:600;padding:2.2cqw 0}
.ig-destaques{display:flex;gap:3.6cqw;padding:4.5cqw 5cqw 4cqw}
.ig-destaques span{display:grid;justify-items:center;gap:1.4cqw;width:15cqw}
.ig-destaques img{width:15cqw;height:15cqw;border-radius:50%;object-fit:cover;object-position:50% 40%;box-shadow:0 0 0 .5cqw #000,0 0 0 1cqw #3a3a3a}
.ig-destaques i{font-style:normal;font-size:2.9cqw;color:#ddd;white-space:nowrap;max-width:17cqw;overflow:hidden;text-overflow:ellipsis}
.ig-grade{display:grid;grid-template-columns:repeat(3,1fr);gap:.5cqw}
.ig-grade img{width:100%;aspect-ratio:4/5;object-fit:cover}
.ig-multi{position:relative}
.ig-multi::after{content:"";position:absolute;right:2cqw;top:2cqw;width:3.4cqw;height:3.4cqw;border:.6cqw solid #fff;border-radius:.6cqw;box-shadow:.9cqw -.9cqw 0 -.2cqw rgba(255,255,255,.9)}

/* entrada da página: a capa e o feed do celular aparecem em sequência, uma vez */
@media (prefers-reduced-motion:no-preference){
  .hero-capa{animation:sobe 700ms var(--ease-out) both}
  .cel-tela{animation:sobe 700ms var(--ease-out) 120ms both}
  .ig-grade>*{animation:aparece 500ms var(--ease-out) both}
  .ig-grade>*:nth-child(1){animation-delay:520ms}
  .ig-grade>*:nth-child(2){animation-delay:590ms}
  .ig-grade>*:nth-child(3){animation-delay:660ms}
  .ig-grade>*:nth-child(4){animation-delay:730ms}
  .ig-grade>*:nth-child(5){animation-delay:800ms}
  .ig-grade>*:nth-child(6){animation-delay:870ms}
}
@keyframes sobe{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
@keyframes aparece{from{opacity:0;transform:scale(.96)}to{opacity:1;transform:none}}

/* blocos */
.bloco{padding:var(--secao) var(--margem) 0;max-width:var(--max);margin:0 auto}
.cab h2,.bloco>h2,.dados h2,.creme h2,.compra h2,.duvidas h2{font-size:clamp(38px,10.4vw,48px);line-height:1;color:var(--tinta);text-wrap:balance}
.cab p{margin-top:12px;max-width:52ch}
.cab{margin-bottom:20px}

/* artes clicáveis */
a.abre{display:block;overflow:hidden;background:var(--chao2);cursor:zoom-in;border-radius:2px}
a.abre img{width:100%;transition:transform 400ms var(--ease-out)}
@media (hover:hover){a.abre:hover img{transform:scale(1.025)}}
a.abre:active img{transform:scale(.985);transition-duration:160ms}
.legenda{display:block;font-size:15px;color:var(--apagado);margin-top:10px;line-height:1.35}
/* no celular a arte já diz o que é: legenda só no computador */
.grade-posts .legenda,.fila-stories .legenda{display:none}

/* carrossel no celular: moldura de post do Instagram, desliza de lado */
.post-ig{margin-inline:calc(var(--margem) * -1)}
.pig-cab{display:flex;align-items:center;gap:10px;padding:0 var(--margem) 10px;font-size:14px}
.pig-av{width:32px;height:32px;border-radius:50%;display:grid;place-items:center;background:var(--chao3);color:var(--ouro);font:italic 400 14px/1 var(--serif);box-shadow:0 0 0 1.5px var(--chao),0 0 0 3px var(--ouro)}
.pig-cab b{font-weight:600}
.pig-cab .pig-mais{margin-left:auto;letter-spacing:.12em;color:var(--apagado)}
.pig-palco{position:relative}
.trilho{display:grid;grid-auto-flow:column;grid-auto-columns:100%;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;overscroll-behavior-x:contain}
.trilho::-webkit-scrollbar{display:none}
.trilho li{scroll-snap-align:start;scroll-snap-stop:always}
.trilho .legenda{display:none}
.trilho a.abre,.trilho .arte{border-radius:0}
.pig-cont{position:absolute;right:12px;top:12px;background:rgba(14,10,8,.72);color:#fff;font:600 12px/1 var(--sans);padding:6px 9px;border-radius:99px;font-variant-numeric:tabular-nums;pointer-events:none}
.pig-pontos{display:flex;justify-content:center;gap:5px;padding:12px 0 0}
.pig-pontos i{width:6px;height:6px;border-radius:50%;background:#5a4d42;transition:background-color 200ms ease}
.pig-pontos i.on{background:var(--ouro)}
.dica-toque{color:var(--apagado);font-size:15px;margin-top:12px}

/* posts */
.grade-posts{display:grid;grid-template-columns:1fr 1fr;gap:10px}

/* stories */
.fila-stories{display:grid;grid-auto-flow:column;grid-auto-columns:58%;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;margin-inline:calc(var(--margem) * -1);padding:0 var(--margem) 8px;scroll-padding-inline:var(--margem);scrollbar-width:none;overscroll-behavior-x:contain}
.fila-stories::-webkit-scrollbar{display:none}
.fila-stories li{scroll-snap-align:start}

/* quando postar */
.datas{border-bottom:1px solid var(--fio)}
.datas li{display:grid;grid-template-columns:1fr auto;grid-template-areas:"q m" "o m";column-gap:16px;row-gap:2px;align-items:center;padding:14px 0;border-top:1px solid var(--fio)}
.quando{grid-area:q;font:italic 400 22px/1.1 var(--serif);color:var(--ouro);align-self:end}
.oque{grid-area:o;font-size:15px;line-height:1.4;align-self:start}
.mini{grid-area:m;display:flex;gap:6px;align-items:flex-end}
.mini img{width:56px;height:70px;object-fit:cover}
.mini img.st{width:40px}

/* seus dados / regras do conselho */
.dados{display:grid;gap:28px}
.declara{font-size:19px;line-height:1.42;margin-top:16px;max-width:36ch}
.aviso{color:var(--apagado);margin-top:12px;max-width:46ch;font-size:16px}
.dados-prova{margin:0}
.recorte{position:relative;aspect-ratio:720/226;overflow:visible}
.recorte img{width:100%;height:100%;object-fit:cover;object-position:50% 100%}
.aqui{position:absolute;top:44%;transform:translateY(-50%);background:var(--ouro);color:var(--ouro-tinta);font:600 15px/1 var(--sans);padding:8px 12px 8px 10px;border-radius:3px;box-shadow:0 6px 18px rgba(0,0,0,.35)}
.aqui::before{content:"";position:absolute;right:100%;top:50%;transform:translateY(-50%);border:7px solid transparent;border-right-color:var(--ouro)}
.dados-prova figcaption{color:var(--apagado);font-size:15px;margin-top:12px;max-width:52ch}

/* campo creme */
.creme{max-width:none;padding-inline:0;margin-top:var(--secao);padding-top:0}
.creme-in{background:var(--creme);color:var(--creme-tinta);padding:56px var(--margem)}
.creme-in>*{max-width:calc(var(--max) - 2 * var(--margem));margin-inline:auto}
.creme h2{color:var(--creme-tinta)}
.passos{counter-reset:p;display:grid;gap:24px;margin-top:28px}
.passos>li{counter-increment:p;display:grid;grid-template-columns:40px 1fr;column-gap:12px;align-content:start}
.passos>li::before{content:counter(p);grid-row:1/4;font:italic 400 42px/.9 var(--serif);color:#8a6238}
.passos b{font-weight:600;font-size:18px}
.passos span{color:var(--creme-apagado);margin-top:2px;max-width:46ch}
.pasta{margin-top:8px;display:grid;gap:0;font-size:15px;color:var(--creme-tinta)}
.pasta li{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-top:1px solid rgba(43,32,28,.14)}
.pasta li:last-child{border-bottom:1px solid rgba(43,32,28,.14)}
.pasta code{font:600 15px/1.3 var(--sans)}
.pasta small{font-size:15px;color:var(--creme-apagado);text-align:right;font-variant-numeric:tabular-nums}
.pronta{margin-top:36px;background:var(--creme2);padding:22px 18px}
.pronta h3{font-size:30px;line-height:1.05}
.pronta p{margin-top:10px;max-width:58ch}

/* compra */
.compra{display:grid;gap:28px}
.compra-arte{display:none}
.leva{margin-top:20px;display:grid;gap:8px;font-size:18px}
.leva li{padding-left:22px;position:relative}
.leva li::before{content:"";position:absolute;left:2px;top:.62em;width:8px;height:8px;border-radius:50%;background:var(--ouro)}
.btn-grande{margin-top:26px;width:100%;min-height:58px;font-size:18px}
.garantias{display:grid;gap:12px;margin-top:24px;color:var(--apagado);font-size:15px;max-width:52ch}
.garantias b{color:var(--tinta);font-weight:600}

/* dúvidas */
.abre-duvidas{color:var(--apagado);margin-top:14px;max-width:56ch;font-size:16px}
.lista-duvidas{margin-top:20px;display:grid;gap:8px}
details{background:var(--chao2)}
summary{cursor:pointer;list-style:none;padding:17px 52px 17px 18px;font-weight:600;font-size:17px;position:relative;min-height:56px}
summary::-webkit-details-marker{display:none}
summary::after{content:"+";position:absolute;right:18px;top:50%;transform:translateY(-50%);font:400 28px/1 var(--serif);color:var(--ouro);transition:transform 200ms var(--ease-out)}
details[open] summary::after{transform:translateY(-50%) rotate(45deg)}
details p{padding:0 18px 20px;color:#e3d8cb;max-width:62ch}

/* quem fez: foto de verdade, sem moldura enfeitada */
.quem{display:grid;gap:20px}
.quem-foto{margin:0;display:flex;align-items:flex-end;gap:16px}
.quem-foto img{width:120px;height:150px;object-fit:cover;background:var(--creme2);border-radius:2px;flex:none}
/* nome, cidade e @ encostados na base da foto: a linha do @ fecha junto com a borda de baixo do retrato */
.quem-foto figcaption{display:grid;justify-items:start;gap:2px;font-size:16px;line-height:1.3}
.quem-foto b{font-weight:600;font-size:17px}
.quem-local{font-size:15px;color:var(--apagado)}
.quem-foto a{color:var(--ouro);text-underline-offset:3px;line-height:1;margin-top:10px;position:relative;display:inline-block;padding-bottom:1px}
.quem-foto a::after{content:"";position:absolute;inset:-14px -10px -14px -10px}  /* área de toque de 44px sem empurrar o texto */
.quem p{font-size:19px;line-height:1.5;max-width:40ch}

/* rodapé */
.rodape{padding:var(--secao) var(--margem) 36px;max-width:var(--max);margin:0 auto}
.rodape-nome{font:italic 400 clamp(42px,11vw,112px)/.95 var(--serif);text-wrap:balance;color:var(--ouro);letter-spacing:-.02em}
.rodape .btn-grande{margin-top:32px}
.rodape-linha{display:flex;flex-wrap:wrap;gap:8px 28px;justify-content:space-between;align-items:last baseline;margin-top:24px;color:var(--apagado);font-size:15px}
.rodape-linha a{color:var(--tinta);text-underline-offset:4px;min-height:44px;display:inline-flex;align-items:center}

/* barra fixa de compra no celular */
.barra{position:fixed;left:0;right:0;bottom:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:10px var(--margem);padding-bottom:max(10px,env(safe-area-inset-bottom));background:var(--chao2);box-shadow:0 -10px 30px rgba(10,7,5,.55)}
.barra p{display:grid;line-height:1.15}
.barra p b{font:italic 400 30px/1 var(--serif)}
.barra p span{font-size:13px;color:var(--apagado)}
.barra .btn{min-height:48px;padding:12px 22px;flex:none}
.js .barra{transform:translateY(110%);transition:transform 320ms var(--ease-gaveta),visibility 0s 320ms;visibility:hidden}
.js .barra.on{transform:none;visibility:visible;transition:transform 320ms var(--ease-gaveta),visibility 0s}
.com-barra{padding-bottom:76px}

/* tela cheia */
.luz{border:0;padding:0;margin:0;width:100vw;max-width:100vw;height:100dvh;max-height:100dvh;background:#0d0a08;color:var(--tinta)}
.luz::backdrop{background:#0d0a08}
.luz[open]{display:grid;place-items:center}
.luz figure{margin:0;display:grid;justify-items:center;gap:12px;padding:64px 12px 84px}
.luz img{max-width:min(92vw,720px);max-height:calc(100dvh - 170px);width:auto;height:auto}
.luz figcaption{font-size:15px;color:var(--apagado);text-align:center;max-width:44ch}
.luz button{position:absolute;background:var(--chao3);color:var(--tinta);border:0;font:600 15px var(--sans);min-width:48px;min-height:48px;border-radius:999px;cursor:pointer;transition:transform 160ms var(--ease-out)}
.luz button:active{transform:scale(.95)}
.luz-fechar{top:max(12px,env(safe-area-inset-top));right:12px;padding:0 18px}
.luz-seta{bottom:max(18px,env(safe-area-inset-bottom));font:400 30px/1 var(--serif)!important}
.luz-seta.ant{left:calc(50% - 60px)}
.luz-seta.prox{left:calc(50% + 12px)}

/* vitrine (página inicial) */
.vit-hero{padding:4px var(--margem) 0;max-width:var(--max);margin:0 auto;display:grid;gap:28px}
.vit-hero h1{font-size:clamp(44px,12.4vw,60px);line-height:.95;color:var(--ouro);margin-top:10px;text-wrap:balance}
/* no celular, faixa que desliza com 1,3 capa à vista; no computador, 3 capas alinhadas pela base */
.vit-capas{display:grid;grid-auto-flow:column;grid-auto-columns:74%;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;margin-inline:calc(var(--margem) * -1);padding:0 var(--margem);scroll-padding-inline:var(--margem);scrollbar-width:none;overscroll-behavior-x:contain}
.vit-capas::-webkit-scrollbar{display:none}
.vit-capas a{display:block;text-decoration:none;scroll-snap-align:start}
.vit-capas span{display:block;font-size:15px;color:var(--tinta);margin-top:10px;line-height:1.3}
.vit-confia{color:var(--apagado);font-size:15px;margin-top:16px}
.vit-hero .btn{margin-top:22px;width:100%}
.vitrine{display:grid;grid-template-columns:1fr 1fr;gap:28px 12px}
.vitrine a{text-decoration:none;display:block}
.vitrine img{width:100%;object-fit:cover;transition:transform 400ms var(--ease-out)}
.vitrine .foto{overflow:hidden;border-radius:2px}
@media (hover:hover){.vitrine a:hover img{transform:scale(1.03)}.vitrine a:hover b{color:var(--ouro)}}
.vitrine a:active img{transform:scale(.985)}
.vitrine b{display:block;font:600 18px/1.25 var(--sans);margin-top:10px;transition:color 200ms ease;text-wrap:balance}
.vitrine span{display:block;font-size:15px;color:var(--apagado);margin-top:2px}
.vit-como{display:grid;gap:22px;margin-top:28px}
.vit-como p{max-width:44ch}
.vit-como b{display:block;font-weight:600;font-size:18px;margin-bottom:2px}

/* e-book */
.eb-capa{display:block;width:78%;margin:6px auto 0}
.eb-capa img{width:100%}
.eb-lista{display:grid;gap:14px;margin-top:22px;max-width:62ch}
.eb-lista li{padding-left:22px;position:relative}
.eb-lista li::before{content:"";position:absolute;left:2px;top:.62em;width:8px;height:8px;border-radius:50%;background:var(--ouro)}
.eb-desc{font-size:18px;line-height:1.5;max-width:46ch}

/* tablet e computador */
@media (min-width:900px){
  :root{--margem:48px;--secao:160px}
  body{font-size:18px}
  .com-barra{padding-bottom:0}
  .topo{position:sticky;top:0;z-index:10;background:var(--chao);padding-block:10px}
  .topo-comprar{background:var(--ouro);color:var(--ouro-tinta);padding:0 20px;border-radius:999px;transition:transform 160ms var(--ease-out)}
  .topo-comprar.off{background:var(--chao3);color:var(--apagado)}
  .topo-comprar:active{transform:scale(.97)}
  @media (hover:hover){.topo-comprar:hover{text-decoration:none;background:#f5e4bd}}
  .barra{display:none}

  .hero{grid-template-columns:6fr 6fr;grid-template-areas:"texto palco" "compra palco";grid-template-rows:1fr auto;column-gap:64px;row-gap:40px;padding-top:36px}
  .hero-texto{grid-area:texto;align-self:end}
  .hero-compra{grid-area:compra;align-self:end;margin-bottom:56px;grid-template-columns:auto auto;justify-content:start}
  .hero-palco{grid-area:palco;margin:0}
  .hero h1{font-size:clamp(60px,5.3vw,78px)}
  .rotulo{font-size:17px}
  .hero-sub{font-size:22px;margin-top:32px}
  .preco-valor{font-size:60px}
  .hero-compra .btn{width:auto;min-height:58px;padding-inline:34px;font-size:18px}
  .seguro{font-size:15px}
  .hero-palco{grid-template-columns:68fr 32fr}
  .hero-capa{margin-top:6cqw}
  .palco-lado{display:grid;grid-template-columns:minmax(0,1fr);grid-column:2;grid-row:1;margin-left:-12px;gap:14px;align-content:start}
  .celular{grid-column:1;grid-row:1;margin:0}
  .palco-nota{grid-column:1;grid-row:2;margin:0;padding-left:12px;font-size:15px}

  .cab{display:grid;grid-template-columns:5fr 7fr;gap:48px;align-items:end;margin-bottom:44px}
  .cab h2,.bloco>h2,.dados h2,.creme h2,.compra h2,.duvidas h2{font-size:clamp(56px,5.4vw,80px)}
  .cab p{margin:0;max-width:48ch;font-size:19px}

  .post-ig{margin:0}
  .pig-cab,.pig-cont,.pig-pontos,.dica-toque{display:none}
  .trilho{grid-auto-flow:row;grid-template-columns:repeat(3,1fr);gap:40px 24px;overflow:visible}
  .trilho .legenda{display:block}
  .trilho a.abre,.trilho .arte{border-radius:2px}
  .grade-posts .legenda,.fila-stories .legenda{display:block}

  .grade-posts{grid-template-columns:repeat(4,1fr);gap:24px}

  .fila-stories{grid-auto-flow:row;grid-template-columns:repeat(4,1fr);gap:24px;overflow:visible;margin:0;padding:0}

  .datas li{grid-template-columns:280px 220px 1fr;grid-template-areas:"q m o";column-gap:40px;padding:22px 0}
  .quando{font-size:34px;align-self:center}
  .oque{font-size:18px;align-self:center;max-width:52ch}
  .mini{gap:10px}
  .mini img{width:80px;height:100px}.mini img.st{width:56px}

  .dados{grid-template-columns:5fr 7fr;gap:72px;align-items:center}
  .declara{font-size:24px;max-width:32ch}
  .aqui{font-size:17px;padding:10px 14px 10px 12px}

  .creme-in{padding:120px var(--margem)}
  .passos{grid-template-columns:1fr 1fr 1.5fr 1fr;gap:44px;margin-top:56px}
  .passos>li{grid-template-columns:1fr;row-gap:10px;align-content:start}
  .passos>li::before{grid-row:auto;font-size:72px}
  .pronta{margin-top:72px;padding:36px 40px;display:grid;grid-template-columns:5fr 7fr;gap:40px;align-items:center}
  .pronta h3{font-size:44px}
  .pronta p{margin:0;font-size:19px}

  .compra{grid-template-columns:6fr 6fr;gap:72px;align-items:center}
  .compra-arte{display:block}
  .btn-grande{width:auto;padding-inline:40px}

  .duvidas{display:grid;grid-template-columns:4fr 8fr;gap:48px;align-items:start}
  .lista-duvidas{margin:0}

  .quem{grid-template-columns:4fr 8fr;grid-template-rows:auto 1fr;column-gap:48px;row-gap:32px;align-items:start}
  .quem h2{grid-column:1;grid-row:1}
  .quem-foto{grid-column:1;grid-row:2}
  .quem p{grid-column:2;grid-row:1/3;font-size:28px;line-height:1.4;margin:0;max-width:34ch}

  .luz-seta{top:50%;bottom:auto;transform:translateY(-50%)}
  .luz-seta:active{transform:translateY(-50%) scale(.95)}
  .luz-seta.ant{left:24px}.luz-seta.prox{left:auto;right:24px}

  .vit-hero{grid-template-columns:minmax(0,1fr) minmax(0,1.65fr);column-gap:56px;align-items:stretch;padding-top:56px}
  .vit-hero h1{font-size:clamp(64px,6vw,92px)}
  .vit-hero .hero-sub{font-size:22px;margin-top:28px}
  /* 3 capas em escada, da altura do texto: a 1ª começa na linha do rótulo, a 3ª termina na base do botão.
     Sem sobreposição: vão de 24px entre elas, então nenhuma letra da arte fica cortada pela capa do lado. */
  .vit-capas{display:block;position:relative;overflow:visible;margin:0;padding:0;min-height:470px;container-type:inline-size}
  .vit-capas a{--w:min(240px,calc((100cqw - 48px) / 3));position:absolute;width:var(--w)}
  .vit-capas a:nth-child(1){left:0;top:0}
  .vit-capas a:nth-child(2){left:calc(50% - var(--w) / 2);top:calc((100% - var(--w) * 1.25) / 2)}
  .vit-capas a:nth-child(3){right:0;top:calc(100% - var(--w) * 1.25)}
  .vit-capas span{font-size:16px}
  .vit-hero .btn{width:auto;min-height:58px;padding-inline:34px;font-size:18px}
  .vitrine{grid-template-columns:repeat(4,1fr);gap:48px 24px}
  .vitrine b{font-size:19px}
  .vit-como{grid-template-columns:repeat(3,1fr);gap:44px;margin-top:48px}

  .eb-capa{width:auto;margin:0}
  .eb-lista{grid-template-columns:1fr 1fr;column-gap:48px;max-width:none}
}
@media (min-width:1200px){.vitrine{grid-template-columns:repeat(5,1fr)}}

@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  *,*::before,*::after{animation:none!important;transition:none!important}
}
"""

# ----------------------------------------------------------------------------------------------
# JS (barra fixa, contador do carrossel, tela cheia, UTM pro checkout, eventos do pixel)
# ----------------------------------------------------------------------------------------------
JS = r"""(function () {
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
"""


# ----------------------------------------------------------------------------------------------
# pedaços comuns
# ----------------------------------------------------------------------------------------------
PAGINAS = []   # (caminho, [imagens]) de cada página gerada, pro sitemap.xml


def dimensoes(rel):
    """Largura e altura de uma imagem do site (sips do Mac). None se não der pra ler."""
    try:
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(AQUI / rel)], capture_output=True, text=True, check=True).stdout
        w, h = re.search(r"pixelWidth:\s*(\d+)", out), re.search(r"pixelHeight:\s*(\d+)", out)
        return (int(w.group(1)), int(h.group(1))) if w and h else None
    except Exception:
        return None


def texto_puro(s):
    """HTML da página -> texto igual ao que aparece na tela (pro JSON-LD bater com o visível)."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", str(s or "")))).strip()


def jsonld(*objs):
    """<script type="application/ld+json"> com os objetos; "</" escapado pra nunca fechar o script antes da hora."""
    tags = []
    for o in objs:
        if o:
            tags.append('<script type="application/ld+json">' + json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>")
    return "\n".join(tags)


def ld_produto(nome, desc, imagens, url_compra, preco, sku, categoria):
    """Product com Offer. Sem aggregateRating e sem review: não existe avaliação de verdade pra mostrar."""
    if not url_compra:
        return None
    return {
        "@context": "https://schema.org", "@type": "Product", "name": nome, "description": desc,
        "image": imagens, "sku": sku, "category": categoria,
        "brand": {"@type": "Brand", "name": MARCA},
        "offers": {
            "@type": "Offer", "url": url_compra, "price": f"{float(valor(preco)):.2f}", "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock", "itemCondition": "https://schema.org/NewCondition",
            "seller": {"@type": "Organization", "name": MARCA},
            # garantia de 7 dias da Kiwify (é o que a página promete)
            "hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy", "applicableCountry": "BR",
                                        "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                                        "merchantReturnDays": 7, "returnFees": "https://schema.org/FreeReturn"},
        },
    }


def ld_faq(perguntas):
    if not perguntas:
        return None
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": texto_puro(q),
                            "acceptedAnswer": {"@type": "Answer", "text": texto_puro(r)}} for q, r in perguntas]}


def ld_trilha(*itens):
    """BreadcrumbList: [(nome, caminho), ...] a partir da raiz do site."""
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": n, "name": nome, "item": SITE + cam}
                                for n, (nome, cam) in enumerate(itens, 1)]}


def head(title, desc, og, base, view_content=False, caminho="", og_alt="", ld="", preco=None, imagens=()):
    """caminho: endereço da página a partir de SITE ("" = página inicial, "dentista/", "ebooks/ceia-sem-stress/").
    Monta canonical, Open Graph, Twitter e o JSON-LD (ld) e anota a página pro sitemap."""
    canon = SITE + caminho
    PAGINAS.append((caminho, [og] + [i for i in imagens if i != og]))
    dim = dimensoes(og.replace(SITE, "", 1)) if og.startswith(SITE) else None
    og_dim = f'\n<meta property="og:image:width" content="{dim[0]}">\n<meta property="og:image:height" content="{dim[1]}">' if dim else ""
    og_alt = og_alt or title
    tipo = "product" if preco else "website"
    preco_meta = (f'\n<meta property="product:price:amount" content="{float(valor(preco)):.2f}">'
                  f'\n<meta property="product:price:currency" content="BRL">') if preco else ""
    verif = ""
    if caminho == "" and GOOGLE_VERIFICACAO.strip():
        m = re.search(r'content="([^"]+)"', GOOGLE_VERIFICACAO)
        verif = f'\n<meta name="google-site-verification" content="{esc(m.group(1) if m else GOOGLE_VERIFICACAO.strip())}">'
    seo = f"""<link rel="canonical" href="{esc(canon)}">
<meta name="robots" content="index,follow,max-image-preview:large">{verif}
<meta property="og:type" content="{tipo}">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="Packs de Fim de Ano · {esc(MARCA)}">
<meta property="og:url" content="{esc(canon)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{esc(og)}">{og_dim}
<meta property="og:image:alt" content="{esc(og_alt)}">{preco_meta}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{esc(og)}">
<meta name="twitter:image:alt" content="{esc(og_alt)}">
{ld}"""
    pixel = ""
    if META_PIXEL_ID:
        pixel = ("<script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};"
                 "if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];"
                 "s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');"
                 f"fbq('init','{esc(META_PIXEL_ID)}');fbq('track','PageView');" + ("fbq('track','ViewContent');" if view_content else "") + "</script>")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{seo}
<meta name="theme-color" content="#16110e">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Hanken+Grotesk:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}estilo.css">
{pixel}</head>
"""


def topo(base, slug=None, preco="R$ 27", url=None):
    if slug is None:
        direita = ""
    elif url:
        direita = f'<a class="topo-comprar" href="{esc(url)}" data-compra data-valor="{valor(preco)}">Comprar por {preco}</a>'
    else:
        direita = '<span class="topo-comprar off">Em breve</span>'
    return f"""<header class="topo">
  <div class="topo-in">
    <a class="marca" href="{base or './'}">Packs de Fim de Ano</a>
    {direita}
  </div>
</header>
"""


def valor(preco):
    m = re.search(r"[\d.,]+", preco or "")
    return m.group(0).replace(".", "").replace(",", ".") if m else "0"


def botao(url, txt, preco, cls="btn", ident=""):
    idattr = f' id="{ident}"' if ident else ""
    if url:
        return f'<a class="{cls}"{idattr} href="{esc(url)}" data-compra data-valor="{valor(preco)}">{txt}</a>'
    return f'<span class="{cls} off"{idattr} aria-disabled="true">Em breve</span>'


def barra(url, preco, linha, txt):
    if not url:
        return ""
    return f"""<div class="barra" id="barra">
  <p><b>{preco}</b><span>{linha}</span></p>
  <a class="btn" href="{esc(url)}" data-compra data-valor="{valor(preco)}">{txt}</a>
</div>
"""


LUZ = """<dialog class="luz" id="luz" aria-label="Arte em tela cheia">
  <figure>
    <img id="luz-img" src="data:," alt="">
    <figcaption id="luz-cap"></figcaption>
  </figure>
  <button class="luz-fechar" type="button" data-acao="fechar" aria-label="Fechar">Fechar</button>
  <button class="luz-seta ant" type="button" data-acao="ant" aria-label="Arte anterior">‹</button>
  <button class="luz-seta prox" type="button" data-acao="prox" aria-label="Próxima arte">›</button>
</dialog>
"""


def quem_fez(base, texto):
    foto = ""
    if (AQUI / QUEM_FOTO).exists():
        foto = (f'<figure class="quem-foto"><img src="{base}{QUEM_FOTO}" width="360" height="450" alt="Foto do Guilherme, de camiseta preta, sorrindo" loading="lazy">'
                f'<figcaption><b>Guilherme</b><span class="quem-local">Designer · Timóteo, MG</span><a href="https://instagram.com/{QUEM_IG}" target="_blank" rel="noopener">@{QUEM_IG}</a></figcaption></figure>')
    return f"""<section class="bloco quem" aria-labelledby="t-quem">
  <h2 id="t-quem">Quem fez</h2>
  {foto}
  <p>{texto}</p>
</section>
"""


def nome_pack(slug, pack):
    return NOMES.get(slug) or pack.get("titulo", slug).split("·")[-1].strip()


def rodape(base, frase, extra="", link=("", "Ver os packs de todas as profissões"), cta=""):
    """cta: botão de compra logo abaixo da frase final (quem lê até o fim tem onde comprar sem voltar pro topo)."""
    return f"""<footer class="rodape">
  <p class="rodape-nome">{frase}</p>
  {cta}
  <div class="rodape-linha">
    <a href="{link[0] or base or './'}">{link[1]}</a>
    <span>{extra}Feito por Guilherme, designer em Timóteo, MG.</span>
  </div>
</footer>
"""


# ----------------------------------------------------------------------------------------------
# leitura do venda.md (dois formatos convivem: "**subtítulo**" ou subtítulo solto + "## Descrição")
# ----------------------------------------------------------------------------------------------
def md_inline(s):
    s = esc(s)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)


def ler_venda(path):
    t = path.read_text()
    titulo, secoes, atual = "", {"_topo": []}, "_topo"
    for l in t.splitlines():
        if l.startswith("# ") and not titulo:
            titulo = l[2:].strip(); continue
        if l.startswith("## "):
            atual = l[3:].strip().lower(); secoes.setdefault(atual, []); continue
        secoes.setdefault(atual, []).append(l)

    def paras(linhas):
        blocos, cur = [], []
        for l in linhas + [""]:
            if l.strip():
                cur.append(l.strip())
            elif cur:
                blocos.append(" ".join(cur)); cur = []
        return blocos

    def texto_livre(b):
        return not b.startswith(("-", "#")) and not re.match(r"^\*{0,2}Pre[çc]o", b)

    sub = ""
    for b in paras(secoes["_topo"]):
        if b.startswith("-") or re.match(r"^\*{0,2}Pre[çc]o", b):
            continue
        sub = re.sub(r"^\*\*Subt[íi]tulo:\*\*\s*", "", b).strip()
        sub = re.sub(r"^\*\*(.+)\*\*$", r"\1", sub).strip()
        break
    bullets = []
    for nome, linhas in secoes.items():
        if "entrega" in nome:
            continue
        bullets += [l[2:].strip() for l in linhas if l.startswith("- ")]
    desc = ""
    for nome in ("descrição", "descricao"):
        if secoes.get(nome):
            ps = [p for p in paras(secoes[nome]) if texto_livre(p)]
            desc = ps[0] if ps else ""
    if not desc:
        for nome, linhas in secoes.items():
            if "entrega" in nome:
                continue
            ps = [p for p in paras(linhas) if texto_livre(p) and not p.startswith("**") and p != sub]
            if ps:
                desc = ps[0]; break
    # a seção "Como funciona a entrega" do venda.md fala do formulário da versão personalizada, que é outro
    # produto (upsell de R$ 47): o site não usa esse texto.
    preco = re.search(r"R\$\s*[\d.,]*\d", t)
    return {"titulo": titulo, "sub": sub, "bullets": bullets, "desc": desc,
            "preco": preco.group(0).replace("R$", "R$ ").replace("  ", " ") if preco else ""}


def frases(txt, n):
    partes = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ\"“])", txt.strip())
    return " ".join(partes[:n])


def cap1(s):
    return s[:1].upper() + s[1:] if s else s


def ponto(s):
    s = s.strip()
    return s if s.endswith((".", "!", "?")) else s + "."


# ----------------------------------------------------------------------------------------------
# textos de cada arte (legenda e alt), a partir do pack.json
# ----------------------------------------------------------------------------------------------
def limpa(s, pack):
    s = str(s or "")
    s = s.replace("<br>", " · ")
    s = re.sub(r"<[^>]+>", "", s)
    padrao = {"cidade": "Sua cidade · UF", "negocio": pack.get("profissional", ""), "tel": pack.get("tel", "(00) 00000-0000")}
    s = re.sub(r"\{(\w+)\}", lambda m: str(pack.get(m.group(1)) or padrao.get(m.group(1), "")), s)
    s = s.replace("[", "").replace("]", "")
    return re.sub(r"\s+", " ", s).strip()


def titulo_arte(d, pack, longo=True):
    if not d.get("fino") and d.get("canto") and d.get("tipo") == "frase":
        return f'{limpa(d.get("canto"), pack)} {limpa(d.get("serif"), pack)}'
    partes = [limpa(d.get("fino"), pack), limpa(d.get("serif"), pack)]
    f2 = limpa(d.get("fino2"), pack)
    if d.get("tipo") == "fim":
        f2 = re.split(r"(?<=[.!?])\s", f2)[0] if f2 else ""
        cab = " ".join(p for p in [limpa(d.get("fino"), pack), limpa(d.get("serif"), pack)] if p)
        if f2 and f2[:1].isupper() and not cab.endswith((".", "!", "?")):
            cab += "."
        return " ".join(p for p in [cab, f2] if p)
    if longo and f2 and len(f2) <= 26:
        partes.append(f2)
    return " ".join(p for p in partes if p)


def alt_arte(d, pack, tipo):
    t = titulo_arte(d, pack)
    extra = limpa(d.get("apoio"), pack)
    if d.get("itens"):
        extra = " ".join(limpa(a, pack) + " " + limpa(b, pack) for a, b in d["itens"])
    if d.get("tipo") == "fim":
        extra = limpa(d.get("fino2"), pack)
    alt = f"{tipo}: {t}"
    if extra and extra not in t:
        # o apoio às vezes repete o fim do título ("Janeiro é pra revisão." + "é pra revisão. A agenda..."): corta a repetição
        primeira, _, resto = extra.partition(". ")
        if primeira.rstrip(".") and t.rstrip(".!?").lower().endswith(primeira.rstrip(".").lower()):
            extra = resto
        if extra:
            alt += (" " if t.endswith((".", "!", "?")) else ". ") + extra
    alt = re.sub(r"([.!?])\.+", r"\1", alt)            # "mancham?." e "dormir.." viram "mancham?" e "dormir."
    alt = re.sub(r"(\d{4}) (?=[A-ZÁÉÍÓÚ])", r"\1. ", alt)   # "confiança em 2026 Nos vemos" ganha o ponto que falta
    return ponto(alt)


# ----------------------------------------------------------------------------------------------
# página de cada pack
# ----------------------------------------------------------------------------------------------
NORMA = re.compile(r"(Resolução [A-Z]{2,4} [\d.]+/\d{4}|Provimento [\d.]+/\d{4} da OAB|Código de Ética do [A-Z]{2,4})")
REGRA_RX = re.compile(r"conselho|\bCFN\b|sem promessa|promessa de|sensacionalismo|antes e depois|sem preço|chamada de contratação", re.I)
REGRA = type("R", (), {"search": staticmethod(lambda b: NORMA.search(b) or REGRA_RX.search(b))})


def contar_paginas(pdf):
    if not pdf.exists():
        return None
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes())) or None


def sigla_registro(reg):
    if not reg:
        return ""
    m = re.match(r"[A-Za-zÀ-ú]+", reg)
    s = m.group(0) if m else ""
    return "registro" if s.lower() == "registro" else s


def pagina_pack(slug, pack):
    v = ler_venda(PACKS / "packs" / slug / "venda.md")
    curto = nome_pack(slug, pack)
    url = links.get(slug)
    preco = PRECO
    base = "../"
    im = lambda i: f"{base}img/{slug}/{i}.jpg"
    car, posts, sts = pack["carrossel"], pack["posts"], pack["stories"]
    total = len(car) + len(posts) + len(sts)
    reg = pack.get("registro") or ""
    sigla = sigla_registro(reg)
    arroba = (pack.get("arroba") or "@seuperfil").lstrip("@")
    mono = pack.get("monograma") or "AE"
    prof = pack.get("profissional") or ""
    profissao = pack.get("profissao") or ""
    bl = v["bullets"]
    achar = lambda rx: next((b for b in bl if re.match(rx, b, re.I)), "")

    # textos por nicho, a partir do venda.md
    b_car = achar(r"(1 carrossel|carrossel)")
    b_posts = achar(r"4 posts")
    b_sts = achar(r"4 stories")
    sem_prefixo = lambda b: cap1(re.sub(r"^\d+\s+\w+:\s*|^[^:]+:\s*", "", b, count=1)) if ":" in b else cap1(b)
    regras = [b for b in bl if REGRA.search(b)]
    campos = achar(r"(Espaço|Campo)")
    norma_m = NORMA.search(" ".join(regras))
    norma = norma_m.group(1) if norma_m else ""
    acr = re.search(r"\b(CFO|OAB|CFM|CFP|CFN)\b", " ".join(regras))
    lugar_m = re.search(r"Instagram d[oa] (consultório|escritório|estúdio|salão|clínica)", v["sub"] + " " + v["desc"])

    # hero: celular com o perfil montado, capa do carrossel ao lado
    destaques = []
    for d in sts:
        nome = {"s1": "Perguntas", "s2": "Enquete"}.get(d["id"][:2]) or (d.get("canto") or "Stories")
        destaques.append(f'<span><img src="{im(d["id"])}" width="720" height="1280" alt="" loading="lazy"><i>{esc(nome)}</i></span>')
    ids = {d["id"]: d for d in posts + car}
    p_ids = [d["id"] for d in posts]
    ordem = [p_ids[3], p_ids[2], p_ids[0], p_ids[1], "c1", "c6", "c4", "c5", "c2"]
    grade = "".join(
        (f'<span class="ig-multi"><img src="{im(i)}" width="720" height="900" alt="" loading="lazy"></span>' if i == "c1"
         else f'<img src="{im(i)}" width="720" height="900" alt="" loading="lazy">') for i in ordem if i in ids)
    linha_reg = f"<span>{esc(reg)}</span>" if reg else (f"<span>{esc(limpa(pack.get('cidade'), pack))}</span>" if pack.get("cidade") else "")
    troca = f"Nome, {sigla} e @ você troca pelos seus." if sigla else "Nome, @ e telefone você troca pelos seus."
    c1 = car[0]
    ctx = f"do pack de fim de ano pra {curto[:1].lower() + curto[1:]}"   # contexto no alt das artes (busca de imagem)

    # carrossel
    trilho = "".join(
        f'<li><a class="abre" href="{im(d["id"])}" data-cap="Carrossel, tela {n}: {esc(titulo_arte(d, pack))}">'
        f'<img class="arte" src="{im(d["id"])}" width="720" height="900" alt="{esc(alt_arte(d, pack, f"Tela {n} do carrossel {ctx}"))}" loading="lazy"></a>'
        f'<span class="legenda">{"Capa: " if n == 1 else ""}{esc(titulo_arte(d, pack))}</span></li>'
        for n, d in enumerate(car, 1))
    pontos = '<i class="on"></i>' + "<i></i>" * (len(car) - 1)
    desc_car = ponto(sem_prefixo(b_car)) if b_car else "Conteúdo útil pro seu cliente salvar."
    desc_car = re.sub(r"^(1 carrossel|carrossel) de \d+ telas\s*(com|sobre|de)?\s*", "", desc_car, flags=re.I)
    desc_car = cap1(desc_car)

    grade_posts = "".join(
        f'<li><a class="abre" href="{im(d["id"])}" data-cap="Post: {esc(titulo_arte(d, pack, False))}">'
        f'<img class="arte" src="{im(d["id"])}" width="720" height="900" alt="{esc(alt_arte(d, pack, f"Post {ctx}"))}" loading="lazy"></a>'
        f'<span class="legenda">{esc(titulo_arte(d, pack, False))}</span></li>' for d in posts)
    fila = "".join(
        f'<li><a class="abre" href="{im(d["id"])}" data-cap="Story: {esc(titulo_arte(d, pack, False))}">'
        f'<img class="arte" src="{im(d["id"])}" width="720" height="1280" alt="{esc(alt_arte(d, pack, f"Story {ctx}"))}" loading="lazy"></a>'
        f'<span class="legenda">{esc(titulo_arte(d, pack, False))}</span></li>' for d in sts)
    com_caixa = sum(1 for d in sts if d.get("caixa"))
    desc_sts = ponto(sem_prefixo(b_sts)) if b_sts else ""
    if com_caixa >= 2:
        desc_sts += f" {'Dois deles têm' if com_caixa == 2 else f'{com_caixa} deles têm'} o espaço marcado pra você colar a caixinha de perguntas e a enquete do Instagram."

    # quando postar
    p2, s3, s4 = posts[1], sts[2], sts[3]
    aviso_tipo = p2["id"].split("-", 1)[-1]
    def mini(ids_tipos):
        return "".join(f'<img class="arte{" st" if st else ""}" src="{im(i)}" width="720" height="{1280 if st else 900}" alt="" loading="lazy">' for i, st in ids_tipos)
    tit = lambda d: f"“{titulo_arte(d, pack, False).rstrip('.')}”"
    s4_natal = "natal" in s4["id"]
    # a última tela do carrossel só entra no calendário quando o assunto dela casa com a linha:
    # convite pra janeiro vai na volta, aviso de recesso vai antes de fechar; as outras ficam só no carrossel
    c6 = car[5]
    c6_txt = titulo_arte(c6, pack, False)
    c6_vai = "janeiro" if re.search(r"janeiro", c6_txt, re.I) else ("recesso" if re.search(r"recesso|prazos", c6_txt, re.I) else "")
    mesmo = titulo_arte(p2, pack, False).lower() == titulo_arte(s3, pack, False).lower()
    linha2 = f"{tit(p2)} no feed e nos stories" if mesmo else f"{tit(p2)} no feed e {tit(s3)} nos stories"
    c6_curto = re.split(r"(?<=[.!?])\s", c6_txt)[0].rstrip(".")
    linha2 += f", junto com a tela “{c6_curto}” do carrossel." if c6_vai == "recesso" else "."
    linha6 = f"{tit(posts[3])} no feed" + (f" e o convite da última tela do carrossel, {tit(c6)}." if c6_vai == "janeiro" else ".")
    datas = [
        ("Começo de dezembro", f"O carrossel {tit(c1)}, pra abrir o mês.", [("c1", 0), ("c2", 0)]),
        ("Antes de fechar" if aviso_tipo == "recesso" else "Na primeira quinzena", linha2,
         [(p2["id"], 0), (s3["id"], 1)] + ([("c6", 0)] if c6_vai == "recesso" else [])),
        ("Semana do Natal", "Caixinha de perguntas e enquete nos stories.", [(sts[0]["id"], 1), (sts[1]["id"], 1)]),
        ("24 e 25 de dezembro", f"{tit(posts[0])} no feed" + (f" e {tit(s4)} nos stories." if s4_natal else "."),
         [(posts[0]["id"], 0)] + ([(s4["id"], 1)] if s4_natal else [])),
        ("Virada do ano", f"{tit(posts[2])} no feed" + ("." if s4_natal else f" e {tit(s4)} nos stories."),
         [(posts[2]["id"], 0)] + ([] if s4_natal else [(s4["id"], 1)])),
        ("Na volta, em janeiro", linha6, [(posts[3]["id"], 0)] + ([("c6", 0)] if c6_vai == "janeiro" else [])),
    ]
    # conferência: toda miniatura de uma linha tem que estar citada na frase dessa linha
    todas = {d["id"]: d for d in car + posts + sts}
    for q, o, m in datas:
        for i, _ in m:
            if i == "c2" and "carrossel" in o:
                continue
            chave = {"s1": "perguntas", "s2": "enquete"}.get(i[:2]) if i.startswith(("s1", "s2")) else (c6_curto if i == "c6" else titulo_arte(todas[i], pack, False).rstrip("."))
            if chave.lower() not in o.lower():
                AVISOS.append(f"{slug}: miniatura {i} na linha '{q}' sem citação na frase: {o}")
    lis_datas = "".join(f'<li><p class="quando">{q}</p><div class="mini" aria-hidden="true">{mini(m)}</div><p class="oque">{esc(o)}</p></li>' for q, o, m in datas)
    intro_datas = frases(v["desc"], 1) or "Uma sugestão de ordem pro perfil não ficar parado no fim de ano."

    # bloco dos dados / regras do conselho
    conselho = bool(regras) and bool(reg or norma or acr)
    if conselho:
        if acr:
            h_dados = f"Escrito dentro das regras {'da' if acr.group(1) == 'OAB' else 'do'} {acr.group(1)}"
        else:
            h_dados = "Escrito dentro das regras do conselho"
        declara = " ".join(ponto(cap1(b)) for b in ([campos] if campos and campos not in regras else []) + regras)
        aviso = "Se você mudar os textos, confira se continuam dentro da regra."
    else:
        h_dados = "Seus dados no lugar certo"
        declara = " ".join(ponto(cap1(b)) for b in ([campos] if campos else []) + regras) or "Nome, @ e telefone ficam em campos fáceis de trocar no Canva."
        aviso = "O texto de cada arte já está pronto. Você só troca os dados e as datas."
    sig = limpa(car[5].get("assinatura"), pack) if car[5].get("assinatura") else f"{prof} · {profissao}"
    maior = max(len(x) for x in sig.split(" · ", 1)) if sig else 20
    linhas_sig = [limpa(x, pack) for x in str(car[5].get("assinatura") or "").split("<br>")]
    maior = max((len(x) for x in linhas_sig), default=20)
    aqui_left = min(79, round((112 + maior * 8.8) / 720 * 100 + 6))
    o_que = f"Nome, {sigla} e @" if sigla else "Nome e @"
    cap_dados = f"{o_que} entram aqui, na última tela do carrossel. Nas outras artes eles ficam no rodapé."

    # pasta que chega no e-mail
    pg_posts = contar_paginas(PACKS / "saida" / slug / "canva-posts.pdf")
    pg_sts = contar_paginas(PACKS / "saida" / slug / "canva-stories.pdf")
    pasta = [("carrossel", f"{len(car)} PNG · 1080×1350"), ("posts", f"{len(posts)} PNG · 1080×1350"), ("stories", f"{len(sts)} PNG · 1080×1920")]
    if pg_posts: pasta.append(("canva-posts.pdf", f"{pg_posts} páginas"))
    if pg_sts: pasta.append(("canva-stories.pdf", f"{pg_sts} páginas"))
    lis_pasta = "".join(f"<li><code>{n}</code><small>{q}</small></li>" for n, q in pasta)

    # extras do checkout (só se o pack tiver)
    meus = [b for b in bumps if b.get("bump_de") == slug]
    def nome_bump(b):
        if b["slug"].startswith("whatsapp"): return "mensagens prontas de WhatsApp"
        if b["slug"].startswith("adesivos"): return "adesivos pros stories"
        return b["nome"]
    def reais(c): return f"R${NB}" + f"{int(c) / 100:.2f}".replace(".", ",").replace(",00", "")
    extras = ""
    if meus:
        partes = [f"{nome_bump(b)} ({reais(b['preco_bump'])})" for b in meus]
        extras = " e ".join([", ".join(partes[:-1]), partes[-1]] if len(partes) > 1 else partes)
    garantia_extra = f"<p><b>Extras opcionais no pagamento:</b> {extras}. Só leva se quiser.</p>" if extras else ""
    precos_extras = " e ".join(reais(b["preco_bump"]) for b in meus)
    abre_duvidas = (f'<p class="abre-duvidas">{"Os extras" if len(meus) > 1 else "O extra"} de {precos_extras} que {"aparecem" if len(meus) > 1 else "aparece"} no pagamento {"são opcionais" if len(meus) > 1 else "é opcional"}. O pack sai por {PRECO} do mesmo jeito.</p>' if meus else "")

    # versão personalizada (upsell de R$ 47 oferecido logo depois do pagamento): só aparece quando existir na Kiwify,
    # com a chave "personalizado" no links.json
    tem_personalizado = bool(links.get("personalizado"))
    pronta = (f"""<div class="pronta">
      <h3>Quer que eu coloque seus dados?</h3>
      <p>Versão personalizada por R${NB}47, oferecida logo depois do pagamento. Chega em até 24{NB}h depois que você mandar os dados.</p>
    </div>""" if tem_personalizado else "")
    ou_personalizado = " ou pegue a versão personalizada, oferecida logo depois do pagamento" if tem_personalizado else ""
    exemplo = ", ".join(x for x in [prof, reg, "@" + arroba] if x)
    # dúvidas: a mesma lista vira os <details> da página e o FAQPage do JSON-LD (texto idêntico ao visível)
    duvidas = [
        ("Preciso saber design?", "Não. No Canva você clica no texto e troca o nome, o @, o telefone e as datas. O resto já está pronto."),
        ("Como eu recebo?", "Assim que o pagamento é aprovado, chega um e-mail da Kiwify com o acesso à área de membros. No Pix e no cartão é na hora. No boleto, quando ele compensa, o que pode levar até 3 dias úteis."),
        ("Os PNGs já vêm com os meus dados?", f"Não. Eles vêm com dados de exemplo ({esc(exemplo)}). Pra sair com os seus, edite os PDFs no Canva{ou_personalizado}."),
        ("As fotos são minhas?", "As fotos de exemplo são de banco de imagem com licença livre (Unsplash). Ficam bonitas como estão, mas com fotos suas o perfil fica com a sua cara."),
    ]
    if conselho:
        regra_txt = " ".join(ponto(cap1(b)) for b in regras)
        duvidas.append(("Posso ter problema com o conselho?", f"Os textos foram escritos pensando nas regras de publicidade da sua profissão. {md_inline(regra_txt)} Se você mudar os textos, confira se continuam dentro da regra."))
    duvidas += [
        ("E se eu não gostar?", f"Você tem {GARANTIA}. Pede o reembolso pela Kiwify dentro desse prazo e o dinheiro volta."),
        ("Até quando dá pra usar?", "As artes são pro período de 1º de dezembro até a volta em janeiro. O post de ano novo está com 2027."),
    ]
    lista_duv = "\n    ".join(f"<details><summary>{q}</summary><p>{r}</p></details>" for q, r in duvidas)
    lugar = lugar_m.group(1) if lugar_m else ""
    frase_fim = f"Boas festas pro seu {lugar}." if lugar and lugar != "clínica" else ("Boas festas pra sua clínica." if lugar else "Boas festas, e até janeiro.")
    # o lugar no título casa a página com o anúncio de cada nicho (sempre em até 2 linhas)
    h1 = f"O dezembro {'da' if lugar == 'clínica' else 'do'} {lugar}, pronto." if lugar else "Seu feed de dezembro, pronto."
    nome_produto = v["titulo"] or f"Pack de Fim de Ano · {curto}"
    termo, quem, foco = BUSCA.get(slug, (curto.lower(), "", ""))
    titulo_pag = TITULO_BUSCA.get(slug) or f"Pack de artes de Natal para {termo} | Instagram | {PRECO.replace(NB, ' ')}"
    if len(titulo_pag) > 60:   # o Google corta perto de 60 caracteres: sai o "Instagram" pra o preço continuar à vista
        titulo_pag = titulo_pag.replace(" | Instagram", "")
    if foco:
        desc_meta = f"{total} artes de Natal e Ano Novo pro Instagram {quem}: {foco}. Editável no Canva, {PRECO}."
    else:
        desc_meta = f"{v['sub']} {PRECO}, edite no Canva ou baixe em PNG."
    abs_img = lambda i: f"{SITE}img/{slug}/{i}.jpg"
    imagens = [abs_img("capa-kiwify")] + [abs_img(d["id"]) for d in car + posts + sts]
    ld = jsonld(
        ld_produto(nome_produto, desc_meta, imagens[:4], url, PRECO, slug, "Artes para Instagram"),
        ld_faq(duvidas),
        ld_trilha(("Packs de Fim de Ano", ""), (f"Pack pra {curto[:1].lower() + curto[1:]}", f"{slug}/")),
    )

    return head(titulo_pag, desc_meta, f"{SITE}img/{slug}/capa-kiwify.jpg", base, view_content=True, caminho=f"{slug}/",
                og_alt=f"Capa do pack de Natal e Ano Novo pra {curto[:1].lower() + curto[1:]}: {total} artes pro Instagram",
                ld=ld, preco=PRECO, imagens=imagens) + f"""<body class="com-barra">
<a class="pular" href="#artes">Pular para as artes</a>
{topo(base, slug, preco, url)}
<main>

<section class="hero" aria-labelledby="titulo">
  <div class="hero-texto">
    <h1 id="titulo"{' class="longo"' if len(h1) > 30 else ''}><span class="rotulo">{"Pack de Natal" if slug in ROTULO_CURTO else "Pack de Natal e Ano Novo"} pra {esc(curto[:1].lower() + curto[1:])}</span> {esc(h1)}</h1>
    <p class="hero-sub">{md_inline(v['sub'])}</p>
  </div>
  <div class="hero-compra">
    <span class="preco-valor">{PRECO}</span>
    {botao(url, "Comprar o pack", preco, ident="cta-hero")}
    <p class="seguro">{CONFIA}</p>
  </div>
  <div class="hero-palco">
    <a class="hero-capa abre" href="{im('c1')}" data-cap="Carrossel, tela 1: {esc(titulo_arte(c1, pack))}">
      <img class="arte" src="{im('c1')}" width="720" height="900" alt="{esc(alt_arte(c1, pack, f'Capa do carrossel {ctx}'))}" fetchpriority="high">
    </a>
    <div class="palco-lado">
    <figure class="celular" aria-label="Exemplo de perfil do Instagram com as artes do pack no feed">
      <div class="cel-tela">
        <div class="cel-status" aria-hidden="true"><span>9:41</span><span class="cel-ilha"></span><span class="cel-bat"></span></div>
        <div class="ig-topo"><b>{esc(arroba)}</b></div>
        <div class="ig-perfil">
          <span class="ig-avatar" aria-hidden="true">{esc(mono)}</span>
          <div class="ig-nome"><b>{esc(prof)}</b><span>{esc(profissao)}</span>{linha_reg}</div>
        </div>
        <div class="ig-botoes" aria-hidden="true"><span>Seguir</span><span>Mensagem</span></div>
        <div class="ig-destaques" aria-hidden="true">{''.join(destaques)}</div>
        <div class="ig-grade">{grade}</div>
      </div>
    </figure>
    <p class="palco-nota">Perfil de exemplo. {troca}</p>
    </div>
  </div>
</section>

<section class="bloco carrossel" id="artes" aria-labelledby="t-carrossel">
  <div class="cab">
    <h2 id="t-carrossel">O carrossel de {len(car)} telas</h2>
    <p>{md_inline(desc_car)}</p>
  </div>
  <div class="post-ig">
    <div class="pig-cab" aria-hidden="true"><span class="pig-av">{esc(mono)}</span><b>{esc(arroba)}</b><span class="pig-mais">•••</span></div>
    <div class="pig-palco">
      <ol class="trilho" id="trilho" aria-label="Telas do carrossel">{trilho}</ol>
      <span class="pig-cont" aria-hidden="true"><span id="pig-n">1</span>/{len(car)}</span>
    </div>
    <div class="pig-pontos" aria-hidden="true">{pontos}</div>
  </div>
  <p class="dica-toque">Arraste pro lado. Toque numa arte pra ver em tela cheia.</p>
</section>

<section class="bloco posts" aria-labelledby="t-posts">
  <div class="cab">
    <h2 id="t-posts">{len(posts)} posts pro feed</h2>
    <p>{md_inline(ponto(sem_prefixo(b_posts)) if b_posts else "")} Formato 1080×1350, que aparece inteiro no feed.</p>
  </div>
  <ul class="grade-posts">{grade_posts}</ul>
</section>

<section class="bloco stories" aria-labelledby="t-stories">
  <div class="cab">
    <h2 id="t-stories">{len(sts)} stories</h2>
    <p>{md_inline(desc_sts)}</p>
  </div>
  <ul class="fila-stories">{fila}</ul>
</section>

<section class="bloco agenda" aria-labelledby="t-agenda">
  <div class="cab">
    <h2 id="t-agenda">Quando postar cada uma</h2>
    <p>{md_inline(intro_datas)}</p>
  </div>
  <ol class="datas">{lis_datas}</ol>
</section>

<section class="bloco dados" aria-labelledby="t-dados">
  <div class="dados-texto">
    <h2 id="t-dados">{esc(h_dados)}</h2>
    <p class="declara">{md_inline(declara)}</p>
    <p class="aviso">{aviso}</p>
  </div>
  <figure class="dados-prova">
    <div class="recorte"><img class="arte" src="{im('c6')}" width="720" height="900" alt="Detalhe da última tela do carrossel: {esc(sig)}" loading="lazy"><span class="aqui" style="left:{aqui_left}%">Aqui</span></div>
    <figcaption>{cap_dados}</figcaption>
  </figure>
</section>

<section class="creme" aria-labelledby="t-como">
  <div class="creme-in">
    <h2 id="t-como">Como você recebe</h2>
    <ol class="passos">
      <li><b>Paga na Kiwify</b><span>Pix, cartão ou boleto. A Kiwify processa o pagamento e guarda os arquivos.</span></li>
      <li><b>Recebe o acesso por e-mail</b><span>Com o login da área de membros. No Pix e no cartão é na hora. No boleto, quando ele compensa.</span></li>
      <li><b>Baixa a pasta</b><ul class="pasta">{lis_pasta}</ul></li>
      <li><b>Troca seus dados e posta</b><span>No Canva você troca nome, @, telefone, datas e, se quiser, as fotos de exemplo (banco de imagem com licença livre).</span></li>
    </ol>
    {pronta}
  </div>
</section>

<section class="bloco compra" id="comprar" aria-labelledby="t-compra">
  <div class="compra-arte" aria-hidden="true"><img class="arte" src="{im('c6')}" width="720" height="900" alt="" loading="lazy"></div>
  <div class="compra-texto">
    <h2 id="t-compra">Seu dezembro pronto por {PRECO}</h2>
    <ul class="leva">
      <li>Carrossel de {len(car)} telas</li>
      <li>{len(posts)} posts de feed</li>
      <li>{len(sts)} stories</li>
      <li>PNG em alta e PDF pro Canva</li>
    </ul>
    {botao(url, f"Comprar o pack por {PRECO}", preco, cls="btn btn-grande")}
    <div class="garantias">
      <p><b>{GARANTIA}.</b> Se não gostar, pede o reembolso na Kiwify dentro de 7{NB}dias e recebe o dinheiro de volta.</p>
      <p><b>Pagamento seguro.</b> Pix, cartão ou boleto, processado pela Kiwify.</p>
      {garantia_extra}
    </div>
  </div>
</section>

<section class="bloco duvidas" aria-labelledby="t-duvidas">
  <div>
    <h2 id="t-duvidas">Dúvidas</h2>
    {abre_duvidas}
  </div>
  <div class="lista-duvidas">
    {lista_duv}
  </div>
</section>

{quem_fez(base, "Faço artes de Instagram pra consultórios e negócios locais, e montei este pack com o que todo perfil precisa no fim de ano: conteúdo útil, o aviso de recesso ou de horário e um convite pra janeiro.")}
</main>
{rodape(base, frase_fim, "Fotos de exemplo: Unsplash, licença livre. ", cta=botao(url, f"Comprar o pack por {PRECO}", preco, cls="btn btn-grande", ident="comprar-fim"))}
{barra(url, PRECO, GARANTIA, "Comprar o pack")}
{LUZ}<script src="{base}site.js" defer></script>
</body>
</html>
"""


# ----------------------------------------------------------------------------------------------
# e-books e kits
# ----------------------------------------------------------------------------------------------
def copia_imagem(src, dst, max_lado=None):
    """Copia; se for prévia grande, converte pra JPG menor com o sips do Mac (cai pra cópia simples)."""
    if not src.exists():
        return False
    if max_lado and dst.suffix == ".jpg":
        try:
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80", "-Z", str(max_lado), str(src), "--out", str(dst)],
                           check=True, capture_output=True)
            return True
        except Exception:
            dst = dst.with_suffix(".png")
    shutil.copy(src, dst)
    return True


# resumo curto de cada e-book (no máximo 3 linhas no celular), tirado do venda.md; os detalhes ficam na lista
RESUMO_EBOOK = {
    "2027-no-controle": "Em 30 dias você fica sabendo quanto ganha, quanto gasta e o que fazer com o que sobra. São 39 páginas em PDF.",
    "ceia-sem-stress": "A ceia dividida em três dias: no 22 você compra, no 23 adianta quase tudo e no 24 só assa e serve. São 31 páginas em PDF.",
    "kit-metas-2027": "Você escolhe as metas, imprime, recorta e marca um furinho a cada treino, livro ou dinheiro guardado.",
    "ferias-sem-tela": "Atividades de papel e lápis pra criança fazer sozinha ou com um adulto, e um calendário com uma ideia por dia.",
}


def pagina_ebook(slug, pasta, v, tipo, previas):
    base = "../../"
    url = links.get(slug)
    pr = v["preco"].replace(" ", NB)
    titulo = v["titulo"] or slug
    h1, resto = (titulo.split(":", 1) + [""])[:2]
    sub = v["sub"]
    if resto.strip():
        sub = f"{cap1(resto.strip())}. {sub}"
    rotulo = "E-book em PDF" if tipo == "E-book" else "Kit em PDF pra imprimir"
    lis = "".join(f"<li>{md_inline(b)}</li>" for b in v["bullets"])
    prev = ""
    if previas:
        itens = "".join(f'<li><a class="abre" href="{base}img/ebooks/{p}" data-cap="Página de exemplo {n}"><img class="arte" src="{base}img/ebooks/{p}" width="1080" height="1350" alt="Página de exemplo {n} do {esc(h1)}" loading="lazy"></a></li>' for n, p in enumerate(previas, 1))
        prev = f"""<section class="bloco stories" id="artes" aria-labelledby="t-prev">
  <div class="cab"><h2 id="t-prev">Algumas páginas</h2><p>Toque numa página pra ver em tela cheia.</p></div>
  <ul class="fila-stories">{itens}</ul>
</section>"""
    titulo_busca, desc_busca = SEO_PRODUTO.get(slug, (titulo, sub))
    og = f"{SITE}img/ebooks/{slug}.png"
    imagens = [og, f"{SITE}img/ebooks/{slug}-vertical.png"] + [f"{SITE}img/ebooks/{p}" for p in previas]
    cam = f"ebooks/{slug}/"
    ld = jsonld(
        ld_produto(titulo, desc_busca, imagens[:3], url, pr, slug, "E-book em PDF" if tipo == "E-book" else "Material pra imprimir em PDF"),
        ld_trilha(("Packs de Fim de Ano", ""), (h1.strip(), cam)),
    )
    return head(titulo_busca, desc_busca, og, base, view_content=True, caminho=cam, og_alt=f"Capa: {texto_puro(titulo)}",
                ld=ld, preco=pr, imagens=imagens) + f"""<body class="com-barra">
{topo(base, slug, pr, url)}
<main>
<section class="hero" aria-labelledby="titulo">
  <div class="hero-texto">
    <p class="rotulo">{rotulo}</p>
    <h1 id="titulo">{esc(h1.strip())}</h1>
    <p class="hero-sub">{md_inline(sub)}</p>
  </div>
  <div class="hero-compra">
    <span class="preco-valor">{pr}</span>
    {botao(url, "Comprar o " + ("e-book" if tipo == "E-book" else "kit"), pr, ident="cta-hero")}
    <p class="seguro">{CONFIA}</p>
  </div>
  <div class="hero-palco">
    <a class="eb-capa abre" href="{base}img/ebooks/{slug}-vertical.png" data-cap="Capa: {esc(titulo)}" style="grid-column:1/-1"><img class="arte" src="{base}img/ebooks/{slug}-vertical.png" width="1080" height="1350" alt="Capa do {esc(titulo)}" fetchpriority="high"></a>
  </div>
</section>

{prev}
<section class="bloco"{'' if prev else ' id="artes"'} aria-labelledby="t-dentro">
  <div class="cab"><h2 id="t-dentro">O que tem dentro</h2><p class="eb-desc">{md_inline(RESUMO_EBOOK.get(slug) or frases(v['desc'], 1))}</p></div>
  <ul class="eb-lista">{lis}</ul>
</section>
<section class="bloco compra" id="comprar" aria-labelledby="t-compra">
  <div class="compra-arte" aria-hidden="true"><img class="arte" src="{base}img/ebooks/{slug}.png" width="1080" height="1080" alt="" loading="lazy"></div>
  <div class="compra-texto">
    <h2 id="t-compra">{esc(h1.strip())} por {pr}</h2>
    {botao(url, f"Comprar por {pr}", pr, cls="btn btn-grande")}
    <div class="garantias">
      <p><b>{GARANTIA}.</b> Se não gostar, pede o reembolso na Kiwify dentro de 7{NB}dias e recebe o dinheiro de volta.</p>
      <p><b>Pagamento seguro.</b> Pix, cartão ou boleto, processado pela Kiwify. O acesso chega por e-mail: no Pix e no cartão na hora, no boleto quando ele compensa.</p>
    </div>
  </div>
</section>

{quem_fez(base, "Além dos packs de artes pra Instagram, faço estes materiais pra imprimir e usar em casa no fim de ano.")}</main>
{rodape(base, "Boas festas, e até janeiro.", cta=botao(url, f"Comprar o {'e-book' if tipo == 'E-book' else 'kit'} por {pr}", pr, cls="btn btn-grande", ident="comprar-fim"))}
{barra(url, pr, GARANTIA, "Comprar")}
{LUZ}<script src="{base}site.js" defer></script>
</body>
</html>
"""


# ----------------------------------------------------------------------------------------------
# gera tudo
# ----------------------------------------------------------------------------------------------
AQUI.joinpath("estilo.css").write_text(CSS)
AQUI.joinpath("site.js").write_text(JS)

pacotes = {}
for pj in sorted((PACKS / "packs").glob("*/pack.json")):
    slug = pj.parent.name
    if slug.startswith("_"):
        continue
    if not (AQUI / "img" / slug / "c1.jpg").exists():
        print("pulado (sem as imagens em img/):", slug)
        continue
    pack = json.loads(pj.read_text())
    pacotes[slug] = pack
    d = AQUI / slug; d.mkdir(exist_ok=True)
    (d / "index.html").write_text(pagina_pack(slug, pack))

sem_acento = lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
ordem_vitrine = [s for s in PRIMEIRO if s in pacotes] + sorted((s for s in pacotes if s not in PRIMEIRO), key=lambda s: sem_acento(nome_pack(s, pacotes[s])))
cards = []
for slug in ordem_vitrine:
    estado = f"14 artes · {PRECO}" if links.get(slug) else "Em breve"
    cards.append(f'<li><a href="{slug}/"><div class="foto"><img class="arte" src="img/{slug}/c1.jpg" width="720" height="900" alt="Capa do carrossel do pack de Natal e Ano Novo pra {esc(nome_pack(slug, pacotes[slug]).lower())}" loading="lazy"></div><b>{esc(nome_pack(slug, pacotes[slug]))}</b><span>{estado}</span></a></li>')

eb_cards = []
dst = AQUI / "img" / "ebooks"; dst.mkdir(parents=True, exist_ok=True)
EXTRAS = [AQUI.parent / n / "venda.md" for n in ("kit-metas-2027", "ferias-sem-tela") if (AQUI.parent / n / "venda.md").exists()]
for e in sorted(EBOOKS.glob("*/venda.md")) + EXTRAS:
    slug, pasta = e.parent.name, e.parent
    copia_imagem(pasta / "capa-quadrada.png", dst / f"{slug}.png")
    copia_imagem(pasta / "capa-vertical.png", dst / f"{slug}-vertical.png")
    previas = []
    for n in (1, 2, 3, 4):
        alvo = dst / f"{slug}-previa-{n}.jpg"
        if copia_imagem(pasta / f"previa-{n}.png", alvo, max_lado=900):
            previas.append(alvo.name if alvo.exists() else alvo.with_suffix(".png").name)
    v = ler_venda(e)
    tipo = "E-book" if pasta.parent == EBOOKS else "Kit pra imprimir"
    pd = AQUI / "ebooks" / slug; pd.mkdir(parents=True, exist_ok=True)
    (pd / "index.html").write_text(pagina_ebook(slug, pasta, v, tipo, previas))
    nome = (v["titulo"] or slug).split(":")[0]
    eb_cards.append(f'<li><a href="ebooks/{slug}/"><div class="foto"><img class="arte" src="img/ebooks/{slug}.png" width="1080" height="1080" alt="Capa: {esc(nome)}, {"e-book" if tipo == "E-book" else "kit pra imprimir"} em PDF" loading="lazy"></div><b>{esc(nome)}</b><span>{"E-book" if tipo == "E-book" else "Kit"} ·{NB}{v["preco"].replace(" ", NB)}</span></a></li>')

CARGA = {True: 'fetchpriority="high"', False: 'loading="lazy"'}
vitrine_capas = "".join(
    f'<a class="abre-pack" href="{s}/"><img class="arte" src="img/{s}/c1.jpg" width="720" height="900" alt="Capa do carrossel do pack pra {esc(nome_pack(s, pacotes[s]).lower())}" {CARGA[i == 0]}><span>{esc(nome_pack(s, pacotes[s]))}</span></a>'
    for i, s in enumerate(s for s in ("dentista", "salao-de-beleza", "advogado") if s in pacotes))

ld_home = jsonld(
    {"@context": "https://schema.org", "@type": "WebSite", "name": "Packs de Fim de Ano", "url": SITE, "inLanguage": "pt-BR",
     "publisher": {"@type": "Organization", "name": MARCA}},
    {"@context": "https://schema.org", "@type": "ItemList", "name": "Packs de artes de Natal e Ano Novo por profissão",
     "itemListElement": [{"@type": "ListItem", "position": n, "url": f"{SITE}{s}/", "name": f"Pack pra {nome_pack(s, pacotes[s]).lower()}"}
                         for n, s in enumerate(ordem_vitrine, 1)]},
)
AQUI.joinpath("index.html").write_text(head(
    f"Packs de artes de Natal para Instagram por profissão | {PRECO.replace(NB, ' ')}",
    f"{len(cards)} packs de artes de Natal e Ano Novo pro Instagram, um por profissão: dentista, salão de beleza, confeitaria, advogado e mais. Editáveis no Canva, {PRECO} cada.",
    f"{SITE}img/dentista/capa-kiwify.jpg", "", caminho="", og_alt="Capa do pack de Natal e Ano Novo pra dentistas", ld=ld_home,
    imagens=[f"{SITE}img/{s}/c1.jpg" for s in ordem_vitrine]) + f"""<body>
<a class="pular" href="#packs">Pular para os packs</a>
{topo("", None)}
<main>
<section class="vit-hero" aria-labelledby="titulo">
  <div>
    <h1 id="titulo"><span class="rotulo">Packs de Natal e Ano Novo pra {len(cards)} profissões</span> Seu feed de dezembro, pronto.</h1>
    <p class="hero-sub">14 artes de Instagram por profissão: um carrossel de 6 telas, 4 posts e 4 stories de Natal, recesso e ano novo. {PRECO} cada, pra editar no Canva ou postar em PNG.</p>
    <p class="vit-confia">Pix, cartão ou boleto pela Kiwify · {GARANTIA}</p>
    <a class="btn" href="#packs">Escolher minha profissão</a>
  </div>
  <div class="vit-capas">{vitrine_capas}</div>
</section>

<section class="bloco" id="packs" aria-labelledby="t-packs">
  <div class="cab"><h2 id="t-packs">Escolha a sua profissão</h2><p>Cada pack tem textos escritos pro seu ramo, com espaço pro seu nome, registro e @. Toque numa profissão pra ver as 14 artes.</p></div>
  <ul class="vitrine">{''.join(cards)}</ul>
</section>

{f'''<section class="bloco" aria-labelledby="t-ebooks">
  <div class="cab"><h2 id="t-ebooks">E-books e kits</h2><p>Pra usar em casa no fim de ano: a ceia, as metas, as férias das crianças e o dinheiro de 2027.</p></div>
  <ul class="vitrine">{''.join(eb_cards)}</ul>
</section>''' if eb_cards else ''}

<section class="creme" aria-labelledby="t-como">
  <div class="creme-in">
    <h2 id="t-como">Como funciona</h2>
    <div class="vit-como">
      <p><b>Você paga na Kiwify</b>Pix, cartão ou boleto. A Kiwify processa o pagamento e guarda os arquivos.</p>
      <p><b>Recebe por e-mail</b>O acesso à área de membros chega na hora no Pix e no cartão, e no boleto quando ele compensa.</p>
      <p><b>Tem {GARANTIA}</b>Se não gostar, pede o reembolso pela Kiwify dentro de 7{NB}dias e o dinheiro volta.</p>
    </div>
  </div>
</section>

{quem_fez("", "Faço artes de Instagram pra consultórios e negócios locais, e montei um pack pra cada profissão com o que todo perfil precisa no fim de ano.")}</main>
{rodape("", "Boas festas pro seu Instagram.", "Fotos de exemplo: Unsplash, licença livre. ", ("#packs", "Voltar pra lista de profissões"))}
<script src="site.js" defer></script>
</body>
</html>
""")
# sitemap.xml (com as imagens de cada página, pro Google Imagens) e robots.txt
import datetime
hoje = datetime.date.today().isoformat()
# páginas feitas à mão na pasta do site (ex.: afiliados/) também entram, a não ser que tenham noindex
gerados = {c for c, _ in PAGINAS}
for idx in sorted(AQUI.glob("*/index.html")):
    cam = idx.parent.name + "/"
    topo_html = idx.read_text()[:6000]
    if cam in gerados or re.search(r'name="robots"[^>]*noindex', topo_html):
        continue
    og_m = re.search(r'property="og:image" content="([^"]+)"', topo_html)
    PAGINAS.append((cam, [og_m.group(1)] if og_m and og_m.group(1).startswith(SITE) else []))
xesc = lambda s: html.escape(s, quote=True)
urls = []
for cam, imgs in PAGINAS:
    imgs_xml = "".join(f"\n    <image:image><image:loc>{xesc(i)}</image:loc></image:image>" for i in dict.fromkeys(imgs))
    urls.append(f"  <url>\n    <loc>{xesc(SITE + cam)}</loc>\n    <lastmod>{hoje}</lastmod>{imgs_xml}\n  </url>")
AQUI.joinpath("sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
    + "\n".join(urls) + "\n</urlset>\n")
AQUI.joinpath("robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n")

print("site gerado:", len(cards), "packs,", len(eb_cards), "e-books/kits,", len(PAGINAS), "páginas no sitemap")
for a in AVISOS:
    print("AVISO", a)
