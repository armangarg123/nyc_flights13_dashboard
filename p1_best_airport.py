"""Tab 1 — Best Airport in NYC"""

import numpy as np
import pandas as pd
from dash import html, dcc, callback, Output, Input, dash_table
import plotly.graph_objects as go

from data_loader import airport_metrics_df, ORIGINS, AIRPORT_FULL

DIMS = [
    ("Avg Dep Delay (min)",    True,  "Lower is better"),
    ("Cancellation Rate (%)",  True,  "Lower is better"),
    ("Destinations",           False, "Higher is better"),
    ("Fleet Variety (seat σ)", False, "Higher is better"),
    ("Weather Delay (min)",    True,  "Lower is better"),
]
DIM_NAMES   = [d[0] for d in DIMS]
DIM_LOWER   = [d[1] for d in DIMS]
DIM_DESCS   = [d[2] for d in DIMS]
N           = len(DIMS)
DEFAULT_WT  = 20

AIRPORT_COLORS = {"JFK":"#2563eb","LGA":"#d97706","EWR":"#16a34a"}


def _weight_input(idx, dim_name, desc):
    return html.Div([
        html.Div([
            html.Span(dim_name, style={"fontWeight":"600","fontSize":"0.88rem","color":"#1e293b"}),
            html.Span(f" — {desc}", style={"fontSize":"0.76rem","color":"#64748b","marginLeft":"6px"}),
        ]),
        html.Div([
            dcc.Input(id=f"ap-w{idx}", type="number", min=0, max=100, step=1, value=DEFAULT_WT,
                      style={"width":"68px","padding":"4px 8px","border":"1px solid #cbd5e1",
                             "borderRadius":"6px","backgroundColor":"#f8fafc",
                             "fontFamily":"Inter,sans-serif","fontSize":"0.9rem"}),
            html.Span("%", style={"marginLeft":"4px","color":"#64748b"}),
        ], style={"display":"flex","alignItems":"center","marginTop":"4px"}),
    ], style={"marginBottom":"12px"})


layout = html.Div([
    html.H2("Best Airport in NYC", className="tab-title"),

    html.Div([
        # Weight panel
        html.Div([
            html.H3("Dimension Weights", style={"marginTop":"0","color":"#1e293b"}),
            *[_weight_input(i, DIM_NAMES[i], DIM_DESCS[i]) for i in range(N)],
            html.Div([
                html.Span("Total: ", style={"fontWeight":"600","color":"#1e293b"}),
                html.Span(id="ap-total"),
            ], style={"marginTop":"8px","padding":"8px 14px","borderRadius":"8px",
                      "backgroundColor":"#f1f5f9","border":"1px solid #e2e8f0",
                      "display":"inline-block"}),
        ], style={"width":"290px","flexShrink":"0","background":"#f8fafc",
                  "borderRadius":"12px","padding":"20px","border":"1px solid #e2e8f0"}),

        # Chart + callout
        html.Div([
            html.Div(id="ap-callout"),
            dcc.Graph(id="ap-bar", style={"height":"320px"}),
        ], style={"flex":"1","minWidth":"0"}),
    ], style={"display":"flex","gap":"24px","alignItems":"flex-start"}),

    html.Div(id="ap-table-div", style={"marginTop":"24px"}),
])


def _inputs():
    return [Input(f"ap-w{i}", "value") for i in range(N)]


def _normalise(series, lower_is_better):
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    norm = (series - mn) / (mx - mn)
    return 1 - norm if lower_is_better else norm


@callback(Output("ap-total","children"), Output("ap-total","style"), *_inputs())
def update_total(*weights):
    total = sum(w or 0 for w in weights)
    color = "#16a34a" if total == 100 else "#dc2626"
    return f"{total}%", {"fontWeight":"700","fontSize":"1rem","color":color}


@callback(Output("ap-bar","figure"), Output("ap-callout","children"),
          Output("ap-table-div","children"), *_inputs())
def update_airport(*weights):
    weights = [w or 0 for w in weights]
    total   = sum(weights)

    df     = airport_metrics_df.copy()
    scores = pd.Series(0.0, index=df.index)
    norm_df = pd.DataFrame(index=df.index)

    for i, (dim, lower, _) in enumerate(DIMS):
        norm = _normalise(df[dim], lower)
        norm_df[dim] = norm
        if total > 0:
            scores += norm * (weights[i] / 100)

    scores_df = scores.reset_index().rename(columns={0:"score"})
    scores_df = scores_df.sort_values("score", ascending=True)
    scores_df["full_name"] = scores_df["Airport"].map(AIRPORT_FULL)

    bar_colors = [AIRPORT_COLORS.get(a,"#6366f1") for a in scores_df["Airport"]]

    fig = go.Figure(go.Bar(
        x=scores_df["score"], y=scores_df["full_name"],
        orientation="h",
        marker_color=bar_colors,
        marker_line_color="rgba(0,0,0,0.08)", marker_line_width=1,
        text=[f"{s:.3f}" for s in scores_df["score"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Score: %{x:.4f}<extra></extra>",
    ))
    fig.update_layout(
        title="Overall Weighted Score" + ("" if total==100 else " ⚠️ weights ≠ 100%"),
        xaxis=dict(range=[0,1.15], gridcolor="#e2e8f0", title="Weighted Score"),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(family="Inter,sans-serif", color="#1e293b"),
        margin=dict(l=20, r=80, t=50, b=30),
    )

    # Callout
    best = scores_df.iloc[-1]
    callout = html.Div([
        html.Span("🏆  Best Airport in NYC is  ", style={"fontSize":"1rem","color":"#475569"}),
        html.Span(best["full_name"],
                  style={"fontSize":"1.1rem","fontWeight":"700",
                         "color": AIRPORT_COLORS.get(best["Airport"],"#6366f1")}),
        html.Span(f"  (score: {best['score']:.3f})",
                  style={"fontSize":"0.9rem","color":"#64748b"}),
    ], style={"padding":"12px 18px","borderRadius":"10px","backgroundColor":"#f0fdf4",
              "border":"1px solid #86efac","marginTop":"12px","display":"inline-block"})

    # Table
    tbl = df.copy().reset_index()
    tbl["Weighted Score"] = [f"{scores[a]:.4f}" for a in tbl["Airport"]]
    for col in DIM_NAMES:
        tbl[col] = tbl[col].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "—")

    table = dash_table.DataTable(
        data=tbl.to_dict("records"),
        columns=[{"name":c,"id":c} for c in tbl.columns],
        style_table={"overflowX":"auto"},
        style_header={"backgroundColor":"#f1f5f9","fontWeight":"700","color":"#1e293b",
                      "border":"1px solid #e2e8f0","fontFamily":"Inter,sans-serif"},
        style_cell={"backgroundColor":"#ffffff","color":"#334155","fontFamily":"Inter,sans-serif",
                    "fontSize":"0.87rem","padding":"8px 12px","border":"1px solid #e2e8f0",
                    "textAlign":"center"},
        style_cell_conditional=[
            {"if":{"column_id":"Airport"},"textAlign":"left","fontWeight":"600"},
            {"if":{"column_id":"Weighted Score"},"fontWeight":"700","color":"#2563eb"},
        ],
    )
    return fig, callout, html.Div([
        html.H3("Raw Metrics & Weighted Scores", style={"color":"#1e293b","marginBottom":"10px"}),
        table,
    ])
