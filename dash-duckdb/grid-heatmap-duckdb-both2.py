# grid-heatmap-duckdb.py
# VERSION A: two subplots (stable) + VERSION B: interleaved (experimental, toggled by radio)
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
PARQUET_DIR = "/Users/heyutian/Downloads/oco3_parquet"
CO2_PARQUET = os.path.join(PARQUET_DIR, "co2_sam.parquet")
SIF_PARQUET = os.path.join(PARQUET_DIR, "sif_sam.parquet")


def duck_query(sql):
    con = duckdb.connect()
    df  = con.execute(sql).df()
    con.close()
    return df


SEASON_CASE = """
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

HOUR_CASE = """
    CASE
        WHEN EXTRACT(HOUR FROM local_time) < 6  THEN 'Night'
        WHEN EXTRACT(HOUR FROM local_time) < 12 THEN 'Morning'
        WHEN EXTRACT(HOUR FROM local_time) < 18 THEN 'Afternoon'
        ELSE 'Evening'
    END
"""

TIME_BIN_SQL = {
    "Month":      "strftime(DATE_TRUNC('month', datetime), '%Y-%m')",
    "Half-Month": """CASE
        WHEN EXTRACT(DAY FROM datetime) <= 15
            THEN strftime(DATE_TRUNC('month', datetime), '%Y-%m') || '-01'
        ELSE strftime(DATE_TRUNC('month', datetime), '%Y-%m') || '-16'
    END""",
    "Day": "strftime(CAST(datetime AS DATE), '%Y-%m-%d')",
}

COLORSCALE_CO2 = "RdBu_r"
COLORSCALE_SIF = "PRGn"


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
    WHERE datetime IS NOT NULL ORDER BY 1
""")['season'].tolist())

times_of_day = sorted(duck_query(f"""
    SELECT DISTINCT {HOUR_CASE} AS time_of_day
    FROM read_parquet('{CO2_PARQUET}')
    WHERE local_time IS NOT NULL ORDER BY 1
""")['time_of_day'].tolist())


def fmt_pop(v):
    if v >= 1_000_000: return f"{v/1e6:.0f}M"
    if v >= 1_000:     return f"{v/1e3:.0f}K"
    return str(int(v))

def simple_marks(mn, mx):
    mid = (mn + mx) // 2
    return {mn: str(mn), mid: str(mid), mx: str(mx)}

def pop_marks(mn, mx):
    mid = (mn + mx) // 2
    return {mn: fmt_pop(mn), mid: fmt_pop(mid), mx: fmt_pop(mx)}


app    = dash.Dash(__name__)
server = app.server

CTRL  = {"display": "flex", "alignItems": "center", "margin": "3px 10px"}
LABEL = {"marginRight": "8px", "width": "110px", "fontWeight": "bold",
         "fontSize": "12px", "flexShrink": "0"}

app.layout = html.Div([

    dcc.Graph(
        id='heatmap',
        style={"height": "calc(100vh - 170px)", "minHeight": "300px"},
        config={"responsive": True},
    ),

    html.Div([
        html.Div([
            html.Div([
                html.Label("Year range", style=LABEL),
                html.Div(dcc.RangeSlider(
                    id='year-slider',
                    min=year_min, max=year_max,
                    value=[year_min, year_max],
                    marks=simple_marks(year_min, year_max),
                    step=1,
                    tooltip={"placement": "bottom", "always_visible": False},
                    allowCross=False,
                ), style={"width": "260px"}),
            ], style=CTRL),

            html.Div([
                html.Label("Population", style=LABEL),
                html.Div(dcc.RangeSlider(
                    id='population-slider',
                    min=pop_min, max=pop_max,
                    value=[pop_min, pop_max],
                    marks=pop_marks(pop_min, pop_max),
                    step=100_000,
                    tooltip={"placement": "bottom", "always_visible": False},
                    allowCross=False,
                ), style={"width": "260px"}),
            ], style=CTRL),

            html.Div([
                html.Label("Time of day", style=LABEL),
                dcc.Dropdown(
                    id="time-dropdown",
                    options=[{"label": t, "value": t} for t in times_of_day],
                    value=times_of_day, multi=True,
                    style={"width": "280px", "fontSize": "12px"},
                )
            ], style=CTRL),

            html.Div([
                html.Label("Season", style=LABEL),
                dcc.Dropdown(
                    id="season-dropdown",
                    options=[{"label": s, "value": s} for s in seasons],
                    value=seasons, multi=True,
                    style={"width": "420px", "fontSize": "12px"},
                )
            ], style=CTRL),
        ], style={"display": "flex", "flexWrap": "wrap"}),

        html.Div([
            html.Div([
                html.Label("Variance baseline", style=LABEL),
                dcc.RadioItems(
                    id="mean-radio",
                    options=[
                        {"label": "Global mean",       "value": "global"},
                        {"label": "Mean by time bin",  "value": "timebin"},
                    ],
                    value="global",
                    inline=True,
                    labelStyle={"marginRight": "16px", "fontSize": "12px"},
                ),
            ], style=CTRL),

            html.Div([
                html.Label("Layout", style=LABEL),
                dcc.RadioItems(
                    id="layout-radio",
                    options=[
                        {"label": "Subplots",     "value": "subplot"},
                        {"label": "Interleaved",  "value": "interleaved"},
                    ],
                    value="subplot",
                    inline=True,
                    labelStyle={"marginRight": "16px", "fontSize": "12px"},
                ),
            ], style=CTRL),
        ], style={"display": "flex", "flexWrap": "wrap", "marginTop": "2px"}),

    ], style={"paddingTop": "2px"}),

], style={"fontFamily": "Arial, sans-serif", "background": "white",
          "padding": "6px 14px", "boxSizing": "border-box"})


def compute_variance(pv_vals, mean_type, axis_label="col"):
    """
    Subtract mean from pv_vals (numpy array, shape nc x nt).
    mean_type: 'global'  → single scalar mean
               'timebin' → mean over cities per time column (axis=0)
    Returns var array same shape, NaN preserved.
    """
    if mean_type == "global":
        m = np.nanmean(pv_vals)
        baseline = m
    else:
        m = np.nanmean(pv_vals, axis=0, keepdims=True)
        baseline = m

    var = np.where(np.isnan(pv_vals), np.nan, pv_vals - baseline)
    return var, baseline


def build_customdata(raw_vals, var_vals, cnt_vals, fmt_raw, fmt_var):
    """Build (nc, nt, 3) customdata array: [raw_str, var_str, count_str].
    Only populated for cells that have soundings AND a valid raw value.
    All other cells are left as empty strings — but those cells will already
    be NaN in z (from mask_zero_soundings), so Plotly never fires hover on them.
    """
    nc, nt = raw_vals.shape
    cd = np.empty((nc, nt, 3), dtype=object)
    cd[:] = ""
    for i in range(nc):
        for j in range(nt):
            rv = raw_vals[i, j]
            vv = var_vals[i, j]
            nv = cnt_vals[i, j]
            nv_safe = nv if not np.isnan(nv) else 0
            if np.isnan(rv) or np.isnan(vv) or int(nv_safe) == 0:
                continue
            sign = "+" if vv >= 0 else ""
            cd[i, j, 0] = fmt_raw(rv)
            cd[i, j, 1] = sign + fmt_var(vv)
            cd[i, j, 2] = str(int(nv))
    return cd


def mask_zero_soundings(z_arr, cnt_vals):
    """Return z with NaN wherever soundings == 0, NaN, or raw value is NaN.
    NaN z → no pixel rendered, no hover fired by Plotly.
    cnt_vals may contain NaN for cities absent from a parquet; treat as 0.
    """
    cnt_safe = np.where(np.isnan(cnt_vals), 0, cnt_vals)
    return np.where(cnt_safe == 0, np.nan, z_arr)


@app.callback(
    Output("heatmap", "figure"),
    Input("year-slider",       "value"),
    Input("population-slider", "value"),
    Input("time-dropdown",     "value"),
    Input("season-dropdown",   "value"),
    Input("mean-radio",        "value"),
    Input("layout-radio",      "value"),
)
def update_heatmap(year_range, population_range, selected_times,
                   selected_seasons, mean_type, layout_mode):

    def empty(msg="No data for selected filters"):
        f = go.Figure()
        f.add_annotation(text=msg, xref="paper", yref="paper",
                         x=0.5, y=0.5, showarrow=False, font=dict(size=15))
        f.update_layout(paper_bgcolor="white", plot_bgcolor="white",
                        margin=dict(l=10, r=10, t=10, b=10))
        return f

    if not selected_times or not selected_seasons:
        return empty()

    season_list = ",".join(f"'{s}'" for s in selected_seasons)
    time_list   = ",".join(f"'{t}'" for t in selected_times)
    bin_expr    = TIME_BIN_SQL["Month"]

    filters = f"""
        datetime IS NOT NULL
        AND EXTRACT(YEAR FROM datetime) BETWEEN {year_range[0]} AND {year_range[1]}
        AND population BETWEEN {population_range[0]} AND {population_range[1]}
        AND {SEASON_CASE} IN ({season_list})
        AND {HOUR_CASE}   IN ({time_list})
    """

    co2_df = duck_query(f"""
        SELECT city || ', ' || country AS city_label,
               ({bin_expr})            AS time_bin,
               AVG(xco2)               AS val,
               COUNT(*)                AS n
        FROM read_parquet('{CO2_PARQUET}')
        WHERE {filters}
        GROUP BY city_label, time_bin
        ORDER BY city_label, time_bin
    """)

    sif_df = duck_query(f"""
        SELECT city || ', ' || country AS city_label,
               ({bin_expr})            AS time_bin,
               AVG(Daily_SIF_757nm)    AS val,
               COUNT(*)                AS n
        FROM read_parquet('{SIF_PARQUET}')
        WHERE {filters}
        GROUP BY city_label, time_bin
        ORDER BY city_label, time_bin
    """)

    if co2_df.empty and sif_df.empty:
        return empty()

    cities = sorted(set(co2_df['city_label']) | set(sif_df['city_label']))
    times  = sorted(set(co2_df['time_bin'])   | set(sif_df['time_bin']))
    nc, nt = len(cities), len(times)

    def pivot(df):
        if df.empty:
            return (pd.DataFrame(np.nan, index=cities, columns=times),
                    pd.DataFrame(np.nan, index=cities, columns=times))
        pv = df.pivot(index='city_label', columns='time_bin', values='val')
        pn = df.pivot(index='city_label', columns='time_bin', values='n')
        pv = pv.reindex(index=cities, columns=times)
        pn = pn.reindex(index=cities, columns=times)
        pv_masked = pv.where(pn.fillna(0) > 0, other=np.nan)
        return pv_masked, pn

    co2_pv, co2_pn = pivot(co2_df)
    sif_pv, sif_pn = pivot(sif_df)

    co2_var, co2_baseline = compute_variance(co2_pv.values, mean_type)
    sif_var, sif_baseline = compute_variance(sif_pv.values, mean_type)

    co2_abs = float(np.nanmax(np.abs(co2_var))) if not np.all(np.isnan(co2_var)) else 1.0
    sif_abs = float(np.nanmax(np.abs(sif_var))) if not np.all(np.isnan(sif_var)) else 1.0
    co2_vmin, co2_vmax = -co2_abs, co2_abs
    sif_vmin, sif_vmax = -sif_abs, sif_abs

    co2_z = mask_zero_soundings(co2_var, co2_pn.values)
    sif_z = mask_zero_soundings(sif_var, sif_pn.values)

    if mean_type == "global":
        co2_base_str = f"{float(np.nanmean(co2_pv.values)):.2f} ppm"
        sif_base_str = f"{float(np.nanmean(sif_pv.values)):.4f}"
        baseline_label = f"Global mean — CO₂: {co2_base_str} | SIF: {sif_base_str}"
    else:
        baseline_label = "Variance vs mean per time bin"

    cd_co2 = build_customdata(
        co2_pv.values, co2_var, co2_pn.values,
        lambda v: f"{v:.2f} ppm", lambda v: f"{v:.2f} ppm"
    )
    cd_sif = build_customdata(
        sif_pv.values, sif_var, sif_pn.values,
        lambda v: f"{v:.4f}", lambda v: f"{v:.4f}"
    )

    TICK_FONT = dict(family="Arial", size=10, color="black")
    AXIS_FONT = dict(family="Arial", size=11, color="black")

    HT_CO2 = (
        "<b>%{y}</b><br>"
        "Time: %{x}<br>"
        "CO₂: %{customdata[0]}<br>"
        "Var: %{customdata[1]}<br>"
        "Soundings: %{customdata[2]}"
        "<extra></extra>"
    )
    HT_SIF = (
        "<b>%{y}</b><br>"
        "Time: %{x}<br>"
        "SIF: %{customdata[0]}<br>"
        "Var: %{customdata[1]}<br>"
        "Soundings: %{customdata[2]}"
        "<extra></extra>"
    )

    if layout_mode == "subplot":

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.5, 0.5],
        )

        fig.add_trace(go.Heatmap(
            z=co2_z, x=times, y=cities,
            colorscale=COLORSCALE_CO2,
            zmid=0, zmin=co2_vmin, zmax=co2_vmax,
            colorbar=dict(
                title=dict(text="CO₂ var<br>(ppm)", font=dict(family="Arial", size=10)),
                tickformat="+.1f", tickfont=TICK_FONT,
                lenmode="fraction", len=0.44,
                y=0.75, yanchor="middle",
                x=1.02, xanchor="left",
                thickness=12, outlinewidth=0,
            ),
            customdata=cd_co2, hovertemplate=HT_CO2,
            name="CO₂", showscale=True,
        ), row=1, col=1)

        fig.add_trace(go.Heatmap(
            z=sif_z, x=times, y=cities,
            colorscale=COLORSCALE_SIF,
            zmid=0, zmin=sif_vmin, zmax=sif_vmax,
            colorbar=dict(
                title=dict(text="SIF var", font=dict(family="Arial", size=10)),
                tickformat="+.3f", tickfont=TICK_FONT,
                lenmode="fraction", len=0.44,
                y=0.25, yanchor="middle",
                x=1.02, xanchor="left",
                thickness=12, outlinewidth=0,
            ),
            customdata=cd_sif, hovertemplate=HT_SIF,
            name="SIF", showscale=True,
        ), row=2, col=1)

        fig.update_xaxes(tickfont=TICK_FONT, showticklabels=False, row=1, col=1)
        fig.update_xaxes(tickfont=TICK_FONT, title="Time", title_font=AXIS_FONT, row=2, col=1)
        for row in [1, 2]:
            fig.update_yaxes(tickfont=TICK_FONT, autorange="reversed",
                             title=None, row=row, col=1)

        fig.update_layout(
            title=dict(
                text=(f"CO₂ & SIF Variance  "
                      f"<span style='font-size:11px;color:#888'>{baseline_label}</span>"),
                font=dict(family="Arial", size=14, color="black"),
            ),
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="Arial", size=11),
            autosize=True,
            margin=dict(l=170, r=120, t=52, b=42),
            hovermode="closest",
        )

    else:  # interleaved

        n_rows = nc * 2

        y_all = []
        for city in cities:
            y_all.append(city)
            y_all.append(city + "\u200b")


        tick_vals = y_all
        tick_text = []
        for city in cities:
            tick_text.append(city)
            tick_text.append("")

        z_co2_il = np.full((n_rows, nt), np.nan)
        z_sif_il = np.full((n_rows, nt), np.nan)
        cd_co2_il = np.empty((n_rows, nt, 3), dtype=object)
        cd_sif_il = np.empty((n_rows, nt, 3), dtype=object)
        cd_co2_il[:] = ""
        cd_sif_il[:] = ""

        for i in range(nc):
            r_co2 = i * 2
            r_sif = i * 2 + 1
            z_co2_il[r_co2, :] = co2_z[i, :]
            z_sif_il[r_sif, :] = sif_z[i, :]
            cd_co2_il[r_co2, :, :] = cd_co2[i, :, :]
            cd_sif_il[r_sif, :, :] = cd_sif[i, :, :]

        fig = go.Figure()

        fig.add_trace(go.Heatmap(
            z=z_co2_il, x=times, y=y_all,
            colorscale=COLORSCALE_CO2,
            zmid=0, zmin=co2_vmin, zmax=co2_vmax,
            colorbar=dict(
                title=dict(text="CO₂ var<br>(ppm)", font=dict(family="Arial", size=10)),
                tickformat="+.1f", tickfont=TICK_FONT,
                lenmode="fraction", len=0.82,
                y=0.5, yanchor="middle",
                x=1.02, xanchor="left",
                thickness=12, outlinewidth=0,
            ),
            customdata=cd_co2_il, hovertemplate=HT_CO2,
            name="CO₂", showscale=True,
        ))

        fig.add_trace(go.Heatmap(
            z=z_sif_il, x=times, y=y_all,
            colorscale=COLORSCALE_SIF,
            zmid=0, zmin=sif_vmin, zmax=sif_vmax,
            colorbar=dict(
                title=dict(text="SIF var", font=dict(family="Arial", size=10)),
                tickformat="+.3f", tickfont=TICK_FONT,
                lenmode="fraction", len=0.82,
                y=0.5, yanchor="middle",
                x=1.14, xanchor="left",
                thickness=12, outlinewidth=0,
            ),
            customdata=cd_sif_il, hovertemplate=HT_SIF,
            name="SIF", showscale=True,
        ))

        shapes = []
        for i in range(1, nc):
            shapes.append(dict(
                type="line", xref="paper", yref="y",
                x0=0, x1=1,
                y0=cities[i - 1] + "\u200b",
                y1=cities[i],
                line=dict(color="rgba(0,0,0,0)", width=0),
            ))

        fig.update_layout(
            yaxis=dict(
                tickfont=TICK_FONT,
                autorange="reversed",
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text,
                title=None,
            ),
            xaxis=dict(title="Time", title_font=AXIS_FONT, tickfont=TICK_FONT),
            title=dict(
                text=(f"CO₂ & SIF Variance (Interleaved)  "
                      f"<span style='font-size:11px;color:#888'>{baseline_label}</span>"),
                font=dict(family="Arial", size=14, color="black"),
            ),
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="Arial", size=11),
            autosize=True,
            margin=dict(l=170, r=180, t=52, b=42),
            hovermode="closest",
        )

    return fig


if __name__ == "__main__":
    app.run(debug=True, port=8053)
