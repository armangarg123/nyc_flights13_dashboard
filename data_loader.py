"""
data_loader.py  —  pre-computes every DataFrame used across all tabs.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as scipy_stats

_HERE = Path(__file__).parent
_DATA = _HERE / "data"

def _load(filename):
    local = _DATA / filename
    if local.exists():
        return pd.read_csv(local)
    url = ("https://raw.githubusercontent.com/kostis-christodoulou/e628/main"
           f"/data/nycflights13/{filename}")
    print(f"  Fetching {filename} from GitHub …")
    return pd.read_csv(url)

print("Loading nycflights13 …")
flights  = _load("flights.csv")
airlines = _load("airlines.csv")
airports = _load("airports.csv")
planes   = _load("planes.csv")
weather  = _load("weather.csv")

MONTH_MAP   = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
MONTH_ORDER = list(MONTH_MAP.values())
ORIGINS     = ["JFK","LGA","EWR"]

AIRPORT_FULL = {"JFK":"John F. Kennedy Intl (JFK)",
                "LGA":"LaGuardia (LGA)",
                "EWR":"Newark Liberty Intl (EWR)"}

flights["is_cancelled"] = flights["dep_time"].isna().astype(int)
airport_name = airports.set_index("faa")["name"].to_dict()

# ── Manufacturer cleaning ─────────────────────────────────────────────────────
planes["manufacturer"] = planes["manufacturer"].str.upper().str.strip()
_cond = [
    planes["manufacturer"].str.contains("AIRBUS",             na=False),
    planes["manufacturer"].str.contains("BOEING",             na=False),
    planes["manufacturer"].str.contains("MCDONNELL|DOUGLAS",  na=False, regex=True),
    planes["manufacturer"].str.contains("BOMBARDIER|CANADAIR", na=False, regex=True),
    planes["manufacturer"].str.contains("EMBRAER",            na=False),
    planes["manufacturer"].str.contains("CESSNA",             na=False),
]
_choices = ["AIRBUS","BOEING","MCDONNELL DOUGLAS","BOMBARDIER","EMBRAER","CESSNA"]
planes["manufacturer_clean"] = np.select(_cond, _choices, default=planes["manufacturer"])
_small = planes["manufacturer_clean"].value_counts()
_small = _small[_small < 10].index
planes["manufacturer_final"] = planes["manufacturer_clean"].replace(_small, "Other")
top_manufacturers = planes["manufacturer_final"].value_counts().head(10).index.tolist()

# ── Weather join ──────────────────────────────────────────────────────────────
weather["wind_speed"] = weather["wind_speed"].where(weather["wind_speed"] <= 100)
flights_weather = flights.merge(
    weather, on=["year","month","day","hour","origin"], how="left"
)
flights_weather["temp_bin"]  = pd.cut(flights_weather["temp"], bins=range(0,110,10))
flights_weather["wind_bin"]  = pd.cut(flights_weather["wind_speed"], bins=8)
flights_weather["visib_bin"] = pd.cut(
    flights_weather["visib"], bins=[0,2,5,10,15],
    labels=["Poor (0-2)","Fair (2-5)","Good (5-10)","Excellent (10+)"]
)

# ── Route-adjusted delay ──────────────────────────────────────────────────────
route_delays = (
    flights.groupby(["origin","dest"])
    .agg(avg_delay=("arr_delay","mean"), num_flights=("flight","count"))
    .reset_index().query("num_flights > 50")
)
flights_with_route = flights.merge(
    route_delays[["origin","dest","avg_delay"]].rename(columns={"avg_delay":"route_avg_delay"}),
    on=["origin","dest"], how="left"
).merge(airlines, on="carrier")

carrier_delays_adjusted = (
    flights_with_route.groupby("name")
    .agg(avg_route_difficulty=("route_avg_delay","mean"), num_flights=("flight","count"))
    .round(2).reset_index().sort_values("avg_route_difficulty")
)
carrier_delays_naive = (
    flights.merge(airlines, on="carrier").groupby("name")
    .agg(avg_arr_delay=("arr_delay","mean"), num_flights=("flight","count"))
    .round(2).reset_index().sort_values("avg_arr_delay")
)

# ── Plane-flights join ────────────────────────────────────────────────────────
flights_planes = flights.merge(
    planes[["tailnum","year","seats","manufacturer_final"]]
    .rename(columns={"year":"year_manufactured"}),
    on="tailnum", how="left"
)
flights_planes["plane_age"] = 2013 - flights_planes["year_manufactured"]
flights_planes_clean = flights_planes.query("plane_age >= 0 and plane_age <= 50").copy()

# ── Tab 1: Best Airport metrics ───────────────────────────────────────────────
def compute_airport_metrics():
    rows = []
    for org in ORIGINS:
        f  = flights[flights["origin"] == org]
        fw = flights_weather[flights_weather["origin"] == org]
        fp = flights_planes[flights_planes["origin"] == org]
        rows.append({
            "Airport":               org,
            "Full Name":             AIRPORT_FULL[org],
            "Avg Dep Delay (min)":   round(f["dep_delay"].mean(), 2),
            "Cancellation Rate (%)": round(f["is_cancelled"].mean() * 100, 2),
            "Destinations":          int(f["dest"].nunique()),
            "Fleet Variety (seat σ)":round(fp["seats"].std(), 2),
            "Weather Delay (min)":   round(fw[fw["precip"]>0]["dep_delay"].mean(), 2),
        })
    return pd.DataFrame(rows).set_index("Airport")

airport_metrics_df = compute_airport_metrics()

# ── Tab 2: Best Carrier metrics ───────────────────────────────────────────────
def compute_carrier_metrics():
    rows = []
    for _, al in airlines.iterrows():
        carrier, name = al["carrier"], al["name"]
        f  = flights[flights["carrier"] == carrier]
        if f.empty:
            continue
        fp = flights_planes[flights_planes["carrier"] == carrier]
        rows.append({
            "Carrier":                name,
            "Route-Adj Delay (min)":  round(flights_with_route[flights_with_route["carrier"]==carrier]["route_avg_delay"].mean(), 2),
            "Cancellation Rate (%)":  round(f["is_cancelled"].mean() * 100, 2),
            "Destinations":           int(f["dest"].nunique()),
            "Fleet Variety (seat σ)": round(fp["seats"].std(), 2) if fp["seats"].notna().any() else 0,
            "Avg Plane Age (yrs)":    round(fp["plane_age"].mean(), 2) if fp["plane_age"].notna().any() else np.nan,
        })
    return pd.DataFrame(rows).set_index("Carrier")

carrier_metrics_df = compute_carrier_metrics()

# ── Tab 3: Cancellations ──────────────────────────────────────────────────────
cancelled_by_month = (
    flights
    .groupby(["origin","dest","month"])
    .agg(total=("flight","count"), cancelled=("is_cancelled","sum"))
    .assign(cancel_rate=lambda x: 100 * x["cancelled"] / x["total"])
    .reset_index()
    .assign(month_name=lambda x: x["month"].map(MONTH_MAP))
)
carrier_cancel = (
    flights.merge(airlines, on="carrier")
    .groupby(["dest","origin","month","name"])
    .agg(total=("flight","count"), cancelled=("is_cancelled","sum"))
    .assign(cancel_pct=lambda x: 100 * x["cancelled"] / x["total"])
    .reset_index()
)
all_dests_cancel = sorted(flights["dest"].unique())

# ── Tab 4b: Time of Day ───────────────────────────────────────────────────────
flights["time_of_day"] = pd.cut(
    flights["hour"],
    bins=[0,6,12,17,21,24],
    labels=["Early Morning","Morning","Afternoon","Evening","Night"],
    include_lowest=True, ordered=True,
)
TOP5_CARRIERS = flights["carrier"].value_counts().head(5).index.tolist()

time_delays_overall = (
    flights.dropna(subset=["dep_delay"])
    .groupby("time_of_day", observed=True)
    .agg(avg_dep_delay=("dep_delay","mean"))
    .reset_index()
    .assign(time_of_day=lambda x: x["time_of_day"].astype(str))
)
time_delays_by_carrier = (
    flights.dropna(subset=["dep_delay"])
    .query("carrier in @TOP5_CARRIERS")
    .merge(airlines, on="carrier")
    .groupby(["time_of_day","name"], observed=True)
    .agg(avg_dep_delay=("dep_delay","mean"))
    .reset_index()
    .assign(time_of_day=lambda x: x["time_of_day"].astype(str))
)

# ── Tab 4e: Delay Recovery ────────────────────────────────────────────────────
valid_flights = flights.dropna(subset=["dep_delay","arr_delay","air_time"]).copy()
valid_flights["delay_recovered"] = valid_flights["dep_delay"] - valid_flights["arr_delay"]
valid_flights["duration_category"] = pd.cut(
    valid_flights["air_time"], bins=[0,60,120,180,360],
    labels=["Very Short (<1hr)","Short (1-2hr)","Medium (2-3hr)","Long (3hr+)"]
)
recovery_by_duration = (
    valid_flights.groupby("duration_category", observed=True)
    .agg(avg_dep_delay=("dep_delay","mean"),
         avg_arr_delay=("arr_delay","mean"),
         avg_recovered=("delay_recovered","mean"))
    .round(2).reset_index()
)

# ── Tab 4f: CI by airport ─────────────────────────────────────────────────────
airport_ci_rows = []
for org in ORIGINS:
    grp  = flights.loc[flights["origin"]==org, "dep_delay"].dropna()
    mean = grp.mean()
    se   = grp.std() / np.sqrt(len(grp))
    t    = scipy_stats.t.ppf(0.975, len(grp)-1)
    airport_ci_rows.append({"origin":org,"mean":mean,
                             "ci_lower":mean-t*se,"ci_upper":mean+t*se,"error":t*se})
airport_ci_df = pd.DataFrame(airport_ci_rows)

# ── Tab 5: Popular Carrier ────────────────────────────────────────────────────
def top_dests_for_origin(origin="ALL", n=5):
    f = flights if origin=="ALL" else flights[flights["origin"]==origin]
    return (
        f.groupby("dest").size().reset_index(name="n")
        .sort_values("n", ascending=False).head(n)["dest"].tolist()
    )

def carrier_share(origin, dest_code):
    f = flights if origin=="ALL" else flights[flights["origin"]==origin]
    if dest_code != "ALL":
        f = f[f["dest"]==dest_code]
    return (
        f.merge(airlines, on="carrier")
        .groupby(["carrier","name"]).size()
        .reset_index(name="num_flights")
        .assign(pct=lambda x: 100*x["num_flights"]/x["num_flights"].sum())
        .sort_values("num_flights", ascending=False)
    )

# ── Tab 6: Fleet ──────────────────────────────────────────────────────────────
def fleet_data(min_seats=50):
    pf = (
        flights.groupby("tailnum").size().reset_index(name="num_flights")
        .merge(
            flights_planes[["tailnum","year_manufactured","manufacturer_final","seats"]]
            .drop_duplicates("tailnum"), on="tailnum", how="left"
        )
        .dropna(subset=["seats"]).query("seats >= @min_seats")
        .sort_values("num_flights", ascending=False)
    )
    if pf.empty:
        return None, pd.DataFrame(), pd.DataFrame()
    row     = pf.iloc[0]
    tailnum = row["tailnum"]
    dests   = (
        flights[flights["tailnum"]==tailnum]
        .groupby("dest").size().reset_index(name="num_flights")
        .assign(airport_name=lambda x: x["dest"].map(airport_name).fillna(x["dest"]))
        .sort_values("num_flights", ascending=False)
    )
    eligible = (
        flights_planes.dropna(subset=["seats"]).query("seats >= @min_seats")
        [["tailnum","manufacturer_final"]].drop_duplicates()
    )
    mfr_time = (
        flights.merge(eligible, on="tailnum", how="inner")
        .query("manufacturer_final in @top_manufacturers")
        .groupby(["month","manufacturer_final"]).size()
        .reset_index(name="num_flights")
        .assign(month_name=lambda x: x["month"].map(MONTH_MAP))
    )
    return row, dests, mfr_time

print("✅  Data loading complete.")
