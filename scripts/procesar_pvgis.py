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


def obtener_radiacion_pvgis(lat, lng):
    url = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"
    params = {
        "lat": lat,
        "lon": lng,
        "peakpower": 1,
        "loss": 14,
        "outputformat": "json",
        "raddatabase": "PVGIS-SARAH2"
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            print(f"    Error PVGIS: {response.status_code}")
            return None
        data = response.json()
        irrad = data.get("outputs", {}).get("totals", {}).get("fixed", {}).get("H(i)_y", None)
        return round(irrad, 2) if irrad else None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def procesar_radiacion():
    # Solo procesa municipios que no tienen radiación todavía
    municipios = supabase.table("municipios").select("id, nombre, lat, lng, radiacion_solar_kwh").execute()

    pendientes = [m for m in municipios.data if not m.get("radiacion_solar_kwh")]
    ya_tienen = len(municipios.data) - len(pendientes)

    print(f"Total municipios: {len(municipios.data)}")
    print(f"Ya tienen radiación: {ya_tienen}")
    print(f"Pendientes: {len(pendientes)}\n")

    for m in pendientes:
        nombre = m["nombre"]
        lat = m["lat"]
        lng = m["lng"]

        if not lat or not lng:
            print(f"  ⚠️ Sin coordenadas: {nombre}")
            continue

        print(f"  {nombre} ({lat}, {lng})...")
        radiacion = obtener_radiacion_pvgis(lat, lng)

        if radiacion:
            # Guardar en municipios — permanente, no se borra al reprocesar años
            supabase.table("municipios").update({
                "radiacion_solar_kwh": radiacion
            }).eq("id", m["id"]).execute()
            print(f"    OK: {radiacion} kWh/m²/año")
        else:
            print(f"    Sin datos")

        time.sleep(1)

    print("\nProceso completo.")


if __name__ == "__main__":
    procesar_radiacion()
