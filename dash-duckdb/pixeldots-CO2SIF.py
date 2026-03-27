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

# print("C40 not in DB:", C40_CITIES_ - all_cities_in_db)
# print("Olympic not in DB:", OLYMPIC_CITIES_ - all_cities_in_db)

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

TIME_BIN_SQL = {
    "Month": "strftime(DATE_TRUNC('month', datetime), '%Y-%m')",
    "Half-Month": """CASE
        WHEN EXTRACT(DAY FROM datetime) <= 15
            THEN strftime(DATE_TRUNC('month', datetime), '%Y-%m') || '-01'
        ELSE strftime(DATE_TRUNC('month', datetime), '%Y-%m') || '-16'
    END""",
    "Day": "strftime(CAST(datetime AS DATE), '%Y-%m-%d')",
}

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

app.layout = html.Div([
    dcc.Store(id="dark-mode-store", data=False),
    dcc.Graph(id="heatmap", style={"height": "calc(100vh - 160px)", "minHeight": "300px"}, config={"responsive": True}),
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
                html.Label("Var baseline", style=LBL),
                dcc.RadioItems(id="mean-radio",
                    options=[{"label": "Global mean", "value": "global"}, {"label": "Mean by time bin", "value": "timebin"}],
                    value="global", inline=True, labelStyle={"marginRight": "14px", "fontSize": "12px"}),
            ], style=ROW),
            html.Div([
                html.Label("Layout", style=LBL),
                dcc.RadioItems(id="layout-radio",
                    options=[{"label": "Subplots", "value": "subplot"}, {"label": "Interleaved", "value": "interleaved"}],
                    value="subplot", inline=True, labelStyle={"marginRight": "14px", "fontSize": "12px"}),
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


def pivot_dataset(df, cities, times):
    if df.empty:
        return pd.DataFrame(np.nan, index=cities, columns=times), pd.DataFrame(np.nan, index=cities, columns=times)
    pv = df.pivot(index="city_label", columns="time_bin", values="val").reindex(index=cities, columns=times)
    pn = df.pivot(index="city_label", columns="time_bin", values="n").reindex(index=cities, columns=times)
    return pv.where(pn.fillna(0) > 0, other=np.nan), pn


def compute_variance(vals, mean_type):
    baseline = np.nanmean(vals) if mean_type == "global" else np.nanmean(vals, axis=0, keepdims=True)
    return np.where(np.isnan(vals), np.nan, vals - baseline), baseline


def make_z(var_arr, cnt_arr):
    cnt_safe = np.where(np.isnan(cnt_arr), 0, cnt_arr)
    return np.where(cnt_safe == 0, np.nan, var_arr)


def make_customdata(raw, var, cnt, fmt_r, fmt_v):
    nc, nt = raw.shape
    cd = np.full((nc, nt, 3), "", dtype=object)
    for i in range(nc):
        for j in range(nt):
            rv, vv, nv = raw[i, j], var[i, j], cnt[i, j]
            n_safe = 0 if np.isnan(nv) else int(nv)
            if np.isnan(rv) or np.isnan(vv) or n_safe == 0:
                continue
            cd[i, j] = [fmt_r(rv), ("+" if vv >= 0 else "") + fmt_v(vv), str(n_safe)]
    return cd


def colorbar_cfg(title_text, fmt, x_pos, y_pos, tick_font):
    return dict(
        title=dict(text=title_text, font=dict(family="Arial", size=10)),
        tickformat=fmt, tickfont=tick_font,
        lenmode="fraction", len=0.44,
        y=y_pos, yanchor="middle",
        x=x_pos, xanchor="left",
        thickness=12, outlinewidth=0,
    )

@app.callback(
    Output("dark-mode-store", "data"),
    Input("dark-mode-button", "n_clicks"),
    prevent_initial_call=False
)
def toggle_dark_mode(n_clicks):
    return n_clicks % 2 == 1

@app.callback(
    Output("heatmap", "figure"),
    Input("year-slider", "value"),
    Input("population-slider", "value"),
    Input("time-dropdown", "value"),
    Input("season-dropdown", "value"),
    Input("mean-radio", "value"),
    Input("layout-radio", "value"),
    Input("city-subset-radio","value"),
    Input("dark-mode-store", "data"),
    prevent_initial_call=False
)
def update_heatmap(year_range, pop_range, sel_times, sel_seasons, mean_type, layout_mode, city_subset, dark_mode):
    def empty(msg="No data for selected filters"):
        f = go.Figure()
        f.add_annotation(text=msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=15))
        f.update_layout(paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=10, b=10))
        return f

    if not sel_times or not sel_seasons:
        return empty()

    s_list = ",".join(f"'{s}'" for s in sel_seasons)
    t_list = ",".join(f"'{t}'" for t in sel_times)
    bin_expr = TIME_BIN_SQL["Month"]

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

    co2_df = duck_query(f"""
        SELECT city || ', ' || country AS city_label, ({bin_expr}) AS time_bin, AVG(xco2) AS val, COUNT(*) AS n
        FROM read_parquet('{CO2_PARQUET}') WHERE {filters}
        GROUP BY city_label, time_bin ORDER BY city_label, time_bin""")

    sif_df = duck_query(f"""
        SELECT city || ', ' || country AS city_label, ({bin_expr}) AS time_bin, AVG(Daily_SIF_757nm) AS val, COUNT(*) AS n
        FROM read_parquet('{SIF_PARQUET}') WHERE {filters}
        GROUP BY city_label, time_bin ORDER BY city_label, time_bin""")

    if co2_df.empty and sif_df.empty:
        return empty()

    cities = sorted(set(co2_df["city_label"]) | set(sif_df["city_label"]))
    times  = sorted(set(co2_df["time_bin"])   | set(sif_df["time_bin"]))
    nc, nt = len(cities), len(times)

    co2_pv, co2_pn = pivot_dataset(co2_df, cities, times)
    sif_pv, sif_pn = pivot_dataset(sif_df, cities, times)

    co2_var, _ = compute_variance(co2_pv.values, mean_type)
    sif_var, _ = compute_variance(sif_pv.values, mean_type)

    co2_z = make_z(co2_var, co2_pn.values)
    sif_z = make_z(sif_var, sif_pn.values)

    co2_vmin = float(np.nanmin(co2_z)) if not np.all(np.isnan(co2_z)) else -1.0
    co2_vmax = float(np.nanmax(co2_z)) if not np.all(np.isnan(co2_z)) else  1.0
    sif_vmin = float(np.nanmin(sif_z)) if not np.all(np.isnan(sif_z)) else -1.0
    sif_vmax = float(np.nanmax(sif_z)) if not np.all(np.isnan(sif_z)) else  1.0

    co2_sym = max(abs(co2_vmin), abs(co2_vmax))
    sif_sym = max(abs(sif_vmin), abs(sif_vmax))

    if mean_type == "global":
        bl = (f"Global mean — CO₂: {float(np.nanmean(co2_pv.values)):.2f} ppm "
              f"| SIF: {float(np.nanmean(sif_pv.values)):.4f}")
    else:
        bl = "Var vs mean per time bin"

    cd_co2 = make_customdata(co2_pv.values, co2_var, co2_pn.values,
                             lambda v: f"{v:.2f} ppm", lambda v: f"{v:.2f} ppm")
    cd_sif = make_customdata(sif_pv.values, sif_var, sif_pn.values,
                             lambda v: f"{v:.4f}", lambda v: f"{v:.4f}")

    bg_color = "#000000" if dark_mode else "white"
    text_color = "#ffffff" if dark_mode else "black"
    plot_color = "#000000" if dark_mode else "white"

    TF = dict(family="Arial", size=10, color=text_color)
    AF = dict(family="Arial", size=11, color=text_color)

    HT_CO2 = "<b>%{y}</b><br>Time: %{x}<br>CO₂: %{customdata[0]}<br>Var: %{customdata[1]}<br>Soundings: %{customdata[2]}<extra></extra>"
    HT_SIF = "<b>%{y}</b><br>Time: %{x}<br>SIF: %{customdata[0]}<br>Var: %{customdata[1]}<br>Soundings: %{customdata[2]}<extra></extra>"

    base_layout = dict(
        title=dict(text=f"CO₂ & SIF Variance  <span style='font-size:11px;color:{'#888' if dark_mode else '#888'}'>{bl}</span>",
                   font=dict(family="Arial", size=14, color=text_color)),
        paper_bgcolor=bg_color, plot_bgcolor=plot_color,
        font=dict(family="Arial", size=11, color=text_color),
        autosize=True, hovermode="closest",
    )

    def flatten_grid_with_size(count_array, z_array, x_vals, y_vals, cd_array):
        x_flat, y_flat, size_flat, cd_flat = [], [], [], []
        max_count = np.nanmax(count_array)
        if max_count == 0 or np.isnan(max_count):
            max_count = 1

        for i, y in enumerate(y_vals):
            for j, x in enumerate(x_vals):
                if not np.isnan(count_array[i, j]) and count_array[i, j] > 0 and not np.isnan(z_array[i, j]):
                    x_flat.append(j)
                    y_flat.append(i)
                    size_flat.append(5 + 25 * (count_array[i, j] / max_count))
                    cd_flat.append(cd_array[i, j])
        return x_flat, y_flat, size_flat, cd_flat

    def flatten_grid_with_color(z_array, count_array, x_vals, y_vals, cd_array):
        x_flat, y_flat, z_flat, cd_flat = [], [], [], []
        for i, y in enumerate(y_vals):
            for j, x in enumerate(x_vals):
                if not np.isnan(z_array[i, j]) and not np.isnan(count_array[i, j]):
                    x_flat.append(j)
                    y_flat.append(i)
                    z_flat.append(z_array[i, j])
                    cd_flat.append(cd_array[i, j])
        return x_flat, y_flat, z_flat, cd_flat

    if layout_mode == "subplot":
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.5])

        x_co2, y_co2, size_co2, cd_co2_scatter = flatten_grid_with_size(co2_pn.values, co2_z, times, cities, cd_co2)

        fig.add_trace(go.Scatter(
            x=x_co2, y=y_co2, mode='markers',
            marker=dict(
                size=size_co2,
                color='white' if dark_mode else 'black',
                line=dict(width=0),
                opacity=0.7,
            ),
            customdata=cd_co2_scatter,
            hovertemplate=HT_CO2,
            name="CO₂", showlegend=False,
        ), row=1, col=1)

        x_sif, y_sif, z_sif, cd_sif_scatter = flatten_grid_with_color(sif_z, sif_pn.values, times, cities, cd_sif)

        fig.add_trace(go.Scatter(
            x=x_sif, y=y_sif, mode='markers',
            marker=dict(
                size=12,
                color=z_sif,
                colorscale=[[0, "#000000"], [0.5, "#808080"], [1, "#f1f1f1"]] if dark_mode else [[0, "#f1f1f1"], [0.5, "#808080"], [1, "#000000"]],
                line=dict(width=0),
                colorbar=dict(
                    title=dict(text="SIF var", font=dict(family="Arial", size=10)),
                    tickformat="+.3f",
                    tickfont=TF,
                    lenmode="fraction", len=0.44,
                    y=0.25, yanchor="middle",
                    x=1.02, xanchor="left",
                    thickness=12, outlinewidth=0,
                ),
                cmin=-sif_sym, cmax=sif_sym, cmid=0,
            ),
            customdata=cd_sif_scatter,
            hovertemplate=HT_SIF,
            name="SIF", showlegend=False,
        ), row=2, col=1)

        fig.update_xaxes(tickfont=TF, showticklabels=False, showgrid=False, row=1, col=1)
        fig.update_xaxes(tickfont=TF, title="Time", title_font=AF, showgrid=False, row=2, col=1)
        for r in [1, 2]:
            fig.update_yaxes(tickfont=TF, autorange="reversed", title=None, showgrid=False, row=r, col=1)

        fig.update_layout(**base_layout, margin=dict(l=170, r=120, t=52, b=42))

    else:
        n_rows = nc * 2
        y_all = []
        for city in cities:
            y_all.append(city)
            y_all.append(city + "\u200b")

        tick_text = []
        for city in cities:
            tick_text.append(city)
            tick_text.append("")

        fig = go.Figure()

        for i, city in enumerate(cities):
            city_indices = [j for j in range(nt) if not np.isnan(co2_pn.iloc[i, j]) and not np.isnan(co2_z[i, j])]
            if city_indices:
                x_co2_city = [times[j] for j in city_indices]
                y_co2_city = [city] * len(city_indices)
                max_count = np.nanmax(co2_pn.values)
                if max_count == 0 or np.isnan(max_count):
                    max_count = 1
                size_co2_city = [5 + 25 * (co2_pn.iloc[i, j] / max_count) for j in city_indices]
                cd_co2_city = [cd_co2[i, j] for j in city_indices]

                fig.add_trace(go.Scatter(
                    x=x_co2_city, y=y_co2_city, mode='markers',
                    marker=dict(size=size_co2_city, color='black', line=dict(width=0), opacity=0.7),
                    customdata=cd_co2_city,
                    hovertemplate=HT_CO2,
                    name="CO₂", legendgroup="CO2", showlegend=(i==0),
                ))

        for i, city in enumerate(cities):
            city_indices = [j for j in range(nt) if not np.isnan(sif_pn.iloc[i, j]) and not np.isnan(sif_z[i, j])]
            if city_indices:
                x_sif_city = [times[j] for j in city_indices]
                y_sif_city = [city + "\u200b"] * len(city_indices)
                z_sif_city = [sif_z[i, j] for j in city_indices]
                cd_sif_city = [cd_sif[i, j] for j in city_indices]

                fig.add_trace(go.Scatter(
                    x=x_sif_city, y=y_sif_city, mode='markers',
                    marker=dict(
                        size=12,
                        color=z_sif_city,
                        colorscale=[[0, "#ffffff"], [0.5, "#808080"], [1, "#000000"]] if not dark_mode else [[0, "#000000"], [0.5, "#808080"], [1, "#ffffff"]],
                        line=dict(width=0),
                        cmin=-sif_sym, cmax=sif_sym, cmid=0,
                    ),
                    customdata=cd_sif_city,
                    hovertemplate=HT_SIF,
                    name="SIF", legendgroup="SIF", showlegend=(i==0),
                ))

        max_label_len = max(len(c) for c in cities)
        left_margin = max(120, min(220, max_label_len * 7))

        fig.update_layout(
            **base_layout,
            yaxis=dict(
                tickfont=TF, autorange="reversed",
                tickmode="array", tickvals=y_all, ticktext=tick_text,
                title=None,
                showgrid=False,
            ),
            xaxis=dict(title="Time", title_font=AF, tickfont=TF,showgrid=False),
            margin=dict(l=left_margin, r=180, t=52, b=42),
        )

    return fig


if __name__ == "__main__":
    app.run(debug=True, port=8052)
