"""
app.py — NYC Flights 2013 Dashboard  v4
Run:   python3 app.py
Open:  http://127.0.0.1:8050
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import dash
from dash import html, dcc, Output, Input

from pages import (p1_best_airport, p2_best_carrier, p3_cancellations,
                   p4_delay, p5_destinations, p6_fleet)

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "NYC Flights 2013"

_TAB = {
    "padding":"10px 20px",
    "fontFamily":"Inter,sans-serif",
    "fontSize":"0.9rem",
    "color":"#64748b",
    "borderBottom":"2px solid transparent",
    "backgroundColor":"#ffffff",
}
_TAB_SEL = {**_TAB,
    "color":"#4338ca",
    "fontWeight":"700",
    "borderBottom":"2px solid #6366f1",
    "backgroundColor":"#f8fafc",
}

app.layout = html.Div([

    html.Div([
        html.Div([
            html.Span("✈️", style={"fontSize":"1.6rem","marginRight":"10px"}),
            html.Span("NYC Flights 2013",
                      style={"fontSize":"1.4rem","fontWeight":"700","color":"#ffffff",
                             "letterSpacing":"-0.3px"}),
        ], style={"display":"flex","alignItems":"center"}),
        html.Span("Interactive Analysis Dashboard",
                  style={"fontSize":"0.82rem","color":"#94a3b8","marginTop":"2px"}),
    ], style={
        "background":"linear-gradient(135deg, #1e293b 0%, #334155 100%)",
        "padding":"16px 32px",
        "display":"flex","alignItems":"center","justifyContent":"space-between",
        "boxShadow":"0 1px 4px rgba(0,0,0,0.15)",
    }),

    html.Div([
        dcc.Tabs(id="main-tabs", value="tab-airport",
            children=[
                dcc.Tab(label="Best Airport in NYC",   value="tab-airport",  style=_TAB, selected_style=_TAB_SEL),
                dcc.Tab(label="Best Carrier from NYC", value="tab-carrier",  style=_TAB, selected_style=_TAB_SEL),
                dcc.Tab(label="Cancellations",         value="tab-cancel",   style=_TAB, selected_style=_TAB_SEL),
                dcc.Tab(label="Delay",                 value="tab-delay",    style=_TAB, selected_style=_TAB_SEL),
                dcc.Tab(label="Carrier - Market Share",  value="tab-dest",     style=_TAB, selected_style=_TAB_SEL),
                dcc.Tab(label="Fleet",                 value="tab-fleet",    style=_TAB, selected_style=_TAB_SEL),
            ],
            style={"borderBottom":"1px solid #e2e8f0"},
        ),
    ], style={"backgroundColor":"#ffffff","boxShadow":"0 1px 3px rgba(0,0,0,0.06)"}),

    html.Div(id="main-content",
             style={"padding":"28px 36px","backgroundColor":"#f8fafc","minHeight":"90vh"}),

], style={"fontFamily":"Inter,sans-serif","backgroundColor":"#f8fafc"})


@app.callback(Output("main-content","children"), Input("main-tabs","value"))
def render_tab(tab):
    return {
        "tab-airport": p1_best_airport.layout,
        "tab-carrier": p2_best_carrier.layout,
        "tab-cancel":  p3_cancellations.layout,
        "tab-delay":   p4_delay.layout,
        "tab-dest":    p5_destinations.layout,
        "tab-fleet":   p6_fleet.layout,
    }.get(tab, html.P("Page not found"))


if __name__ == "__main__":
    app.run(debug=True)
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
