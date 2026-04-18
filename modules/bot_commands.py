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
        "👁 <b>WatchTower</b> — Monitor de Rede\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "📡 <b>WAN</b>\n"
        "  /wan — status dos links\n\n"
        "🖥 <b>Dispositivos</b>\n"
        "  /devices — listar todos\n"
        "  /ping &lt;nome&gt; — pingar dispositivo\n\n"
        "🔐 <b>Segurança</b>\n"
        "  /logins — últimos acessos ao pfSense\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ {_now()}"
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
        "📡 <b>Status dos Gateways</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(linhas) +
        "\n━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ {_now()}"
    )
    await update.message.reply_text(texto, parse_mode="HTML")


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Uso: <code>/ping &lt;nome&gt;</code>\n"
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
            "Use /devices para ver a lista completa.",
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
            "🟢 <b>ONLINE</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"🖥 <b>Dispositivo:</b> {encontrado}\n"
            f"🎯 <b>IP:</b> <code>{ip}</code>\n"
            f"📊 <b>Latência:</b> {lat}\n"
            f"⏱ {_now()}"
        )
    else:
        texto = (
            "🔴 <b>OFFLINE</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
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

    # agrupa pelo primeiro termo do nome (AP, SWITCH, CAMERA, etc.)
    categorias: dict[str, list] = {}
    for nome, ip in devices.items():
        prefixo = nome.split()[0] if " " in nome else nome
        categorias.setdefault(prefixo, []).append((nome, ip))

    linhas = [f"🖥 <b>Dispositivos cadastrados</b> ({len(devices)})\n━━━━━━━━━━━━━━━━━━━"]

    for cat in sorted(categorias.keys()):
        itens = sorted(categorias[cat], key=lambda x: x[0])
        linhas.append(f"\n<b>{cat}</b>")
        for nome, ip in itens:
            # nome sem o prefixo repetido para ficar mais limpo
            nome_curto = nome[len(cat):].strip() or nome
            linhas.append(f"  • {nome_curto}\n    <code>{ip}</code>")

    texto = "\n".join(linhas)

    if len(texto) <= 4096:
        await update.message.reply_text(texto, parse_mode="HTML")
    else:
        for parte in [texto[i:i+4000] for i in range(0, len(texto), 4000)]:
            await update.message.reply_text(parte, parse_mode="HTML")


async def cmd_logins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_path = "/var/log/pfsense/all.log"

    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            linhas_raw = f.readlines()
    except FileNotFoundError:
        await update.message.reply_text("❌ Log do pfSense não encontrado.")
        return

    eventos = [
        l.strip() for l in linhas_raw
        if "php-fpm" in l and "/index.php" in l
        and any(k in l for k in ("Successful login", "logged out", "Failed login"))
    ][-20:]

    if not eventos:
        await update.message.reply_text("ℹ️ Nenhum acesso ao webConfigurator encontrado.")
        return

    linhas = []
    for linha in eventos:
        try:
            partes  = linha.split("/index.php:")[-1].strip()
            usuario = partes.split("'")[1] if "'" in partes else "?"
            origem  = partes.split("from:")[-1].strip().split()[0] if "from:" in partes else "?"
            # converte "2026-04-17T21:44:00-03:00" → "17/04/2026 21:44:00"
            ts_raw  = linha.split()[0]
            ts      = datetime.fromisoformat(ts_raw).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            usuario, origem, ts = "?", "?", "?"

        if "Successful login" in linha:
            emoji = "✅"
            acao  = "Login"
        elif "logged out" in linha.lower():
            emoji = "🚪"
            acao  = "Logout"
        elif "Failed login" in linha:
            emoji = "❌"
            acao  = "Falha"
        else:
            continue

        linhas.append(f"{emoji} <b>{acao}</b> — <code>{usuario}</code> ({origem})\n    ⏱ {ts}")

    texto = (
        "🔐 <b>Acessos ao webConfigurator</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(linhas) +
        "\n━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ {_now()}"
    )

    if len(texto) <= 4096:
        await update.message.reply_text(texto, parse_mode="HTML")
    else:
        for parte in [texto[i:i+4000] for i in range(0, len(texto), 4000)]:
            await update.message.reply_text(parte, parse_mode="HTML")