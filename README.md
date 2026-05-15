# Foundational Economy Index (FEI) — Marginal Municipalities, Piedmont

A data-driven framework to map and assess foundational service provision in marginal territories, using Google Maps Places API as a dynamic proxy for physical infrastructure.

> Based on: *Revitalizing Marginal Areas: A Foundational Economy Approach* (under review, Statistics and Economics for Policymakers Studies)

---

## Overview

This repository provides the methodology, sample data, and analytical code to replicate the **Foundational Economy Index (FEI)** for marginal municipalities. The FEI captures the territorial distribution and density of essential services — healthcare, education, food access, transport, civic infrastructure, and more — using geolocated Points of Interest (POIs) collected via the Google Maps Places API.

The framework was developed and tested on **372 marginal municipalities in the Piedmont region (Italy)**, classified as intermediate, peripheral, or ultra-peripheral under the National Strategy for Inner Areas (SNAI, 2021–2027).

---

## Repository Structure

```
foundational-economy-piedmont/
│
├── README.md
│
├── data/
│   └── sample_municipalities.csv        # Sample of 2 anonymised municipalities
│
├── collection/
│   └── google_places_collector.py       # Data collection script (Google Maps API)
│
├── analysis/
│   ├── fei_computation.py               # FEI and FES calculation
│   ├── spatial_regression.py            # OLS + SLM + SEM + SDM + impacts
│   └── clustering.py                    # Cosine similarity + hierarchical clustering
│
└── figures/
    ├── fei_distribution.svg             # FEI score distribution
    └── moran_scatter.svg                # Moran's I scatter plot
```

---

## Data Collection

POIs are collected using the **Google Maps Places API (Nearby Search)**. For each municipality, the script queries all available service types within a configurable radius (default: 5 km) around the municipal centroid.

### Input format

Your input CSV must contain at least:

| Column | Description |
|--------|-------------|
| `municipality` | Municipality name |
| `region` | Region name (e.g. `Piedmont`) |
| `latitude` | Centroid latitude (WGS84) |
| `longitude` | Centroid longitude (WGS84) |
| `snai_class` | SNAI classification (D, E, or F) |

### Running the collector

```python
# collection/google_places_collector.py

API_KEY    = "YOUR_GOOGLE_API_KEY"   # insert your key here
INPUT_CSV  = "data/your_municipalities.csv"
OUTPUT_XLS = "data/your_output.xlsx"
RADIUS_M   = 5000                    # search radius in metres
DELAY_SEC  = 0.2                     # pause between requests
```

```bash
python collection/google_places_collector.py
```

The script iterates over all Google Places categories, deduplicates results by `place_id`, and saves a flat Excel file with one row per POI. See `data/sample_municipalities.csv` for the expected output format.

> **Note:** A Google Cloud account with the Places API enabled is required. The API is billable beyond the free tier. See [Google Places API documentation](https://developers.google.com/maps/documentation/places/web-service).

---

## Sample Data

`data/sample_municipalities.csv` contains a small anonymised sample of two municipalities with their collected POIs. Column descriptions:

| Column | Description |
|--------|-------------|
| `municipality` | Municipality name |
| `name` | POI name |
| `formatted_address` | Full address |
| `place_id` | Unique Google Place ID |
| `latitude` / `longitude` | POI coordinates |
| `rating` | Google user rating (0–5) |
| `user_ratings_total` | Number of reviews |
| `types` | Comma-separated Google Places types (e.g. `pharmacy, health, store`) |
| `business_status` | `OPERATIONAL`, `CLOSED_TEMPORARILY`, etc. |
| `permanently_closed` | Boolean |

---

## Service Classification

Each POI is mapped to one of **8 foundational service categories** based on its Google Places `types` field:

| FE Domain | Category | Example Google types |
|-----------|----------|----------------------|
| **Material** | Food Access | `grocery_or_supermarket`, `bakery`, `meal_takeaway` |
| **Material** | Transportation | `bus_station`, `train_station`, `gas_station`, `transit_station` |
| **Material** | Bank & Postal | `bank`, `atm`, `post_office` |
| **Providential** | Health & Medicine | `hospital`, `pharmacy`, `doctor`, `dentist` |
| **Providential** | Education | `school`, `primary_school`, `secondary_school`, `university` |
| **Providential** | Civic Infrastructure | `city_hall`, `local_government_office`, `police`, `fire_station` |
| **Providential** | Social Hubs | `library`, `park`, `bar`, `cafe`, `church` |
| **Overlooked** | Cultural Necessities | `tourist_attraction`, `restaurant`, `lodging`, `museum` |

POIs tagged as `point_of_interest` or `establishment` only (without a more specific type) are excluded from the FEI computation.

---

## Formulas

### Economic Service Coverage (ESC)

Measures the breadth of service types offered by a single facility $s_i$:

$$ESC_{s_i} = \sum_{d \in \{FE, TE\}} \sum_{t_k \in d} \delta(t_k \in \text{types}_{s_i})$$

Where $\delta(\cdot) = 1$ if the service type $t_k$ is present in the POI's type list, $0$ otherwise.

### Foundational Economy Index (FEI)

Aggregates foundational service counts at the municipal level:

$$FEI_i = \sum_{c \in C} S_{i,c}$$

Where:
- $C$ = set of 8 foundational service categories
- $S_{i,c}$ = number of POIs of category $c$ in municipality $i$

### Foundational Economy Score (FES) — normalised

Min-max normalisation to $[0, 1]$ for cross-municipal comparison:

$$FES_i = \frac{FEI_i - \min(FEI)}{\max(FEI) - \min(FEI)}$$

---

## Spatial Analysis

Spatial autocorrelation and regression models are estimated using a **K-Nearest Neighbours spatial weights matrix** (k = 5, row-standardised).

```python
from libpysal.weights import KNN
from esda.moran import Moran

w = KNN.from_dataframe(gdf, k=5)
w.transform = 'r'
moran = Moran(gdf['FEI'], w)
```

Four models are estimated and compared:

| Model | Description |
|-------|-------------|
| OLS | Baseline ordinary least squares |
| SLM | Spatial Lag Model — spatial dependence in $y$ |
| SEM | Spatial Error Model — spatial dependence in $\varepsilon$ |
| SDM | Spatial Durbin Model — spatial lags in both $y$ and $X$ |

For SLM and SDM, **Direct, Indirect, and Total effects** are computed following LeSage & Pace (2009) using the spatial multiplier $(I - \rho W)^{-1}$.

### Robustness check

Moran's I is stable across spatial weights specifications:

| k | Moran's I | p-value |
|---|-----------|---------|
| 3 | 0.061 | 0.047 |
| 5 | 0.060 | 0.031 |
| 7 | 0.046 | 0.040 |

---

## Clustering

Municipalities are grouped by service profile similarity using **hierarchical agglomerative clustering** with cosine similarity and Ward's linkage:

```python
from sklearn.metrics.pairwise import cosine_similarity
from scipy.cluster.hierarchy import linkage, fcluster

sim_matrix = cosine_similarity(service_matrix)
Z = linkage(1 - sim_matrix, method='ward')
labels = fcluster(Z, t=20, criterion='distance')
```

Three clusters were identified (modularity = 0.62):
- **Cluster 1 — High Service**: diversified foundational infrastructure
- **Cluster 2 — Intermediate**: partial provision of essential services
- **Cluster 3 — Low Service**: structural under-provision, service deserts

---

## Validation

Google Maps POI counts are validated against official ASIA register data (ISTAT):

- **Spearman's ρ = 0.81** (p < 0.001) — strong monotonic correlation
- **R² = 0.64** on log-log regression — 64% of variance in registered firms explained by Google POI counts

---

## Dependencies

```
requests
pandas
openpyxl
tqdm
geopandas
libpysal
esda
spreg
scikit-learn
scipy
matplotlib
shapely
```

---

## How to Replicate

1. **Prepare your municipality list** with coordinates and SNAI classification
2. **Run the data collector** to gather POIs via Google Maps API
3. **Classify POIs** into the 8 foundational service categories
4. **Compute FEI and FES** for each municipality
5. **Run spatial regressions** (OLS → SLM → SEM → SDM)
6. **Cluster municipalities** by service profile

Each step corresponds to a script in the `analysis/` folder.

---

## Citation

If you use this methodology or data, please cite:

```
Varavallo, G., Barbera, F., Di Clemente, R. (under review).
Revitalizing Marginal Areas: A Foundational Economy Approach.
Statistics and Economics for Policymakers Studies.
```

---

## License

Data collected via Google Maps API is subject to [Google Maps Platform Terms of Service](https://cloud.google.com/maps-platform/terms). The sample data provided in this repository is anonymised and shared for reproducibility purposes only.

Code is released under the MIT License.

---

## Contact

For questions about the methodology, open an issue or contact the corresponding author at filippo.barbera@unito.it
