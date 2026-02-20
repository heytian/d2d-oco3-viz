import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output
import plotly.express as px

df = pd.read_csv("./data/Olympic_Cities_Updated_pop.csv")

df["datetime"] = pd.to_datetime(
    df["datetime"],
    format="%m/%d/%y %H:%M",
    errors="coerce"
)

df["year"] = df["datetime"].dt.year
df["month"] = df["datetime"].dt.month

df["time_bin"] = df["datetime"].dt.to_period("M").astype(str)

df["local_time"] = pd.to_datetime(
    df["local_time"],
    format="%m/%d/%y %H:%M",
    errors="coerce"
)
df["hour"] = df["local_time"].dt.hour

df["time_of_day"] = pd.cut(
    df["hour"],
    bins=[0, 6, 12, 18, 24],
    labels=["Night", "Morning", "Afternoon", "Evening"],
    right=False
)

def assign_season(row):
    lat = row['latitude']
    month = row['month']

    if -20 <= lat <= 20:
        if 5 <= month <= 10:
            return "Tropical Wet"
        else:
            return "Tropical Dry"

    if 20 < lat <= 60:
        if month in [12, 1, 2]:
            return "Winter (North)"
        elif month in [3, 4, 5]:
            return "Spring (North)"
        elif month in [6, 7, 8]:
            return "Summer (North)"
        else:
            return "Autumn (North)"

    if -60 <= lat < -20:
        if month in [12, 1, 2]:
            return "Summer (South)"
        elif month in [3, 4, 5]:
            return "Autumn (South)"
        elif month in [6, 7, 8]:
            return "Winter (South)"
        else:
            return "Spring (South)"

    return "Other"

df["season"] = df.apply(assign_season, axis=1)

def simple_marks(min_val, max_val):
    mid = (min_val + max_val)//2
    return {min_val: str(min_val), mid: str(mid), max_val: str(max_val)}

app = dash.Dash(
    __name__,
    external_stylesheets=["./dash-flask-apps/assets/style.css"]
)

app.layout = html.Div([

    dcc.Graph(id='heatmap'),

    # html.H1("OCO-3 CO2",style={"font-family":"Arial", "font-size":"16px", "color":"black"}),

    html.Div([
        html.Label("Time Range (Years)", style={"margin-right":"10px", "width":"150px"}),
        dcc.RangeSlider(
            id='year-slider',
            min=int(df["year"].min()),
            max=int(df["year"].max()),
            value=[int(df["year"].min()), int(df["year"].max())],
            marks=simple_marks(int(df["year"].min()), int(df["year"].max())),
            step=0.05,
            tooltip={"placement":"bottom", "always_visible":False},
            allowCross=False
        )
    ], style={"display":"flex", "align-items":"center", "margin":"10px"}),

    html.Div([
        html.Label("Population Range", style={"margin-right":"10px", "width":"150px"}),
        dcc.RangeSlider(
            id='population-slider',
            min=int(df["population"].min()),
            max=int(df["population"].max()),
            value=[int(df["population"].min()), int(df["population"].max())],
            marks=simple_marks(int(df["population"].min()), int(df["population"].max())),
            step=100000,
            tooltip={"placement":"bottom", "always_visible":False},
            allowCross=False
        )
    ], style={"display":"flex", "align-items":"center", "margin":"10px"}),

    html.Div([
        html.Label("Time of Day", style={"margin-right":"10px", "width":"150px"}),
        dcc.Dropdown(
            id="time-dropdown",
            options=[{"label": t, "value": t} for t in sorted(df["time_of_day"].dropna().unique())],
            value=list(df["time_of_day"].dropna().unique()),
            multi=True,
            style={"width":"450px"}
        )
    ], style={"display":"flex", "align-items":"center", "margin":"10px"}),

    html.Div([
        html.Label("Season", style={"margin-right":"10px", "width":"150px"}),
        dcc.Dropdown(
            id="season-dropdown",
            options=[{"label": s, "value": s} for s in sorted(df["season"].dropna().unique())],
            value=list(df["season"].dropna().unique()),
            multi=True,
            style={"width":"1100px"}
        )
    ], style={"display":"flex", "align-items":"center", "margin":"10px"})

])


@app.callback(
    Output("heatmap", "figure"),
    Input("year-slider", "value"),
    Input("population-slider", "value"),
    Input("time-dropdown", "value"),
    Input("season-dropdown", "value")
)
def update_heatmap(year_range, population_range, selected_times, selected_seasons):

    filtered = df[
        (df["year"] >= year_range[0]) &
        (df["year"] <= year_range[1]) &
        (df["population"] >= population_range[0]) &
        (df["population"] <= population_range[1]) &
        (df["time_of_day"].isin(selected_times)) &
        (df["season"].isin(selected_seasons))
    ].copy()

    y_axis = "city"

    agg = (
        filtered.groupby(["time_bin", y_axis])["xco2"]
        .mean()
        .reset_index(name="value")
    )

    pivot = agg.pivot(index=y_axis, columns="time_bin", values="value")
    pivot = pivot.dropna(axis=0, how='all')
    pivot = pivot.dropna(axis=1, how='all')

    fig = px.imshow(
        pivot.values,
        x=pivot.columns,
        y=pivot.index,
        aspect="auto",
        color_continuous_scale="Greys", #Other Options: Plasma/Magma/Viridis
        labels={"x": "Time", "y": y_axis, "color": "CO₂ (ppm)"}
    )

    fig.update_traces(
        zmin=400,
        zmax=450,
    )

    fig.update_layout(
        template="plotly_white",
        title="Atmospheric CO2 Levels of Olympic Host Cities",
        title_font=dict(family="Arial", size=18, color="black"),
        xaxis=dict(title_font=dict(family="Arial", size=16, color="black"),
                tickfont=dict(family="Arial", size=12, color="black")),
        yaxis=dict(title_font=dict(family="Arial", size=16, color="black"),
                tickfont=dict(family="Arial", size=12, color="black")),
        coloraxis_colorbar=dict(title_font=dict(family="Arial", size=14, color="black"),
                                tickfont=dict(family="Arial", size=12, color="black")),
        font=dict(
            family="Arial, sans-serif",
            color='black',
            size=14),
        paper_bgcolor="white",
        plot_bgcolor="#ffffff",
        height=600
    )

    return fig


if __name__ == "__main__":
    app.run(debug=True, port=8052)


# To run this app, open terminal inside VS code, activate venv, and "pip install dash plotly pandas numpy", then "python grid-heatmap.py"
