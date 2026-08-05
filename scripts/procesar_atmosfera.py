import requests
import os
import sys
import time
import math
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(dotenv_path=env_path)

AEMET_KEY = os.getenv("AEMET_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
HEADERS = {"api_key": AEMET_KEY}

MUNICIPIO_ESTACION = {
    "Las Palmas de Gran Canaria": "C658X",
    "San Bartolomé de Tirajana": "C635B",
    "Telde": "C648N",
    "Gáldar": "C619X",
    "Arucas": "C669B",
    "Santa Lucía de Tirajana": "C635B",
    "Ingenio": "C648C",
    "Agüimes": "C648C",
    "Mogán": "C629X",
    "La Aldea de San Nicolás": "C619Y",
    "Tejeda": "C614H",
    "Valsequillo": "C611E",
    "Teror": "C656V",
    "Vega de San Mateo": "C611E",
    "Firgas": "C669B",
    "Moya": "C669B",
    "Santa María de Guía": "C619X",
    "Agaete": "C619X",
    "Artenara": "C612F",
    "Santa Brígida": "C611E",
    "Valleseco": "C665T",
}


def punto_de_rocio(temp_c, humedad_relativa):
    a, b = 17.27, 237.7
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(humedad_relativa / 100.0)
    return round((b * alpha) / (a - alpha), 2)


def calcular_awgp(temp_c, humedad_relativa):
    e_sat = 6.112 * math.exp((17.67 * temp_c) / (temp_c + 243.5))
    awgp = (e_sat * humedad_relativa * 2.1674) / (273.15 + temp_c)
    return round(awgp, 3)


def parsear_numero(valor):
    if not valor or valor.strip() == "":
        return None
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


def obtener_datos_estacion(codigo_estacion, fecha_inicio, fecha_fin, reintentos=4):
    url = (
        f"https://opendata.aemet.es/opendata/api/valores/climatologicos/"
        f"diarios/datos/fechaini/{fecha_inicio}/fechafin/{fecha_fin}/"
        f"estacion/{codigo_estacion}"
    )

    for intento in range(reintentos):
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 429:
            espera = 15 * (intento + 1)
            print(f"    Rate limit. Esperando {espera}s...")
            time.sleep(espera)
            continue

        if response.status_code != 200:
            print(f"    Error inicial: {response.status_code}")
            return None

        try:
            data = response.json()
        except ValueError:
            time.sleep(10)
            continue

        if data.get("estado") != 200:
            print(f"    AEMET estado {data.get('estado')}: {data.get('descripcion')}")
            return None

        time.sleep(2)
        datos_response = requests.get(data.get("datos"))
        if datos_response.status_code != 200:
            return None

        try:
            resultado = datos_response.json()
        except ValueError:
            time.sleep(10)
            continue

        if not isinstance(resultado, list):
            time.sleep(10)
            continue

        return resultado

    return None


def obtener_datos_año_completo(codigo_estacion, año):
    tramo1 = obtener_datos_estacion(
        codigo_estacion,
        f"{año}-01-01T00:00:00UTC",
        f"{año}-06-30T23:59:59UTC"
    )
    time.sleep(10)
    tramo2 = obtener_datos_estacion(
        codigo_estacion,
        f"{año}-07-01T00:00:00UTC",
        f"{año}-12-31T23:59:59UTC"
    )

    datos = []
    if tramo1:
        datos.extend(tramo1)
    if tramo2:
        datos.extend(tramo2)

    return datos if datos else None


def procesar_municipio(nombre_municipio, codigo_estacion, año):
    print(f"\n  {nombre_municipio} ({codigo_estacion})...")

    res = supabase.table("municipios").select("id").eq("nombre", nombre_municipio).execute()
    if not res.data:
        print(f"    No encontrado en Supabase")
        return
    municipio_id = res.data[0]["id"]

    supabase.table("atmosfera").delete().eq("municipio_id", municipio_id).eq("año", año).eq("tipo", "historico").execute()

    datos = obtener_datos_año_completo(codigo_estacion, año)
    if not datos:
        print(f"    Sin datos")
        return

    temps, humedades = [], []
    dias_bajo_rocio_cfi = 0
    dias_bajo_rocio_df = 0
    dias_niebla = 0
    awgp_valores = []
    dias_validos = 0

    for dia in datos:
        if not isinstance(dia, dict):
            continue

        t_med = parsear_numero(dia.get("tmed"))
        t_min = parsear_numero(dia.get("tmin"))
        hr = parsear_numero(dia.get("hrMedia"))
        hr_max = parsear_numero(dia.get("hrMax"))

        if t_med is not None:
            temps.append(t_med)
        if hr is not None:
            humedades.append(hr)

        if t_min is not None and hr is not None:
            td_dia = punto_de_rocio(t_min, hr)
            if t_min <= td_dia + 1:
                dias_bajo_rocio_cfi += 1
            if t_min <= td_dia:
                dias_bajo_rocio_df += 1
            awgp_dia = calcular_awgp(t_med if t_med else t_min, hr)
            awgp_valores.append(awgp_dia)
            dias_validos += 1

        if hr_max is not None and hr_max > 95:
            dias_niebla += 1

    if not temps or not humedades:
        print(f"    Datos insuficientes")
        return

    temp_media_anual = round(sum(temps) / len(temps), 2)
    humedad_media_anual = round(sum(humedades) / len(humedades), 2)
    td = punto_de_rocio(temp_media_anual, humedad_media_anual)
    cfi = round(dias_bajo_rocio_cfi / dias_validos, 3) if dias_validos else None
    dew_frequency = round(dias_bajo_rocio_df / dias_validos, 3) if dias_validos else None
    fce = round(dias_niebla / len(datos), 3) if datos else None
    awgp_medio = round(sum(awgp_valores) / len(awgp_valores), 3) if awgp_valores else None

    supabase.table("atmosfera").insert({
        "municipio_id": municipio_id,
        "año": año,
        "tipo": "historico",
        "temp_media_c": temp_media_anual,
        "humedad_relativa_pct": humedad_media_anual,
        "punto_rocio_c": td,
        "diferencia_temp_rocio": round(temp_media_anual - td, 2),
        "cfi": cfi,
        "dew_frequency": dew_frequency,
        "fce": fce,
        "awgp": awgp_medio,
        "fuente": "AEMET OpenData"
    }).execute()

    print(f"    OK T:{temp_media_anual}°C HR:{humedad_media_anual}% CFI:{cfi} FCE:{fce}")


def procesar_año(año):
    print(f"\n{'='*50}")
    print(f"AÑO {año}")
    print(f"{'='*50}")

    municipios_lista = list(MUNICIPIO_ESTACION.items())
    for i, (municipio, estacion) in enumerate(municipios_lista):
        procesar_municipio(municipio, estacion, año)
        if i < len(municipios_lista) - 1:
            time.sleep(12)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        AÑO = int(sys.argv[1])
        procesar_año(AÑO)
    else:
        AÑO = 2025
        procesar_año(AÑO)
