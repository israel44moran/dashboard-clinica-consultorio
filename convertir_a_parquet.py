"""Convierte el SQLite a un Parquet liviano y eficiente.

El dashboard original carga 463k filas del .db a memoria. En Streamlit
Cloud free tier (1 GB RAM) el proceso colapsa por la sobrecarga de
pandas + dtypes ineficientes (todo en object/float64).

Este script:
  1. Lee la tabla `casos` + JOIN con `municipios` para tener el nombre.
  2. Convierte tipos a categoricos y enteros chicos -> reduce ~80% la RAM.
  3. Guarda como Parquet con compresion snappy -> ~20-30 MB en disco.

Resultado: el dashboard arranca en segundos y cabe holgado en el free tier.

Uso:
    python convertir_a_parquet.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

RUTA_DB = Path(__file__).parent / "covid_veracruz.db"
RUTA_PARQUET = Path(__file__).parent / "casos_veracruz.parquet"


def convertir() -> None:
    if not RUTA_DB.exists():
        print(f"ERROR: no encuentro {RUTA_DB.name}", file=sys.stderr)
        print("Corre primero: python preparar_datos.py", file=sys.stderr)
        sys.exit(1)

    print(f"Leyendo {RUTA_DB.name} ({RUTA_DB.stat().st_size/1024/1024:.1f} MB)...")
    con = sqlite3.connect(RUTA_DB)
    df = pd.read_sql(
        """
        SELECT c.*, m.nombre AS municipio
        FROM casos c
        LEFT JOIN municipios m ON m.clave = c.municipio_res
        """,
        con,
    )
    con.close()
    print(f"  {len(df):,} filas, {len(df.columns)} columnas")
    print(f"  Memoria pandas en bruto: {df.memory_usage(deep=True).sum()/1024/1024:.1f} MB")

    # Fechas
    for c in ("fecha_sintomas", "fecha_ingreso", "fecha_def"):
        df[c] = pd.to_datetime(df[c], errors="coerce")

    # Enteros chicos
    df["edad"] = df["edad"].astype("Int16")
    df["entidad_res"] = df["entidad_res"].astype("Int16")
    df["municipio_res"] = df["municipio_res"].astype("Int16")
    for c in ("es_defuncion", "confirmado"):
        df[c] = df[c].astype("Int8")

    # Comorbilidades y banderas (0/1 con NaN posibles)
    banderas = ["neumonia", "intubado", "uci", "embarazo", "diabetes", "epoc",
                "asma", "inmusupr", "hipertension", "cardiovascular", "obesidad",
                "renal_cronica", "tabaquismo"]
    for c in banderas:
        if c in df.columns:
            df[c] = df[c].astype("Int8")

    # Categoricos (ahorran muchisima RAM cuando hay pocos valores unicos)
    for c in ("sexo", "tipo_paciente", "clasificacion", "municipio"):
        if c in df.columns:
            df[c] = df[c].astype("category")

    # id_registro no se usa en el dashboard; lo quitamos para ahorrar 40MB.
    if "id_registro" in df.columns:
        df = df.drop(columns=["id_registro"])

    print(f"  Memoria pandas optimizada: {df.memory_usage(deep=True).sum()/1024/1024:.1f} MB")
    print(f"  Reduccion: ~{(1 - df.memory_usage(deep=True).sum() / (463599 * len(df.columns) * 8)) * 100:.0f}%")

    print(f"\nEscribiendo {RUTA_PARQUET.name} con compresion snappy...")
    df.to_parquet(RUTA_PARQUET, compression="snappy", index=False)
    tam = RUTA_PARQUET.stat().st_size / 1024 / 1024
    print(f"  OK -> {tam:.1f} MB en disco")
    print(f"  Ratio vs SQLite: {tam / (RUTA_DB.stat().st_size / 1024 / 1024) * 100:.1f}%")
    print()
    print("Verificacion: re-leyendo el parquet...")
    df2 = pd.read_parquet(RUTA_PARQUET)
    print(f"  {len(df2):,} filas leidas, dtypes preservados")
    print(f"  Memoria al cargar: {df2.memory_usage(deep=True).sum()/1024/1024:.1f} MB")


if __name__ == "__main__":
    convertir()
