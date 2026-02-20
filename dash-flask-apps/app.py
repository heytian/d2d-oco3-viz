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

df['year'] = df['datetime'].dt.year
df['month'] = df['datetime'].dt.month

def classify_climate(row):
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
        # FLIPPED seasons
        if month in [12, 1, 2]:
            return "Summer (South)"
        elif month in [3, 4, 5]:
            return "Autumn (South)"
        elif month in [6, 7, 8]:
            return "Winter (South)"
        else:
            return "Spring (South)"

    return "Other"

df["climate_zone"] = df.apply(classify_climate, axis=1)

df["local_time"] = pd.to_datetime(
    df["local_time"],
    format="%m/%d/%y %H:%M",
    errors="coerce"
)

df["hour"] = df["local_time"].dt.hour

df["day_night"] = np.where(
    (df["hour"] >= 6) & (df["hour"] < 18),
    "Day",
    "Night"
)


app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Grid-Sorting-Viz"),

    html.Div([
        html.Label("Time Range"),
        dcc.RangeSlider(
            id='year-slider',
            min=int(df['year'].min()),
            max=int(df['year'].max()),
            value=[int(df['year'].min()), int(df['year'].max())],
            marks={
                int(y): str(int(y))
                for y in sorted(df['year'].unique())
            },
            step=1
        )

    ], style={'width':'80%', 'margin':'20px'}),

    html.Div([
        html.Label("Vertical Axis"),
        dcc.Dropdown(
            id='y-axis-dropdown',
            options=[
                {'label':'Population', 'value':'population'},
            ],
            value='population'
        ),
        html.Label("Square Metric"),
        dcc.Dropdown(
            id='square-metric-dropdown',
            options=[
                {'label':'Data Density', 'value':'density'},
                {'label':'CO2 Level', 'value':'xco2'}
            ],
            value='xco2'
        ),

        html.Label("Climate Zone"),
        dcc.Dropdown(
            id='climate-dropdown',
            options=[{'label':z, 'value':z} for z in df['climate_zone'].unique()],
            multi=True
        ),

        html.Label("Day / Night"),
        dcc.Dropdown(
            id='daynight-dropdown',
            options=[
                {'label':'Day', 'value':'Day'},
                {'label':'Night', 'value':'Night'}
            ],
            multi=True
        ),

        html.Label("Sort by Population"),
        dcc.Dropdown(
            id='population-sort',
            options=[
                {'label':'High → Low', 'value':'desc'},
                {'label':'Low → High', 'value':'asc'}
            ]
        )

    ], style={'width':'40%', 'display':'inline-block', 'margin':'20px'}),

    dcc.Graph(id='grid-graph')
])

@app.callback(
    Output('grid-graph', 'figure'),
    Input('year-slider', 'value'),
    Input('y-axis-dropdown', 'value'),
    Input('square-metric-dropdown', 'value'),
    Input('climate-dropdown', 'value'),
    Input('daynight-dropdown', 'value'),
    Input('population-sort', 'value')
)

# def update_graph(year_range, y_axis, square_metric):
#     filtered = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]

#     bins_x = pd.date_range(filtered['datetime'].min(), filtered['datetime'].max(), periods=50)
#     bins_y = np.linspace(filtered[y_axis].min(), filtered[y_axis].max(), 50)

#     filtered['x_bin'] = pd.cut(filtered['datetime'], bins=bins_x)
#     filtered['y_bin'] = pd.cut(filtered[y_axis], bins=bins_y)

#     if square_metric == 'density':
#         agg = filtered.groupby(['x_bin','y_bin']).size().reset_index(name='value')
#     else:
#         agg = filtered.groupby(['x_bin','y_bin'])['xco2'].mean().reset_index(name='value')

#     agg['x_center'] = agg['x_bin'].apply(lambda x: x.mid)
#     agg['y_center'] = agg['y_bin'].apply(lambda x: x.mid)

#     fig = px.scatter(
#         agg, x='x_center', y='y_center', size='value', color='value',
#         color_continuous_scale='Viridis',
#         labels={'x_center':'Time', 'y_center':y_axis, 'value':square_metric},
#         hover_data={'x_center':True,'y_center':True,'value':True}
#     )

#     fig.update_traces(marker=dict(sizemode='area', sizeref=2.*max(agg['value'])/(40.**2), line_width=0))
#     fig.update_layout(title="CO2 Grid by Time and "+y_axis.capitalize())

#     return fig

def update_graph(year_range, y_axis, square_metric,
                 climate_filter, daynight_filter, pop_sort):

    filtered = df[
        (df['year'] >= year_range[0]) &
        (df['year'] <= year_range[1])
    ]

    if climate_filter:
        filtered = filtered[filtered['climate_zone'].isin(climate_filter)]

    if daynight_filter:
        filtered = filtered[filtered['day_night'].isin(daynight_filter)]

    if pop_sort == 'desc':
        filtered = filtered.sort_values('population', ascending=False)
    elif pop_sort == 'asc':
        filtered = filtered.sort_values('population', ascending=True)


if __name__ == "__main__":
    app.run(debug=True, port=8051)

# To run this app, open terminal inside VS code, activate venv, and "pip install dash plotly pandas numpy", then "python app.py"

