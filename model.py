import pandas as pd
import numpy as np

# =============================================================================
# --- DATA LOADING & MOCK DATA ---
# =============================================================================
def load_market_data():
    return pd.DataFrame({
        'Market': [
            'Springfield', 'South Park', 'Duckburg', 'Bedrock', 'Hogsmeade',
            'Metropolis', 'Gotham', 'Mordor', 'Lilliput', 'Emerald City',
            'Narnia', 'The Shire', 'Kings Landing', 'Tatooine', 'Quahog'
        ],
        'GB': [
            8416110, 7893618, 16285318, 30667796, 12594129,
            6567916, 54124385, 5555084, 36419613, 24708032,
            5388682, 69873567, 38925106, 3229994, 21067481
        ],
        'Surge': [
            0.3872, 0.0804, 0.0754, 0.1140, 0.1428,
            0.2520, 0.1975, 0.1159, 0.1820, 0.1040,
            0.0374, 0.1471, 0.1303, 0.2771, 0.1400
        ],
        'CM': [
            -0.06, 0.15, 0.17, 0.05, 0.08,
             0.10, 0.06, 0.10, 0.02, 0.06,
             0.07, 0.09, 0.04, 0.09, 0.06
        ],
        'Share': [
            0.95, 0.90, 0.93, 0.95, 0.85,
            0.50, 0.73, 0.85, 0.70, 0.78,
            0.55, 0.76, 0.73, 0.90, 0.82
        ],
        'Redline': [
            0.80, 0.80, 0.80, 0.80, 0.80,
            0.60, 0.75, 0.80, 0.75, 0.80,
            0.50, 0.75, 0.75, 0.80, 0.80
        ],
        'CPIT': [
            2.627, 3.760, 3.711, 3.950, 4.081,
            4.253, 3.365, 3.167, 2.736, 3.206,
            3.427, 3.385, 2.897, 2.575, 3.375
        ],
        'CPISH': [
            5.704, 2.009, 1.884, 2.849, 3.569,
            6.300, 4.938, 2.898, 4.549, 2.599,
            0.935, 3.677, 3.257, 6.927, 3.501
        ],
        'Avg_Fare': [
            4.42, 5.954, 5.877, 6.730, 6.172,
            5.452, 5.807, 5.198, 4.910, 5.138,
            5.914, 5.695, 4.755, 6.932, 5.048
        ],
        'Comp_Fare': [
            4.32, 6.481, 5.761, 6.057, 5.246,
            4.362, 5.692, 4.938, 4.665, 4.624,
            5.027, 5.353, 4.518, 7.001, 4.543
        ],
        'TPH': [
            2.382, 1.792, 1.836, 2.299, 2.305,
            2.252, 2.311, 1.689, 2.146, 1.931,
            1.831, 1.973, 1.772, 2.119, 1.937
        ],
        'Growth': [
            0.288, 0.216, 0.216, 0.302, 0.158,
           -0.072, 0.317, 0.259, 0.360, 0.230,
            0.317, 0.288, 0.259, 0.720, 0.144
        ],
        'CR': [
            0.6975, 0.7122, 0.8647, 0.7115, 0.7305,
            0.7965, 0.6890, 0.8212, 0.9089, 0.7023,
            0.7201, 0.8254, 0.7058, 0.7511, 0.8330
        ],
    })

# =============================================================================
# --- FINANCIAL & LTV UTILITIES ---
# =============================================================================
def compute_ltv_mult_base(retention=0.35, discount_rate=0.025, n_quarters=8):
    return sum((retention ** t) / ((1 + discount_rate) ** t) for t in range(1, n_quarters + 1))

def build_ltv_curves(retention=0.35, discount_rate=0.025, n_quarters=8, ltv_critical=3.0, ltv_mild=2.0, ltv_safe=1.5):
    rows = []
    pv_accum = ret_accum = 0.0
    for t in range(1, n_quarters + 1):
        pv_accum += (retention ** t) / ((1 + discount_rate) ** t)
        ret_accum += retention ** t
        rows.append({
            'Quarter': f'Q{t}',
            'Retention Pure (accumulated)': round(ret_accum, 4),
            'PV Pure (accumulated)': round(pv_accum, 4),
            'CRITICAL mult': ltv_critical,
            'MILD mult': ltv_mild,
            'SAFE mult': ltv_safe,
        })
    return pd.DataFrame(rows)

# =============================================================================
# --- MAIN OPTIMIZATION ENGINE ---
# =============================================================================
def run_optimization(df, budget_pct=0.10, cap_pct=0.20, margin=0.25,
                     w_critical=2.0, w_mild=1.3, w_safe=1.0, growth_weight=0.5,
                     ltv_critical=1.5, ltv_mild=0.75, ltv_safe=0.50, hurdle_rate=1.5,
                     discount_elasticity=1.0):
    
    # --- SETUP & INITIAL CALCULATIONS ---
    df = df.copy()
    df['Trips_Base'] = df['GB'] / df['Avg_Fare']
    # Budget is 10% of total regional Gross Bookings
    BUDGET = df['GB'].sum() * budget_pct
    
    ltv_map = {'CRITICAL': ltv_critical, 'MILD': ltv_mild, 'SAFE': ltv_safe}
    ltv_fin_mult = compute_ltv_mult_base()

    # --- 1. STRATEGIC TIER CLASSIFICATION ---
    condicoes = [df['Share'] < df['Redline'], df['Share'] < df['Redline'] + 0.10]
    df['tier'] = np.select(condicoes, ['CRITICAL', 'MILD'], default='SAFE')

    # --- 2. LEVER ELIGIBILITY RULES ---
    df['rider_ok']  = df['CM'] >= 0.00
    df['driver_ok'] = df['CM'] >= -0.10
    # Price INCREASE lever: unlocked if we have a competitive price advantage (>3%)
    df['price_up_ok'] = (df['Comp_Fare'] > df['Avg_Fare'] * 1.03) & ~((df['Surge'] > 0.25) & (df['CR'] < 0.72))
    # [FIX 2] Price DISCOUNT lever: unlocked if we are >3% more expensive than competition
    # Case: "discounts are funded by Uber's margin" → competes for the 10% cash budget
    df['price_down_ok'] = (df['Avg_Fare'] > df['Comp_Fare'] * 1.03) & (df['tier'] == 'CRITICAL') & ~((df['Surge'] > 0.25) & (df['CR'] < 0.72))

    # --- 3. PRICING REVENUE (SELF-FUNDED) ---
    # Price increases generate 5% extra revenue on market GB
    df['pricing_revenue'] = np.where(df['price_up_ok'], df['GB'] * 0.05, 0.0)
    # Elasticity penalty: 15% reduction in trip impact efficiency
    df['trips_price_impact'] = np.where(df['price_up_ok'], (df['pricing_revenue'] / df['Avg_Fare']) * 0.85, 0.0)

    # --- 4. ROI CALCULATION (FOR DISCRETIONARY BUDGET) ---
    # ROI = (Trips per $) * Price * Margin
    df['roi_rider']  = np.where(df['rider_ok'], (1.0 / df['CPIT']) * df['Avg_Fare'] * margin, 0.0)
    df['roi_driver'] = np.where(df['driver_ok'], (df['TPH'] / df['CPISH']) * (1.0 / df['CR']) * df['Avg_Fare'] * margin, 0.0)
    
    # [FIX 2] Pricing discount ROI: competes for budget alongside Rider & Driver
    # Discount closes half the fare gap (capped at 10%), generates trips via elasticity
    fare_gap = (df['Avg_Fare'] / df['Comp_Fare'] - 1).clip(lower=0)
    df['discount_pct'] = np.where(df['price_down_ok'], np.minimum(fare_gap * 0.5, 0.10), 0.0)
    df['new_fare'] = df['Avg_Fare'] * (1 - df['discount_pct'])
    # Efficiency: trips generated per $ of discount cost
    # e_discount = (Trips_Base * discount_pct * elasticity) / (GB * discount_pct) = elasticity / Avg_Fare
    e_discount = np.where(df['price_down_ok'], discount_elasticity / df['Avg_Fare'], 0.0)
    df['roi_discount'] = np.where(df['price_down_ok'], e_discount * df['new_fare'] * margin, 0.0)

    # All three levers compete for the 10% cash budget
    df['best_roi'] = df[['roi_rider', 'roi_driver', 'roi_discount']].max(axis=1)

    e_rider  = np.where(df['rider_ok'], 1.0 / df['CPIT'], 0.0)
    e_driver = np.where(df['driver_ok'], (df['TPH'] / df['CPISH']) * (1.0 / df['CR']), 0.0)
    df['best_e'] = np.maximum.reduce([e_rider, e_driver, e_discount])

    # [FIX 1] Compute BLENDED efficiency for hurdle rate (not best_e)
    # The lever split is proportional to ROI, so blended_e reflects actual deployment
    roi_sum_for_blend = df['roi_rider'] + df['roi_driver'] + df['roi_discount']
    blend_pct_r = np.where(roi_sum_for_blend > 0, df['roi_rider'] / roi_sum_for_blend, 0.0)
    blend_pct_d = np.where(roi_sum_for_blend > 0, df['roi_driver'] / roi_sum_for_blend, 0.0)
    blend_pct_disc = np.where(roi_sum_for_blend > 0, df['roi_discount'] / roi_sum_for_blend, 0.0)
    df['blended_e'] = e_rider * blend_pct_r + e_driver * blend_pct_d + e_discount * blend_pct_disc

    # --- 5. HURDLE RATE FILTER ---
    df['ltv_strat'] = df['tier'].map(ltv_map)
    # [FIX 1] Hurdle uses blended efficiency — reflects actual deployment, not best-case
    df['pv_per_dollar'] = df['blended_e'] * df['Avg_Fare'] * margin * (1 + ltv_fin_mult + df['ltv_strat']) - 1
    df['supply_crisis'] = (df['Surge'] > 0.25) & (df['CR'] < 0.72)
    # Critical markets bypass the hurdle for strategic defense
    df['passes_hurdle'] = (df['tier'] == 'CRITICAL') | df['supply_crisis'] | (df['pv_per_dollar'] >= hurdle_rate)

    # --- 6. COMPOSITE SCORING ---
    weight_map = {'CRITICAL': w_critical, 'MILD': w_mild, 'SAFE': w_safe}
    df['weight'] = df['tier'].map(weight_map)
    df['growth_bonus'] = 1.0 + df['Growth'].clip(lower=0) * growth_weight
    df['score'] = np.where(df['passes_hurdle'], df['best_roi'] * df['weight'] * df['growth_bonus'], 0.0)

    # --- 7. CAPS & MINIMUM INVESTMENT ---
    lift = np.minimum(df['Redline'] - df['Share'] + 0.01, df['Surge'])
    trips_need = lift * df['Trips_Base'] / 0.5
    df['min_investment'] = np.where((df['tier'] == 'CRITICAL') & (df['blended_e'] > 0), trips_need / df['blended_e'], 0.0)
    df['cap'] = df['GB'] * cap_pct
    df['min_investment'] = df[['min_investment', 'cap']].min(axis=1)

    total_min = df['min_investment'].sum()
    if total_min > BUDGET:
        df['min_investment'] *= (BUDGET / total_min)

    # --- 8. GREEDY ALLOCATION (CASH BUDGET ONLY) ---
    df['investment'] = df['min_investment'].copy()
    df['headroom'] = (df['cap'] - df['investment']).clip(lower=0)
    df.loc[~df['passes_hurdle'], 'headroom'] = 0.0
    remaining = BUDGET - df['investment'].sum()

    for _ in range(50):
        if remaining < 0.01: break
        eligible = df['headroom'] > 0
        score_sum = df.loc[eligible, 'score'].sum()
        if score_sum == 0: break
        proposed = (df.loc[eligible, 'score'] / score_sum) * remaining
        capped = proposed.clip(upper=df.loc[eligible, 'headroom'])
        df.loc[eligible, 'investment'] += capped
        df['headroom'] = (df['cap'] - df['investment']).clip(lower=0)
        df.loc[~df['passes_hurdle'], 'headroom'] = 0.0
        remaining -= capped.sum()

    budget_used = df['investment'].sum()
    budget_returned = BUDGET - budget_used

    # --- 9. IMPACT PROJECTION ---
    # [FIX 2] Three-way lever split: Rider / Driver / Discount (proportional to ROI)
    roi_total = df['roi_rider'] + df['roi_driver'] + df['roi_discount']
    valid_roi = (roi_total > 0) & (df['investment'] > 0)

    pct_r    = np.where(valid_roi, df['roi_rider']    / roi_total, 0.0)
    pct_d    = np.where(valid_roi, df['roi_driver']   / roi_total, 0.0)
    pct_disc = np.where(valid_roi, df['roi_discount'] / roi_total, 0.0)

    inv_r    = df['investment'] * pct_r
    inv_d    = df['investment'] * pct_d
    inv_disc = df['investment'] * pct_disc

    trips_r    = np.where((inv_r > 0) & df['rider_ok'], inv_r / df['CPIT'], 0.0)
    trips_d    = np.where((inv_d > 0) & df['driver_ok'], (inv_d / df['CPISH']) * df['TPH'] * (1 / df['CR']), 0.0)
    trips_disc = np.where(inv_disc > 0, inv_disc * e_discount, 0.0)
    
    # Impact = Rider trips + Driver trips + Discount trips + Pricing-increase trips
    trips = trips_r + trips_d + trips_disc + df['trips_price_impact']
    cash_outlay = inv_r + inv_d + inv_disc

    gb_delta = trips * df['Avg_Fare']
    # Profit Q1 (NPM1) = Incremental Margin + Price-Increase Rev - Cash Spent
    npm1 = (gb_delta * margin) + df['pricing_revenue'] - cash_outlay
    
    # [FIX 3] LTV with reduced strategic multipliers (default 1.5/0.75/0.5 instead of 3/2/1.5)
    ltv_financial = gb_delta * margin * ltv_fin_mult
    ltv_strategic = gb_delta * margin * df['ltv_strat']
    ltv = ltv_financial + ltv_strategic
    platform_value = npm1 + ltv 

    raw_lift = np.where(df['Trips_Base'] > 0, (trips / df['Trips_Base']) * 0.5, 0.0)
    share_q1 = np.minimum.reduce([
        df['Share'] + raw_lift,
        df['Share'] + (1 - df['CR']),
        df['Share'] + df['Surge'],
        np.ones(len(df))
    ])

    # --- 10. RESULTS AGGREGATION ---
    results_df = pd.DataFrame({
        'Market': df['Market'],
        'Tier': df['tier'],
        'Score': df['score'].round(3),
        'Passes_Hurdle': np.where(df['passes_hurdle'], '✓', '✗'),
        'PV_per_Dollar': df['pv_per_dollar'].round(3),
        'Investment': df['investment'],
        'Cash_Investment': cash_outlay,
        'Pricing_Revenue': df['pricing_revenue'],
        'Discount_Cost': inv_disc,
        'Rider_Pct': pct_r,
        'Driver_Pct': pct_d,
        'Discount_Pct': pct_disc,
        'Trips_Q1': trips,
        'GB_Delta_Q1': gb_delta,
        'NPM1': npm1,
        'LTV_Financial': ltv_financial,
        'LTV_Strategic': ltv_strategic,
        'LTV': ltv,
        'Platform_Value': platform_value,
        'Share_Q0': df['Share'],
        'Share_Q1': share_q1,
        'Redline': df['Redline'],
        'Redline_Q1_OK': np.where(share_q1 >= df['Redline'], '✓', '✗')
    }).sort_values('Investment', ascending=False)

    summary = {
        'budget': BUDGET / 1e6,
        'allocated': budget_used / 1e6,
        'returned': budget_returned / 1e6,
        'utilization': budget_used / BUDGET if BUDGET > 0 else 0,
        'npm1': results_df['NPM1'].sum() / 1e6,
        'ltv': results_df['LTV'].sum() / 1e6,
        'platform_value': results_df['Platform_Value'].sum() / 1e6,
        'redline_ok': (results_df['Redline_Q1_OK'] == '✓').sum(),
        'total_markets': len(results_df),
        'markets_funded': (results_df['Investment'] > 0).sum(),
        'markets_excluded': (results_df['Passes_Hurdle'] == '✗').sum(),
        'n_critical': (results_df['Tier'] == 'CRITICAL').sum(),
        'n_mild': (results_df['Tier'] == 'MILD').sum(),
        'n_safe': (results_df['Tier'] == 'SAFE').sum(),
        'ltv_mult_base': ltv_fin_mult,
    }

    return results_df, summary