"""Descarga los datos abiertos COVID-19 de la DGE (México).

Fuente oficial: Dirección General de Epidemiología, Secretaría de Salud.
https://www.gob.mx/salud/documentos/datos-abiertos-152127

Descarga los 4 archivos anuales históricos (2020-2023) y el diccionario.
Total: ~300 MB comprimidos. Los archivos se guardan en ./datos_raw/
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

DIR_RAW = Path(__file__).parent / "datos_raw"

ARCHIVOS = {
    "COVID19MEXICO2020.zip":
        "https://datosabiertos.salud.gob.mx/gobmx/salud/datos_abiertos/historicos/2020/COVID19MEXICO2020.zip",
    "COVID19MEXICO2021.zip":
        "https://datosabiertos.salud.gob.mx/gobmx/salud/datos_abiertos/historicos/2021/COVID19MEXICO2021.zip",
    "COVID19MEXICO2022.zip":
        "https://datosabiertos.salud.gob.mx/gobmx/salud/datos_abiertos/historicos/2022/COVID19MEXICO2022.zip",
    "COVID19MEXICO2023.zip":
        "https://datosabiertos.salud.gob.mx/gobmx/salud/datos_abiertos/historicos/2023/COVID19MEXICO2023.zip",
    "diccionario_datos_abiertos.zip":
        "https://datosabiertos.salud.gob.mx/gobmx/salud/datos_abiertos/diccionario_datos_abiertos.zip",
}


def _progreso(bloque: int, tam_bloque: int, tam_total: int) -> None:
    if tam_total <= 0:
        return
    bajados = bloque * tam_bloque
    pct = min(100, bajados * 100 // tam_total)
    mb_b = bajados / (1024 * 1024)
    mb_t = tam_total / (1024 * 1024)
    sys.stdout.write(f"\r    {pct:3d}%  [{mb_b:6.1f} / {mb_t:6.1f} MB]")
    sys.stdout.flush()


def descargar(nombre: str, url: str, destino: Path) -> None:
    salida = destino / nombre
    if salida.exists():
        tam_mb = salida.stat().st_size / (1024 * 1024)
        print(f"  {nombre}  ya existe ({tam_mb:.1f} MB), se omite")
        return

    print(f"  {nombre}")
    print(f"    {url}")
    try:
        urllib.request.urlretrieve(url, salida, reporthook=_progreso)
        print()
    except Exception as e:
        if salida.exists():
            salida.unlink()
        print(f"\n    ERROR: {e}")
        raise


def main() -> None:
    DIR_RAW.mkdir(exist_ok=True)
    print(f"Descargando datos abiertos DGE a: {DIR_RAW}")
    print()

    for nombre, url in ARCHIVOS.items():
        descargar(nombre, url, DIR_RAW)

    print()
    print("Descarga completa.")
    print("Siguiente paso: python preparar_datos.py")


if __name__ == "__main__":
    main()
