#!/usr/bin/env python3
"""Protótipo do analisador do Rastro de Velocidade.

Uso:
    python analisador_rastro_prototipo.py imagem.png

O programa lê duas regiões independentes:
1. "Intervalo de Datas", no painel esquerdo.
2. "Velocidade (km/h)", no canto inferior direito.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

DATE_TIME_RE = re.compile(
    r"(\d{2})[\s/.-]*(\d{2})[\s/.-]*(\d{4})\s+"
    r"(\d{1,2})\s*[:.]\s*(\d{2})"
)

def localizar_tesseract() -> str:
    encontrado = shutil.which("tesseract")
    if encontrado:
        return encontrado
    caminhos = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe",
        Path(r"C:\Tesseract-OCR\tesseract.exe"),
    ]
    for caminho in caminhos:
        if caminho.exists():
            return str(caminho)
    raise RuntimeError(
        "Tesseract OCR não encontrado. Execute primeiro o arquivo INSTALAR.bat."
    )

def ocr(image: Image.Image, psm: int = 7, whitelist: str | None = None) -> str:
    """Executa OCR local em uma imagem já recortada e ampliada."""
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "ocr.png"
        image.save(source)
        command = [localizar_tesseract(), str(source), "stdout", "--psm", str(psm), "-l", "eng"]
        if whitelist:
            command.extend(["-c", f"tessedit_char_whitelist={whitelist}"])
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return result.stdout.strip()

def preparar(image: Image.Image, escala: int = 6, limiar: int | None = None) -> Image.Image:
    gray = ImageOps.grayscale(image)
    gray = ImageEnhance.Contrast(gray).enhance(2.0)
    gray = gray.resize((gray.width * escala, gray.height * escala))
    if limiar is not None:
        gray = gray.point(lambda value: 255 if value >= limiar else 0)
    return gray

def extrair_intervalo(image: Image.Image) -> dict[str, str] | None:
    width, height = image.size
    if width < 500:
        return None
    left_panel = image.crop((0, 0, min(width, int(width * 0.30)), int(height * 0.38)))
    leituras: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    for escala, limiar in ((6, None), (5, 215), (6, 215)):
        text = ocr(preparar(left_panel, escala=escala, limiar=limiar), psm=6)
        normalized = text.replace("~", "-").replace("—", "-")
        values = DATE_TIME_RE.findall(normalized)
        if len(values) >= 2:
            inicio, fim = values[0], values[1]
            dia_i, mes_i, ano_i, hora_i, minuto_i = map(int, inicio)
            dia_f, mes_f, ano_f, hora_f, minuto_f = map(int, fim)
            valido = (
                1 <= dia_i <= 31 and 1 <= mes_i <= 12 and 2020 <= ano_i <= 2100
                and 0 <= hora_i <= 23 and 0 <= minuto_i <= 59
                and 1 <= dia_f <= 31 and 1 <= mes_f <= 12 and 2020 <= ano_f <= 2100
                and 0 <= hora_f <= 23 and 0 <= minuto_f <= 59
            )
            if valido:
                leituras.append((inicio, fim))
    if not leituras:
        return None
    start, end = Counter(leituras).most_common(1)[0][0]
    return {
        "data_inicio": f"{start[0]}/{start[1]}/{start[2]}",
        "hora_inicio": f"{int(start[3]):02d}:{start[4]}",
        "data_fim": f"{end[0]}/{end[1]}/{end[2]}",
        "hora_fim": f"{int(end[3]):02d}:{end[4]}",
    }

def colorido(rgb: tuple[int, int, int]) -> bool:
    red, green, blue = rgb
    saturation = max(rgb) - min(rgb)
    brightness = (red + green + blue) / 3
    return saturation > 30 and 35 < brightness < 250

def maior_segmento_por_linha(panel: Image.Image) -> list[dict[str, int]]:
    pixels = panel.load()
    width, height = panel.size
    rows: list[dict[str, int]] = []
    for y in range(height):
        start = -1
        best: tuple[int, int, int] | None = None
        for x in range(width):
            is_colored = colorido(pixels[x, y][:3])
            if is_colored and start < 0:
                start = x
            elif not is_colored and start >= 0:
                candidate = (start, x - 1, x - start)
                if best is None or candidate[2] > best[2]:
                    best = candidate
                start = -1
        if start >= 0:
            candidate = (start, width - 1, width - start)
            if best is None or candidate[2] > best[2]:
                best = candidate
        if best and best[2] >= max(6, round(width * 0.025)):
            rows.append({"y": y, "inicio": best[0], "fim": best[1], "largura": best[2]})
    return rows

def corrigir_numero(valor: str) -> str:
    if "," in valor:
        numero = float(valor.replace(",", "."))
    else:
        digitos = re.sub(r"\D", "", valor)
        if len(digitos) >= 2 and int(digitos) > 10:
            if len(digitos) > 2:
                digitos = digitos[-2:]
            numero = float(f"{digitos[:-1]}.{digitos[-1]}")
        else:
            numero = float(digitos)
    return f"{numero:g}".replace(".", ",")

def ler_faixa(text: str) -> str | None:
    normalized = (
        text.lower()
        .replace("o", "0")
        .replace("|", "1")
        .replace(".", ",")
        .replace(" ", "")
    )
    above = re.search(r"(?:>=|≥)(\d+(?:,\d+)?)", normalized)
    interval = re.search(r"(\d+(?:,\d+)?)a(\d+(?:,\d+)?)", normalized)
    if above:
        return f"≥ {corrigir_numero(above.group(1))} km/h"
    if interval:
        inicio = corrigir_numero(interval.group(1))
        fim = corrigir_numero(interval.group(2))
        if float(inicio.replace(",", ".")) < float(fim.replace(",", ".")):
            return f"{inicio} a {fim} km/h"
    return None

def ler_percentual(text: str) -> float | None:
    normalized = text.replace(" ", "").replace("O", "0").replace("o", "0")
    decimal = re.search(r"(\d{1,3})\s*[,.]\s*(\d{1,2})\s*%?", normalized)
    if decimal:
        value = float(f"{decimal.group(1)}.{decimal.group(2)}")
        return value if 0 <= value <= 100 else None
    compact = re.search(r"(\d{3,5})\s*%", normalized)
    if compact:
        digits = compact.group(1)
        value = float(f"{digits[:-2]}.{digits[-2:]}")
        return value if 0 <= value <= 100 else None
    return None

def ler_percentuais(text: str) -> list[float]:
    """Extrai todos os percentuais possíveis, mesmo com um ruído antes do número."""
    normalized = text.replace(" ", "").replace("O", "0").replace("o", "0")
    values: list[float] = []
    for match in re.finditer(r"(\d{1,3})[,.](\d{1,2})%?", normalized):
        value = float(f"{match.group(1)}.{match.group(2)}")
        if 0 <= value <= 100:
            values.append(value)
    for match in re.finditer(r"(?:^|\D)(\d{3,5})%(?:\D|$)", normalized):
        digits = match.group(1)
        value = float(f"{digits[:-2]}.{digits[-2:]}")
        if 0 <= value <= 100:
            values.append(value)
    originais = list(values)
    confusoes = [
        ("7", "9"), ("9", "7"),
        ("1", "7"), ("7", "1"),
        ("0", "8"), ("8", "0"),
    ]
    for valor in originais:
        texto = f"{valor:.2f}"
        for a, b in confusoes:
            texto_alt = texto.replace(a, b)
            try:
                valor_alt = float(texto_alt)
                if 0 <= valor_alt <= 100 and valor_alt not in values:
                    values.append(valor_alt)
            except ValueError:
                pass
    return values

def _extrair_legenda_painel(panel: Image.Image) -> dict[str, object] | None:
    panel = panel.convert("RGB")
    panel_width, panel_height = panel.size
    candidates = [
        row for row in maior_segmento_por_linha(panel)
        if (
            panel_height * 0.30 < row["y"] < panel_height * 0.96
            and panel_width * 0.12 < row["inicio"] < panel_width * 0.60
            and row["fim"] < panel_width * 0.85
        )
    ]
    if not candidates:
        return None
    winner = max(candidates, key=lambda row: row["largura"])
    neighbors = [
        row for row in candidates
        if abs(row["y"] - winner["y"]) <= max(12, round(panel_height * 0.075))
        and abs(row["inicio"] - winner["inicio"]) <= 3
        and row["largura"] >= winner["largura"] * 0.90
    ]
    center_y = round(sum(row["y"] for row in neighbors) / len(neighbors)) if neighbors else winner["y"]
    half_height = max(12, min(18, round(panel_height * 0.04)))
    top = max(0, center_y - half_height)
    bottom = min(panel_height, center_y + half_height)
    percent_half_height = max(16, min(30, round(panel_height * 0.06)))
    percent_top = max(0, center_y - percent_half_height)
    percent_bottom = min(panel_height, center_y + percent_half_height)

    leituras_faixa: list[tuple[str, str]] = []
    deslocamentos = sorted({
        30, 40, 50,
        *(round(panel_width * fracao) for fracao in (0.12, 0.15)),
    })
    for deslocamento in deslocamentos:
        label_left = max(0, winner["inicio"] - deslocamento)
        label_crop = panel.crop((label_left, top, winner["inicio"], bottom))
        for escala in (10, 14):
            candidate_text = ocr(preparar(label_crop, escala=escala), psm=7)
            candidate_range = ler_faixa(candidate_text)
            if candidate_range:
                leituras_faixa.append((candidate_range, candidate_text))

    speed_range = None
    label_text = ""
    if leituras_faixa:
        contagem_faixas = Counter(value for value, _ in leituras_faixa)
        speed_range = contagem_faixas.most_common(1)[0][0]
        label_text = next(text for value, text in leituras_faixa if value == speed_range)

    fim_grade_estimado = round(panel_width * 0.832)
    largura_grade = max(1, fim_grade_estimado - winner["inicio"])
    percentual_visual = winner["largura"] / largura_grade * 100
    leituras_percentual: list[tuple[float, str]] = []

    for fracao in (0.70, 0.74, 0.78):
        percent_crop = panel.crop((round(panel_width * fracao), percent_top, panel_width, percent_bottom))
        for threshold in (200, None):
            candidate_text = ocr(
                preparar(percent_crop, escala=14, limiar=threshold),
                psm=7,
                whitelist="0123456789,.%",
            )
            valores = ler_percentuais(candidate_text)
            compacto = candidate_text.replace(" ", "")
            if "%" not in compacto and compacto.endswith("8"):
                valores.extend(int(valor * 10) / 10 for valor in list(valores))
            candidatos = list(valores)
            if percentual_visual >= 75:
                for valor in valores:
                    if valor < 40:
                        candidatos.append(valor + 70)
            for candidate_value in candidatos:
                if abs(candidate_value - percentual_visual) <= 30:
                    leituras_percentual.append((round(candidate_value, 2), candidate_text))

    if not leituras_percentual:
        for fracao in (0.72, 0.76, 0.80):
            percent_crop = panel.crop((round(panel_width * fracao), percent_top, panel_width, percent_bottom))
            for threshold in (None, 200):
                candidate_text = ocr(
                    preparar(percent_crop, escala=12, limiar=threshold),
                    psm=7,
                )
                valores = ler_percentuais(candidate_text)
                compacto = candidate_text.replace(" ", "")
                if "%" not in compacto and compacto.endswith("8"):
                    valores.extend(int(valor * 10) / 10 for valor in list(valores))
                candidatos = list(valores)
                if percentual_visual >= 75:
                    for valor in valores:
                        if valor < 40:
                            candidatos.append(valor + 70)
                for candidate_value in candidatos:
                    if abs(candidate_value - percentual_visual) <= 30:
                        leituras_percentual.append((round(candidate_value, 2), candidate_text))

    percentage = None
    percent_text = ""
    if leituras_percentual:
        contagem = Counter(value for value, _ in leituras_percentual)
        valores_validos = list(contagem)
        if percentual_visual >= 75:
            altos = [valor for valor in valores_validos if valor >= 60]
            if altos:
                valores_validos = altos
        com_simbolo = {
            valor for valor, texto_lido in leituras_percentual
            if "%" in texto_lido
        }
        confiaveis = [valor for valor in valores_validos if valor in com_simbolo]
        if confiaveis:
            valores_validos = confiaveis
        alvo_visual = min(100.0, percentual_visual)
        proximos = [
            valor for valor in valores_validos
            if abs(valor - alvo_visual) <= 30
        ]
        if proximos:
            valores_validos = proximos
        percentage = min(
            valores_validos,
            key=lambda valor: (round(abs(valor - alvo_visual), 1), -contagem[valor]),
        )
        percent_text = next(text for value, text in leituras_percentual if value == percentage)

    if speed_range is None or percentage is None:
        return None

    return {
        "faixa": speed_range,
        "percentual": round(percentage, 2),
        "linha_y": center_y,
        "largura_barra": winner["largura"],
        "ocr_faixa": label_text,
        "ocr_percentual": percent_text,
    }

def extrair_legenda(image: Image.Image) -> dict[str, object] | None:
    """Localiza a legenda no canto direito sem depender de tamanho fixo.

    São testadas regiões proporcionais de diferentes larguras e alturas. Isso
    cobre capturas em Full HD, notebooks, zoom do navegador e painéis maiores.
    """
    width, height = image.size
    if width < 500:
        return _extrair_legenda_painel(image)

    regioes_vistas: set[tuple[int, int]] = set()
    for largura_fracao in (0.30, 0.28, 0.26, 0.32, 0.24, 0.34, 0.22, 0.36, 0.20, 0.38, 0.40):
        for topo_fracao in (0.55, 0.50, 0.60, 0.45, 0.65, 0.40, 0.70):
            panel_width = max(220, round(width * largura_fracao))
            panel_width = min(width, panel_width)
            topo = round(height * topo_fracao)
            chave = (panel_width, topo)
            if chave in regioes_vistas:
                continue
            regioes_vistas.add(chave)
            panel = image.crop((width - panel_width, topo, width, height))
            resultado = _extrair_legenda_painel(panel)
            if resultado:
                return resultado
    return None

def analisar(path: Path) -> dict[str, object]:
    image = Image.open(path).convert("RGB")
    interval = extrair_intervalo(image)
    legend = extrair_legenda(image)
    return {
        "arquivo": path.name,
        "intervalo": interval,
        "velocidade": legend,
        "status": "ok" if legend and (interval or image.width < 500) else "revisar",
    }

def main() -> int:
    if len(sys.argv) < 2:
        print("Informe pelo menos uma imagem.", file=sys.stderr)
        return 2
    for argument in sys.argv[1:]:
        print(json.dumps(analisar(Path(argument)), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
