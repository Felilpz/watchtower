import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import STATIC_JSON_PATH
from modules.wan_monitor import status_gateways, ping_host

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _carregar_devices() -> dict:
    try:
        with open(STATIC_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"static.json não encontrado em: {STATIC_JSON_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"erro ao parsear static.json: {e}")
        return {}


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "👁 <b>WatchTower Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Monitoramento de rede e segurança.\n\n"
        "📋 <b>Comandos:</b>\n"
        "  /wan — status dos links WAN\n"
        "  /ping &lt;nome&gt; — pingar dispositivo\n"
        "  /devices — listar dispositivos\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(texto, parse_mode="HTML")


async def cmd_wan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Verificando gateways...", parse_mode="HTML")

    gateways = status_gateways()
    linhas = []

    for nome, info in gateways.items():
        if info["online"]:
            lat = f"{info['latencia']:.1f} ms" if info["latencia"] else "— ms"
            linhas.append(f"🟢 <b>{nome}</b> — {lat}\n    └ <code>{info['alvo']}</code>")
        else:
            linhas.append(f"🔴 <b>{nome}</b> — OFFLINE\n    └ <code>{info['alvo']}</code>")

    texto = (
        f"📡 <b>Status dos Gateways</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(linhas) +
        f"\n━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ {_now()}"
    )
    await update.message.reply_text(texto, parse_mode="HTML")


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Uso: <code>/ping &lt;nome do dispositivo&gt;</code>\n"
            "Ex: <code>/ping SWITCH 01</code>",
            parse_mode="HTML"
        )
        return

    nome_buscado = " ".join(context.args).upper()
    devices = _carregar_devices()

    if not devices:
        await update.message.reply_text("❌ Não foi possível carregar o static.json.")
        return

    ip = devices.get(nome_buscado)
    encontrado = nome_buscado

    if not ip:
        for nome, endereco in devices.items():
            if nome_buscado in nome.upper():
                ip = endereco
                encontrado = nome
                break

    if not ip:
        await update.message.reply_text(
            f"❓ <b>{nome_buscado}</b> não encontrado.\n"
            f"Use /devices para ver a lista completa.",
            parse_mode="HTML"
        )
        return

    await update.message.reply_text(
        f"🔍 Pingando <b>{encontrado}</b> (<code>{ip}</code>)...",
        parse_mode="HTML"
    )

    online, latencia = ping_host(ip)

    if online:
        lat = f"{latencia:.1f} ms" if latencia else "— ms"
        texto = (
            f"🟢 <b>ONLINE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🖥 <b>Dispositivo:</b> {encontrado}\n"
            f"🎯 <b>IP:</b> <code>{ip}</code>\n"
            f"📊 <b>Latência:</b> {lat}\n"
            f"⏱ {_now()}"
        )
    else:
        texto = (
            f"🔴 <b>OFFLINE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🖥 <b>Dispositivo:</b> {encontrado}\n"
            f"🎯 <b>IP:</b> <code>{ip}</code>\n"
            f"⏱ {_now()}"
        )

    await update.message.reply_text(texto, parse_mode="HTML")


async def cmd_devices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    devices = _carregar_devices()

    if not devices:
        await update.message.reply_text("❌ Não foi possível carregar o static.json.")
        return

    categorias: dict[str, list] = {}
    for nome, ip in devices.items():
        prefixo = nome.split()[0] if " " in nome else "OUTROS"
        categorias.setdefault(prefixo, []).append((nome, ip))

    linhas = []
    for cat, itens in sorted(categorias.items()):
        linhas.append(f"\n<b>▸ {cat}</b>")
        for nome, ip in sorted(itens):
            linhas.append(f"  <code>{ip}</code>  {nome}")

    texto = (
        f"🖥 <b>Dispositivos cadastrados</b> ({len(devices)})\n"
        f"━━━━━━━━━━━━━━━━━━━"
        + "".join(linhas)
    )

    if len(texto) <= 4096:
        await update.message.reply_text(texto, parse_mode="HTML")
    else:
        for parte in [texto[i:i+4000] for i in range(0, len(texto), 4000)]:
            await update.message.reply_text(parte, parse_mode="HTML")