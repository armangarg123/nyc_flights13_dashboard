"""Tab 5 — Popular Carrier"""

from dash import html, dcc, callback, Output, Input
import plotly.graph_objects as go

from data_loader import top_dests_for_origin, carrier_share, airport_name, AIRPORT_FULL

ORIGIN_OPTIONS = [
    {"label":"All NYC airports","value":"ALL"},
    {"label":"JFK","value":"JFK"},
    {"label":"LGA","value":"LGA"},
    {"label":"EWR","value":"EWR"},
]

layout = html.Div([
    html.H2("Popular Carrier", className="tab-title"),

    html.Div([
        html.Div([
            html.Label("Origin Airport:"),
            dcc.Dropdown(id="p5-origin", options=ORIGIN_OPTIONS,
                         value="ALL", clearable=False, style={"width":"240px"}),
        ]),
        html.Div([
            html.Label("Destination:"),
            dcc.Dropdown(id="p5-dest", options=[], value=None,
                         clearable=False, style={"width":"380px"}),
        ]),
    ], className="control-row", style={"gap":"32px"}),

    html.Div(id="p5-callout", style={"marginBottom":"12px"}),
    dcc.Graph(id="p5-bar", style={"height":"500px"}),
])


@callback(Output("p5-dest","options"), Output("p5-dest","value"),
          Input("p5-origin","value"))
def update_dest_options(origin):
    dests = top_dests_for_origin(origin, n=5)
    options = (
        [{"label":"All destinations","value":"ALL"}] +
        [{"label":f"{d} — {airport_name.get(d,d)}","value":d} for d in dests]
    )
    return options, "ALL"


@callback(Output("p5-bar","figure"), Output("p5-callout","children"),
          Input("p5-origin","value"), Input("p5-dest","value"))
def update_chart(origin, dest):
    if dest is None:
        return go.Figure().update_layout(plot_bgcolor="#ffffff",paper_bgcolor="#ffffff"), ""

    df = carrier_share(origin, dest)

    # Chart title
    origin_label = "All NYC Airports" if origin=="ALL" else AIRPORT_FULL.get(origin, origin)
    dest_label   = "All Destinations" if dest=="ALL" else f"{airport_name.get(dest,dest)} ({dest})"
    chart_title  = f"{origin_label} → {dest_label} — Carrier Market Share 2013"

    fig = go.Figure(go.Bar(
        x=df["num_flights"], y=df["name"],
        orientation="h",
        marker=dict(
            color=df["num_flights"],
            colorscale=[[0,"#c7d2fe"],[0.5,"#6366f1"],[1,"#312e81"]],
            showscale=False,
        ),
        text=[f"{p:.1f}%" for p in df["pct"]],
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(color="white", size=12),
        customdata=df["pct"],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Flights: %{x:,}<br>"
            "Market share: %{customdata:.1f}%<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=chart_title,
        xaxis_title="Number of Flights",
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(family="Inter,sans-serif", color="#1e293b"),
        margin=dict(l=180, r=60, t=60, b=40),
    )
    fig.update_xaxes(gridcolor="#f1f5f9")

    # Callout
    best_carrier = df.iloc[0]["name"]
    best_pct     = df.iloc[0]["pct"]

    if origin == "ALL" and dest == "ALL":
        msg = f"Most popular carrier across all NYC airports and destinations"
    elif origin == "ALL":
        msg = f"Most popular carrier from all NYC airports to {dest_label}"
    elif dest == "ALL":
        msg = f"Most popular carrier from {AIRPORT_FULL.get(origin,origin)} to all destinations"
    else:
        msg = f"Most popular carrier from {AIRPORT_FULL.get(origin,origin)} to {dest_label}"

    callout = html.Div([
        html.Span(f"✈️  {msg} is  ", style={"fontSize":"1rem","color":"#475569"}),
        html.Span(best_carrier,
                  style={"fontSize":"1.1rem","fontWeight":"700","color":"#4338ca"}),
        html.Span(f"  ({best_pct:.1f}% market share)",
                  style={"fontSize":"0.9rem","color":"#64748b"}),
    ], style={"padding":"12px 18px","borderRadius":"10px","backgroundColor":"#eef2ff",
              "border":"1px solid #a5b4fc","display":"inline-block"})

    return fig, callout
