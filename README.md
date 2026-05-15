# Foundational Economy Toolkit

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green?logo=python)](https://www.python.org/)
[![Google Maps API](https://img.shields.io/badge/Google_Maps-Places_API-4285F4?logo=googlemaps&logoColor=white)](https://developers.google.com/maps/documentation/places/web-service)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-0.14%2B-blue)](https://geopandas.org/)
[![PySAL](https://img.shields.io/badge/PySAL-libpysal-orange)](https://pysal.org/)
[![Status](https://img.shields.io/badge/Paper-Under_Review-yellow)](https://www.mdpi.com/journal/stats)

---

## Overview

This repository provides the methodology, sample data, and analytical code behind the **Foundational Economy Index (FEI)** - a data-driven framework to map and assess the availability of essential services in marginal territories.

> **Varavallo, G., Barbera, F., Di Clemente, R. (under review).**
> *Revitalizing Marginal Areas: A Foundational Economy Approach.*


The FEI captures the territorial distribution and density of foundational services: healthcare, education, food access, transport, civic infrastructure, and more, using geolocated Points of Interest (POIs) collected via the **Google Maps Places API** as a dynamic, scalable proxy for physical infrastructure.

The framework was developed and tested on **372 marginal municipalities in the Piedmont region (Italy)**, classified as intermediate, peripheral, or ultra-peripheral under the National Strategy for Inner Areas (SNAI, 2021–2027). The analytical pipeline is designed to be **replicable in any territorial context** where Google Maps API coverage is available.

---

## Maps & Figures

### SNAI Inner Areas Classification — Italy and Piedmont Region

![SNAI Classification — Italy](figures/inner_areas_classification_maps_rev2.svg)

*Italian municipalities by SNAI inner areas classification (2021–2027). Source: SNAI (2021–2027) — elaboration by Varavallo, G.*

---

![SNAI Classification — Piedmont](figures/region_inner_areas_classification_maps.svg)

*Spatial distribution of the 372 marginal municipalities in the Piedmont region selected for analysis (SNAI classes D, E, F). Source: SNAI (2021–2027), ISTAT (2022) — elaboration by Varavallo,G.*

---

---

## Data Collection

POIs are collected using the **Google Maps Places API (Nearby Search)**. For each municipality, the script queries all available service types within a configurable radius around the municipal centroid, deduplicates results by `place_id`, and outputs a flat Excel file.

### Input format

Your input CSV must contain at least:

| Column | Description |
|--------|-------------|
| `municipality` | Municipality name |
| `region` | Region name (e.g. `Piedmont`) |
| `latitude` | Centroid latitude — WGS84 |
| `longitude` | Centroid longitude — WGS84 |
| `snai_class` | SNAI classification (`D`, `E`, or `F`) |

### Running the collector

```python
# collection/google_places_collector.py

API_KEY   = "YOUR_GOOGLE_API_KEY"         # insert your Google Maps API key
INPUT_CSV = "data/your_municipalities.csv"
RADIUS_M  = 5000                          # search radius in metres (default: 5 km)
```

```bash
python collection/google_places_collector.py
```

> **Note:** A Google Cloud account with the Places API enabled is required. See [Google Places API documentation](https://developers.google.com/maps/documentation/places/web-service) for setup and billing details.

---

## Service Classification

Each POI is assigned to one of **8 foundational service categories** based on its Google Places `types` field, following the three-domain Foundational Economy framework (Bentham et al., 2013):

| FE Domain | Category | Example Google `types` |
|-----------|----------|------------------------|
| **Material** | Food Access | `grocery_or_supermarket`, `bakery`, `meal_takeaway` |
| **Material** | Transportation | `bus_station`, `train_station`, `gas_station`, `transit_station` |
| **Material** | Bank & Postal | `bank`, `atm`, `post_office` |
| **Providential** | Health & Medicine | `hospital`, `pharmacy`, `doctor`, `dentist` |
| **Providential** | Education | `school`, `primary_school`, `secondary_school`, `university` |
| **Providential** | Civic Infrastructure | `city_hall`, `local_government_office`, `police`, `fire_station` |
| **Providential** | Social Hubs | `library`, `park`, `bar`, `cafe`, `church` |
| **Overlooked** | Cultural Necessities | `tourist_attraction`, `restaurant`, `lodging`, `museum` |

POIs tagged only as `point_of_interest` or `establishment` (without a more specific type) are excluded from the FEI computation.

---

## Formulas

### Economic Service Coverage (ESC)

Measures the breadth of service types provided by a single facility $s_i$, distinguishing between Foundational Economy (FE) and Tradeable Economy (TE) domains:

$$ESC_{s_i} = \sum_{d \in \{FE,\ TE\}} \sum_{t_k \in d} \delta\bigl(t_k \in \text{types}_{s_i}\bigr)$$

where $\delta(\cdot) = 1$ if type $t_k$ is present in the POI's type list, $0$ otherwise.

### Foundational Economy Index (FEI)

Aggregates foundational service counts at the municipal level as an unweighted sum across all categories:

$$FEI_i = \sum_{c \in C} S_{i,c}$$

where $C$ is the set of 8 foundational service categories and $S_{i,c}$ is the number of POIs of category $c$ present in municipality $i$.

### Foundational Economy Score (FES)

Min-max normalisation to $[0, 1]$ for cross-municipal comparison:

$$FES_i = \frac{FEI_i - \min(FEI)}{\max(FEI) - \min(FEI)}$$

---


## Clustering

Municipalities are grouped by service profile similarity using **hierarchical agglomerative clustering** with cosine similarity and Ward's linkage (modularity = 0.62):

```python
from sklearn.metrics.pairwise import cosine_similarity
from scipy.cluster.hierarchy import linkage, fcluster

sim_matrix = cosine_similarity(service_matrix)
Z = linkage(1 - sim_matrix, method='ward')
labels = fcluster(Z, t=20, criterion='distance')
```

Three clusters were identified:

| Cluster | Label | Description |
|---------|-------|-------------|
| 1 | **High Service** | Diversified foundational infrastructure |
| 2 | **Intermediate** | Partial provision of essential services |
| 3 | **Low Service** | Structural under-provision; service deserts |

---

## Validation

Google Maps POI counts are validated against the official ISTAT ASIA register of active firms:

- **Spearman's ρ = 0.81** (p < 0.001) — strong monotonic correlation
- **R² = 0.64** on log-log regression

---

## Data Sources

| Dimension | Variables | Source | Year |
|-----------|-----------|--------|------|
| Geography | Altimetric zone, forest cover | ISTAT, MIPAAF | 2020–2022 |
| Demography | Population, population change, foreign residents | ISTAT | 2011–2022 |
| Economy | Active firms, employees by sector, unemployment | ISTAT ASIA Register | 2020–2022 |
| Territory | SNAI classification (D → F) | SNAI | 2021–2027 |
| Services | Geolocated POIs | Google Maps Places API | 2023–2024 |

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.8+ | Data analysis and scripting |
| `requests` / `pandas` | API data collection and processing |
| `geopandas` | Geospatial data manipulation |
| `libpysal` / `esda` / `spreg` | Spatial weights, Moran's I, spatial regression |
| `scikit-learn` / `scipy` | Cosine similarity, hierarchical clustering |
| `matplotlib` | Figures and diagnostics |
| QGIS | Cartographic processing and map production |

---

## Citation

```bibtex
@article{varavallo_barbera_diclemente_underreview,
  author  = {Varavallo, Giuseppe and Barbera, Filippo and Di Clemente, Riccardo},
  title   = {Revitalizing Marginal Areas: A Foundational Economy Approach},
  journal = {Statistics and Economics for Policymakers Studies},
  year    = {under review},
  note    = {Manuscript SEPS-D-25-03080}
}
```

---

## Authors

**Giuseppe Varavallo** — Department of Cultures, Politics and Society & Department of Economics and Statistics "Cognetti de Martiis", University of Turin
✉ giuseppe.varavallo@unito.it

**Filippo Barbera** — Department of Cultures, Politics and Society, University of Turin & Collegio Carlo Alberto
✉ filippo.barbera@unito.it

**Riccardo Di Clemente** — Northeastern University London, Complex Connections Lab & ISI Foundation, Turin
✉ r.diclemente@northeastern.ac.uk

---
## Repository Structure

```
Foundational-Economy-Toolkit/
│
├── README.md
│
├── data/
│   └── sample_municipalities.csv        # Anonymised sample (2 municipalities)
│
├── collection/
│   └── google_places_collector.py       # Google Maps Places API data collector
│
└── figures/
    ├── inner_areas_classification_maps_rev2.svg
    └── region_inner_areas_classification_maps.svg
```

## License

Code: [MIT License](LICENSE).
Data and figures: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
POI data collected via Google Maps API is subject to [Google Maps Platform Terms of Service](https://cloud.google.com/maps-platform/terms) and is shared here for reproducibility purposes only.
