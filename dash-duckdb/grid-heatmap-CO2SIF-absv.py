# grid-heatmap-duckdb.py
# under development as of Mar 5 2026
# Deploy on Render: reads Parquet files committed to repo or mounted volume

import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import duckdb
import os

### file path for gdrive parquet

# PARQUET_DIR = "/tmp/oco3_parquet"
# os.makedirs(PARQUET_DIR, exist_ok=True)
# CO2_PARQUET = os.path.join(PARQUET_DIR, "co2_sam.parquet")
# SIF_PARQUET = os.path.join(PARQUET_DIR, "sif_sam.parquet")

# # Replace ID within quotes from G Drive sharing link e.g. https://drive.google.com/file/d/THIS_PART_IS_THE_ID/view
# # For long-term deployment can consider uploading parquets to HuggingFace
# DRIVE_FILES = {
#     CO2_PARQUET: "1iWrl3T33Q3S2UHmcYIoINSsYI2kLh-F_", # update with your own Gdrive link ID
#     SIF_PARQUET: "1Bc1ANfZK7BaXS093ivxASPvxVOoHJ7nv", # update with your own Gdrive link ID
# }

### file path for local testing of parquet
PARQUET_DIR="/Users/heyutian/Downloads/oco3_parquet"
os.makedirs(PARQUET_DIR, exist_ok=True)
CO2_PARQUET = os.path.join(PARQUET_DIR, "co2_sam.parquet")
SIF_PARQUET = os.path.join(PARQUET_DIR, "sif_sam.parquet")

def duck_query(sql):
    con = duckdb.connect()
    df = con.execute(sql).df()
    con.close()
    return df

SEASON_CASE = f"""
    CASE
        WHEN latitude BETWEEN -20 AND 20 AND EXTRACT(MONTH FROM datetime) BETWEEN 5 AND 10
            THEN 'Tropical Wet'
        WHEN latitude BETWEEN -20 AND 20
            THEN 'Tropical Dry'
        WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime) IN (12,1,2)
            THEN 'Winter (North)'
        WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime) IN (3,4,5)
            THEN 'Spring (North)'
        WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime) IN (6,7,8)
            THEN 'Summer (North)'
        WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime) IN (9,10,11)
            THEN 'Autumn (North)'
        WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime) IN (12,1,2)
            THEN 'Summer (South)'
        WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime) IN (3,4,5)
            THEN 'Autumn (South)'
        WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime) IN (6,7,8)
            THEN 'Winter (South)'
        WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime) IN (9,10,11)
            THEN 'Spring (South)'
        ELSE 'Other'
    END
"""

HOUR_CASE = f"""
    CASE
        WHEN EXTRACT(HOUR FROM local_time) < 6  THEN 'Night'
        WHEN EXTRACT(HOUR FROM local_time) < 12 THEN 'Morning'
        WHEN EXTRACT(HOUR FROM local_time) < 18 THEN 'Afternoon'
        ELSE 'Evening'
    END
"""

bounds = duck_query(f"""
    SELECT
        MIN(EXTRACT(YEAR FROM datetime))::int AS year_min,
        MAX(EXTRACT(YEAR FROM datetime))::int AS year_max,
        MIN(population)::int                  AS pop_min,
        MAX(population)::int                  AS pop_max
    FROM read_parquet('{CO2_PARQUET}')
    WHERE datetime IS NOT NULL
""").iloc[0]

year_min, year_max = int(bounds.year_min), int(bounds.year_max)
pop_min,  pop_max  = int(bounds.pop_min),  int(bounds.pop_max)

seasons = sorted(duck_query(f"""
    SELECT DISTINCT {SEASON_CASE} AS season
    FROM read_parquet('{CO2_PARQUET}')
    WHERE datetime IS NOT NULL
    ORDER BY 1
""")['season'].tolist())

times_of_day = sorted(duck_query(f"""
    SELECT DISTINCT {HOUR_CASE} AS time_of_day
    FROM read_parquet('{CO2_PARQUET}')
    WHERE local_time IS NOT NULL
    ORDER BY 1
""")['time_of_day'].tolist())

def fmt_pop(v):
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
    if v >= 1_000:     return f"{v/1_000:.0f}K"
    return str(v)

def simple_marks(mn, mx):
    mid = (mn + mx) // 2
    return {mn: str(mn), mid: str(mid), mx: str(mx)}

def pop_marks(mn, mx):
    mid = (mn + mx) // 2
    return {mn: fmt_pop(mn), mid: fmt_pop(mid), mx: fmt_pop(mx)}


app  = dash.Dash(__name__)
server = app.server

app.layout = html.Div([

    dcc.Graph(id='heatmap'),

    html.Div([
        html.Label("Time Range (Years)", style={"margin-right":"10px","width":"150px"}),
        dcc.RangeSlider(
            id='year-slider',
            min=year_min, max=year_max,
            value=[year_min, year_max],
            marks=simple_marks(year_min, year_max),
            step=1,
            tooltip={"placement":"bottom","always_visible":False},
            allowCross=False
        )
    ], style={"display":"flex","align-items":"center","margin":"10px"}),

    html.Div([
        html.Label("Population Range", style={"margin-right":"10px","width":"150px"}),
        dcc.RangeSlider(
            id='population-slider',
            min=pop_min, max=pop_max,
            value=[pop_min, pop_max],
            marks=pop_marks(pop_min, pop_max),
            step=100_000,
            tooltip={"placement":"bottom","always_visible":False},
            allowCross=False
        )
    ], style={"display":"flex","align-items":"center","margin":"10px"}),

    html.Div([
        html.Label("Time of Day", style={"margin-right":"10px","width":"150px"}),
        dcc.Dropdown(
            id="time-dropdown",
            options=[{"label":t,"value":t} for t in times_of_day],
            value=times_of_day,
            multi=True,
            style={"width":"450px"}
        )
    ], style={"display":"flex","align-items":"center","margin":"10px"}),

    html.Div([
        html.Label("Season", style={"margin-right":"10px","width":"150px"}),
        dcc.Dropdown(
            id="season-dropdown",
            options=[{"label":s,"value":s} for s in seasons],
            value=seasons,
            multi=True,
            style={"width":"1100px"}
        )
    ], style={"display":"flex","align-items":"center","margin":"10px"})

], style={"font-family":"Arial, sans-serif","background":"white","padding":"20px"})


@app.callback(
    Output("heatmap", "figure"),
    Input("year-slider", "value"),
    Input("population-slider", "value"),
    Input("time-dropdown", "value"),
    Input("season-dropdown", "value")
)
def update_heatmap(year_range, population_range, selected_times, selected_seasons):

    if not selected_times or not selected_seasons:
        fig = make_subplots(rows=2, cols=1)
        fig.add_annotation(text="No data selected", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    season_list = ",".join(f"'{s}'" for s in selected_seasons)
    time_list   = ",".join(f"'{t}'" for t in selected_times)

    # --- CO2 query (unchanged) ---
    co2_query = f"""
        SELECT
            city || ', ' || country                              AS city_label,
            strftime(DATE_TRUNC('month', datetime), '%Y-%m')    AS time_bin,
            AVG(xco2)                                           AS xco2_mean
        FROM read_parquet('{CO2_PARQUET}')
        WHERE
            datetime   IS NOT NULL
            AND EXTRACT(YEAR FROM datetime) BETWEEN {year_range[0]} AND {year_range[1]}
            AND population BETWEEN {population_range[0]} AND {population_range[1]}
            AND {SEASON_CASE} IN ({season_list})
            AND {HOUR_CASE}   IN ({time_list})
        GROUP BY city_label, time_bin
        ORDER BY time_bin
    """

    sif_query = f"""
        SELECT
            city || ', ' || country                              AS city_label,
            strftime(DATE_TRUNC('month', datetime), '%Y-%m')    AS time_bin,
            AVG(Daily_SIF_757nm)                                            AS sif_mean
        FROM read_parquet('{SIF_PARQUET}')
        WHERE
            datetime   IS NOT NULL
            AND EXTRACT(YEAR FROM datetime) BETWEEN {year_range[0]} AND {year_range[1]}
            AND population BETWEEN {population_range[0]} AND {population_range[1]}
            AND {SEASON_CASE} IN ({season_list})
            AND {HOUR_CASE}   IN ({time_list})
        GROUP BY city_label, time_bin
        ORDER BY time_bin
    """

    co2_agg = duck_query(co2_query)
    sif_agg = duck_query(sif_query)

    if co2_agg.empty and sif_agg.empty:
        fig = make_subplots(rows=2, cols=1)
        fig.add_annotation(text="No data for selected filters", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    # --- Pivot both datasets ---
    def make_pivot(df, val_col):
        pivot = df.pivot(index="city_label", columns="time_bin", values=val_col)
        return pivot.dropna(axis=0, how='all').dropna(axis=1, how='all')

    co2_pivot = make_pivot(co2_agg, "xco2_mean") if not co2_agg.empty else pd.DataFrame()
    sif_pivot = make_pivot(sif_agg, "sif_mean")  if not sif_agg.empty else pd.DataFrame()

    # Align rows (cities) across both pivots so they line up vertically
    shared_cities = co2_pivot.index.union(sif_pivot.index)
    co2_pivot = co2_pivot.reindex(shared_cities)
    sif_pivot = sif_pivot.reindex(shared_cities)

    # Shared time axis
    shared_times = co2_pivot.columns.union(sif_pivot.columns).tolist()
    co2_pivot = co2_pivot.reindex(columns=shared_times)
    sif_pivot = sif_pivot.reindex(columns=shared_times)

    city_labels = shared_cities.tolist()

    AXIS_FONT  = dict(family="Arial", size=14, color="black")
    TICK_FONT  = dict(family="Arial", size=11, color="black")


    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=["Atmospheric CO₂ (ppm)", "Solar-Induced Fluorescence — SIF (mW/m²/sr/nm)"]
    )

    fig.add_trace(
        go.Heatmap(
            z=co2_pivot.values,
            x=shared_times,
            y=city_labels,
            colorscale="Greys",
            zmin=400, zmax=450,
            colorbar=dict(
                title=dict(text="CO₂ (ppm)", font=AXIS_FONT),
                tickfont=TICK_FONT,
                len=0.45,
                y=0.78,
                yanchor="middle"
            ),
            name="CO₂"
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Heatmap(
            z=sif_pivot.values,
            x=shared_times,
            y=city_labels,
            colorscale="Greens",
            colorbar=dict(
                title=dict(text="SIF", font=AXIS_FONT),
                tickfont=TICK_FONT,
                len=0.45,
                y=0.22,
                yanchor="middle"
            ),
            name="SIF"
        ),
        row=2, col=1
    )

    fig.update_layout(
        template="plotly_white",
        title=dict(
            text="Atmospheric CO₂ & SIF Levels (SAM)",
            font=dict(family="Arial", size=18, color="black")
        ),
        font=dict(family="Arial, sans-serif", color="black", size=14),
        paper_bgcolor="white",
        plot_bgcolor="#ffffff",
        height=900,
    )

    for axis in [fig.layout.xaxis, fig.layout.xaxis2]:
        axis.update(title_font=AXIS_FONT, tickfont=TICK_FONT)

    for axis in [fig.layout.yaxis, fig.layout.yaxis2]:
        axis.update(
            title="City",
            title_font=AXIS_FONT,
            tickfont=TICK_FONT
        )

    fig.layout.xaxis2.update(title="Time", title_font=AXIS_FONT)

    return fig


if __name__ == "__main__":
    app.run(debug=True, port=8052)
