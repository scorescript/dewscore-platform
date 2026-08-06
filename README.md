# DewScore: A Geospatial Platform for Atmospheric Water Harvesting Potential Assessment
https://doi.org/10.5281/zenodo.21816513
 
## Overview

DewScore is a geospatial decision support system (GDSS) for evaluating the 
territorial potential of atmospheric water harvesting (AWH) technologies at 
municipal scale. It integrates official meteorological data with a psychrometric 
engine to produce four physically grounded indices: CFI, DF, FCE and AWGP.

The platform is publicly available at https://dewscore.eu

## Indices

| Index | Full name | Description |
|-------|-----------|-------------|
| CFI | Condensation Feasibility Index | Fraction of days where T_min ≤ T_d + 1°C |
| DF | Dew Frequency | Fraction of days with natural dew occurrence |
| FCE | Fog Collection Efficiency | Fraction of days with RH_max > 95% |
| AWGP | Atmospheric Water Generation Potential | Absolute moisture density (g/m³) |

All indices are computed using the Magnus–Tetens approximation.


## Data Sources

| Source | Variable | Period |
|--------|----------|--------|
| AEMET OpenData | Daily temperature, humidity | 2008–2025 |
| PVGIS (JRC) | Annual solar irradiation | Climatological mean |
| Open-Meteo | Monthly solar radiation, wind | 2008–2025 |
| IGN | Municipal boundaries (PostGIS) | 2024 |

## Study Area

Canary Islands, Spain — 88 municipalities across 7 islands. 
Selected as a representative case of arid insular territory with 
high atmospheric water harvesting potential.

## Repository Structure

dewscore-paper/
├── scripts/
│ ├── procesar_atmosfera.py # CFI, DF, FCE, AWGP computation (AEMET)
│ ├── procesar_pvgis.py # Solar irradiation retrieval (PVGIS)
│ └── procesar_solar_mensual.py # Monthly solar + wind data (Open-Meteo)
├── requirements.txt
├── LICENSE
└── README.md


## Reproducibility

### Requirements

pip install -r requirements.txt


### Environment variables

Create a `.env` file with your credentials:

SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
AEMET_API_KEY=your_aemet_key


AEMET API keys are available free of charge at: 
https://opendata.aemet.es/centrodedescargas/altaUsuario

### Run

python scripts/procesar_atmosfera.py 2025
python scripts/procesar_pvgis.py
python scripts/procesar_solar_mensual.py


## Citation

If you use this code or methodology in your research, please cite:

scorescript. (2026). scorescript/dewscore-platform: v1.0.0 (Version DewScore) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.21816513


## License

MIT License — see [LICENSE](LICENSE) for details.
