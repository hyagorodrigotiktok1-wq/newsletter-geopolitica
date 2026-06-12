# Newsletter diária — Geopolítica & Economia no WhatsApp

Todo dia às **07:07 (horário de Brasília)** o GitHub Actions roda o
`newsletter.py`, que:

1. Busca as cotações do dia (dólar, euro, bitcoin) na AwesomeAPI (gratuita);
2. Coleta as principais manchetes de geopolítica mundial (G1 Mundo, BBC
   Brasil, RFI Brasil) e de economia do Brasil (G1 Economia, InfoMoney,
   Agência Brasil) via RSS;
3. Monta o resumo e envia no WhatsApp via [CallMeBot](https://www.callmebot.com/blog/free-api-whatsapp-messages/).

Tudo roda na nuvem do GitHub — não depende de nenhum computador ligado.

## Configuração (uma vez só)

Em **Settings → Secrets and variables → Actions** do repositório, crie:

| Secret             | Valor                                      |
| ------------------ | ------------------------------------------ |
| `CALLMEBOT_PHONE`  | seu número com DDI, ex. `+5511999998888`   |
| `CALLMEBOT_APIKEY` | a chave que o CallMeBot enviou no WhatsApp |

## Testar manualmente

Aba **Actions → Newsletter diária no WhatsApp → Run workflow**.

Localmente (sem enviar): `DRY_RUN=1 python newsletter.py`

## Personalizar

- Fontes: edite as listas `FEEDS_MUNDO` e `FEEDS_BRASIL` no `newsletter.py`.
- Horário: edite o `cron` em `.github/workflows/newsletter.yml` (em UTC;
  Brasília = UTC−3).
- Quantidade de manchetes: constantes `POR_FEED` e `POR_SECAO`.
