import pandas as pd
import numpy as np

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


def compute_ltv_mult_base(retention=0.35, discount_rate=0.025, n_quarters=8):
    return sum(
        (retention ** t) / ((1 + discount_rate) ** t)
        for t in range(1, n_quarters + 1)
    )


def build_ltv_curves(retention=0.35, discount_rate=0.025,
                     n_quarters=8, ltv_critical=3.0,
                     ltv_mild=2.0, ltv_safe=1.5):
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


def classify_tier(share, redline):
    if share < redline:
        return 'CRITICAL'
    elif share < redline + 0.10:
        return 'MILD'
    return 'SAFE'


def run_optimization(
    df,
    budget_pct    = 0.10,
    cap_pct       = 0.20,
    margin        = 0.25,
    w_critical    = 2.0,
    w_mild        = 1.3,
    w_safe        = 1.0,
    growth_weight = 0.5,
    ltv_critical  = 3.0,
    ltv_mild      = 2.0,
    ltv_safe      = 1.5,
    hurdle_rate   = 1.5,
):
    df = df.copy()
    df['Trips_Base'] = df['GB'] / df['Avg_Fare']
    df['tier'] = df.apply(lambda r: classify_tier(r['Share'], r['Redline']), axis=1)

    BUDGET  = df['GB'].sum() * budget_pct
    ltv_map = {'CRITICAL': ltv_critical, 'MILD': ltv_mild, 'SAFE': ltv_safe}

    # lever eligibility
    df['rider_ok']  = df['CM'] >= 0.00
    df['driver_ok'] = df['CM'] >= -0.10
    df['price_ok']  = (df['Avg_Fare'] > df['Comp_Fare'] * 1.03) & \
                      ~((df['Surge'] > 0.25) & (df['CR'] < 0.72))

    # ROI per lever
    df['roi_rider'] = df.apply(
        lambda r: (1.0 / r['CPIT']) * r['Avg_Fare'] * margin if r['rider_ok'] else 0.0, axis=1)
    df['roi_driver'] = df.apply(
        lambda r: (r['TPH'] / r['CPISH']) * (1.0 / r['CR']) * r['Avg_Fare'] * margin
        if r['driver_ok'] else 0.0, axis=1)
    df['roi_price'] = df.apply(
        lambda r: (1.0 / r['CPIT']) * r['Avg_Fare'] * margin * 0.85
        if r['price_ok'] else 0.0, axis=1)

    df['best_roi'] = df[['roi_rider', 'roi_driver', 'roi_price']].max(axis=1)
    df['best_e'] = df.apply(lambda r: max(
        (1.0 / r['CPIT']) if r['rider_ok'] else 0.0,
        (r['TPH'] / r['CPISH']) * (1.0 / r['CR']) if r['driver_ok'] else 0.0,
        (1.0 / r['CPIT']) * 0.85 if r['price_ok'] else 0.0,
    ), axis=1)

    # hurdle filter
    df['pv_per_dollar'] = df.apply(
        lambda r: r['best_e'] * r['Avg_Fare'] * margin * (1 + ltv_map[r['tier']]) - 1, axis=1)

    df['supply_crisis'] = (df['Surge'] > 0.25) & (df['CR'] < 0.72)

    df['passes_hurdle'] = (
        (df['tier'] == 'CRITICAL') |
        (df['supply_crisis'])      |
        (df['pv_per_dollar'] >= hurdle_rate)
    )

    # composite score
    weight_map = {'CRITICAL': w_critical, 'MILD': w_mild, 'SAFE': w_safe}
    df['weight']       = df['tier'].map(weight_map)
    df['growth_bonus'] = 1.0 + df['Growth'].clip(lower=0) * growth_weight
    df['score'] = df.apply(
        lambda r: r['best_roi'] * r['weight'] * r['growth_bonus']
        if r['passes_hurdle'] else 0.0, axis=1)

    # minimum investment for CRITICAL markets
    def min_inv(r):
        if r['tier'] != 'CRITICAL' or r['best_e'] == 0:
            return 0.0
        lift  = min(r['Redline'] - r['Share'] + 0.01, r['Surge'])
        trips = lift * r['Trips_Base'] / 0.5
        return trips / r['best_e']

    df['min_investment'] = df.apply(min_inv, axis=1)
    df['cap']            = df['GB'] * cap_pct
    df['min_investment'] = df[['min_investment', 'cap']].min(axis=1)

    total_min = df['min_investment'].sum()
    if total_min > BUDGET:
        df['min_investment'] *= BUDGET / total_min

    # greedy allocation
    df['investment'] = df['min_investment'].copy()
    df['headroom']   = (df['cap'] - df['investment']).clip(lower=0)
    df.loc[~df['passes_hurdle'], 'headroom'] = 0.0
    remaining = BUDGET - df['investment'].sum()

    for _ in range(50):
        if remaining < 0.01:
            break
        eligible  = df['headroom'] > 0
        score_sum = df.loc[eligible, 'score'].sum()
        if score_sum == 0:
            break
        proposed = (df.loc[eligible, 'score'] / score_sum) * remaining
        capped   = proposed.clip(upper=df.loc[eligible, 'headroom'])
        df.loc[eligible, 'investment'] += capped
        df['headroom'] = (df['cap'] - df['investment']).clip(lower=0)
        df.loc[~df['passes_hurdle'], 'headroom'] = 0.0
        remaining -= capped.sum()

    budget_used     = df['investment'].sum()
    budget_returned = BUDGET - budget_used

    # per-market impact projection
    results      = []
    ltv_fin_mult = compute_ltv_mult_base()  # calculado uma vez, fora do loop

    for _, row in df.iterrows():
        inv = row['investment']
        roi_total = row['roi_rider'] + row['roi_driver'] + row['roi_price']

        if roi_total > 0 and inv > 0:
            pct_r = row['roi_rider']  / roi_total
            pct_d = row['roi_driver'] / roi_total
            pct_p = row['roi_price']  / roi_total
        else:
            pct_r = pct_d = pct_p = 0.0

        inv_r = inv * pct_r
        inv_d = inv * pct_d
        inv_p = inv * pct_p

        trips_r = (inv_r / row['CPIT']) if inv_r > 0 and row['rider_ok'] else 0.0
        trips_d = (inv_d / row['CPISH']) * row['TPH'] * (1 / row['CR']) \
                  if inv_d > 0 and row['driver_ok'] else 0.0
        trips_p = (inv_p / row['CPIT']) if inv_p > 0 and row['price_ok'] else 0.0
        trips   = trips_r + trips_d + trips_p

        cash_outlay     = inv_r + inv_d
        pricing_revenue = trips_p * row['Avg_Fare']

        if cash_outlay > 0:
            pct_r_cash = inv_r / cash_outlay
            pct_d_cash = inv_d / cash_outlay
        else:
            pct_r_cash = pct_d_cash = 0.0

        gb_delta      = trips * row['Avg_Fare']
        npm1          = gb_delta * margin - inv
        ltv_financial = gb_delta * ltv_fin_mult
        ltv_strategic = gb_delta * margin * ltv_map[row['tier']]
        ltv           = ltv_financial + ltv_strategic
        platform_value = npm1 + ltv

        raw_lift = (trips / row['Trips_Base']) * 0.5 if row['Trips_Base'] > 0 else 0.0
        share_q1 = min(
            row['Share'] + raw_lift,
            row['Share'] + (1 - row['CR']),
            row['Share'] + row['Surge'],
            1.0
        )

        results.append({
            'Market':          row['Market'],
            'Tier':            row['tier'],
            'Score':           round(row['score'], 3),
            'Passes_Hurdle':   '✓' if row['passes_hurdle'] else '✗',
            'PV_per_Dollar':   round(row['pv_per_dollar'], 3),
            'Investment':      inv,
            'Min_Investment':  row['min_investment'],
            'Cash_Investment': cash_outlay,
            'Pricing_Revenue': pricing_revenue,
            'Rider_Pct':       pct_r_cash,
            'Driver_Pct':      pct_d_cash,
            'Trips_Q1':        trips,
            'GB_Delta_Q1':     gb_delta,
            'NPM1':            npm1,
            'LTV_Financial':   ltv_financial,
            'LTV_Strategic':   ltv_strategic,
            'LTV':             ltv,
            'Platform_Value':  platform_value,
            'Share_Q0':        row['Share'],
            'Share_Q1':        share_q1,
            'Redline':         row['Redline'],
            'Redline_Q1_OK':   '✓' if share_q1 >= row['Redline'] else '✗',
        })

    results_df = pd.DataFrame(results).sort_values('Investment', ascending=False)

    summary = {
        'budget':           BUDGET / 1e6,
        'allocated':        budget_used / 1e6,
        'returned':         budget_returned / 1e6,
        'utilization':      budget_used / BUDGET,
        'npm1':             results_df['NPM1'].sum() / 1e6,
        'ltv':              results_df['LTV'].sum() / 1e6,
        'platform_value':   results_df['Platform_Value'].sum() / 1e6,
        'redline_ok':       (results_df['Redline_Q1_OK'] == '✓').sum(),
        'total_markets':    len(results_df),
        'markets_funded':   (results_df['Investment'] > 0).sum(),
        'markets_excluded': (results_df['Passes_Hurdle'] == '✗').sum(),
        'n_critical':       (results_df['Tier'] == 'CRITICAL').sum(),
        'n_mild':           (results_df['Tier'] == 'MILD').sum(),
        'n_safe':           (results_df['Tier'] == 'SAFE').sum(),
        'ltv_mult_base':    compute_ltv_mult_base(),
    }

    return results_df, summary