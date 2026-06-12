# -*- coding: utf-8 -*-
"""
Newsletter diária de geopolítica e economia (mundo + Brasil), enviada
por WhatsApp via CallMeBot. Pensada para rodar no GitHub Actions.

Variáveis de ambiente:
  CALLMEBOT_PHONE   número com DDI, ex.: +5511999998888
  CALLMEBOT_APIKEY  chave recebida no cadastro do CallMeBot
  DRY_RUN=1         apenas imprime a newsletter, não envia
"""
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import feedparser

TZ = ZoneInfo("America/Sao_Paulo")

# o console do Windows usa cp1252 por padrão e não imprime emoji
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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

POR_FEED = 2          # manchetes por fonte
POR_SECAO = 6         # máximo de manchetes por seção
CHUNK = 1800          # tamanho máximo de cada mensagem no WhatsApp

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
DIAS = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]


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
                itens.append((fonte, titulo, link))
        except Exception as exc:  # uma fonte fora do ar não derruba a newsletter
            print(f"[aviso] falha ao ler {fonte}: {exc}", file=sys.stderr)
    return itens[:limite]


def pega_cotacoes():
    try:
        r = requests.get(
            "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL,BTC-BRL",
            timeout=30,
        )
        r.raise_for_status()
        dados = r.json()
        linhas = []
        for chave, nome, fmt in [
            ("USDBRL", "Dólar", "R$ {:.2f}"),
            ("EURBRL", "Euro", "R$ {:.2f}"),
            ("BTCBRL", "Bitcoin", "R$ {:,.0f}"),
        ]:
            if chave not in dados:
                continue
            d = dados[chave]
            valor = fmt.format(float(d["bid"])).replace(",", "X").replace(".", ",").replace("X", ".")
            pct = float(d.get("pctChange", 0))
            seta = "📈" if pct >= 0 else "📉"
            linhas.append(f"• {nome}: {valor} ({pct:+.2f}%) {seta}")
        return linhas
    except Exception as exc:
        print(f"[aviso] falha nas cotações: {exc}", file=sys.stderr)
        return []


def monta_newsletter() -> str:
    agora = datetime.now(TZ)
    data = f"{DIAS[agora.weekday()]}, {agora.day} de {MESES[agora.month - 1]} de {agora.year}"

    partes = [f"🗞️ *RESUMO DIÁRIO*\n_{data.capitalize()}_"]

    cotacoes = pega_cotacoes()
    if cotacoes:
        partes.append("💱 *Mercados agora*\n" + "\n".join(cotacoes))

    vistos = set()  # compartilhado entre as seções para não repetir manchete
    mundo = pega_manchetes(FEEDS_MUNDO, POR_SECAO, vistos)
    if mundo:
        linhas = [f"• {t} _({f})_\n{l}" for f, t, l in mundo]
        partes.append("🌍 *Geopolítica & Mundo*\n" + "\n\n".join(linhas))

    brasil = pega_manchetes(FEEDS_BRASIL, POR_SECAO, vistos)
    if brasil:
        linhas = [f"• {t} _({f})_\n{l}" for f, t, l in brasil]
        partes.append("🇧🇷 *Brasil — Economia*\n" + "\n\n".join(linhas))

    partes.append("_Bom dia e boa leitura! ☕_")
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


def main():
    texto = monta_newsletter()
    if os.environ.get("DRY_RUN") or not os.environ.get("CALLMEBOT_APIKEY"):
        print(texto)
        print("\n[dry-run] nada foi enviado", file=sys.stderr)
        return
    envia_whatsapp(texto)


if __name__ == "__main__":
    main()
