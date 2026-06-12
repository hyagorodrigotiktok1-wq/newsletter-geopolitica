# -*- coding: utf-8 -*-
"""
Newsletter diária de geopolítica e economia (mundo + Brasil).

Gera a edição do dia em duas saídas:
  1. Página HTML (docs/index.html + docs/arquivo/AAAA-MM-DD.html) para o
     GitHub Pages, em estilo jornalístico;
  2. Mensagem curta no WhatsApp via CallMeBot, com link para a edição.

Variáveis de ambiente:
  CALLMEBOT_PHONE   número com DDI, ex.: +5511999998888
  CALLMEBOT_APIKEY  chave recebida no cadastro do CallMeBot
  DRY_RUN=1         gera o site e imprime a mensagem, mas não envia
"""
import html
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import feedparser

TZ = ZoneInfo("America/Sao_Paulo")

# o console do Windows usa cp1252 por padrão e não imprime emoji
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent
DOCS = RAIZ / "docs"
ARQUIVO = DOCS / "arquivo"
SITE_URL = "https://hyagorodrigotiktok1-wq.github.io/newsletter-geopolitica"

FEEDS_MUNDO = [
    ("G1 Mundo", "https://g1.globo.com/rss/g1/mundo/"),
    ("BBC Brasil", "https://feeds.bbci.co.uk/portuguese/rss.xml"),
    ("RFI Brasil", "https://www.rfi.fr/br/rss"),
]

FEEDS_BRASIL = [
    ("G1 Economia", "https://g1.globo.com/rss/g1/economia/"),
    ("InfoMoney", "https://www.infomoney.com.br/feed/"),
    ("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml"),
]

POR_FEED = 2          # manchetes por fonte (site)
POR_SECAO = 6         # máximo de manchetes por seção (site)
NO_WHATSAPP = 3       # manchetes por seção na mensagem do WhatsApp
CHUNK = 1800          # tamanho máximo de cada mensagem no WhatsApp

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
DIAS = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]


# ---------------------------------------------------------------- coleta

def normaliza(titulo: str) -> str:
    t = unicodedata.normalize("NFKD", titulo.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", "", t).strip()


def pega_manchetes(feeds, limite, vistos):
    itens = []
    for fonte, url in feeds:
        try:
            d = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            for e in d.entries[:POR_FEED]:
                titulo = (e.get("title") or "").strip()
                link = (e.get("link") or "").strip()
                if not titulo:
                    continue
                chave = normaliza(titulo)[:60]
                if chave in vistos:
                    continue
                vistos.add(chave)
                itens.append({"fonte": fonte, "titulo": titulo, "link": link})
        except Exception as exc:  # uma fonte fora do ar não derruba a newsletter
            print(f"[aviso] falha ao ler {fonte}: {exc}", file=sys.stderr)
    return itens[:limite]


def fmt_brl(valor: float, casas: int = 2) -> str:
    txt = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {txt}"


def pega_cotacoes():
    try:
        r = requests.get(
            "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL,BTC-BRL",
            timeout=30,
        )
        r.raise_for_status()
        dados = r.json()
        cotacoes = []
        for chave, nome, casas in [
            ("USDBRL", "Dólar", 2),
            ("EURBRL", "Euro", 2),
            ("BTCBRL", "Bitcoin", 0),
        ]:
            if chave not in dados:
                continue
            d = dados[chave]
            cotacoes.append({
                "nome": nome,
                "valor": fmt_brl(float(d["bid"]), casas),
                "pct": float(d.get("pctChange", 0)),
            })
        return cotacoes
    except Exception as exc:
        print(f"[aviso] falha nas cotações: {exc}", file=sys.stderr)
        return []


def coleta():
    agora = datetime.now(TZ)
    vistos = set()  # compartilhado entre as seções para não repetir manchete
    return {
        "agora": agora,
        "data_longa": (f"{DIAS[agora.weekday()]}, {agora.day} de "
                       f"{MESES[agora.month - 1]} de {agora.year}").capitalize(),
        "cotacoes": pega_cotacoes(),
        "mundo": pega_manchetes(FEEDS_MUNDO, POR_SECAO, vistos),
        "brasil": pega_manchetes(FEEDS_BRASIL, POR_SECAO, vistos),
    }


# ---------------------------------------------------------------- site

ESTILO = """
:root { --tinta: #121212; --papel: #fdfbf7; --vermelho: #b1090b; --cinza: #6b6b6b; }
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 760px; padding: 0 22px 60px;
       background: var(--papel); color: var(--tinta);
       font-family: Georgia, 'Times New Roman', serif; line-height: 1.55; }
.masthead { border-bottom: 3px double var(--tinta); padding: 34px 0 16px;
            text-align: center; }
.masthead h1 { margin: 0; font-size: 42px; letter-spacing: 1px; font-weight: 700; }
.masthead h1 a { color: inherit; text-decoration: none; }
.masthead .sub { margin-top: 6px; font-size: 13px; text-transform: uppercase;
                 letter-spacing: 3px; color: var(--cinza); }
.data { text-align: center; font-size: 13px; text-transform: uppercase;
        letter-spacing: 2px; color: var(--cinza); padding: 12px 0;
        border-bottom: 1px solid #d8d4cb; }
.mercados { display: flex; justify-content: center; gap: 36px; flex-wrap: wrap;
            padding: 18px 0; border-bottom: 1px solid #d8d4cb; }
.mercados .ativo { text-align: center; }
.mercados .nome { font-size: 12px; text-transform: uppercase; letter-spacing: 2px;
                  color: var(--cinza); }
.mercados .valor { font-size: 21px; font-weight: 700; }
.mercados .pct { font-size: 13px; }
.pos { color: #1e6b34; } .neg { color: var(--vermelho); }
h2.secao { margin: 40px 0 6px; font-size: 14px; text-transform: uppercase;
           letter-spacing: 3px; color: var(--vermelho); }
h2.secao::after { content: ""; display: block; width: 46px;
                  border-bottom: 2px solid var(--vermelho); margin-top: 6px; }
article { padding: 16px 0; border-bottom: 1px solid #e4e0d6; }
article h3 { margin: 0 0 4px; font-size: 21px; line-height: 1.3; font-weight: 700; }
article h3 a { color: var(--tinta); text-decoration: none; }
article h3 a:hover { text-decoration: underline; }
article .fonte { font-size: 12px; text-transform: uppercase; letter-spacing: 2px;
                 color: var(--cinza); }
footer { margin-top: 50px; padding-top: 14px; border-top: 3px double var(--tinta);
         font-size: 14px; color: var(--cinza); }
footer h4 { margin: 18px 0 6px; font-size: 12px; text-transform: uppercase;
            letter-spacing: 2px; color: var(--tinta); }
footer a { color: var(--tinta); }
footer ul { margin: 4px 0; padding-left: 18px; }
"""


def render_manchetes(itens):
    blocos = []
    for m in itens:
        blocos.append(
            f'<article><h3><a href="{html.escape(m["link"])}">'
            f'{html.escape(m["titulo"])}</a></h3>'
            f'<div class="fonte">{html.escape(m["fonte"])}</div></article>'
        )
    return "\n".join(blocos)


def render_html(d, edicoes_anteriores):
    cot = []
    for c in d["cotacoes"]:
        classe = "pos" if c["pct"] >= 0 else "neg"
        pct = f"{c['pct']:+.2f}".replace(".", ",") + "%"
        cot.append(
            f'<div class="ativo"><div class="nome">{c["nome"]}</div>'
            f'<div class="valor">{c["valor"]}</div>'
            f'<div class="pct {classe}">{pct}</div></div>'
        )

    arquivo_html = ""
    if edicoes_anteriores:
        links = "\n".join(
            f'<li><a href="{href}">{rotulo}</a></li>'
            for rotulo, href in edicoes_anteriores[:30]
        )
        arquivo_html = f"<h4>Edições anteriores</h4><ul>{links}</ul>"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Resumo Diário — {d["data_longa"]}</title>
<style>{ESTILO}</style>
</head>
<body>
<header class="masthead">
  <h1><a href="{SITE_URL}/">Resumo Diário</a></h1>
  <div class="sub">Geopolítica &amp; Economia · Mundo e Brasil</div>
</header>
<div class="data">{d["data_longa"]}</div>
<div class="mercados">{"".join(cot)}</div>

<h2 class="secao">Geopolítica &amp; Mundo</h2>
{render_manchetes(d["mundo"])}

<h2 class="secao">Brasil — Economia</h2>
{render_manchetes(d["brasil"])}

<footer>
  <div>Manchetes coletadas automaticamente de G1, BBC Brasil, RFI Brasil,
  InfoMoney e Agência Brasil. Cotações: AwesomeAPI.
  Nova edição todos os dias às 7h da manhã.</div>
  {arquivo_html}
</footer>
</body>
</html>
"""


def lista_edicoes_anteriores(excluir: str):
    edicoes = []
    if ARQUIVO.exists():
        for arq in sorted(ARQUIVO.glob("????-??-??.html"), reverse=True):
            if arq.stem == excluir:
                continue
            ano, mes, dia = arq.stem.split("-")
            rotulo = f"{int(dia)} de {MESES[int(mes) - 1]} de {ano}"
            edicoes.append((rotulo, f"{SITE_URL}/arquivo/{arq.name}"))
    return edicoes


def salva_site(d):
    hoje = d["agora"].strftime("%Y-%m-%d")
    ARQUIVO.mkdir(parents=True, exist_ok=True)
    (DOCS / ".nojekyll").touch()
    pagina = render_html(d, lista_edicoes_anteriores(excluir=hoje))
    (ARQUIVO / f"{hoje}.html").write_text(pagina, encoding="utf-8")
    (DOCS / "index.html").write_text(pagina, encoding="utf-8")
    print(f"[ok] site gerado: docs/index.html e docs/arquivo/{hoje}.html")


# ---------------------------------------------------------------- whatsapp

def monta_whatsapp(d) -> str:
    agora = d["agora"]
    partes = [f"🗞️ *RESUMO DIÁRIO* — {DIAS[agora.weekday()].split('-')[0]}, "
              f"{agora.day:02d}/{agora.month:02d}"]

    if d["cotacoes"]:
        linhas = []
        for c in d["cotacoes"]:
            pct = f"{c['pct']:+.2f}".replace(".", ",")
            seta = "📈" if c["pct"] >= 0 else "📉"
            linhas.append(f"• {c['nome']}: {c['valor']} ({pct}%) {seta}")
        partes.append("💱 *Mercados*\n" + "\n".join(linhas))

    if d["mundo"]:
        linhas = [f"• {m['titulo']}" for m in d["mundo"][:NO_WHATSAPP]]
        partes.append("🌍 *Mundo*\n" + "\n".join(linhas))

    if d["brasil"]:
        linhas = [f"• {m['titulo']}" for m in d["brasil"][:NO_WHATSAPP]]
        partes.append("🇧🇷 *Brasil*\n" + "\n".join(linhas))

    partes.append(f"📰 *Edição completa, com links e arquivo:*\n{SITE_URL}/")
    return "\n\n".join(partes)


def divide_em_blocos(texto: str, tamanho: int):
    blocos, atual = [], ""
    for linha in texto.split("\n"):
        if len(atual) + len(linha) + 1 > tamanho and atual:
            blocos.append(atual.rstrip())
            atual = ""
        atual += linha + "\n"
    if atual.strip():
        blocos.append(atual.rstrip())
    return blocos


def envia_whatsapp(texto: str):
    phone = os.environ["CALLMEBOT_PHONE"]
    apikey = os.environ["CALLMEBOT_APIKEY"]
    blocos = divide_em_blocos(texto, CHUNK)
    for i, bloco in enumerate(blocos, 1):
        r = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": phone, "apikey": apikey, "text": bloco},
            timeout=120,
        )
        r.raise_for_status()
        print(f"[ok] bloco {i}/{len(blocos)} enviado ({len(bloco)} caracteres)")
        if i < len(blocos):
            time.sleep(10)  # respeita o rate limit do CallMeBot


# ---------------------------------------------------------------- main

def main():
    d = coleta()
    salva_site(d)
    texto = monta_whatsapp(d)
    if os.environ.get("DRY_RUN") or not os.environ.get("CALLMEBOT_APIKEY"):
        print(texto)
        print("\n[dry-run] nada foi enviado", file=sys.stderr)
        return
    envia_whatsapp(texto)


if __name__ == "__main__":
    main()
