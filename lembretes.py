"""
Lembretes do Desafio 182 no WhatsApp (via CallMeBot).

Uso: python lembretes.py <manha|almoco|tarde|noite|domingo>

Variáveis de ambiente: CALLMEBOT_PHONE, CALLMEBOT_APIKEY (as mesmas da newsletter).
Sem CALLMEBOT_APIKEY ou com DRY_RUN=1, só imprime a mensagem.
"""
import os
import re
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

APP = "https://claude.ai/artifact/AqsJ5kScfZvABcXoNbUZ6b"
INICIO = date(2026, 11, 22)
TOTAL = 182
FIM = INICIO + timedelta(days=TOTAL - 1)

# weekday(): seg=0 ... dom=6
AREA = {0: "Empresa", 1: "Relacionamento", 2: "Empresa", 3: "Relacionamento",
        4: "Empresa", 5: "Espiritualidade", 6: "Espiritualidade"}

FRASES = [
    "Disciplina é escolher entre o que você quer agora e o que você mais quer.",
    "Dia ruim? Faça o mínimo. O mínimo mantém a sequência viva.",
    "Você não precisa de motivação. Precisa começar. A motivação vem depois.",
    "Cada check é um voto na pessoa que você está se tornando.",
    "Um deslize não apaga o caminho. Só não deixe virar dois.",
    "Ninguém vê o treino das 5:30. Todo mundo vê o resultado em maio.",
    "Recomeçar também é coragem. Hoje é mais um tijolo.",
]


def mensagem(slot: str, hoje: date) -> str | None:
    n = (hoje - INICIO).days + 1
    area = AREA[hoje.weekday()]
    frase = FRASES[n % len(FRASES)]
    luta = hoje.weekday() in (0, 2)  # segunda e quarta
    treino = "Muay thai às 10h" if luta else "Academia às 13:30"

    if hoje < INICIO:
        if slot == "noite":
            return ("Amanhã começa o Desafio 182.\n\n"
                    "Deite agora: o primeiro check de amanhã é ter dormido até as 23h. "
                    "Despertador antes das 6h.\n\n"
                    f"Seu app: {APP}")
        return None
    if hoje > FIM:
        return None

    if slot == "manha":
        return (f"Bom dia. Dia {n} de {TOTAL}.\n\n"
                "Ritual da manhã:\n"
                "1. Oração de gratidão\n"
                "2. Meditar 5 min\n"
                "3. Planejar o dia: 3 prioridades\n"
                "4. Depois: 1h de vendas no digital\n\n"
                f"Área do dia: {area}.\n"
                f"Treino: {treino}.\n\n"
                f"{frase}\n{APP}")
    if slot == "almoco":
        return (f"Dia {n}: checagem do meio-dia.\n\n"
                "- Água: já foram 1,5 L?\n"
                + ("- Muay thai feito? Marque o treino no app\n" if luta else "- Academia às 13:30\n") +
                "- Almoço de comida de verdade\n"
                f"- 1h de {area} e 1h de vendas: já fez?\n\n"
                f"{APP}")
    if slot == "tarde":
        return (f"Dia {n}: ainda dá tempo.\n\n"
                "O que falta hoje? Estudo de vendas, área do dia, treino, leitura?\n"
                "Se o dia apertou, faça a versão mínima (20 min) e marque no app.\n\n"
                f"{APP}")
    if slot == "noite":
        return (f"Dia {n}: hora de desacelerar.\n\n"
                "- Ler 5 páginas\n"
                "- Fechar os 3 L de água\n"
                "- Marcar o dia no app\n"
                "- Telas desligadas. Dormir até as 23h\n\n"
                f"{APP}")
    if slot == "domingo":
        extra = ("Hoje também é dia de escrever suas metas de 6 meses, 2 e 5 anos (aba Metas).\n"
                 if n == 1 else "Comece revisando a semana que passou.\n")
        return ("Domingo: planejamento da semana.\n\n"
                "10 minutos na aba Semana:\n"
                "- 3 metas da semana\n"
                "- Dias e horários dos 5 treinos\n"
                "- Foco da empresa\n"
                f"{extra}\n{APP}")
    raise SystemExit(f"slot desconhecido: {slot}")


def envia(texto: str):
    r = requests.get(
        "https://api.callmebot.com/whatsapp.php",
        params={"phone": os.environ["CALLMEBOT_PHONE"],
                "apikey": os.environ["CALLMEBOT_APIKEY"], "text": texto},
        timeout=120,
    )
    r.raise_for_status()
    # O CallMeBot responde 200 mesmo quando recusa a mensagem; o motivo vem no corpo.
    corpo = re.sub(r"<[^>]+>", " ", r.text)
    corpo = re.sub(r"\s+", " ", corpo).strip()
    print(f"[callmebot] {corpo[:600]}")
    if not re.search(r"queued|sent|enviad", corpo, re.I) or re.search(r"error|invalid|not ", corpo, re.I):
        raise SystemExit("[erro] o CallMeBot não confirmou o envio (veja a resposta acima)")
    print("[ok] enviado")


def main():
    slot = sys.argv[1] if len(sys.argv) > 1 else ""
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    if os.environ.get("DATA"):
        hoje = date.fromisoformat(os.environ["DATA"])
    texto = mensagem(slot, hoje)
    if not texto:
        print(f"[skip] nada para enviar em {hoje} ({slot})")
        return
    if os.environ.get("DRY_RUN") or not os.environ.get("CALLMEBOT_APIKEY"):
        print(texto)
        print("\n[dry-run] nada foi enviado", file=sys.stderr)
        return
    envia(texto)


if __name__ == "__main__":
    main()
