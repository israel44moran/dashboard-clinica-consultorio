"""Lee los 4 ZIPs anuales de la DGE, filtra a Veracruz, decodifica catálogos
y construye una base SQLite lista para el dashboard.

Salida: covid_veracruz.db con las tablas:
- casos       (registros nominales filtrados a Veracruz)
- municipios  (catálogo de municipios de Veracruz)

La columna ENTIDAD_RES = 30 corresponde a Veracruz.
"""
from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

import pandas as pd

DIR_BASE = Path(__file__).parent
DIR_RAW = DIR_BASE / "datos_raw"
RUTA_DB = DIR_BASE / "covid_veracruz.db"
RUTA_DIC = DIR_RAW / "dict" / "240708 Catalogos.xlsx"

ENTIDAD_VERACRUZ = 30

ARCHIVOS_ANUALES = [
    "COVID19MEXICO2020.zip",
    "COVID19MEXICO2021.zip",
    "COVID19MEXICO2022.zip",
    "COVID19MEXICO2023.zip",
]

CHUNK = 200_000

# ============================================================
# CATÁLOGOS
# ============================================================
CAT_SEXO = {1: "Mujer", 2: "Hombre", 99: None}
CAT_TIPO = {1: "Ambulatorio", 2: "Hospitalizado", 99: None}
CAT_CLASIF = {
    1: "Confirmado",
    2: "Confirmado",
    3: "Confirmado",
    4: "Inválido",
    5: "No realizado",
    6: "Sospechoso",
    7: "Negativo",
}

# Comorbilidades y otros campos Sí/No: convertimos a 1/0/NULL
SI_NO = {1: 1, 2: 0, 97: None, 98: None, 99: None}

COMORBILIDADES = [
    "DIABETES", "EPOC", "ASMA", "INMUSUPR", "HIPERTENSION",
    "CARDIOVASCULAR", "OBESIDAD", "RENAL_CRONICA", "TABAQUISMO",
]
SI_NO_EXTRA = ["NEUMONIA", "INTUBADO", "UCI", "EMBARAZO"]


# ============================================================
# CARGA DE CATÁLOGOS AUXILIARES (entidades y municipios)
# ============================================================
def cargar_entidades() -> dict[int, str]:
    df = pd.read_excel(RUTA_DIC, sheet_name="Catálogo de ENTIDADES")
    return dict(zip(df["CLAVE_ENTIDAD"], df["ENTIDAD_FEDERATIVA"]))


def cargar_municipios_veracruz() -> pd.DataFrame:
    df = pd.read_excel(RUTA_DIC, sheet_name="Catálogo MUNICIPIOS")
    df.columns = [c.strip() for c in df.columns]
    col_ent = next(c for c in df.columns if "ENTIDAD" in c.upper())
    col_mun = next(c for c in df.columns if "MUNICIPIO" in c.upper() and "CLAVE" in c.upper())
    col_nom = next(c for c in df.columns if c.upper() == "MUNICIPIO")
    ver = df[df[col_ent] == ENTIDAD_VERACRUZ].copy()
    ver = ver.rename(columns={col_mun: "clave", col_nom: "nombre"})
    return ver[["clave", "nombre"]].reset_index(drop=True)


# ============================================================
# ESQUEMA
# ============================================================
def crear_esquema(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS casos;
        DROP TABLE IF EXISTS municipios;

        CREATE TABLE municipios (
            clave   INTEGER PRIMARY KEY,
            nombre  TEXT NOT NULL
        );

        CREATE TABLE casos (
            id_registro      TEXT PRIMARY KEY,
            fecha_sintomas   TEXT,
            fecha_ingreso    TEXT,
            fecha_def        TEXT,
            es_defuncion     INTEGER NOT NULL,
            sexo             TEXT,
            edad             INTEGER,
            entidad_res      INTEGER,
            municipio_res    INTEGER,
            tipo_paciente    TEXT,
            clasificacion    TEXT,
            confirmado       INTEGER NOT NULL,
            neumonia         INTEGER,
            intubado         INTEGER,
            uci              INTEGER,
            embarazo         INTEGER,
            diabetes         INTEGER,
            epoc             INTEGER,
            asma             INTEGER,
            inmusupr         INTEGER,
            hipertension     INTEGER,
            cardiovascular   INTEGER,
            obesidad         INTEGER,
            renal_cronica    INTEGER,
            tabaquismo       INTEGER
        );

        CREATE INDEX ix_casos_fsint ON casos(fecha_sintomas);
        CREATE INDEX ix_casos_conf  ON casos(confirmado);
        CREATE INDEX ix_casos_mun   ON casos(municipio_res);
        """
    )
    con.commit()


# ============================================================
# TRANSFORMACIÓN DE UN CHUNK
# ============================================================
def transformar(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["ENTIDAD_RES"] == ENTIDAD_VERACRUZ].copy()
    if df.empty:
        return df

    df["fecha_def_raw"] = df["FECHA_DEF"].astype(str)
    df["es_defuncion"] = (df["fecha_def_raw"] != "9999-99-99").astype(int)
    df["fecha_def"] = df["fecha_def_raw"].where(df["es_defuncion"] == 1, None)

    df["sexo"] = df["SEXO"].map(CAT_SEXO)
    df["tipo_paciente"] = df["TIPO_PACIENTE"].map(CAT_TIPO)
    df["clasificacion"] = df["CLASIFICACION_FINAL"].map(CAT_CLASIF)
    df["confirmado"] = df["CLASIFICACION_FINAL"].isin([1, 2, 3]).astype(int)

    for col in COMORBILIDADES + SI_NO_EXTRA:
        df[col.lower()] = df[col].map(SI_NO).astype("Int64")

    salida = pd.DataFrame({
        "id_registro": df["ID_REGISTRO"].astype(str),
        "fecha_sintomas": df["FECHA_SINTOMAS"],
        "fecha_ingreso": df["FECHA_INGRESO"],
        "fecha_def": df["fecha_def"],
        "es_defuncion": df["es_defuncion"],
        "sexo": df["sexo"],
        "edad": df["EDAD"],
        "entidad_res": df["ENTIDAD_RES"],
        "municipio_res": df["MUNICIPIO_RES"],
        "tipo_paciente": df["tipo_paciente"],
        "clasificacion": df["clasificacion"],
        "confirmado": df["confirmado"],
        "neumonia": df["neumonia"],
        "intubado": df["intubado"],
        "uci": df["uci"],
        "embarazo": df["embarazo"],
        "diabetes": df["diabetes"],
        "epoc": df["epoc"],
        "asma": df["asma"],
        "inmusupr": df["inmusupr"],
        "hipertension": df["hipertension"],
        "cardiovascular": df["cardiovascular"],
        "obesidad": df["obesidad"],
        "renal_cronica": df["renal_cronica"],
        "tabaquismo": df["tabaquismo"],
    })
    return salida


# ============================================================
# PROCESO PRINCIPAL
# ============================================================
def procesar_archivo(zip_path: Path, con: sqlite3.Connection) -> int:
    total = 0
    with zipfile.ZipFile(zip_path) as z:
        nombre_csv = z.namelist()[0]
        with z.open(nombre_csv) as f:
            for chunk in pd.read_csv(f, encoding="latin-1", chunksize=CHUNK, low_memory=False):
                limpio = transformar(chunk)
                if not limpio.empty:
                    limpio.to_sql("casos", con, if_exists="append", index=False)
                    total += len(limpio)
                    print(f"    procesados {total:>8,} de Veracruz...", end="\r")
    print()
    return total


def main() -> None:
    if not RUTA_DIC.exists():
        print("ERROR: falta el diccionario. Ejecuta primero descargar_datos.py")
        return

    if RUTA_DB.exists():
        RUTA_DB.unlink()

    con = sqlite3.connect(RUTA_DB)
    crear_esquema(con)

    print("Cargando catálogo de municipios de Veracruz...")
    municipios = cargar_municipios_veracruz()
    municipios.to_sql("municipios", con, if_exists="append", index=False)
    print(f"  {len(municipios)} municipios cargados")
    print()

    print("Procesando archivos anuales (filtrando a Veracruz)...")
    gran_total = 0
    for nombre in ARCHIVOS_ANUALES:
        ruta = DIR_RAW / nombre
        if not ruta.exists():
            print(f"  ! falta {nombre}, se omite")
            continue
        print(f"  {nombre}")
        gran_total += procesar_archivo(ruta, con)

    print()
    cur = con.cursor()
    n_total = cur.execute("SELECT COUNT(*) FROM casos").fetchone()[0]
    n_conf = cur.execute("SELECT COUNT(*) FROM casos WHERE confirmado=1").fetchone()[0]
    n_def = cur.execute("SELECT COUNT(*) FROM casos WHERE es_defuncion=1 AND confirmado=1").fetchone()[0]
    print(f"Total cargado:       {n_total:,} registros")
    print(f"  Confirmados:       {n_conf:,}")
    print(f"  Defunciones conf.: {n_def:,}")
    print(f"  CFR:               {n_def/n_conf*100:.2f}%")
    print(f"Base lista:          {RUTA_DB.name}")
    con.close()


if __name__ == "__main__":
    main()
