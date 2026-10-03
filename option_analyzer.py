import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def generate_option_chain_data(symbol="NIFTY", current_price=24850.0):
    """
    Generates realistic option chain strike data around current price.
    """
    symbol = symbol.upper()
    
    if symbol == "NIFTY":
        strike_step = 50
        spot = current_price if current_price else 24850.0
    elif symbol == "BANKNIFTY":
        strike_step = 100
        spot = current_price if current_price else 54200.0
    elif symbol == "FINNIFTY":
        strike_step = 50
        spot = current_price if current_price else 25100.0
    else:
        strike_step = 25
        spot = current_price if current_price else 3000.0

    atm_strike = round(spot / strike_step) * strike_step
    strikes = [atm_strike + i * strike_step for i in range(-15, 16)]
    
    np.random.seed(hash(symbol) % 2**32)
    
    call_oi = []
    put_oi = []
    call_oi_chg = []
    put_oi_chg = []
    
    for k in strikes:
        # Calls have higher OI OTM (above spot)
        # Puts have higher OI OTM (below spot)
        dist = (k - spot) / strike_step
        
        call_base = np.exp(-dist * 0.15) if dist >= 0 else np.exp(dist * 0.3)
        put_base = np.exp(dist * 0.15) if dist <= 0 else np.exp(-dist * 0.3)
        
        c_oi = int((call_base * np.random.uniform(80000, 150000)) + np.random.uniform(5000, 20000))
        p_oi = int((put_base * np.random.uniform(80000, 150000)) + np.random.uniform(5000, 20000))
        
        # Add prominent Call Wall and Put Wall
        if k == atm_strike + 3 * strike_step:
            c_oi += 180000  # Major Call Resistance Wall
        if k == atm_strike - 3 * strike_step:
            p_oi += 200000  # Major Put Support Wall
            
        c_chg = int(np.random.uniform(-15000, 35000))
        p_chg = int(np.random.uniform(-15000, 35000))
        
        call_oi.append(c_oi)
        put_oi.append(p_oi)
        call_oi_chg.append(c_chg)
        put_oi_chg.append(p_chg)
        
    df = pd.DataFrame({
        'strike': strikes,
        'call_oi': call_oi,
        'call_oi_chg': call_oi_chg,
        'put_oi': put_oi,
        'put_oi_chg': put_oi_chg
    })
    
    return df, spot

def calculate_max_pain(df):
    """
    Calculates the Max Pain strike where option buyers suffer maximum financial loss.
    """
    strikes = df['strike'].values
    call_ois = df['call_oi'].values
    put_ois = df['put_oi'].values
    
    min_pain = float('inf')
    max_pain_strike = strikes[0]
    pain_values = {}
    
    for s in strikes:
        # Expiry at s:
        # Call payout = max(0, s - k) * call_oi
        # Put payout = max(0, k - s) * put_oi
        call_loss = np.maximum(0, s - strikes) * call_ois
        put_loss = np.maximum(0, strikes - s) * put_ois
        
        total_loss = np.sum(call_loss) + np.sum(put_loss)
        pain_values[s] = total_loss
        
        if total_loss < min_pain:
            min_pain = total_loss
            max_pain_strike = s
            
    return max_pain_strike, pain_values

def analyze_option_concentration(symbol="NIFTY", spot_price=None):
    """
    Main Option Analysis function returning Max Pain, PCR, Seller Concentration & Signals.
    """
    df, spot = generate_option_chain_data(symbol, current_price=spot_price)
    
    max_pain_strike, _ = calculate_max_pain(df)
    
    # Top Call Wall (Max Call OI) -> Resistance
    call_wall_row = df.loc[df['call_oi'].idxmax()]
    call_wall_strike = call_wall_row['strike']
    max_call_oi = call_wall_row['call_oi']
    
    # Top Put Wall (Max Put OI) -> Support
    put_wall_row = df.loc[df['put_oi'].idxmax()]
    put_wall_strike = put_wall_row['strike']
    max_put_oi = put_wall_row['put_oi']
    
    total_call_oi = df['call_oi'].sum()
    total_put_oi = df['put_oi'].sum()
    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0
    
    # PCR Verdict
    if pcr > 1.25:
        pcr_bias = "BULLISH (HEAVY PUT WRITING / SMART SUPPORT)"
    elif pcr < 0.8:
        pcr_bias = "BEARISH (HEAVY CALL WRITING / SMART RESISTANCE)"
    else:
        pcr_bias = "NEUTRAL / RANGEBOUND"
        
    # Unwinding & Short Covering Detection
    unwinding_alerts = []
    
    # Check Call Unwinding / Short Covering (Negative Call OI Chg at high strikes)
    call_unwind = df[(df['call_oi_chg'] < -10000) & (df['strike'] >= spot)]
    for _, r in call_unwind.iterrows():
        unwinding_alerts.append({
            "type": "CALL_SHORT_COVERING",
            "strike": int(r['strike']),
            "chg": int(r['call_oi_chg']),
            "msg": f"Smart Money unwinding Short Calls at {r['strike']} strike (Short Covering / Bullish Breakout Sign)."
        })
        
    # Check Put Unwinding (Negative Put OI Chg at lower strikes)
    put_unwind = df[(df['put_oi_chg'] < -10000) & (df['strike'] <= spot)]
    for _, r in put_unwind.iterrows():
        unwinding_alerts.append({
            "type": "PUT_UNWINDING",
            "strike": int(r['strike']),
            "chg": int(r['put_oi_chg']),
            "msg": f"Smart Money abandoning Short Puts at {r['strike']} strike (Support Failure / Bearish Sign)."
        })

    # Convert DataFrame to JSON friendly format
    chain_list = df.to_dict(orient='records')
    
    return {
        "symbol": symbol.upper(),
        "spot_price": round(spot, 2),
        "max_pain": int(max_pain_strike),
        "call_wall": {
            "strike": int(call_wall_strike),
            "oi": int(max_call_oi)
        },
        "put_wall": {
            "strike": int(put_wall_strike),
            "oi": int(max_put_oi)
        },
        "total_call_oi": int(total_call_oi),
        "total_put_oi": int(total_put_oi),
        "pcr": pcr,
        "pcr_bias": pcr_bias,
        "unwinding_alerts": unwinding_alerts,
        "chain": chain_list
    }

if __name__ == "__main__":
    res = analyze_option_concentration("NIFTY")
    print("Symbol:", res['symbol'])
    print("Spot Price:", res['spot_price'])
    print("Max Pain:", res['max_pain'])
    print("Call Wall (Resistance):", res['call_wall'])
    print("Put Wall (Support):", res['put_wall'])
    print("PCR:", res['pcr'], "-", res['pcr_bias'])
    print("Unwinding Alerts:", len(res['unwinding_alerts']))
