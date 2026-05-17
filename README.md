# Proyecto 7 — Observatorio COVID-19 · Veracruz

Dashboard epidemiológico construido sobre los **datos abiertos oficiales** de la Dirección General de Epidemiología (DGE) de la Secretaría de Salud de México. Cubre **2020-2023** filtrado a registros nominales del estado de **Veracruz** (~463,000 registros, de los cuales ~243,000 son casos confirmados de COVID-19).

## Por qué este proyecto

A nivel individual los datos clínicos están protegidos por la LFPDPPP, pero la DGE publica registros nominales anonimizados — el dataset más rico de salud pública en México. Este proyecto demuestra:

- Descargar y procesar **300 MB de datos reales** del gobierno
- Filtrar y normalizar con catálogos oficiales (CIE-10, entidades, municipios)
- Cargar a SQLite con índices para consultas rápidas
- Construir un dashboard epidemiológico de nivel profesional

## Stack

- **Python 3.10+**
- **SQLite** — almacenamiento relacional con índices
- **Streamlit** — interfaz web
- **Plotly** — gráficas interactivas
- **Pandas** — ETL en chunks

## Fuente de datos

**Dirección General de Epidemiología — Datos abiertos COVID-19**
Página oficial: https://www.gob.mx/salud/documentos/datos-abiertos-152127

| Archivo | Tamaño | Cobertura |
|---|---|---|
| COVID19MEXICO2020.zip | 59 MB  | 2020 completo |
| COVID19MEXICO2021.zip | 131 MB | 2021 completo |
| COVID19MEXICO2022.zip | 92 MB  | 2022 completo |
| COVID19MEXICO2023.zip | 17 MB  | 2023 (cierre del programa) |
| diccionario_datos_abiertos.zip | <1 MB | catálogos |

A partir de 2024 la DGE consolidó COVID dentro de la vigilancia respiratoria conjunta con influenza; estos cuatro archivos son la base histórica oficial cerrada.

## Cómo correrlo

```bash
pip install -r requirements.txt
python descargar_datos.py     # descarga los 4 ZIPs + diccionario (~300 MB)
python preparar_datos.py      # filtra a Veracruz, decodifica, carga a SQLite
streamlit run dashboard.py
```

El proceso completo toma 3-5 minutos en una conexión doméstica.

## Estructura

```
.
├── descargar_datos.py      # Descarga los archivos oficiales DGE
├── preparar_datos.py       # ETL: filtra a Veracruz y construye SQLite
├── dashboard.py            # Aplicación Streamlit
├── datos_raw/              # ZIPs descargados (gitignored)
├── covid_veracruz.db       # Base SQLite generada
├── requirements.txt
└── README.md
```

### Esquema de la base

**`casos`** (463,599 registros)
- `id_registro`, `fecha_sintomas`, `fecha_ingreso`, `fecha_def`
- `es_defuncion`, `confirmado` (banderas)
- `sexo`, `edad`, `entidad_res`, `municipio_res`
- `tipo_paciente` (Ambulatorio / Hospitalizado)
- `clasificacion` (Confirmado / Negativo / Sospechoso / ...)
- `neumonia`, `intubado`, `uci`, `embarazo`
- Comorbilidades: `diabetes`, `hipertension`, `obesidad`, `epoc`, `asma`, `inmusupr`, `cardiovascular`, `renal_cronica`, `tabaquismo`

**`municipios`** (213 municipios de Veracruz, catálogo oficial DGE)

## Vistas del dashboard

1. **Indicadores clave** — registros, defunciones, letalidad (CFR), hospitalizaciones, UCI
2. **Curva epidémica** — casos y defunciones por semana (doble eje, fecha de inicio de síntomas)
3. **Pirámide demográfica** — distribución por sexo y grupo de edad
4. **Letalidad por edad** — CFR creciente con la edad (patrón epidemiológico real)
5. **Factores de riesgo** — prevalencia de cada comorbilidad en el total vs en defunciones
6. **Geografía** — top 15 municipios con más casos
7. **Severidad** — tipo de atención (ambulatoria/hospitalaria), neumonía, intubación, UCI

Todos los filtros (rango de fechas, sexo, universo de análisis) se aplican en cascada.

## Notas metodológicas

- El universo por defecto son **casos confirmados** (clasificación 1, 2 o 3 según la DGE).
- La **letalidad (CFR)** se calcula sobre el universo seleccionado, no sobre la población.
- Las **defunciones** se posicionan por *fecha de inicio de síntomas* del caso fallecido, no por fecha de defunción. Esto facilita relacionar muertes con olas de contagio.
- El conteo de Veracruz puede diferir ligeramente de reportes en línea porque aquí se filtra por `ENTIDAD_RES` (residencia del paciente), no por `ENTIDAD_UM` (unidad médica que atendió).

## Cita de fuente

> Dirección General de Epidemiología, Secretaría de Salud de México.
> *Datos abiertos sobre COVID-19, archivos históricos 2020-2023.*
> Disponible en: https://www.gob.mx/salud/documentos/datos-abiertos-152127
