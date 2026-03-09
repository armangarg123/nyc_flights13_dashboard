"""Tab 4 — Delay  (6 inner sub-tabs)"""

import numpy as np
import pandas as pd
from dash import html, dcc, callback, Output, Input
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_loader import (
    carrier_delays_naive, carrier_delays_adjusted,
    time_delays_overall, time_delays_by_carrier,
    flights_weather, flights_planes_clean,
    valid_flights, recovery_by_duration,
    flights, airport_ci_df, MONTH_MAP, ORIGINS,
)

AIRPORT_OPTIONS = [{"label":"All airports","value":"ALL"},
                   {"label":"JFK","value":"JFK"},
                   {"label":"LGA","value":"LGA"},
                   {"label":"EWR","value":"EWR"}]
CARRIER_OPTIONS = (
    [{"label":"All carriers","value":"ALL"}] +
    [{"label":c,"value":c} for c in sorted(flights_planes_clean["carrier"].dropna().unique())]
)
TIME_ORDER = ["Early Morning","Morning","Afternoon","Evening","Night"]
AIRPORT_COLORS = {"JFK":"#2563eb","LGA":"#d97706","EWR":"#16a34a"}
METRIC_LABELS  = {"avg_dep_delay":"Avg Departure Delay (min)",
                  "avg_arr_delay":"Avg Arrival Delay (min)",
                  "cancel_rate":"Cancellation Rate (%)","num_flights":"Total Flights"}

layout = html.Div([
    html.H2("Delay Analysis", className="tab-title"),
    dcc.Tabs(
        id="delay-subtabs", value="sub-airline",
        children=[
            dcc.Tab(label="a) Delay by Airline",     value="sub-airline"),
            dcc.Tab(label="b) Delay by Time of Day", value="sub-tod"),
            dcc.Tab(label="c) Weather",              value="sub-weather"),
            dcc.Tab(label="d) Plane Age",            value="sub-age"),
            dcc.Tab(label="e) Delay Recovery",       value="sub-recovery"),
            dcc.Tab(label="f) Delay by Origin",      value="sub-origin"),
        ],
        colors={"border":"#e2e8f0","primary":"#6366f1","background":"#f8fafc"},
    ),
    html.Div(id="delay-sub-content", style={"paddingTop":"20px"}),
])


@callback(Output("delay-sub-content","children"), Input("delay-subtabs","value"))
def render_sub(sub):
    return {"sub-airline":_layout_airline,"sub-tod":_layout_tod,
            "sub-weather":_layout_weather,"sub-age":_layout_age,
            "sub-recovery":_layout_recovery,"sub-origin":_layout_origin}.get(sub, lambda:html.P("?"))()


# ── a) Delay by Airline ───────────────────────────────────────────────────────
def _layout_airline():
    return html.Div([
        html.Div([
            html.Label("View:"),
            dcc.RadioItems(id="p4a-toggle",
                options=[{"label":"Average delay per airline (unadjusted)","value":"unadjusted"},
                         {"label":"Average delay per airline (adjusted for routes)","value":"adjusted"}],
                value="unadjusted", inline=True, className="radio-inline"),
        ], className="control-row"),
        dcc.Graph(id="p4a-bar", style={"height":"580px"}),
    ])


@callback(Output("p4a-bar","figure"), Input("p4a-toggle","value"))
def update_airline(view):
    if view=="unadjusted":
        df = carrier_delays_naive.sort_values("avg_arr_delay")
        x_col, x_label, title = "avg_arr_delay","Average Arrival Delay (min)","Unadjusted"
    else:
        df = carrier_delays_adjusted.sort_values("avg_route_difficulty")
        x_col, x_label, title = "avg_route_difficulty","Average Route Difficulty (min)","Adjusted for Routes"
    colors = ["#dc2626" if v>0 else "#6366f1" for v in df[x_col]]
    fig = go.Figure(go.Bar(
        x=df[x_col], y=df["name"], orientation="h", marker_color=colors,
        hovertemplate="<b>%{y}</b><br>"+x_label+": %{x:.2f} min<extra></extra>"))
    fig.add_vline(x=0, line_color="#475569", line_width=1.5, line_dash="dash")
    fig.update_layout(title=f"Average Delay per Airline — {title}", xaxis_title=x_label,
                      yaxis=dict(autorange="reversed"),
                      plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                      font=dict(family="Inter,sans-serif",color="#1e293b"))
    fig.update_xaxes(gridcolor="#f1f5f9")
    return fig


# ── b) Time of Day — FIXED ────────────────────────────────────────────────────
def _layout_tod():
    return html.Div([dcc.Graph(id="p4b-tod", style={"height":"520px"})])


@callback(Output("p4b-tod","figure"), Input("delay-subtabs","value"))
def update_tod(sub):
    if sub != "sub-tod":
        return go.Figure()

    overall    = time_delays_overall.copy()
    by_carrier = time_delays_by_carrier.copy()
    carriers   = sorted(by_carrier["name"].unique())
    palette    = ["#6366f1","#f59e0b","#10b981","#ef4444","#8b5cf6"]
    color_map  = dict(zip(carriers, palette[:len(carriers)]))

    fig = go.Figure()

    # Overall bars — light grey, behind
    for i, tod in enumerate(TIME_ORDER):
        row = overall[overall["time_of_day"]==tod]
        val = float(row["avg_dep_delay"].values[0]) if not row.empty else 0
        fig.add_trace(go.Bar(
            name="Overall", x=[tod], y=[val],
            marker_color="rgba(148,163,184,0.35)",
            marker_line_color="rgba(100,116,139,0.4)", marker_line_width=1,
            legendgroup="overall", showlegend=(i==0),
            offsetgroup="overall",
            hovertemplate=f"<b>Overall — {tod}</b><br>{val:.1f} min<extra></extra>",
        ))

    # Per-carrier bars
    for carrier in carriers:
        sub_df = by_carrier[by_carrier["name"]==carrier].copy()
        # Ensure all time slots present
        x_vals, y_vals = [], []
        for tod in TIME_ORDER:
            row = sub_df[sub_df["time_of_day"]==tod]
            x_vals.append(tod)
            y_vals.append(float(row["avg_dep_delay"].values[0]) if not row.empty else 0)
        fig.add_trace(go.Bar(
            name=carrier, x=x_vals, y=y_vals,
            marker_color=color_map.get(carrier,"#94a3b8"), opacity=0.85,
            legendgroup=carrier, offsetgroup=carrier,
            hovertemplate=f"<b>{carrier}</b> — %{{x}}<br>%{{y:.1f}} min<extra></extra>",
        ))

    fig.add_hline(y=0, line_color="#475569", line_width=1, line_dash="dash")
    fig.update_layout(
        barmode="group",
        title="Average Departure Delay by Time of Day — Top 5 Carriers vs Overall",
        xaxis=dict(categoryorder="array", categoryarray=TIME_ORDER,
                   title="Time of Day"),
        yaxis=dict(title="Avg Departure Delay (min)", gridcolor="#f1f5f9"),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(family="Inter,sans-serif", color="#1e293b"),
        legend_title="Carrier",
    )
    return fig


# ── c) Weather ────────────────────────────────────────────────────────────────
def _layout_weather():
    return html.Div([
        html.Div([
            html.Div([html.Label("Airport:"),
                      dcc.Dropdown(id="p4c-airport", options=AIRPORT_OPTIONS,
                                   value="ALL", clearable=False, style={"width":"200px"})]),
            html.Div([html.Label("Delay type:"),
                      dcc.RadioItems(id="p4c-delay",
                          options=[{"label":"Departure","value":"dep"},
                                   {"label":"Arrival",  "value":"arr"},
                                   {"label":"Both",     "value":"both"}],
                          value="dep", inline=True, className="radio-inline")]),
        ], className="control-row", style={"gap":"40px"}),
        dcc.Graph(id="p4c-grid", style={"height":"640px"}),
    ])


def _wagg(df, bin_col, cols):
    return (
        df.dropna(subset=[bin_col]+cols)
        .groupby(bin_col, observed=True)
        .agg(**{c:(c,"mean") for c in cols})
        .reset_index().rename(columns={bin_col:"bin"})
        .assign(bin=lambda x: x["bin"].astype(str))
    )


@callback(Output("p4c-grid","figure"),
          Input("p4c-airport","value"), Input("p4c-delay","value"))
def update_weather(airport, delay_type):
    df   = flights_weather if airport=="ALL" else flights_weather[flights_weather["origin"]==airport]
    cols = (["dep_delay","arr_delay"] if delay_type=="both"
            else ["dep_delay"] if delay_type=="dep" else ["arr_delay"])
    temp  = _wagg(df,"temp_bin",cols); wind = _wagg(df,"wind_bin",cols)
    visib = _wagg(df,"visib_bin",cols)
    prec  = (df.assign(bin=lambda x:(x["precip"]>0).map({False:"No Rain",True:"Rain"}))
             .dropna(subset=cols).groupby("bin").agg(**{c:(c,"mean") for c in cols}).reset_index())
    panels = [("Temperature (°F)",temp,"line"),("Visibility",visib,"bar"),
              ("Wind Speed",wind,"line"),("Precipitation",prec,"bar")]
    fig = make_subplots(rows=2,cols=2,subplot_titles=[p[0] for p in panels],
                        vertical_spacing=0.14,horizontal_spacing=0.10)
    dep_col, arr_col = "#6366f1","#f59e0b"
    for idx,(_,data,kind) in enumerate(panels):
        r,c = idx//2+1, idx%2+1
        for col,color,label in [("dep_delay",dep_col,"Departure"),("arr_delay",arr_col,"Arrival")]:
            if col not in data.columns: continue
            if kind=="line":
                fig.add_trace(go.Scatter(x=data["bin"],y=data[col],mode="lines+markers",
                    line=dict(color=color,width=2),marker=dict(size=6),
                    name=label,legendgroup=label,showlegend=(idx==0),
                    hovertemplate=f"{label}: %{{y:.1f}} min<extra></extra>"),row=r,col=c)
            else:
                fig.add_trace(go.Bar(x=data["bin"],y=data[col],marker_color=color,opacity=0.8,
                    name=label,legendgroup=label,showlegend=(idx==0),
                    hovertemplate=f"{label}: %{{y:.1f}} min<extra></extra>"),row=r,col=c)
        fig.add_hline(y=0,line_dash="dash",line_color="#475569",line_width=1,opacity=0.4,row=r,col=c)
    fig.update_yaxes(gridcolor="#f1f5f9")
    fig.update_layout(title=f"Weather Impact on Delays — {airport}",barmode="group",
                      plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
                      font=dict(family="Inter,sans-serif",color="#1e293b"),legend_title="Delay type")
    return fig


# ── d) Plane Age ──────────────────────────────────────────────────────────────
def _layout_age():
    return html.Div([
        html.Div([
            html.Div([html.Label("Carrier:"),
                      dcc.Dropdown(id="p4d-carrier",options=CARRIER_OPTIONS,
                                   value="ALL",clearable=False,style={"width":"200px"})]),
            html.Div([html.Label("Age bin width (years):"),
                      dcc.Slider(id="p4d-binwidth",min=1,max=10,step=1,value=5,
                                 marks={1:"1",5:"5",10:"10"})],style={"width":"260px"}),
        ], className="control-row", style={"gap":"40px"}),
        html.Div([
            html.Div([dcc.Graph(id="p4d-hist",   style={"height":"460px"})],style={"flex":"1"}),
            html.Div([dcc.Graph(id="p4d-scatter",style={"height":"460px"})],style={"flex":"1"}),
        ], style={"display":"flex","gap":"16px"}),
    ])


@callback(Output("p4d-hist","figure"),Output("p4d-scatter","figure"),
          Input("p4d-carrier","value"),Input("p4d-binwidth","value"))
def update_age(carrier,binwidth):
    df = flights_planes_clean.copy()
    if carrier!="ALL": df = df[df["carrier"]==carrier]
    df = df.dropna(subset=["plane_age"])
    hist = px.histogram(df,x="plane_age",nbins=max(1,int(50/binwidth)),
                        color_discrete_sequence=["#6366f1"],
                        labels={"plane_age":"Plane Age (years)"})
    hist.update_layout(title=f"Distribution of Aircraft Age — {carrier}",
                       plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
                       font=dict(family="Inter,sans-serif",color="#1e293b"))
    hist.update_yaxes(gridcolor="#f1f5f9")
    bins=list(range(0,52,binwidth))
    df2=df.dropna(subset=["dep_delay"]).copy()
    df2["age_bin_mid"]=pd.cut(df2["plane_age"],bins=bins).apply(
        lambda x: x.mid if pd.notna(x) else np.nan)
    agg=(df2.dropna(subset=["age_bin_mid"]).groupby("age_bin_mid")
         .agg(avg_dep_delay=("dep_delay","mean"),n=("dep_delay","count"))
         .reset_index().query("n>=10"))
    corr=df2[["plane_age","dep_delay"]].corr().iloc[0,1]
    scat=px.scatter(agg,x="age_bin_mid",y="avg_dep_delay",size="n",trendline="ols",
                    color_discrete_sequence=["#6366f1"],
                    labels={"age_bin_mid":"Plane Age (years)","avg_dep_delay":"Avg Dep Delay (min)","n":"Flights"})
    scat.add_hline(y=0,line_color="#dc2626",line_dash="dash",line_width=1,opacity=0.5)
    scat.update_layout(title=f"Plane Age vs Departure Delay — r = {corr:.3f}  ({carrier})",
                       plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
                       font=dict(family="Inter,sans-serif",color="#1e293b"))
    scat.update_xaxes(gridcolor="#f1f5f9"); scat.update_yaxes(gridcolor="#f1f5f9")
    return hist,scat


# ── e) Delay Recovery ─────────────────────────────────────────────────────────
def _layout_recovery():
    return html.Div([
        html.Div([html.Label("Scatter sample size:"),
                  dcc.Slider(id="p4e-sample",min=1000,max=30000,step=1000,value=10000,
                             marks={1000:"1k",10000:"10k",20000:"20k",30000:"30k"},
                             tooltip={"placement":"bottom"})],
                 className="control-row",style={"width":"440px"}),
        html.Div([
            html.Div([dcc.Graph(id="p4e-scatter", style={"height":"480px"})],style={"flex":"1"}),
            html.Div([dcc.Graph(id="p4e-recovery",style={"height":"480px"})],style={"flex":"1"}),
        ], style={"display":"flex","gap":"16px"}),
    ])


@callback(Output("p4e-scatter","figure"),Input("p4e-sample","value"))
def update_scatter(n):
    df=valid_flights.dropna(subset=["dep_delay","arr_delay"]).sample(n=min(n,len(valid_flights)),random_state=42)
    mn=min(df["dep_delay"].min(),df["arr_delay"].min())
    mx=max(df["dep_delay"].max(),df["arr_delay"].max())
    fig=px.scatter(df,x="dep_delay",y="arr_delay",opacity=0.2,color_discrete_sequence=["#6366f1"],
                   labels={"dep_delay":"Departure Delay (min)","arr_delay":"Arrival Delay (min)"})
    fig.add_trace(go.Scatter(x=[mn,mx],y=[mn,mx],mode="lines",
                             line=dict(color="#dc2626",dash="dash",width=2),name="No recovery"))
    fig.update_layout(title="Departure vs Arrival Delay — Points Below Line = Time Made Up",
                      plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
                      font=dict(family="Inter,sans-serif",color="#1e293b"))
    fig.update_xaxes(gridcolor="#f1f5f9"); fig.update_yaxes(gridcolor="#f1f5f9")
    return fig


@callback(Output("p4e-recovery","figure"),Input("delay-subtabs","value"))
def update_recovery(_):
    df=recovery_by_duration.copy()
    fig=px.bar(df,x="duration_category",y="avg_recovered",
               color="avg_recovered",color_continuous_scale=["#c7d2fe","#312e81"],
               text=df["avg_recovered"].round(1),
               labels={"duration_category":"Flight Duration","avg_recovered":"Avg Minutes Recovered"})
    fig.update_traces(textposition="outside")
    fig.update_layout(title="Delay Recovered by Flight Duration",coloraxis_showscale=False,
                      plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
                      font=dict(family="Inter,sans-serif",color="#1e293b"))
    fig.update_yaxes(gridcolor="#f1f5f9")
    return fig


# ── f) Delay by Origin ────────────────────────────────────────────────────────
def _layout_origin():
    return html.Div([
        html.Div([
            html.Div([html.Label("Metric:"),
                      dcc.Dropdown(id="p4f-metric",
                          options=[{"label":v,"value":k} for k,v in METRIC_LABELS.items()],
                          value="avg_dep_delay",clearable=False,style={"width":"280px"})]),
            html.Div([html.Label("Month range:"),
                      dcc.RangeSlider(id="p4f-months",min=1,max=12,step=1,value=[1,12],
                                      marks={m:MONTH_MAP[m] for m in [1,3,6,9,12]},
                                      tooltip={"placement":"bottom"})],style={"width":"360px"}),
        ], className="control-row", style={"gap":"40px"}),
        html.Div([
            html.Div([dcc.Graph(id="p4f-ci", style={"height":"320px"})],style={"flex":"1"}),
            html.Div([dcc.Graph(id="p4f-bar",style={"height":"320px"})],style={"flex":"1"}),
        ], style={"display":"flex","gap":"16px"}),
        html.Div(id="p4f-winner",style={"marginTop":"8px"}),
    ])


@callback(Output("p4f-ci","figure"),Input("delay-subtabs","value"))
def draw_ci(sub):
    if sub!="sub-origin": return go.Figure()
    df=airport_ci_df.copy(); fig=go.Figure()
    for _,row in df.iterrows():
        col=AIRPORT_COLORS.get(row["origin"],"#6366f1")
        fig.add_trace(go.Scatter(x=[row["ci_lower"],row["ci_upper"]],y=[row["origin"],row["origin"]],
            mode="lines",line=dict(color=col,width=10),opacity=0.5,showlegend=False,hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[row["mean"]],y=[row["origin"]],mode="markers",
            marker=dict(color=col,size=14,line=dict(color="white",width=2)),
            name=row["origin"],showlegend=True,
            hovertemplate=(f"<b>{row['origin']}</b><br>Mean: {row['mean']:.2f} min<br>"
                           f"95% CI: [{row['ci_lower']:.2f}, {row['ci_upper']:.2f}]<extra></extra>")))
    fig.update_layout(title="Departure Delay — 95% Confidence Intervals",
                      xaxis_title="Avg Departure Delay (min)",
                      plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
                      font=dict(family="Inter,sans-serif",color="#1e293b"),
                      showlegend=False,height=320,margin=dict(l=60,r=20,t=50,b=40))
    fig.update_xaxes(gridcolor="#f1f5f9")
    return fig


@callback(Output("p4f-bar","figure"),Output("p4f-winner","children"),
          Input("p4f-metric","value"),Input("p4f-months","value"))
def update_origin_bar(metric,month_range):
    sub=flights[(flights["month"]>=month_range[0])&(flights["month"]<=month_range[1])].copy()
    sub["cancelled"]=sub["dep_time"].isna().astype(int)
    perf=(sub.groupby("origin")
          .agg(avg_dep_delay=("dep_delay","mean"),avg_arr_delay=("arr_delay","mean"),
               cancel_rate=("cancelled","mean"),num_flights=("flight","count"))
          .reset_index().assign(cancel_rate=lambda x: x["cancel_rate"]*100))
    lower_is_better=(metric!="num_flights")
    perf_sorted=perf.sort_values(metric,ascending=lower_is_better)
    winner=perf_sorted["origin"].iloc[0]; label=METRIC_LABELS[metric]
    colors=[AIRPORT_COLORS.get(o,"#6366f1") for o in perf_sorted["origin"]]
    fig=go.Figure(go.Bar(x=perf_sorted["origin"],y=perf_sorted[metric],marker_color=colors,
        text=perf_sorted[metric].round(2),textposition="outside",
        hovertemplate="<b>%{x}</b><br>"+label+": %{y:.3f}<extra></extra>"))
    fig.update_layout(title=f"{label} — {MONTH_MAP[month_range[0]]} to {MONTH_MAP[month_range[1]]}",
                      yaxis_title=label,plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
                      font=dict(family="Inter,sans-serif",color="#1e293b"),
                      height=320,margin=dict(l=20,r=20,t=50,b=40))
    fig.update_yaxes(gridcolor="#f1f5f9")
    unit="%" if metric=="cancel_rate" else ("flights" if metric=="num_flights" else "min")
    winner_val=perf_sorted[metric].iloc[0]
    winner_div=html.P(f"🏆  Best by '{label}':  {winner}  ({winner_val:.2f} {unit})",
        style={"fontWeight":"bold","fontSize":"1rem",
               "color":AIRPORT_COLORS.get(winner,"#6366f1"),"margin":"8px 0"})
    return fig,winner_div
