"""Tab 3 — Cancellations"""

import pandas as pd
from dash import html, dcc, callback, Output, Input
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_loader import cancelled_by_month, carrier_cancel, all_dests_cancel, MONTH_MAP, MONTH_ORDER

layout = html.Div([
    html.H2("Cancellations", className="tab-title"),

    html.Div([
        html.Div([
            html.Label("Origin Airport:"),
            dcc.Dropdown(
                id="p3-airport",
                options=[{"label":"All airports","value":"ALL"},
                         {"label":"JFK","value":"JFK"},
                         {"label":"LGA","value":"LGA"},
                         {"label":"EWR","value":"EWR"}],
                value="ALL", clearable=False, style={"width":"200px"},
            ),
        ], style={"flex":"1"}),
        html.Div([
            html.Label("Destination (carrier chart):"),
            dcc.Dropdown(
                id="p3-dest",
                options=[{"label":"All destinations","value":"ALL"}] +
                        [{"label":d,"value":d} for d in all_dests_cancel],
                value="ALL", clearable=False, style={"width":"260px"},
            ),
        ], style={"flex":"1.6"}),
    ], style={"display":"flex","gap":"16px","marginBottom":"16px"}),

    html.Div([
        html.Div([dcc.Graph(id="p3-monthly", style={"height":"500px"})], style={"flex":"1"}),
        html.Div([dcc.Graph(id="p3-carrier", style={"height":"500px"})], style={"flex":"1.6"}),
    ], style={"display":"flex","gap":"16px"}),
])


@callback(Output("p3-monthly","figure"), Input("p3-airport","value"))
def update_monthly(airport):
    df = cancelled_by_month.copy()
    if airport != "ALL":
        df = df[df["origin"]==airport]
    df = (
        df.groupby("month", as_index=False)
        .agg(total=("total","sum"), cancelled=("cancelled","sum"))
        .assign(cancel_rate=lambda x: 100*x["cancelled"]/x["total"],
                month_name=lambda x: x["month"].map(MONTH_MAP))
    )
    df["month_name"] = pd.Categorical(df["month_name"], categories=MONTH_ORDER, ordered=True)
    df = df.sort_values("month_name")

    feb_rate = float(df.loc[df["month"]==2,"cancel_rate"].values[0])
    fig = go.Figure()
    for _, row in df.iterrows():
        is_feb = row["month"]==2
        fig.add_trace(go.Bar(
            x=[row["month_name"]], y=[row["cancel_rate"]],
            marker_color="#dc2626" if is_feb else "#60a5fa",
            marker_opacity=1.0 if is_feb else 0.75,
            showlegend=False,
            hovertemplate=(f"<b>{row['month_name']}</b><br>"
                           f"Cancel rate: {row['cancel_rate']:.2f}%<br>"
                           f"Cancelled: {int(row['cancelled']):,}<br>"
                           f"Total: {int(row['total']):,}<extra></extra>"),
        ))
    fig.add_annotation(
        x="Feb", y=feb_rate+0.25,
        text="Survivor bias:<br>worst-weather flights cancelled —<br>not in delay stats",
        showarrow=True, arrowhead=2, arrowcolor="#dc2626",
        ax=72, ay=-52,
        font=dict(size=10, color="#dc2626"),
        bgcolor="#fff1f2", bordercolor="#fca5a5", borderwidth=1, borderpad=4,
    )
    fig.update_layout(
        title=f"Monthly Cancellation Rate by Airport — {airport}",
        xaxis_title=None, yaxis_title="Cancellation Rate (%)",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(family="Inter,sans-serif", color="#1e293b"), bargap=0.2,
    )
    fig.update_yaxes(gridcolor="#f1f5f9")
    return fig


@callback(Output("p3-carrier","figure"),
          Input("p3-airport","value"), Input("p3-dest","value"))
def update_carrier(airport, dest):
    df = carrier_cancel.copy()
    if airport != "ALL":
        df = df[df["origin"]==airport]
    if dest != "ALL":
        df = df[df["dest"]==dest]
    if df.empty:
        return go.Figure().update_layout(title="No data for this selection",
                                         plot_bgcolor="#ffffff", paper_bgcolor="#ffffff")
    df = (
        df.groupby(["month","name"], as_index=False)
        .agg(total=("total","sum"), cancelled=("cancelled","sum"))
        .assign(cancel_pct=lambda x: 100*x["cancelled"]/x["total"])
    )
    mean_rate = df["cancel_pct"].mean()
    carriers  = sorted(df["name"].unique())
    n = len(carriers); ncols = min(3,n); nrows = -(-n//ncols)

    fig = make_subplots(rows=nrows, cols=ncols, subplot_titles=carriers,
                        vertical_spacing=0.12, horizontal_spacing=0.08)
    for idx, name in enumerate(carriers):
        r, c = idx//ncols+1, idx%ncols+1
        sub  = df[df["name"]==name].sort_values("month")
        fig.add_trace(go.Scatter(
            x=sub["month"], y=sub["cancel_pct"], mode="lines+markers",
            line=dict(color="#6366f1", width=2), marker=dict(size=5, color="#a5b4fc"),
            showlegend=False,
            hovertemplate="Month %{x}<br>Cancel rate: %{y:.1f}%<extra></extra>",
        ), row=r, col=c)
        fig.add_hline(y=mean_rate, line_dash="dash", line_color="#dc2626",
                      line_width=1, opacity=0.6, row=r, col=c)
    fig.update_xaxes(tickvals=list(range(1,13)),
                     ticktext=["J","F","M","A","M","J","J","A","S","O","N","D"])
    fig.update_yaxes(rangemode="tozero", gridcolor="#f1f5f9")
    fig.update_layout(
        title=f"Monthly Cancellation Rate by Carrier  (red dashed = mean {mean_rate:.1f}%)",
        height=max(320,260*nrows),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(family="Inter,sans-serif", color="#1e293b"),
    )
    return fig
