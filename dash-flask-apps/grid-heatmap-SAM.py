import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:<INSERTPASSWORD>@localhost:5432/geocode" #replace with sql password
)
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    bounds = conn.execute(text("""
        SELECT
            MIN(EXTRACT(YEAR FROM datetime::timestamp))::int AS year_min,
            MAX(EXTRACT(YEAR FROM datetime::timestamp))::int AS year_max,
            MIN(population)::int AS pop_min,
            MAX(population)::int AS pop_max
        FROM co2_sam_cities_pop
        WHERE datetime IS NOT NULL
    """)).fetchone()

    year_min, year_max = bounds[0], bounds[1]
    pop_min,  pop_max  = bounds[2], bounds[3]

def fmt_pop(v):
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    elif v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(v)

def simple_marks(min_val, max_val):
    mid = (min_val + max_val) // 2
    return {
        min_val: str(min_val),
        mid:     str(mid),
        max_val: str(max_val)
    }

def pop_marks(min_val, max_val):
    mid = (min_val + max_val) // 2
    return {
        min_val: fmt_pop(min_val),
        mid:     fmt_pop(mid),
        max_val: fmt_pop(max_val)
    }

SEASON_CASE = """
    CASE
        WHEN latitude BETWEEN -20 AND 20 AND EXTRACT(MONTH FROM datetime::timestamp) BETWEEN 5 AND 10
            THEN 'Tropical Wet'
        WHEN latitude BETWEEN -20 AND 20
            THEN 'Tropical Dry'
        WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime::timestamp) IN (12,1,2)
            THEN 'Winter (North)'
        WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime::timestamp) IN (3,4,5)
            THEN 'Spring (North)'
        WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime::timestamp) IN (6,7,8)
            THEN 'Summer (North)'
        WHEN latitude > 20 AND latitude <= 60 AND EXTRACT(MONTH FROM datetime::timestamp) IN (9,10,11)
            THEN 'Autumn (North)'
        WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime::timestamp) IN (12,1,2)
            THEN 'Summer (South)'
        WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime::timestamp) IN (3,4,5)
            THEN 'Autumn (South)'
        WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime::timestamp) IN (6,7,8)
            THEN 'Winter (South)'
        WHEN latitude >= -60 AND latitude < -20 AND EXTRACT(MONTH FROM datetime::timestamp) IN (9,10,11)
            THEN 'Spring (South)'
        ELSE 'Other'
    END
"""

HOUR_CASE = """
    CASE
        WHEN EXTRACT(HOUR FROM local_time::timestamp) < 6  THEN 'Night'
        WHEN EXTRACT(HOUR FROM local_time::timestamp) < 12 THEN 'Morning'
        WHEN EXTRACT(HOUR FROM local_time::timestamp) < 18 THEN 'Afternoon'
        ELSE 'Evening'
    END
"""

with engine.connect() as conn:
    seasons = sorted([r[0] for r in conn.execute(text(f"""
        SELECT DISTINCT {SEASON_CASE} AS season
        FROM co2_sam_cities_pop
        WHERE datetime IS NOT NULL
        ORDER BY 1
    """)).fetchall()])

    times_of_day = sorted([r[0] for r in conn.execute(text(f"""
        SELECT DISTINCT {HOUR_CASE} AS time_of_day
        FROM co2_sam_cities_pop
        WHERE local_time IS NOT NULL
        ORDER BY 1
    """)).fetchall()])

app = dash.Dash(__name__)
server = app.server  # needed for deployment

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
            step=100000,
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
    Output("heatmap","figure"),
    Input("year-slider","value"),
    Input("population-slider","value"),
    Input("time-dropdown","value"),
    Input("season-dropdown","value")
)
def update_heatmap(year_range, population_range, selected_times, selected_seasons):

    if not selected_times or not selected_seasons:
        return px.imshow([[0]], title="No data selected")

    season_list   = ",".join(f"'{s}'" for s in selected_seasons)
    time_list     = ",".join(f"'{t}'" for t in selected_times)

    query = f"""
        SELECT
            city || ', ' || country   AS city_label,
            TO_CHAR(DATE_TRUNC('month', datetime::timestamp), 'YYYY-MM') AS time_bin,
            AVG(xco2) AS xco2_mean
        FROM co2_sam_cities_pop
        WHERE
            datetime  IS NOT NULL
            AND EXTRACT(YEAR FROM datetime::timestamp) BETWEEN {year_range[0]} AND {year_range[1]}
            AND population BETWEEN {population_range[0]} AND {population_range[1]}
            AND {SEASON_CASE} IN ({season_list})
            AND {HOUR_CASE}   IN ({time_list})
        GROUP BY city_label, time_bin
        ORDER BY time_bin
    """

    agg = pd.read_sql(query, engine)

    if agg.empty:
        return px.imshow([[0]], title="No data for selected filters")

    pivot = agg.pivot(index="city_label", columns="time_bin", values="xco2_mean")
    pivot = pivot.dropna(axis=0, how='all').dropna(axis=1, how='all')

    fig = px.imshow(
        pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        aspect="auto",
        color_continuous_scale="Greys",
        labels={"x":"Time","y":"City","color":"CO₂ (ppm)"}
    )

    fig.update_traces(zmin=400, zmax=450)

    fig.update_layout(
        template="plotly_white",
        title="Atmospheric CO₂ Levels (SAM)",
        title_font=dict(family="Arial", size=18, color="black"),
        xaxis=dict(title_font=dict(family="Arial",size=16,color="black"),
                   tickfont=dict(family="Arial",size=12,color="black")),
        yaxis=dict(title_font=dict(family="Arial",size=16,color="black"),
                   tickfont=dict(family="Arial",size=12,color="black")),
        coloraxis_colorbar=dict(title_font=dict(family="Arial",size=14,color="black"),
                                tickfont=dict(family="Arial",size=12,color="black")),
        font=dict(family="Arial, sans-serif", color="black", size=14),
        paper_bgcolor="white",
        plot_bgcolor="#ffffff",
        height=600
    )

    return fig


if __name__ == "__main__":
    app.run(debug=True, port=8052)
