"""Tab 2 — Best Carrier from NYC"""

import numpy as np
import pandas as pd
from dash import html, dcc, callback, Output, Input, dash_table
import plotly.graph_objects as go
import plotly.express as px

from data_loader import carrier_metrics_df

DIMS = [
    ("Route-Adj Delay (min)",  True,  "Lower is better"),
    ("Cancellation Rate (%)",  True,  "Lower is better"),
    ("Destinations",           False, "Higher is better"),
    ("Fleet Variety (seat σ)", False, "Higher is better"),
    ("Avg Plane Age (yrs)",    True,  "Lower is better"),
]
DIM_NAMES  = [d[0] for d in DIMS]
DIM_LOWER  = [d[1] for d in DIMS]
DIM_DESCS  = [d[2] for d in DIMS]
N          = len(DIMS)
DEFAULT_WT = 20


def _weight_input(idx, dim_name, desc):
    return html.Div([
        html.Div([
            html.Span(dim_name, style={"fontWeight":"600","fontSize":"0.88rem","color":"#1e293b"}),
            html.Span(f" — {desc}", style={"fontSize":"0.76rem","color":"#64748b","marginLeft":"6px"}),
        ]),
        html.Div([
            dcc.Input(id=f"cr-w{idx}", type="number", min=0, max=100, step=1, value=DEFAULT_WT,
                      style={"width":"68px","padding":"4px 8px","border":"1px solid #cbd5e1",
                             "borderRadius":"6px","backgroundColor":"#f8fafc",
                             "fontFamily":"Inter,sans-serif","fontSize":"0.9rem"}),
            html.Span("%", style={"marginLeft":"4px","color":"#64748b"}),
        ], style={"display":"flex","alignItems":"center","marginTop":"4px"}),
    ], style={"marginBottom":"12px"})


layout = html.Div([
    html.H2("Best Carrier from NYC", className="tab-title"),

    html.Div([
        # Weights panel
        html.Div([
            html.H3("Dimension Weights", style={"marginTop":"0","color":"#1e293b"}),
            *[_weight_input(i, DIM_NAMES[i], DIM_DESCS[i]) for i in range(N)],
            html.Div([
                html.Span("Total: ", style={"fontWeight":"600","color":"#1e293b"}),
                html.Span(id="cr-total"),
            ], style={"marginTop":"8px","padding":"8px 14px","borderRadius":"8px",
                      "backgroundColor":"#f1f5f9","border":"1px solid #e2e8f0",
                      "display":"inline-block"}),
        ], style={"width":"290px","flexShrink":"0","background":"#f8fafc",
                  "borderRadius":"12px","padding":"20px","border":"1px solid #e2e8f0"}),

        # Chart + callout
        html.Div([
            html.Div(id="cr-callout"),
            dcc.Graph(id="cr-bar", style={"height":"620px"}),
        ], style={"flex":"1","minWidth":"0"}),
    ], style={"display":"flex","gap":"24px","alignItems":"flex-start"}),

    html.Div(id="cr-table-div", style={"marginTop":"24px"}),
])


def _inputs():
    return [Input(f"cr-w{i}", "value") for i in range(N)]


def _normalise(series, lower_is_better):
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    norm = (series - mn) / (mx - mn)
    return 1 - norm if lower_is_better else norm


@callback(Output("cr-total","children"), Output("cr-total","style"), *_inputs())
def update_total(*weights):
    total = sum(w or 0 for w in weights)
    color = "#16a34a" if total==100 else "#dc2626"
    return f"{total}%", {"fontWeight":"700","fontSize":"1rem","color":color}


@callback(Output("cr-bar","figure"), Output("cr-callout","children"),
          Output("cr-table-div","children"), *_inputs())
def update_carrier(*weights):
    weights = [w or 0 for w in weights]
    total   = sum(weights)

    df     = carrier_metrics_df.copy().dropna()
    scores = pd.Series(0.0, index=df.index)

    for i, (dim, lower, _) in enumerate(DIMS):
        norm = _normalise(df[dim], lower)
        if total > 0:
            scores += norm * (weights[i] / 100)

    scores_df = (
        scores.reset_index()
        .rename(columns={"Carrier":"Carrier", 0:"score"})
        .sort_values("score", ascending=False)   # descending: best at top
    )

    n = len(scores_df)
    # Gradient: best = deep indigo, worst = light slate
    bar_colors = px.colors.sample_colorscale(
        [[0,"#c7d2fe"],[0.5,"#6366f1"],[1,"#312e81"]],
        [i/(max(n-1,1)) for i in range(n)]
    )[::-1]  # reverse so highest bar gets darkest colour

    fig = go.Figure(go.Bar(
        x=scores_df["score"], y=scores_df["Carrier"],
        orientation="h",
        marker_color=bar_colors,
        marker_line_color="rgba(0,0,0,0.06)", marker_line_width=1,
        text=[f"{s:.3f}" for s in scores_df["score"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Score: %{x:.4f}<extra></extra>",
    ))
    fig.update_layout(
        title="Carrier Ranking by Weighted Score (Best → Worst)" +
              ("" if total==100 else " ⚠️ weights ≠ 100%"),
        xaxis=dict(range=[0,1.15], gridcolor="#e2e8f0", title="Weighted Score"),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(family="Inter,sans-serif", color="#1e293b"),
        margin=dict(l=180, r=80, t=50, b=30),
    )

    # Callout — best is first row (descending sort)
    best_carrier = scores_df.iloc[0]["Carrier"]
    best_score   = scores_df.iloc[0]["score"]
    callout = html.Div([
        html.Span("🏆  Best Carrier from NYC is  ", style={"fontSize":"1rem","color":"#475569"}),
        html.Span(best_carrier,
                  style={"fontSize":"1.1rem","fontWeight":"700","color":"#4338ca"}),
        html.Span(f"  (score: {best_score:.3f})",
                  style={"fontSize":"0.9rem","color":"#64748b"}),
    ], style={"padding":"12px 18px","borderRadius":"10px","backgroundColor":"#eef2ff",
              "border":"1px solid #a5b4fc","marginTop":"12px","display":"inline-block"})

    # Table
    tbl = df.copy().reset_index()
    tbl["Weighted Score"] = [f"{scores.get(c,0):.4f}" for c in tbl["Carrier"]]
    for col in DIM_NAMES:
        tbl[col] = tbl[col].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "—")

    table = dash_table.DataTable(
        data=tbl.to_dict("records"),
        columns=[{"name":c,"id":c} for c in tbl.columns],
        sort_action="native",
        style_table={"overflowX":"auto"},
        style_header={"backgroundColor":"#f1f5f9","fontWeight":"700","color":"#1e293b",
                      "border":"1px solid #e2e8f0","fontFamily":"Inter,sans-serif"},
        style_cell={"backgroundColor":"#ffffff","color":"#334155","fontFamily":"Inter,sans-serif",
                    "fontSize":"0.85rem","padding":"7px 10px","border":"1px solid #e2e8f0",
                    "textAlign":"center"},
        style_cell_conditional=[
            {"if":{"column_id":"Carrier"},"textAlign":"left","fontWeight":"600"},
            {"if":{"column_id":"Weighted Score"},"fontWeight":"700","color":"#4338ca"},
        ],
    )
    return fig, callout, html.Div([
        html.H3("Raw Metrics & Weighted Scores", style={"color":"#1e293b","marginBottom":"10px"}),
        table,
    ])
