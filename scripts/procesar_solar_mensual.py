import requests
import os
import time
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

AÑOS = list(range(2008, 2026))


def obtener_datos_open_meteo(lat, lng, fecha_ini, fecha_fin):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": fecha_ini,
        "end_date": fecha_fin,
        "daily": "shortwave_radiation_sum,wind_speed_10m_max",
        "timezone": "Europe/Madrid"
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            print(f"    Error {r.status_code}: {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        print(f"    Error: {e}")
        return None


def agrupar_por_mes(daily_data, key):
    if not daily_data or "daily" not in daily_data:
        return {}
    fechas = daily_data["daily"].get("time", [])
    valores = daily_data["daily"].get(key, [])
    por_mes = {}
    for fecha, valor in zip(fechas, valores):
        if valor is None:
            continue
        mes = int(fecha.split("-")[1])
        por_mes.setdefault(mes, []).append(valor)
    return por_mes


def ya_existe(municipio_id, año):
    res = supabase.table("solar_mensual").select("id").eq("municipio_id", municipio_id).eq("año", año).limit(1).execute()
    return len(res.data) > 0


def procesar_municipio_año(municipio_id, nombre, lat, lng, año):
    if ya_existe(municipio_id, año):
        print(f"  ⏭ {nombre} {año} — ya existe")
        return

    fecha_ini = f"{año}-01-01"
    fecha_fin = f"{año}-12-31"

    print(f"  {nombre} — {año}...")

    datos = obtener_datos_open_meteo(lat, lng, fecha_ini, fecha_fin)
    if not datos:
        print(f"    Sin datos")
        return

    time.sleep(0.5)

    radiacion_por_mes = agrupar_por_mes(datos, "shortwave_radiation_sum")
    viento_por_mes = agrupar_por_mes(datos, "wind_speed_10m_max")

    filas = []
    for mes in range(1, 13):
        rad_vals = radiacion_por_mes.get(mes, [])
        viento_vals = viento_por_mes.get(mes, [])

        if not rad_vals:
            continue

        # Open-Meteo da radiación en MJ/m² → convertimos a kWh/m² (÷ 3.6)
        radiacion_kwh = round(sum(rad_vals) / 3.6, 2)
        radiacion_media_diaria = round(radiacion_kwh / len(rad_vals), 3)
        viento_max = round(max(viento_vals), 1) if viento_vals else None
        viento_medio = round(sum(viento_vals) / len(viento_vals), 1) if viento_vals else None

        filas.append({
            "municipio_id": municipio_id,
            "año": año,
            "mes": mes,
            "radiacion_kwh_m2": radiacion_kwh,
            "radiacion_media_diaria": radiacion_media_diaria,
            "viento_max_kmh": viento_max,
            "viento_medio_kmh": viento_medio,
            "calima_media": None,
            "calima_max": None,
            "fuente": "Open-Meteo"
        })

    if filas:
        supabase.table("solar_mensual").upsert(
            filas,
            on_conflict="municipio_id,año,mes"
        ).execute()
        print(f"    OK — {len(filas)} meses")


def main():
    municipios = supabase.table("municipios").select("id, nombre, lat, lng").execute().data
    print(f"Procesando {len(municipios)} municipios × {len(AÑOS)} años\n")

    for m in municipios:
        if not m["lat"] or not m["lng"]:
            print(f"  Sin coordenadas: {m['nombre']}")
            continue
        for año in AÑOS:
            procesar_municipio_año(m["id"], m["nombre"], m["lat"], m["lng"], año)

    print("\nProceso completo.")


if __name__ == "__main__":
    main()
