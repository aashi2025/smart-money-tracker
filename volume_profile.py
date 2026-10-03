import numpy as np
import pandas as pd
import datetime
import math
import logging

logger = logging.getLogger(__name__)

def generate_mock_intraday_candles(symbol="NIFTY", days=5, num_bins=50):
    """
    Generates realistic intraday candle data (1-minute / 5-minute candles)
    for index or stock symbols with realistic volume distribution.
    Used as reliable fallback or stand-alone visualization engine.
    """
    # Base prices for key symbols
    base_prices = {
        "NIFTY": 24850.0,
        "BANKNIFTY": 54200.0,
        "FINNIFTY": 25100.0,
        "RELIANCE": 3020.0,
        "HDFCBANK": 1680.0,
        "TCS": 4250.0,
        "INFY": 1920.0,
        "ICICIBANK": 1240.0
    }
    
    base_price = base_prices.get(symbol.upper(), 2500.0)
    
    # Generate 5-minute intervals for 'days' trading days (75 bars per day, 9:15 to 15:30)
    total_bars = days * 75
    
    np.random.seed(hash(symbol + str(days)) % 2**32)
    
    # Random walk with mean reversion and institutional volume spikes
    returns = np.random.normal(0.0001, 0.0015, total_bars)
    
    # Add institutional POC clustering around key levels
    price_series = [base_price]
    for r in returns:
        new_p = price_series[-1] * (1 + r)
        price_series.append(new_p)
        
    prices = np.array(price_series[1:])
    
    # Generate volume with institutional volume profiles (U-shaped intraday volume + spike at POC)
    poc_center = np.median(prices)
    distance_from_poc = np.abs(prices - poc_center) / base_price
    
    # High volume near POC and at open/close
    base_vol = np.random.gamma(shape=2.0, scale=1500, size=total_bars)
    poc_vol_boost = np.exp(-distance_from_poc * 150) * 8000
    
    # Intraday pattern factor (high at open 9:15 and close 15:30)
    time_factors = 1.0 + 0.8 * np.sin(np.linspace(0, np.pi * days, total_bars))**2
    
    volume = (base_vol + poc_vol_boost) * time_factors
    
    highs = prices * (1 + np.abs(np.random.normal(0, 0.001, total_bars)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.001, total_bars)))
    opens = (highs + lows) / 2 + np.random.normal(0, 0.0005, total_bars) * prices
    closes = prices
    
    now = datetime.datetime.now()
    timestamps = [now - datetime.timedelta(minutes=5 * (total_bars - i)) for i in range(total_bars)]
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volume
    })
    
    return df

def calculate_volume_profile(df, num_bins=40, va_percent=0.70):
    """
    Computes Volume Profile, POC, VAH, VAL, VWAP, and Anchored VWAP.
    """
    if df is None or df.empty:
        return None
    
    min_price = df['low'].min()
    max_price = df['high'].max()
    
    # Add small margin
    price_range = max_price - min_price
    min_price -= price_range * 0.002
    max_price += price_range * 0.002
    
    bins = np.linspace(min_price, max_price, num_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2.0
    bin_volumes = np.zeros(num_bins)
    
    # Distribute candle volume across price bins
    for _, row in df.iterrows():
        p_low = row['low']
        p_high = row['high']
        vol = row['volume']
        
        # Find affected bins
        in_range_idx = np.where((bin_centers >= p_low) & (bin_centers <= p_high))[0]
        if len(in_range_idx) > 0:
            vol_per_bin = vol / len(in_range_idx)
            bin_volumes[in_range_idx] += vol_per_bin
        else:
            # Fallback to close price bin
            close_idx = np.digitize(row['close'], bins) - 1
            close_idx = max(0, min(num_bins - 1, close_idx))
            bin_volumes[close_idx] += vol
            
    total_volume = np.sum(bin_volumes)
    if total_volume == 0:
        return None
        
    # Identify Point of Control (POC)
    poc_idx = np.argmax(bin_volumes)
    poc_price = bin_centers[poc_idx]
    
    # Calculate Value Area (70% Volume around POC)
    target_va_vol = total_volume * va_percent
    accumulated_vol = bin_volumes[poc_idx]
    va_bins = {poc_idx}
    
    up_idx = poc_idx + 1
    down_idx = poc_idx - 1
    
    while accumulated_vol < target_va_vol and (up_idx < num_bins or down_idx >= 0):
        up_vol = bin_volumes[up_idx] if up_idx < num_bins else 0
        down_vol = bin_volumes[down_idx] if down_idx >= 0 else 0
        
        if up_vol >= down_vol and up_idx < num_bins:
            accumulated_vol += up_vol
            va_bins.add(up_idx)
            up_idx += 1
        elif down_idx >= 0:
            accumulated_vol += down_vol
            va_bins.add(down_idx)
            down_idx -= 1
        else:
            break
            
    va_min_idx = min(va_bins)
    va_max_idx = max(va_bins)
    
    val_price = bins[va_min_idx]       # Value Area Low
    vah_price = bins[va_max_idx + 1]   # Value Area High
    
    # Compute Session VWAP
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3.0
    df['pv'] = df['typical_price'] * df['volume']
    vwap_price = df['pv'].sum() / df['volume'].sum()
    
    # Anchored VWAP (e.g. from lowest point or start of week)
    min_price_idx = df['low'].idxmin()
    df_anchored = df.loc[min_price_idx:]
    anchored_vwap = df_anchored['pv'].sum() / df_anchored['volume'].sum() if not df_anchored.empty else vwap_price
    
    current_price = df['close'].iloc[-1]
    
    # Determine Institutional Signal & Regime
    if current_price > vah_price and current_price > vwap_price:
        signal = "INSTITUTIONAL MARKUP (BULLISH)"
        signal_code = "MARKUP"
        explanation = f"Price ({current_price:.2f}) is trading above VAH ({vah_price:.2f}) & VWAP ({vwap_price:.2f}). Smart Money is aggressively marking up prices."
    elif current_price < val_price and current_price < vwap_price:
        signal = "INSTITUTIONAL MARKDOWN (BEARISH)"
        signal_code = "MARKDOWN"
        explanation = f"Price ({current_price:.2f}) is trading below VAL ({val_price:.2f}) & VWAP ({vwap_price:.2f}). Smart Money is liquidating / shorting."
    elif abs(current_price - poc_price) / poc_price < 0.003:
        signal = "RE-TESTING POC (INSTITUTIONAL MAGNET)"
        signal_code = "POC_RETEST"
        explanation = f"Price ({current_price:.2f}) is retesting the Point of Control ({poc_price:.2f}). Expect high-probability reaction / reversal."
    else:
        signal = "VALUE AREA BALANCED CONSOLIDATION"
        signal_code = "BALANCED"
        explanation = f"Price ({current_price:.2f}) is ranging inside the Value Area [{val_price:.2f} - {vah_price:.2f}]."

    # Build profile histogram data for frontend rendering
    profile_data = []
    for i in range(num_bins):
        is_poc = bool(i == poc_idx)
        in_va = bool(i in va_bins)
        profile_data.append({
            "price_lower": float(round(bins[i], 2)),
            "price_upper": float(round(bins[i+1], 2)),
            "price_mid": float(round(bin_centers[i], 2)),
            "volume": float(round(bin_volumes[i], 2)),
            "is_poc": is_poc,
            "in_value_area": in_va
        })
        
    return {
        "current_price": float(round(current_price, 2)),
        "poc": float(round(poc_price, 2)),
        "vah": float(round(vah_price, 2)),
        "val": float(round(val_price, 2)),
        "vwap": float(round(vwap_price, 2)),
        "anchored_vwap": float(round(anchored_vwap, 2)),
        "signal": signal,
        "signal_code": signal_code,
        "explanation": explanation,
        "total_volume": float(round(total_volume, 2)),
        "profile": profile_data
    }

def get_volume_profile_analysis(symbol="NIFTY", days=5, num_bins=40):
    df = generate_mock_intraday_candles(symbol, days=days, num_bins=num_bins)
    return calculate_volume_profile(df, num_bins=num_bins)

if __name__ == "__main__":
    res = get_volume_profile_analysis("NIFTY")
    print("Symbol: NIFTY")
    print("Current Price:", res['current_price'])
    print("POC:", res['poc'])
    print("VAH:", res['vah'])
    print("VAL:", res['val'])
    print("VWAP:", res['vwap'])
    print("Signal:", res['signal'])
