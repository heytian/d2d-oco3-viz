import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import duckdb
import os

#file path for local testing of parquet
PARQUET_DIR = "/Users/heyutian/Downloads/oco3_parquet"
CO2_PARQUET = os.path.join(PARQUET_DIR, "co2_sam.parquet")
SIF_PARQUET = os.path.join(PARQUET_DIR, "sif_sam.parquet")

#C40 cities from Abhishek's 2025 paper
C40_CITIES_ = {
    "Johannesburg", "Cape Town", "Nairobi", "Durban",
    "Mumbai", "Kolkata", "New Delhi", "Dubai", "Dhaka", "Karachi", "Amman", "Chennai",
    "Rio de Janeiro", "Buenos Aires", "Sao Paulo", "Lima", "Santiago",
    "Mexico City", "Guadalajara",
    "Hangzhou", "Wuhan", "Qingdao", "Dalian", "Chengdu",
    "Tokyo", "Seoul", "Melbourne", "Sydney", "Hanoi",
    "Paris", "Istanbul", "Rome", "Milan", "Barcelona", "London", "Athens",
    "Tel Aviv-Yafo", "Madrid", "Rotterdam",
    "Los Angeles", "New York", "Washington DC", "San Francisco", "Houston",
    "Seattle", "Miami", "Montreal", "Boston", "Portland", "Chicago",
    "Phoenix", "Vancouver", "Philadelphia", "Toronto",
}

# Olympic host cities
OLYMPIC_CITIES_ = {
    "Athens", "Paris", "St. Louis", "London", "Stockholm", "Antwerp", "Chamonix", "St. Moritz",
    "Amsterdam", "Lake Placid", "Los Angeles", "Garmisch-Partenkirchen", "Berlin", "Oslo",
    "Helsinki", "Cortina d'Ampezzo", "Melbourne", "Squaw Valley", "Rome", "Innsbruck", "Tokyo",
    "Grenoble", "Mexico City", "Sapporo", "Munich", "Montreal", "Moscow", "Sarajevo", "Calgary",
    "Seoul", "Albertville", "Barcelona", "Lillehammer", "Atlanta", "Nagano", "Sydney", "Salt Lake City", "Turin",
    "Beijing", "Vancouver", "Sochi", "Rio de Janeiro", "Pyeongchang", "Milano Cortina"
}

def duck_query(sql):
    con = duckdb.connect()
    df = con.execute(sql).df()
    con.close()
    return df

all_cities_in_db = set(duck_query(f"""
    SELECT DISTINCT city FROM read_parquet('{CO2_PARQUET}')
""")['city'].tolist())

C40_CITIES = C40_CITIES_ & all_cities_in_db
OLYMPIC_CITIES = OLYMPIC_CITIES_ & all_cities_in_db

SEASON_CASE = """CASE
    WHEN latitude BETWEEN -20 AND 20 AND EXTRACT(MONTH FROM datetime) BETWEEN 5 AND 10 THEN 'Tropical Wet'
    WHEN latitude BETWEEN -20 AND 20 THEN 'Tropical Dry'
    WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime) IN (12,1,2) THEN 'Winter (North)'
    WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime) IN (3,4,5) THEN 'Spring (North)'
    WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime) IN (6,7,8) THEN 'Summer (North)'
    WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime) IN (9,10,11) THEN 'Autumn (North)'
    WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime) IN (12,1,2) THEN 'Summer (South)'
    WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime) IN (3,4,5) THEN 'Autumn (South)'
    WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime) IN (6,7,8) THEN 'Winter (South)'
    WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime) IN (9,10,11) THEN 'Spring (South)'
    ELSE 'Other'
END"""

HOUR_CASE = """CASE
    WHEN EXTRACT(HOUR FROM local_time) < 6  THEN 'Night'
    WHEN EXTRACT(HOUR FROM local_time) < 12 THEN 'Morning'
    WHEN EXTRACT(HOUR FROM local_time) < 18 THEN 'Afternoon'
    ELSE 'Evening'
END"""

bounds = duck_query(f"""
    SELECT
        MIN(EXTRACT(YEAR FROM datetime))::int AS year_min,
        MAX(EXTRACT(YEAR FROM datetime))::int AS year_max,
        MIN(population)::int AS pop_min,
        MAX(population)::int AS pop_max
    FROM read_parquet('{CO2_PARQUET}')
    WHERE datetime IS NOT NULL
""").iloc[0]

year_min, year_max = int(bounds.year_min), int(bounds.year_max)
pop_min,  pop_max  = int(bounds.pop_min),  int(bounds.pop_max)

seasons = sorted(duck_query(f"""
    SELECT DISTINCT {SEASON_CASE} AS s FROM read_parquet('{CO2_PARQUET}')
    WHERE datetime IS NOT NULL ORDER BY 1
""")['s'].tolist())

times_of_day = sorted(duck_query(f"""
    SELECT DISTINCT {HOUR_CASE} AS t FROM read_parquet('{CO2_PARQUET}')
    WHERE local_time IS NOT NULL ORDER BY 1
""")['t'].tolist())

def fmt_pop(v):
    if v >= 1_000_000: return f"{v/1e6:.0f}M"
    if v >= 1_000:     return f"{v/1e3:.0f}K"
    return str(int(v))

def make_marks(mn, mx, fmt=str):
    mid = (mn + mx) // 2
    return {mn: fmt(mn), mid: fmt(mid), mx: fmt(mx)}

app = dash.Dash(__name__)
server = app.server

ROW = {"display": "flex", "alignItems": "center", "margin": "3px 10px"}
LBL = {"marginRight": "8px", "width": "115px", "fontWeight": "bold", "fontSize": "12px", "flexShrink": "0"}

PERCENTILE_OPTIONS = [
    {"label": "15%", "value": 15},
    {"label": "20%", "value": 20},
    {"label": "30%", "value": 30},
    {"label": "45%", "value": 45}
]

app.layout = html.Div([
    dcc.Store(id="dark-mode-store", data=False),
    dcc.Graph(id="quadrant-plot", style={"height": "calc(100vh - 180px)", "minHeight": "400px"}, config={"responsive": True}),
    html.Div([
        html.Div([
            html.Div([
                html.Label("Year range", style=LBL),
                html.Div(dcc.RangeSlider(id="year-slider", min=year_min, max=year_max,
                    value=[year_min, year_max], marks=make_marks(year_min, year_max),
                    step=1, tooltip={"placement": "bottom", "always_visible": False}, allowCross=False,
                ), style={"width": "240px"}),
            ], style=ROW),
            html.Div([
                html.Label("Population", style=LBL),
                html.Div(dcc.RangeSlider(id="population-slider", min=pop_min, max=pop_max,
                    value=[pop_min, pop_max], marks=make_marks(pop_min, pop_max, fmt_pop),
                    step=100_000, tooltip={"placement": "bottom", "always_visible": False}, allowCross=False,
                ), style={"width": "240px"}),
            ], style=ROW),
            html.Div([
                html.Label("Time of day", style=LBL),
                dcc.Dropdown(id="time-dropdown", options=[{"label": t, "value": t} for t in times_of_day],
                    value=times_of_day, multi=True, style={"width": "280px", "fontSize": "12px"}),
            ], style=ROW),
            html.Div([
                html.Label("Season", style=LBL),
                dcc.Dropdown(id="season-dropdown", options=[{"label": s, "value": s} for s in seasons],
                    value=seasons, multi=True, style={"width": "400px", "fontSize": "12px"}),
            ], style=ROW),
        ], style={"display": "flex", "flexWrap": "wrap"}),
        html.Div([
            html.Div([
                html.Label("Extreme % to highlight", style=LBL),
                dcc.Dropdown(id="extreme-percentage", options=PERCENTILE_OPTIONS,
                    value=5, style={"width": "200px", "fontSize": "12px"}),
            ], style=ROW),
            html.Div([
                html.Label("City subset", style=LBL),
                dcc.RadioItems(id="city-subset-radio",
                    options=[
                        {"label": "All cities", "value": "all"},
                        {"label": "C40 cities", "value": "c40"},
                        {"label": "Olympic cities", "value": "olympic"},
                    ],
                    value="all", inline=True, labelStyle={"marginRight": "14px", "fontSize": "12px"}),
            ], style=ROW),
            html.Div([
                html.Label("Theme", style=LBL),
                html.Button(
                    "Dark Mode",
                    id="dark-mode-button",
                    n_clicks=0,
                    style={
                        "padding": "6px 12px",
                        "border": "1px solid #ccc",
                        "borderRadius": "4px",
                        "cursor": "pointer",
                        "fontSize": "12px",
                        "backgroundColor": "#f0f0f0",
                        "color": "black",
                    }
                ),
            ], style=ROW),
        ], style={"display": "flex", "flexWrap": "wrap", "marginTop": "2px"}),
    ]),
], style={"fontFamily": "Arial, sans-serif", "background": "white", "padding": "6px 14px", "boxSizing": "border-box"})

@app.callback(
    Output("dark-mode-store", "data"),
    Input("dark-mode-button", "n_clicks"),
    prevent_initial_call=False
)
def toggle_dark_mode(n_clicks):
    return n_clicks % 2 == 1

@app.callback(
    Output("quadrant-plot", "figure"),
    Input("year-slider", "value"),
    Input("population-slider", "value"),
    Input("time-dropdown", "value"),
    Input("season-dropdown", "value"),
    Input("extreme-percentage", "value"),
    Input("city-subset-radio", "value"),
    Input("dark-mode-store", "data"),
    prevent_initial_call=False
)
def update_quadrant(year_range, pop_range, sel_times, sel_seasons, extreme_pct, city_subset, dark_mode):
    # Handle None values
    if extreme_pct is None:
        extreme_pct = 5

    def empty(msg="No data for selected filters"):
        f = go.Figure()
        f.add_annotation(text=msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=15))
        f.update_layout(paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=10, b=10))
        return f

    if not sel_times or not sel_seasons:
        return empty()

    s_list = ",".join(f"'{s}'" for s in sel_seasons)
    t_list = ",".join(f"'{t}'" for t in sel_times)

    if city_subset == "c40":
        city_names = ",".join(f"'{c}'" for c in C40_CITIES)
        city_filter = f"AND city IN ({city_names})"
    elif city_subset == "olympic":
        city_names = ",".join(f"'{c}'" for c in OLYMPIC_CITIES)
        city_filter = f"AND city IN ({city_names})"
    else:
        city_filter = ""

    filters = f"""datetime IS NOT NULL
        AND EXTRACT(YEAR FROM datetime) BETWEEN {year_range[0]} AND {year_range[1]}
        AND population BETWEEN {pop_range[0]} AND {pop_range[1]}
        AND {SEASON_CASE} IN ({s_list})
        AND {HOUR_CASE} IN ({t_list})
        {city_filter}"""

    # Fetch averaged CO2 and SIF by city
    try:
        co2_city_data = duck_query(f"""
            SELECT city, AVG(xco2) AS co2_val
            FROM read_parquet('{CO2_PARQUET}')
            WHERE {filters}
            GROUP BY city
        """)

        sif_city_data = duck_query(f"""
            SELECT city, AVG(Daily_SIF_757nm) AS sif_val
            FROM read_parquet('{SIF_PARQUET}')
            WHERE {filters}
            GROUP BY city
        """)
    except Exception as e:
        print(f"Query error: {e}")
        return empty(f"Query error: {str(e)}")

    if co2_city_data.empty or sif_city_data.empty:
        return empty(f"No CO2 data: {co2_city_data.empty}, No SIF data: {sif_city_data.empty}")

    # Merge on city with inner join
    merged_data = co2_city_data.merge(sif_city_data, on='city', how='inner')

    if merged_data.empty:
        return empty("No matching cities in both datasets")

    # Use median to define quadrants (visual categorization)
    co2_median = merged_data["co2_val"].median()
    sif_median = merged_data["sif_val"].median()

    # Assign quadrants based on median
    def get_quadrant(co2, sif):
        if pd.isna(co2) or pd.isna(sif):
            return None
        if co2 >= co2_median and sif >= sif_median:
            return "High CO₂, High SIF"
        elif co2 < co2_median and sif >= sif_median:
            return "Low CO₂, High SIF"
        elif co2 >= co2_median and sif < sif_median:
            return "High CO₂, Low SIF"
        else:
            return "Low CO₂, Low SIF"

    merged_data["quadrant"] = merged_data.apply(lambda row: get_quadrant(row["co2_val"], row["sif_val"]), axis=1)

    # Identify extreme values: top/bottom X% for high/low quadrants
    def identify_extremes(qdata, co2_col, sif_col, extreme_pct, quadrant_name):
        """Mark cities in top/bottom X% as extremes for each quadrant"""
        is_high_co2 = "High CO₂" in quadrant_name
        is_high_sif = "High SIF" in quadrant_name

        if qdata.empty:
            return qdata

        # For high quadrants, mark top extreme_pct%
        # For low quadrants, mark bottom extreme_pct%
        if is_high_co2:
            co2_threshold = qdata[co2_col].quantile((100 - extreme_pct) / 100)
            qdata_co2_extreme = qdata[qdata[co2_col] >= co2_threshold]
        else:
            co2_threshold = qdata[co2_col].quantile(extreme_pct / 100)
            qdata_co2_extreme = qdata[qdata[co2_col] <= co2_threshold]

        if is_high_sif:
            sif_threshold = qdata[sif_col].quantile((100 - extreme_pct) / 100)
            qdata_sif_extreme = qdata[qdata[sif_col] >= sif_threshold]
        else:
            sif_threshold = qdata[sif_col].quantile(extreme_pct / 100)
            qdata_sif_extreme = qdata[qdata[sif_col] <= sif_threshold]

        # Cities that are extreme in both CO2 and SIF for this quadrant
        extreme_cities = set(qdata_co2_extreme.index) & set(qdata_sif_extreme.index)
        qdata['is_extreme'] = qdata.index.isin(extreme_cities)
        return qdata

    # Mark extremes within each quadrant
    merged_data['is_extreme'] = False
    for quadrant in ["High CO₂, High SIF", "Low CO₂, High SIF", "High CO₂, Low SIF", "Low CO₂, Low SIF"]:
        quad_mask = merged_data["quadrant"] == quadrant
        quad_indices = merged_data[quad_mask].index
        if len(quad_indices) > 0:
            quad_data = merged_data.loc[quad_indices].copy()
            quad_data = identify_extremes(quad_data, "co2_val", "sif_val", extreme_pct, quadrant)
            merged_data.loc[quad_indices, 'is_extreme'] = quad_data['is_extreme']

    bg_color = "#000000" if dark_mode else "white"
    text_color = "#ffffff" if dark_mode else "black"
    plot_color = "#1a1a1a" if dark_mode else "#f9f9f9"

    # Define colors for quadrants
    quadrant_colors = {
        "High CO₂, High SIF": "#FF6B6B",  # red
        "Low CO₂, High SIF": "#4ECDC4",   # teal
        "High CO₂, Low SIF": "#FFE66D",   # yellow
        "Low CO₂, Low SIF": "#95E1D3",    # mint
    }

    fig = go.Figure()

    # Add traces for each quadrant
    for quadrant in ["High CO₂, High SIF", "Low CO₂, High SIF", "High CO₂, Low SIF", "Low CO₂, Low SIF"]:
        quad_data = merged_data[merged_data["quadrant"] == quadrant]
        if not quad_data.empty:
            # Separate extreme and faded cities
            extreme_data = quad_data[quad_data["is_extreme"]]
            faded_data = quad_data[~quad_data["is_extreme"]]

            # Add faded cities (low opacity, no outline)
            if not faded_data.empty:
                fig.add_trace(go.Scatter(
                    x=faded_data["co2_val"],
                    y=faded_data["sif_val"],
                    mode='markers',
                    name=f"{quadrant} (other)",
                    marker=dict(
                        size=5,
                        color=quadrant_colors[quadrant],
                        opacity=0.2,
                        line=dict(width=0),
                    ),
                    hovertemplate="<b>%{customdata[0]}</b><br>CO₂: %{x:.2f} ppm<br>SIF: %{y:.4f}<extra></extra>",
                    customdata=faded_data[["city"]].values,
                    showlegend=False,
                ))

            # Add extreme cities (darker, with outline)
            if not extreme_data.empty:
                fig.add_trace(go.Scatter(
                    x=extreme_data["co2_val"],
                    y=extreme_data["sif_val"],
                    mode='markers',
                    name=quadrant,
                    marker=dict(
                        size=8,
                        color=quadrant_colors[quadrant],
                        opacity=0.9,
                        line=dict(width=2, color="rgba(0,0,0,0.8)"),
                    ),
                    hovertemplate="<b>%{customdata[0]}</b><br>CO₂: %{x:.2f} ppm<br>SIF: %{y:.4f}<extra></extra>",
                    customdata=extreme_data[["city"]].values,
                ))

    # Remove the old threshold visualization section that adds hlines and vlines

    fig.update_layout(
        title=f"CO₂ vs SIF Quadrant Analysis",
        xaxis_title="CO₂ (ppm)",
        yaxis_title="SIF (757nm)",
        paper_bgcolor=bg_color,
        plot_bgcolor=plot_color,
        font=dict(family="Arial", size=11, color=text_color),
        hovermode="closest",
        autosize=True,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(0,0,0,0.3)" if dark_mode else "rgba(255,255,255,0.8)",
        ),
        margin=dict(l=80, r=80, t=60, b=60),
    )

    grid_color = "rgba(128,128,128,0.2)" if dark_mode else "rgba(200,200,200,0.5)"
    fig.update_xaxes(gridcolor=grid_color, zeroline=False)
    fig.update_yaxes(gridcolor=grid_color, zeroline=False)

    return fig

if __name__ == "__main__":
    app.run(debug=True, port=8054)
