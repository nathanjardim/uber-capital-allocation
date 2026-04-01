import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
from model import load_market_data, run_optimization, build_ltv_curves

# ============================================================================
# CONFIG
# ============================================================================

st.set_page_config(
    page_title="Uber Capital Allocation",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# GLOBAL CSS
# ============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Global ──────────────────────────────────────────────────────────────── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* ── Hero ────────────────────────────────────────────────────────────────── */
.uber-hero {
    background: #000000;
    border-radius: 10px;
    padding: 26px 32px;
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}
.uber-hero-title {
    font-size: 24px; font-weight: 700; color: #FFFFFF;
    letter-spacing: -0.5px; margin: 0 0 6px 0; line-height: 1.2;
}
.uber-hero-sub { font-size: 12px; color: #9CA3AF; margin: 0; letter-spacing: 0.3px; }
.uber-hero-badge {
    background: #06C167; color: #000000;
    font-size: 11px; font-weight: 700; padding: 5px 12px;
    border-radius: 20px; text-transform: uppercase; letter-spacing: 0.8px;
    white-space: nowrap; margin-left: 16px;
}

/* ── KPI Grid ────────────────────────────────────────────────────────────── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 10px;
    margin: 16px 0;
}
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 14px 16px;
    border-top: 3px solid #000000;
}
.kpi-label {
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.6px; color: #9CA3AF; margin-bottom: 8px;
}
.kpi-value { font-size: 20px; font-weight: 700; color: #111827; line-height: 1; }
.kpi-delta { font-size: 11px; margin-top: 5px; font-weight: 500; }
.kpi-green { color: #06C167; }
.kpi-gray  { color: #9CA3AF; }
.kpi-red   { color: #EF4444; }

/* ── Section titles ──────────────────────────────────────────────────────── */
.section-title {
    font-size: 17px; font-weight: 700; color: #111827;
    letter-spacing: -0.3px; margin: 0 0 2px 0;
}
.section-caption {
    font-size: 12px; color: #6B7280;
    margin: 0 0 12px 0; line-height: 1.5;
}

/* ── Tier Cards ──────────────────────────────────────────────────────────── */
.tier-card { border-radius: 8px; padding: 18px 20px; min-height: 160px; }
.tier-critical { background: #FEF2F2; border: 1.5px solid #FECACA; }
.tier-mild     { background: #FFFBEB; border: 1.5px solid #FDE68A; }
.tier-safe     { background: #F0FDF4; border: 1.5px solid #BBF7D0; }
.tier-tag {
    display: inline-block; font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
    padding: 3px 9px; border-radius: 20px; margin-bottom: 10px;
}
.tier-tag-critical { background: #DC2626; color: #FFFFFF; }
.tier-tag-mild     { background: #D97706; color: #FFFFFF; }
.tier-tag-safe     { background: #16A34A; color: #FFFFFF; }
.tier-count {
    font-size: 32px; font-weight: 700; color: #111827;
    line-height: 1; margin-bottom: 10px;
}
.tier-market-item {
    font-size: 13px; color: #374151;
    padding: 4px 0; border-bottom: 1px solid rgba(0,0,0,0.05);
}
.tier-market-item:last-child { border-bottom: none; }

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: #000000 !important;
    color: #FFFFFF !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important; font-size: 15px !important;
    border: none !important; border-radius: 8px !important;
    height: 50px !important; letter-spacing: 0.2px !important;
}
.stButton > button[kind="primary"]:hover { background: #1F2937 !important; }

.stDownloadButton > button {
    background: #FFFFFF !important; color: #111827 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important; font-size: 14px !important;
    border: 1.5px solid #D1D5DB !important;
    border-radius: 8px !important; height: 46px !important;
}
.stDownloadButton > button:hover { border-color: #000000 !important; }

/* ── Misc ────────────────────────────────────────────────────────────────── */
.uber-divider { border: none; border-top: 1px solid #F3F4F6; margin: 20px 0; }
[data-testid="stSidebar"] { background: #F9FAFB !important; }
[data-testid="stAlert"]   { border-radius: 8px; }
[data-testid="stInfo"]    { border-radius: 8px; font-size: 13px; }

/* ── Accent override ─────────────────────────────────────────────────────── */
[data-baseweb="slider"] [role="slider"] {
    background-color: #000000 !important;
    border-color:     #000000 !important;
}
[data-baseweb="tab"] [aria-selected="true"] {
    border-bottom-color: #000000 !important;
    color: #000000 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Hero Header ────────────────────────────────────────────────────────────
st.markdown("""
<div class="uber-hero">
    <div>
        <p class="uber-hero-title">Capital Allocation Model</p>
        <p class="uber-hero-sub">
            Score-Based Greedy Optimization &nbsp;·&nbsp;
            Q1 Impact + LTV Projection &nbsp;·&nbsp;
            Hurdle Rate Filter &nbsp;·&nbsp;
            15 LatAm Markets
        </p>
    </div>
    <span class="uber-hero-badge">LatAm · 15 Markets</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:right; padding: 6px 4px 0 0;">
    <span style="font-size:13px; color:#374151;">
        Made by <strong style="color:#111827;">Nathan Jardim</strong>
        &nbsp;·&nbsp; Selective Process
        &nbsp;·&nbsp; Uber LatAm, 2026
    </span>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.markdown("""
<div style="padding: 4px 0 12px 0;">
    <p style="font-size:16px; font-weight:700; color:#111827; margin:0;">Model Parameters</p>
    <p style="font-size:11px; color:#9CA3AF; margin:4px 0 0 0;">Adjust assumptions to simulate scenarios</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("**💰 Budget & Caps**")
budget_pct = st.sidebar.slider(
    "Budget (% of Total GB)", 5, 25, 10, 1,
) / 100
cap_pct = st.sidebar.slider(
    "Max per Market (% of own GB)", 5, 40, 20, 5,
) / 100
margin = st.sidebar.slider(
    "Platform Margin (%)", 15, 40, 25, 5,
) / 100

st.sidebar.markdown("---")
st.sidebar.markdown("**📈 LTV Multipliers**")
ltv_critical = st.sidebar.slider("LTV mult — CRITICAL", 0.5, 5.0, 1.5, 0.25)
ltv_mild     = st.sidebar.slider("LTV mult — MILD",     0.25, 4.0, 0.75, 0.25)
ltv_safe     = st.sidebar.slider("LTV mult — SAFE",     0.25, 3.0, 0.50, 0.25)

st.sidebar.markdown("---")
st.sidebar.markdown("**📉 Hurdle Rate**")
hurdle_rate = st.sidebar.slider("Min PV per $ (hurdle)", 0.5, 4.0, 1.5, 0.5)

st.sidebar.markdown("---")

# ============================================================================
# SECTION 1 — MARKET INPUTS
# ============================================================================

st.markdown('<hr class="uber-divider">', unsafe_allow_html=True)
st.markdown('<p class="section-title">📥 Market Inputs</p>', unsafe_allow_html=True)


df_default = load_market_data()
df_edited = st.data_editor(
    df_default,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Market":    st.column_config.TextColumn("Market", disabled=True),
        "GB":        st.column_config.NumberColumn("Gross Bookings ($)", format="$%d"),
        "Surge":     st.column_config.NumberColumn("Surge %", format="%.4f"),
        "CM":        st.column_config.NumberColumn("Contribution Margin", format="%.2f"),
        "Share":     st.column_config.NumberColumn("Market Share", min_value=0.0, max_value=1.0, format="%.2f"),
        "Redline":   st.column_config.NumberColumn("Redline", min_value=0.0, max_value=1.0, format="%.2f"),
        "CPIT":      st.column_config.NumberColumn("CPIT ($)", format="%.3f"),
        "CPISH":     st.column_config.NumberColumn("CPISH ($)", format="%.3f"),
        "Avg_Fare":  st.column_config.NumberColumn("Avg Fare ($)", format="%.3f"),
        "Comp_Fare": st.column_config.NumberColumn("Comp Fare ($)", format="%.3f"),
        "TPH":       st.column_config.NumberColumn("Trips/Hour", format="%.3f"),
        "Growth":    st.column_config.NumberColumn("Annual Growth", format="%.3f"),
        "CR":        st.column_config.NumberColumn("C/R", format="%.4f"),
    }
)

# ============================================================================
# SECTION 2 — RUN
# ============================================================================

st.markdown('<hr class="uber-divider">', unsafe_allow_html=True)
run = st.button("Run Optimization →", type="primary", use_container_width=True)

# ============================================================================
# SECTION 3 — RESULTS
# ============================================================================

if run:
    with st.spinner("Running optimization…"):
        results, summary = run_optimization(
            df=df_edited,
            budget_pct=budget_pct, cap_pct=cap_pct, margin=margin,
            ltv_critical=ltv_critical, ltv_mild=ltv_mild, ltv_safe=ltv_safe,
            hurdle_rate=hurdle_rate,
        )

    st.markdown('<hr class="uber-divider">', unsafe_allow_html=True)

    # ── KPI Cards ─────────────────────────────────────────────────────────
    npm1_cls = "kpi-green" if summary['npm1'] >= 0 else "kpi-red"

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Budget Available</div>
            <div class="kpi-value">${summary['budget']:.1f}M</div>
            <div class="kpi-delta kpi-gray">Total envelope</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Budget Allocated</div>
            <div class="kpi-value">${summary['allocated']:.1f}M</div>
            <div class="kpi-delta kpi-green">{summary['utilization']:.0%} utilized</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Capital Preserved</div>
            <div class="kpi-value">${summary['returned']:.1f}M</div>
            <div class="kpi-delta kpi-gray">{summary['markets_excluded']} mkts excluded</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Net Profit Q1</div>
            <div class="kpi-value">${summary['npm1']:.1f}M</div>
            <div class="kpi-delta {npm1_cls}">Direct Q1 impact</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">LTV Projection</div>
            <div class="kpi-value">${summary['ltv']:.1f}M</div>
            <div class="kpi-delta kpi-gray">4-quarter horizon</div>
        </div>
        <div class="kpi-card" style="border-top-color: #06C167;">
            <div class="kpi-label">Platform Value</div>
            <div class="kpi-value">${summary['platform_value']:.1f}M</div>
            <div class="kpi-delta kpi-green">NPM1 + LTV</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Redline Compliant</div>
            <div class="kpi-value">{summary['redline_ok']}/{summary['total_markets']}</div>
            <div class="kpi-delta kpi-gray">markets above redline</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="uber-divider">', unsafe_allow_html=True)

    # ── Strategic Matrix ───────────────────────────────────────────────────
    st.markdown('<p class="section-title">🗺️ Strategic Market Classification</p>', unsafe_allow_html=True)


    critical_markets = results[results['Tier'] == 'CRITICAL']['Market'].tolist()
    mild_markets     = results[results['Tier'] == 'MILD']['Market'].tolist()
    safe_markets     = results[results['Tier'] == 'SAFE']['Market'].tolist()

    def render_tier_markets(markets):
        return "\n".join(
            f'<div class="tier-market-item">· {m}</div>' for m in markets
        )

    col_c, col_m, col_s = st.columns(3)
    with col_c:
        st.markdown(f"""
        <div class="tier-card tier-critical">
            <span class="tier-tag tier-tag-critical">Critical</span>
            <div class="tier-count">{summary['n_critical']}</div>
            {render_tier_markets(critical_markets)}
        </div>
        """, unsafe_allow_html=True)
    with col_m:
        st.markdown(f"""
        <div class="tier-card tier-mild">
            <span class="tier-tag tier-tag-mild">Mild</span>
            <div class="tier-count">{summary['n_mild']}</div>
            {render_tier_markets(mild_markets)}
        </div>
        """, unsafe_allow_html=True)
    with col_s:
        st.markdown(f"""
        <div class="tier-card tier-safe">
            <span class="tier-tag tier-tag-safe">Safe</span>
            <div class="tier-count">{summary['n_safe']}</div>
            {render_tier_markets(safe_markets)}
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="uber-divider">', unsafe_allow_html=True)

    # ── OUTPUT 1: CITY-LEVEL ALLOCATION ───────────────────────────────────
    st.markdown('<p class="section-title">1️⃣ City-Level Allocation</p>', unsafe_allow_html=True)


    t1 = results[[
        'Market', 'Tier', 'Score', 'PV_per_Dollar', 'Passes_Hurdle',
        'Investment', 'Share_Q0', 'Share_Q1', 'Redline', 'Redline_Q1_OK', 'Platform_Value'
    ]].copy()
    t1['Score']          = t1['Score'].apply(lambda v: f"{v:.3f}")
    t1['PV_per_Dollar']  = t1['PV_per_Dollar'].apply(lambda v: f"{v:.2f}×")
    t1['Investment']     = t1['Investment'].apply(lambda v: f"${v/1e6:.2f}M")
    t1['Share_Q0']       = t1['Share_Q0'].apply(lambda v: f"{v:.1%}")
    t1['Share_Q1']       = t1['Share_Q1'].apply(lambda v: f"{v:.1%}")
    t1['Redline']        = t1['Redline'].apply(lambda v: f"{v:.0%}")
    t1['Platform_Value'] = t1['Platform_Value'].apply(lambda v: f"${v/1e6:.1f}M")
    t1 = t1.rename(columns={
        'PV_per_Dollar': 'PV per $', 'Passes_Hurdle': 'Hurdle',
        'Investment': 'Total Investment', 'Share_Q0': 'Share (current)',
        'Share_Q1': 'Share Q1 (post-inv)', 'Redline_Q1_OK': 'Above Redline Q1',
        'Platform_Value': 'Total Platform Value',
    })
    st.dataframe(t1, use_container_width=True, hide_index=True)
    st.markdown('<hr class="uber-divider">', unsafe_allow_html=True)

    # ── OUTPUT 2: LEVER MIX ───────────────────────────────────────────────
    st.markdown('<p class="section-title">2️⃣ Lever Mix</p>', unsafe_allow_html=True)


    t2 = results[results['Investment'] > 0][[
        'Market', 'Tier', 'Cash_Investment', 'Pricing_Revenue', 'Discount_Cost',
        'Rider_Pct', 'Driver_Pct', 'Discount_Pct'
    ]].copy()

    t2['Cash_Investment'] = t2['Cash_Investment'].apply(lambda v: f"${v/1e6:.2f}M")
    t2['Pricing_Revenue'] = t2['Pricing_Revenue'].apply(lambda v: f"${v/1e6:.2f}M" if v > 0 else "—")
    t2['Discount_Cost']   = t2['Discount_Cost'].apply(lambda v: f"${v/1e6:.2f}M" if v > 1000 else "—")

    t2['Rider_Pct']    = t2['Rider_Pct'].apply(lambda v: f"{v:.0%}")
    t2['Driver_Pct']   = t2['Driver_Pct'].apply(lambda v: f"{v:.0%}")
    t2['Discount_Pct'] = t2['Discount_Pct'].apply(lambda v: f"{v:.0%}" if v > 0.001 else "—")

    t2 = t2.rename(columns={
        'Cash_Investment': 'Total Cash Outlay (10% Budget)',
        'Pricing_Revenue': 'Price Increase Rev (Self-Funded)',
        'Discount_Cost': 'Discount Cost (Budget-Funded)',
        'Rider_Pct': 'Rider Incentives (%)',
        'Driver_Pct': 'Driver Incentives (%)',
        'Discount_Pct': 'Pricing Discount (%)',
    })
    st.dataframe(t2, use_container_width=True, hide_index=True)
    

    st.markdown('<hr class="uber-divider">', unsafe_allow_html=True)

    # ── OUTPUT 3: IMPACT PROJECTION ───────────────────────────────────────
    st.markdown('<p class="section-title">3️⃣ Impact Projection</p>', unsafe_allow_html=True)


    t3 = results[[
        'Market', 'Tier', 'Trips_Q1', 'GB_Delta_Q1', 'NPM1',
        'LTV', 'Platform_Value'
    ]].copy()
    t3['Trips_Q1']       = t3['Trips_Q1'].apply(
        lambda v: f"{v/1e6:.2f}M" if v >= 1e6 else f"{v/1e3:.1f}K" if v >= 1000 else f"{v:.0f}"
    )
    t3['GB_Delta_Q1']    = t3['GB_Delta_Q1'].apply(lambda v: f"${v/1e6:.2f}M")
    t3['NPM1']           = t3['NPM1'].apply(lambda v: f"${v/1e6:.2f}M")
    t3['LTV']            = t3['LTV'].apply(lambda v: f"${v/1e6:.2f}M")
    t3['Platform_Value'] = t3['Platform_Value'].apply(lambda v: f"${v/1e6:.1f}M")
    t3 = t3.rename(columns={
        'Trips_Q1':       'Incremental Trips (Q1)',
        'GB_Delta_Q1':    'GB Impact (Q1)',
        'NPM1':           'Net Profit Q1',
        'LTV':            'LTV (4-Quarter)',
        'Platform_Value': 'Total Platform Value',
    })
    st.dataframe(t3, use_container_width=True, hide_index=True)

    # ── LTV Curve ──────────────────────────────────────────────────────────
    st.markdown("#### 📈 Platform Value Accumulation — 4-Quarter Horizon")


    RETENTION  = 0.35
    DISCOUNT   = 0.025
    N_QUARTERS = 4
    quarters   = [f"Q{t}" for t in range(1, N_QUARTERS + 1)]

    funded     = results[results['Investment'] > 0].copy()
    curve_data = {}

    for _, row in funded.iterrows():
        npm1       = row['NPM1']
        gb_delta   = row['GB_Delta_Q1']
        cumulative = 0.0
        values     = []
        for t in range(1, N_QUARTERS + 1):
            if t == 1:
                cumulative += npm1
            else:
                pv_t = gb_delta * margin * (RETENTION ** t) / ((1 + DISCOUNT) ** t)
                cumulative += pv_t
            values.append(round(cumulative / 1e6, 3))
        curve_data[row['Market']] = {'values': values, 'tier': row['Tier']}

    tier_color = {'CRITICAL': '#EF4444', 'MILD': '#F59E0B', 'SAFE': '#06C167'}
    tier_dash  = {'CRITICAL': 'solid',   'MILD': 'dash',    'SAFE': 'dot'}

    tab_all, tab_critical, tab_mild, tab_safe = st.tabs(
        ["All Markets", "🔴 CRITICAL", "🟡 MILD", "🟢 SAFE"]
    )

    def build_fig(markets_filter=None):
        fig = go.Figure()
        for market, info in curve_data.items():
            if markets_filter and info['tier'] not in markets_filter:
                continue
            fig.add_trace(go.Scatter(
                x=quarters,
                y=info['values'],
                mode='lines+markers',
                name=f"{market} ({info['tier']})",
                line=dict(color=tier_color[info['tier']], width=2.5, dash=tier_dash[info['tier']]),
                marker=dict(size=6, symbol='circle'),
                hovertemplate=(
                    f"<b>{market}</b><br>"
                    "Quarter: %{x}<br>"
                    "Cumulative PV: $%{y:.2f}M<br>"
                    "<extra></extra>"
                ),
            ))
        fig.add_hline(
            y=0, line_dash='dash', line_color='#D1D5DB', line_width=1,
            annotation_text='Breakeven', annotation_position='right',
            annotation_font=dict(size=11, color='#9CA3AF'),
        )
        fig.update_layout(
            height=460,
            margin=dict(l=40, r=20, t=20, b=40),
            font=dict(family='Inter, sans-serif', size=12, color='#374151'),
            legend=dict(
                orientation='h', yanchor='bottom', y=1.02,
                xanchor='right', x=1, font=dict(size=11),
                bgcolor='rgba(255,255,255,0)',
            ),
            xaxis_title='Quarter',
            yaxis_title='Cumulative Platform Value ($M)',
            plot_bgcolor='#FAFAFA',
            paper_bgcolor='#FFFFFF',
            xaxis=dict(showgrid=False, zeroline=False, linecolor='#E5E7EB'),
            yaxis=dict(
                showgrid=True, gridcolor='#F3F4F6', zeroline=False,
                tickprefix='$', ticksuffix='M',
            ),
            hovermode='x unified',
        )
        return fig

    with tab_all:
        st.plotly_chart(build_fig(), use_container_width=True)
    with tab_critical:
        st.plotly_chart(build_fig(['CRITICAL']), use_container_width=True)
    with tab_mild:
        st.plotly_chart(build_fig(['MILD']), use_container_width=True)
    with tab_safe:
        st.plotly_chart(build_fig(['SAFE']), use_container_width=True)

    st.markdown('<hr class="uber-divider">', unsafe_allow_html=True)

    # ── OUTPUT 4: HURDLE RATE SUMMARY ─────────────────────────────────────
    st.markdown('<p class="section-title">4️⃣ Hurdle Rate Summary</p>', unsafe_allow_html=True)

    t4 = results[[
        'Market', 'Tier', 'PV_per_Dollar', 'Passes_Hurdle', 'Investment'
    ]].copy().sort_values('PV_per_Dollar', ascending=False)
    t4['PV_per_Dollar'] = t4['PV_per_Dollar'].apply(lambda v: f"{v:.2f}×")
    t4['Investment']    = t4['Investment'].apply(lambda v: f"${v/1e6:.2f}M" if v > 0 else "—")
    t4 = t4.rename(columns={
        'PV_per_Dollar': 'Platform Value per $',
        'Passes_Hurdle': 'Passes Hurdle',
        'Investment':    'Allocated',
    })
    st.dataframe(t4, use_container_width=True, hide_index=True)



    # ── EXPORT ────────────────────────────────────────────────────────────
    st.markdown('<hr class="uber-divider">', unsafe_allow_html=True)

    def to_excel(df_results, df_inputs):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_results.to_excel(writer, sheet_name='Allocation_Model', index=False)
            df_inputs.to_excel(writer, sheet_name='Market_Inputs', index=False)
        return output.getvalue()

    st.download_button(
        label="⬇️ Export Results to Excel",
        data=to_excel(results, df_edited),
        file_name="Uber_Allocation_Results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )