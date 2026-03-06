import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import duckdb
import os
import gdown

PARQUET_DIR = "/Users/heyutian/Downloads/oco3_parquet"
# PARQUET_DIR = "/tmp/oco3_parquet"
CO2_PARQUET = os.path.join(PARQUET_DIR, "co2_sam.parquet")
SIF_PARQUET = os.path.join(PARQUET_DIR, "sif_sam.parquet")

# DRIVE_FILES = {
#     CO2_PARQUET: "1iWrl3T33Q3S2UHmcYIoINSsYI2kLh-F_",
#     SIF_PARQUET: "1Bc1ANfZK7BaXS093ivxASPvxVOoHJ7nv",
# }

# def download_from_drive():
#     import requests
#     os.makedirs(PARQUET_DIR, exist_ok=True)
#     for path, file_id in DRIVE_FILES.items():
#         if os.path.exists(path):
#             continue
#         url = f"https://drive.google.com/uc?export=download&id={file_id}"
#         # url = f"https://drive.google.com/file/d/{file_id}/view"
#         session = requests.Session()
#         r = session.get(url, stream=True)
#         token = next((v for k, v in r.cookies.items() if "download_warning" in k), None)
#         if token:
#             r = session.get(url, params={"confirm": token}, stream=True)
#         with open(path, "wb") as f:
#             for chunk in r.iter_content(32768):
#                 f.write(chunk)

# download_from_drive()

def duck_query(sql):
    con = duckdb.connect()
    df = con.execute(sql).df()
    con.close()
    return df

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
    SELECT MIN(EXTRACT(YEAR FROM datetime))::int AS year_min,
           MAX(EXTRACT(YEAR FROM datetime))::int AS year_max,
           MIN(population)::int AS pop_min,
           MAX(population)::int AS pop_max
    FROM read_parquet('{CO2_PARQUET}') WHERE datetime IS NOT NULL
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
    dcc.Graph(id="heatmap", style={"height": "calc(100vh - 160px)", "minHeight": "300px"}, config={"responsive": True}),
    html.Div([
        html.Div([
            html.Div([html.Label("Year range", style=LBL),
                html.Div(dcc.RangeSlider(id="year-slider", min=year_min, max=year_max,
                    value=[year_min, year_max], marks=make_marks(year_min, year_max),
                    step=1, tooltip={"placement": "bottom", "always_visible": False}, allowCross=False,
                ), style={"width": "240px"})], style=ROW),
            html.Div([html.Label("Population", style=LBL),
                html.Div(dcc.RangeSlider(id="population-slider", min=pop_min, max=pop_max,
                    value=[pop_min, pop_max], marks=make_marks(pop_min, pop_max, fmt_pop),
                    step=100_000, tooltip={"placement": "bottom", "always_visible": False}, allowCross=False,
                ), style={"width": "240px"})], style=ROW),
            html.Div([html.Label("Time of day", style=LBL),
                dcc.Dropdown(id="time-dropdown", options=[{"label": t, "value": t} for t in times_of_day],
                    value=times_of_day, multi=True, style={"width": "280px", "fontSize": "12px"})], style=ROW),
            html.Div([html.Label("Season", style=LBL),
                dcc.Dropdown(id="season-dropdown", options=[{"label": s, "value": s} for s in seasons],
                    value=seasons, multi=True, style={"width": "400px", "fontSize": "12px"})], style=ROW),
        ], style={"display": "flex", "flexWrap": "wrap"}),
        html.Div([
            html.Div([html.Label("Var baseline", style=LBL),
                dcc.RadioItems(id="mean-radio",
                    options=[{"label": "Global mean", "value": "global"}, {"label": "Mean by time bin", "value": "timebin"}],
                    value="global", inline=True, labelStyle={"marginRight": "14px", "fontSize": "12px"})], style=ROW),
            html.Div([html.Label("Layout", style=LBL),
                dcc.RadioItems(id="layout-radio",
                    options=[{"label": "Subplots", "value": "subplot"}, {"label": "Interleaved", "value": "interleaved"}],
                    value="subplot", inline=True, labelStyle={"marginRight": "14px", "fontSize": "12px"})], style=ROW),
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
    return np.where(np.isnan(vals), np.nan, vals - baseline)

def make_z(var_arr, cnt_arr):
    return np.where(np.where(np.isnan(cnt_arr), 0, cnt_arr) == 0, np.nan, var_arr)

def sym_lim(arr):
    if np.all(np.isnan(arr)):
        return 1.0
    return float(max(abs(np.nanmin(arr)), abs(np.nanmax(arr))))

def make_hover_text(raw, var, cnt, fmt_r, fmt_v, n_rows, n_cols):
    texts = []
    for i in range(n_rows):
        row = []
        for j in range(n_cols):
            rv, vv, nv = float(raw[i, j]), float(var[i, j]), float(cnt[i, j])
            if np.isnan(rv) or np.isnan(vv) or np.isnan(nv) or nv == 0:
                row.append(None)
            else:
                sign = "+" if vv >= 0 else ""
                row.append(f"{fmt_r(rv)}<br>Var: {sign}{fmt_v(vv)}<br>n={int(nv)}")
        texts.append(row)
    return texts


@app.callback(
    Output("heatmap", "figure"),
    Input("year-slider", "value"),
    Input("population-slider", "value"),
    Input("time-dropdown", "value"),
    Input("season-dropdown", "value"),
    Input("mean-radio", "value"),
    Input("layout-radio", "value"),
)
def update_heatmap(year_range, pop_range, sel_times, sel_seasons, mean_type, layout_mode):
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
    filters = f"""datetime IS NOT NULL
        AND EXTRACT(YEAR FROM datetime) BETWEEN {year_range[0]} AND {year_range[1]}
        AND population BETWEEN {pop_range[0]} AND {pop_range[1]}
        AND {SEASON_CASE} IN ({s_list}) AND {HOUR_CASE} IN ({t_list})"""

    co2_df = duck_query(f"""SELECT city || ', ' || country AS city_label, ({bin_expr}) AS time_bin,
        AVG(xco2) AS val, COUNT(*) AS n FROM read_parquet('{CO2_PARQUET}') WHERE {filters}
        GROUP BY city_label, time_bin ORDER BY city_label, time_bin""")
    sif_df = duck_query(f"""SELECT city || ', ' || country AS city_label, ({bin_expr}) AS time_bin,
        AVG(Daily_SIF_757nm) AS val, COUNT(*) AS n FROM read_parquet('{SIF_PARQUET}') WHERE {filters}
        GROUP BY city_label, time_bin ORDER BY city_label, time_bin""")

    if co2_df.empty and sif_df.empty:
        return empty()

    co2_cities = sorted(set(co2_df["city_label"])) if not co2_df.empty else []
    sif_cities = sorted(set(sif_df["city_label"])) if not sif_df.empty else []
    cities = sorted(set(co2_cities) | set(sif_cities))
    times  = sorted(set(co2_df["time_bin"]) | set(sif_df["time_bin"]))
    nc, nt = len(cities), len(times)

    co2_pv, co2_pn = pivot_dataset(co2_df, cities, times)
    sif_pv, sif_pn = pivot_dataset(sif_df, cities, times)

    co2_var = compute_variance(co2_pv.values, mean_type)
    sif_var = compute_variance(sif_pv.values, mean_type)
    co2_z   = make_z(co2_var, co2_pn.values)
    sif_z   = make_z(sif_var, sif_pn.values)

    co2_sym = sym_lim(co2_z)
    sif_sym = sym_lim(sif_z)

    # Re-compute sym limits using only cities present in each dataset
    # so one dataset's NaN rows don't compress the other's color range
    co2_z_own = co2_z[[i for i, c in enumerate(cities) if c in co2_cities], :]
    sif_z_own = sif_z[[i for i, c in enumerate(cities) if c in sif_cities], :]
    co2_sym = sym_lim(co2_z_own)
    sif_sym = sym_lim(sif_z_own)

    bl = (f"Global mean — CO₂: {float(np.nanmean(co2_pv.values)):.2f} ppm | SIF: {float(np.nanmean(sif_pv.values)):.4f}"
          if mean_type == "global" else "Var vs mean per time bin")

    TF = dict(family="Arial", size=10, color="black")
    AF = dict(family="Arial", size=11, color="black")

    base_layout = dict(
        title=dict(text=f"CO₂ & SIF Variance  <span style='font-size:11px;color:#888'>{bl}</span>",
                   font=dict(family="Arial", size=14, color="black")),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Arial", size=11), autosize=True, hovermode="closest",
    )

    co2_hover = make_hover_text(co2_pv.values, co2_var, co2_pn.values,
                                lambda v: f"CO₂: {v:.2f} ppm", lambda v: f"{v:.2f} ppm", nc, nt)
    sif_hover = make_hover_text(sif_pv.values, sif_var, sif_pn.values,
                                lambda v: f"SIF: {v:.4f}", lambda v: f"{v:.4f}", nc, nt)

    if layout_mode == "subplot":
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.5])

        fig.add_trace(go.Heatmap(
            z=co2_z, x=times, y=cities,
            colorscale="RdBu_r", zmid=0, zmin=-co2_sym, zmax=co2_sym,
            colorbar=dict(title=dict(text="CO₂ var<br>(ppm)", font=dict(family="Arial", size=10)),
                tickformat="+.1f", tickfont=TF, lenmode="fraction", len=0.44,
                y=0.75, yanchor="middle", x=1.02, xanchor="left", thickness=12, outlinewidth=0),
            text=co2_hover, hoverinfo="text", name="CO₂",
        ), row=1, col=1)

        fig.add_trace(go.Heatmap(
            z=sif_z, x=times, y=cities,
            colorscale="PRGn", zmid=0, zmin=-sif_sym, zmax=sif_sym,
            colorbar=dict(title=dict(text="SIF var", font=dict(family="Arial", size=10)),
                tickformat="+.3f", tickfont=TF, lenmode="fraction", len=0.44,
                y=0.25, yanchor="middle", x=1.02, xanchor="left", thickness=12, outlinewidth=0),
            text=sif_hover, hoverinfo="text", name="SIF",
        ), row=2, col=1)

        fig.update_xaxes(tickfont=TF, showticklabels=False, row=1, col=1)
        fig.update_xaxes(tickfont=TF, title="Time", title_font=AF, row=2, col=1)
        subplot_h = max(400, nc * 2 * 18 + 140)
        tick_size_sub = max(7, min(11, int((subplot_h - 140) / (nc * 2) * 0.65)))
        for r in [1, 2]:
            fig.update_yaxes(tickfont=dict(family="Arial", size=tick_size_sub, color="black"),
                             autorange="reversed", title=None, row=r, col=1)
        fig.update_layout(**base_layout, margin=dict(l=170, r=120, t=52, b=42), height=subplot_h)

    else:
        n_rows = nc * 2
        y_all = []
        for city in cities:
            y_all.append(city)
            y_all.append(city + "\u200b")

        tick_text = [t for city in cities for t in (city, "")]

        z_co2_il   = np.full((n_rows, nt), np.nan)
        z_sif_il   = np.full((n_rows, nt), np.nan)
        txt_co2_il = [[None] * nt for _ in range(n_rows)]
        txt_sif_il = [[None] * nt for _ in range(n_rows)]

        for i in range(nc):
            z_co2_il[i * 2]         = co2_z[i]
            z_sif_il[i * 2 + 1]     = sif_z[i]
            txt_co2_il[i * 2]       = co2_hover[i]
            txt_sif_il[i * 2 + 1]   = sif_hover[i]

        graph_h   = max(300, nc * 2 * 18 + 120)
        tick_size = max(7, min(11, int((graph_h - 120) / (nc * 2) * 0.7)))
        left_margin = max(120, min(240, max(len(c) for c in cities) * 7))

        fig = go.Figure([
            go.Heatmap(
                z=z_co2_il, x=times, y=y_all,
                colorscale="RdBu_r", zmid=0, zmin=-co2_sym, zmax=co2_sym,
                colorbar=dict(title=dict(text="CO₂ var<br>(ppm)", font=dict(family="Arial", size=10)),
                    tickformat="+.1f", tickfont=TF, lenmode="fraction", len=0.82,
                    y=0.5, yanchor="middle", x=1.02, xanchor="left", thickness=12, outlinewidth=0),
                text=txt_co2_il, hoverinfo="text", name="CO₂",
            ),
            go.Heatmap(
                z=z_sif_il, x=times, y=y_all,
                colorscale="PRGn", zmid=0, zmin=-sif_sym, zmax=sif_sym,
                colorbar=dict(title=dict(text="SIF var", font=dict(family="Arial", size=10)),
                    tickformat="+.3f", tickfont=TF, lenmode="fraction", len=0.82,
                    y=0.5, yanchor="middle", x=1.14, xanchor="left", thickness=12, outlinewidth=0),
                text=txt_sif_il, hoverinfo="text", name="SIF",
            ),
        ])

        fig.update_layout(
            **base_layout,
            yaxis=dict(tickfont=dict(family="Arial", size=tick_size, color="black"),
                autorange="reversed", tickmode="array", tickvals=y_all, ticktext=tick_text, title=None),
            xaxis=dict(title="Time", title_font=AF, tickfont=TF),
            margin=dict(l=left_margin, r=180, t=52, b=42),
            height=graph_h,
        )

    return fig


if __name__ == "__main__":
    app.run(debug=True, port=8053)
