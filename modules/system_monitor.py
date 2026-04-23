import time
import logging
import requests
import psutil
import subprocess
from datetime import datetime, timedelta
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 120

LIMITE_CPU   = 80
LIMITE_RAM   = 85
LIMITE_DISCO = 80
LIMITE_TEMP  = 70

_alertas_ativos: set[str] = set()


def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _send(text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"erro ao enviar alerta sistema: {e}")


def _formatar_uptime(segundos: float) -> str:
    td      = timedelta(seconds=int(segundos))
    dias    = td.days
    horas   = td.seconds // 3600
    minutos = (td.seconds % 3600) // 60
    return f"{dias}d {horas}h {minutos}m"


def _fmt_bytes(b: int) -> str:
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.1f} GB"
    return f"{b / 1024 ** 2:.0f} MB"


def coletar_ubuntu() -> dict:
    cpu  = psutil.cpu_percent(interval=1)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    temp = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for _, entradas in temps.items():
                if entradas:
                    temp = entradas[0].current
                    break
    except Exception:
        pass

    return {
        "cpu":        cpu,
        "ram_pct":    ram.percent,
        "ram_usado":  ram.used,
        "ram_total":  ram.total,
        "disco_pct":  disk.percent,
        "disco_usado": disk.used,
        "disco_total": disk.total,
        "temp":       temp,
        "uptime":     time.time() - psutil.boot_time(),
    }


def _ssh(comando: str) -> str:
    try:
        resultado = subprocess.run(
            [
                "ssh",
                "-i", "/home/ti/.ssh/watchtower_pfsense",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=5",
                "admin@192.168.100.1",
                comando,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return resultado.stdout.decode(errors="ignore").strip()
    except Exception as e:
        logger.error(f"erro ssh pfsense: {e}")
        return ""


def coletar_pfsense() -> dict | None:
    try:
        cpu_raw    = _ssh("sysctl -n kern.cp_time")
        ram_raw    = _ssh("sysctl -n hw.physmem vm.stats.vm.v_active_count vm.stats.vm.v_wire_count vm.stats.vm.v_page_size")
        temp_raw   = _ssh("sysctl -n hw.acpi.thermal.tz0.temperature 2>/dev/null || echo ''")
        uptime_raw = _ssh("sysctl -n kern.boottime")

        cpu = None
        if cpu_raw:
            try:
                valores = list(map(int, cpu_raw.split()))
                total   = sum(valores)
                idle    = valores[-1]
                cpu     = round((1 - idle / total) * 100, 1) if total else None
            except Exception:
                pass

        ram_pct = ram_total = ram_usado = None
        if ram_raw:
            try:
                linhas   = ram_raw.splitlines()
                total_b  = int(linhas[0])
                active   = int(linhas[1])
                wired    = int(linhas[2])
                pg_size  = int(linhas[3])
                usado_b  = (active + wired) * pg_size
                ram_pct  = round(usado_b / total_b * 100, 1)
                ram_total = total_b
                ram_usado = usado_b
            except Exception:
                pass

        temp = None
        if temp_raw:
            try:
                temp = float(temp_raw.replace("C", "").strip())
            except Exception:
                pass

        uptime = None
        if uptime_raw:
            try:
                sec    = int(uptime_raw.split("sec = ")[1].split(",")[0])
                uptime = time.time() - sec
            except Exception:
                pass

        return {
            "cpu":       cpu,
            "ram_pct":   ram_pct,
            "ram_usado": ram_usado,
            "ram_total": ram_total,
            "temp":      temp,
            "uptime":    uptime,
        }

    except Exception as e:
        logger.error(f"erro ao coletar dados pfsense: {e}")
        return None


def formatar_status(ubuntu: dict, pfsense: dict | None) -> str:
    u_cpu    = f"  🔲 <b>CPU:</b>   {ubuntu['cpu']:.0f}%"
    u_ram    = f"  🧠 <b>RAM:</b>   {ubuntu['ram_pct']:.0f}% ({_fmt_bytes(ubuntu['ram_usado'])} / {_fmt_bytes(ubuntu['ram_total'])})"
    u_disco  = f"  💾 <b>Disco:</b> {ubuntu['disco_pct']:.0f}% ({_fmt_bytes(ubuntu['disco_usado'])} / {_fmt_bytes(ubuntu['disco_total'])})"
    u_temp   = f"  🌡 <b>Temp:</b>  {ubuntu['temp']:.0f}°C" if ubuntu["temp"] else "  🌡 <b>Temp:</b>  —"
    u_uptime = f"  ⏱ <b>Uptime:</b> {_formatar_uptime(ubuntu['uptime'])}"

    bloco_ubuntu = (
        "🖥 <b>Ubuntu Server</b>\n"
        f"{u_cpu}\n{u_ram}\n{u_disco}\n{u_temp}\n{u_uptime}"
    )

    if pfsense:
        p_cpu    = f"  🔲 <b>CPU:</b>   {pfsense['cpu']:.0f}%" if pfsense["cpu"] is not None else "  🔲 <b>CPU:</b>  —"
        p_ram    = (
            f"  🧠 <b>RAM:</b>   {pfsense['ram_pct']:.0f}% ({_fmt_bytes(pfsense['ram_usado'])} / {_fmt_bytes(pfsense['ram_total'])})"
            if pfsense["ram_pct"] is not None else "  🧠 <b>RAM:</b>  —"
        )
        p_temp   = f"  🌡 <b>Temp:</b>  {pfsense['temp']:.0f}°C" if pfsense["temp"] else "  🌡 <b>Temp:</b>  —"
        p_uptime = f"  ⏱ <b>Uptime:</b> {_formatar_uptime(pfsense['uptime'])}" if pfsense["uptime"] else "  ⏱ <b>Uptime:</b> —"

        bloco_pfsense = (
            "🔥 <b>pfSense</b>\n"
            f"{p_cpu}\n{p_ram}\n{p_temp}\n{p_uptime}"
        )
    else:
        bloco_pfsense = "🔥 <b>pfSense</b>\n  ❌ sem conexão"

    return (
        "📊 <b>Status do Sistema</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"{bloco_ubuntu}\n\n"
        f"{bloco_pfsense}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ {_now()}"
    )


def _checar_alertas(ubuntu: dict, pfsense: dict | None):
    checks = [
        ("ubuntu_cpu",   ubuntu["cpu"],       LIMITE_CPU,   "🖥 Ubuntu Server", "CPU"),
        ("ubuntu_ram",   ubuntu["ram_pct"],   LIMITE_RAM,   "🖥 Ubuntu Server", "RAM"),
        ("ubuntu_disco", ubuntu["disco_pct"], LIMITE_DISCO, "🖥 Ubuntu Server", "Disco"),
        ("ubuntu_temp",  ubuntu["temp"],      LIMITE_TEMP,  "🖥 Ubuntu Server", "Temperatura"),
    ]

    if pfsense:
        checks += [
            ("pfsense_cpu",  pfsense["cpu"],     LIMITE_CPU,  "🔥 pfSense", "CPU"),
            ("pfsense_ram",  pfsense["ram_pct"], LIMITE_RAM,  "🔥 pfSense", "RAM"),
            ("pfsense_temp", pfsense["temp"],    LIMITE_TEMP, "🔥 pfSense", "Temperatura"),
        ]

    for chave, valor, limite, maquina, recurso in checks:
        if valor is None:
            continue

        if valor >= limite:
            if chave not in _alertas_ativos:
                _alertas_ativos.add(chave)
                unidade = "°C" if "temp" in chave else "%"
                _send(
                    f"⚠️ <b>ALERTA — {recurso} alto</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🖥 <b>Máquina:</b> {maquina}\n"
                    f"📊 <b>Valor:</b> {valor:.0f}{unidade}\n"
                    f"🚨 <b>Limite:</b> {limite}{unidade}\n"
                    f"⏱ {_now()}"
                )
        else:
            _alertas_ativos.discard(chave)


def iniciar_monitor_sistema():
    logger.info(f"monitor sistema iniciado | intervalo: {CHECK_INTERVAL}s")
    while True:
        try:
            ubuntu  = coletar_ubuntu()
            pfsense = coletar_pfsense()
            _checar_alertas(ubuntu, pfsense)
        except Exception as e:
            logger.error(f"erro no monitor sistema: {e}")
        time.sleep(CHECK_INTERVAL)