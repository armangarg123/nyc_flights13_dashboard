"""Tab 6 — Fleet"""

import pandas as pd
from dash import html, dcc, callback, Output, Input
import plotly.express as px
import plotly.graph_objects as go

from data_loader import fleet_data, top_manufacturers, MONTH_ORDER

layout = html.Div([
    html.H2("Fleet Analysis", className="tab-title"),

    html.Div([
        html.Div([
            html.Label("Minimum seats (affects both charts):"),
            dcc.Slider(id="p6-seats", min=0, max=400, step=10, value=50,
                       marks={0:"0",50:"50",100:"100",200:"200",400:"400"},
                       tooltip={"placement":"bottom"}),
        ], style={"width":"440px"}),
        html.Div([
            html.Label("Manufacturers (affects both charts):"),
            dcc.Checklist(id="p6-mfr",
                options=[{"label":m,"value":m} for m in top_manufacturers],
                value=[m for m in top_manufacturers if m!="Other"],
                inline=True, className="checklist-inline"),
        ]),
    ], className="control-row", style={"alignItems":"flex-start","gap":"48px"}),

    html.Div([
        html.Div([dcc.Graph(id="p6-plane",   style={"height":"580px"})], style={"flex":"1"}),
        html.Div([dcc.Graph(id="p6-mfr-line",style={"height":"580px"})], style={"flex":"1"}),
    ], style={"display":"flex","gap":"16px"}),
])


@callback(Output("p6-plane","figure"), Output("p6-mfr-line","figure"),
          Input("p6-seats","value"), Input("p6-mfr","value"))
def update_fleet(min_seats, selected_mfr):
    selected_mfr = selected_mfr or []
    row, dests, mfr_time = fleet_data(min_seats)

    # ── Left: most frequent plane ─────────────────────────────────────────
    if row is None:
        left = go.Figure().update_layout(
            title="No planes match this filter",
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff")
    else:
        tailnum  = row["tailnum"]
        model    = str(row.get("model",""))
        mfr      = str(row.get("manufacturer_final", row.get("manufacturer","")))
        seats    = int(row["seats"])
        nflights = int(row["num_flights"])
        top3     = dests.head(3)["airport_name"].tolist()
        top3_str = " · ".join(top3)

        dest_df = dests.head(15).copy()
        left = go.Figure(go.Bar(
            x=dest_df["num_flights"], y=dest_df["airport_name"],
            orientation="h",
            marker=dict(color=dest_df["num_flights"],
                        colorscale=[[0,"#c7d2fe"],[1,"#312e81"]],showscale=False),
            hovertemplate="<b>%{y}</b><br>Flights: %{x:,}<extra></extra>",
        ))
        left.update_layout(
            title=dict(
                text=f"<b>{mfr} {model}</b>  <span style='color:#6366f1'>({tailnum})</span>",
                x=0, xanchor="left", font=dict(size=16, color="#1e293b"),
            ),
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font=dict(family="Inter,sans-serif", color="#1e293b"),
            margin=dict(l=20,r=20,t=120,b=40),
            annotations=[dict(
                text=(f"<b>Seats:</b> {seats}    "
                      f"<b>Total flights in 2013:</b> {nflights:,}<br>"
                      f"<b>Top 3 destinations:</b> {top3_str}"),
                xref="paper", yref="paper", x=0, y=1.10,
                xanchor="left", yanchor="bottom", showarrow=False,
                font=dict(size=12, color="#334155"),
                bgcolor="#f0f9ff", bordercolor="#7dd3fc",
                borderwidth=1, borderpad=8,
            )],
        )
        left.update_xaxes(gridcolor="#f1f5f9")

    # ── Right: manufacturer over time ─────────────────────────────────────
    df_mfr = mfr_time[mfr_time["manufacturer_final"].isin(selected_mfr)].copy() \
             if not mfr_time.empty else pd.DataFrame()

    if df_mfr.empty:
        right = go.Figure().update_layout(
            title="No data for selected filters",
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff")
    else:
        df_mfr["month_name"] = pd.Categorical(
            df_mfr["month_name"], categories=MONTH_ORDER, ordered=True)
        df_mfr = df_mfr.sort_values("month_name")
        right = px.line(
            df_mfr, x="month_name", y="num_flights",
            color="manufacturer_final", markers=True,
            color_discrete_sequence=px.colors.qualitative.Safe,
            labels={"month_name":"Month","num_flights":"Number of Flights",
                    "manufacturer_final":"Manufacturer"},
        )
        right.update_layout(
            title=f"Flight Volume by Manufacturer  (seats ≥ {min_seats})",
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font=dict(family="Inter,sans-serif",color="#1e293b"),
            legend_title="Manufacturer",
        )
        right.update_yaxes(gridcolor="#f1f5f9")

    return left, right
