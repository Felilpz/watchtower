import json
import logging
import paramiko
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import STATIC_JSON_PATH, PFSENSE_HOST, PFSENSE_USER, PFSENSE_PASS, PFSENSE_PORT
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


def _ssh_pfsense(comando: str) -> str | None:
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=PFSENSE_HOST,
            port=PFSENSE_PORT,
            username=PFSENSE_USER,
            password=PFSENSE_PASS,
            timeout=10,
        )
        _, stdout, stderr = client.exec_command(comando)
        saida = stdout.read().decode(errors="ignore").strip()
        client.close()
        return saida
    except Exception as e:
        logger.error(f"erro ssh pfsense: {e}")
        return None


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
    await update.message.reply_text("🔍 Consultando acessos ao webConfigurator...", parse_mode="HTML")

    saida = _ssh_pfsense("clog /var/log/system.log 2>/dev/null | grep -i 'webconfigurator' | tail -20")

    if saida is None:
        await update.message.reply_text("❌ Não foi possível conectar ao pfSense via SSH.")
        return

    if not saida:
        await update.message.reply_text("ℹ️ Nenhum acesso ao webConfigurator encontrado.")
        return

    linhas = []
    for linha in saida.splitlines():
        l = linha.lower()
        if "successful" in l or "logged in" in l:
            linhas.append(f"🟢 {linha}")
        elif "failed" in l or "invalid" in l or "error" in l:
            linhas.append(f"🔴 {linha}")
        elif "logged out" in l or "logout" in l:
            linhas.append(f"🟡 {linha}")
        else:
            linhas.append(f"⚪ {linha}")

    texto = (
        "🔐 <b>Acessos ao webConfigurator</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<pre>" + "\n".join(linhas) + "</pre>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ {_now()}"
    )

    if len(texto) <= 4096:
        await update.message.reply_text(texto, parse_mode="HTML")
    else:
        for parte in [texto[i:i+4000] for i in range(0, len(texto), 4000)]:
            await update.message.reply_text(parte, parse_mode="HTML")