import requests
import pandas as pd
import io
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Standard headers to bypass basic anti-scraping blocks
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webkit,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.nseindia.com/'
}

def fetch_participant_oi_csv(target_date: datetime.date):
    """
    Downloads participant-wise OI CSV from NSE Archive for a given date.
    URL format: https://archives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv
    If date fails (e.g. holiday/weekend), tries previous trading days up to 10 days back.
    """
    current_date = target_date
    max_attempts = 10
    
    for _ in range(max_attempts):
        date_str = current_date.strftime('%d%m%Y')
        url = f"https://archives.nseindia.com/content/nsccl/fao_participant_oi_{date_str}.csv"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200 and len(response.content) > 100:
                logger.info(f"Successfully fetched NSE Participant OI for {date_str}")
                return response.content.decode('utf-8', errors='ignore'), current_date
        except Exception as e:
            logger.warning(f"Failed attempt for {date_str}: {e}")
        
        # Step back 1 day
        current_date -= datetime.timedelta(days=1)
        
    return None, None

def parse_participant_oi(csv_content):
    """
    Parses the raw CSV content into structured Pandas DataFrame and JSON metrics.
    Line 0: Header description
    Line 1: Columns
    Lines 2-5: Client, DII, FII, Pro
    Line 6: TOTAL
    """
    if not csv_content:
        return None
    
    lines = [line.strip() for line in csv_content.strip().split('\n') if line.strip()]
    
    # Locate header line starting with "Client Type"
    header_idx = -1
    for idx, line in enumerate(lines):
        if line.startswith("Client Type"):
            header_idx = idx
            break
            
    if header_idx == -1:
        logger.error("Could not find 'Client Type' header in CSV")
        return None
        
    csv_data = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(csv_data))
    
    # Strip column spaces
    df.columns = [c.strip() for c in df.columns]
    
    # Clean numeric values
    for col in df.columns:
        if col != 'Client Type':
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
            
    return df

def calculate_participant_metrics(df):
    """
    Calculates detailed Net Positions, Long/Short Ratios, and Institutional Sentiment.
    """
    if df is None or df.empty:
        return None
    
    # Normalize Client Type column
    df['Client Type'] = df['Client Type'].astype(str).str.strip()
    
    metrics = {}
    
    for _, row in df.iterrows():
        client_type = row['Client Type']
        if client_type == 'TOTAL':
            continue
            
        fut_idx_long = float(row.get('Future Index Long', 0))
        fut_idx_short = float(row.get('Future Index Short', 0))
        fut_idx_net = fut_idx_long - fut_idx_short
        
        opt_call_long = float(row.get('Option Index Call Long', 0))
        opt_call_short = float(row.get('Option Index Call Short', 0))
        opt_call_net = opt_call_long - opt_call_short
        
        opt_put_long = float(row.get('Option Index Put Long', 0))
        opt_put_short = float(row.get('Option Index Put Short', 0))
        opt_put_net = opt_put_long - opt_put_short
        
        fut_stk_long = float(row.get('Future Stock Long', 0))
        fut_stk_short = float(row.get('Future Stock Short', 0))
        fut_stk_net = fut_stk_long - fut_stk_short
        
        # Long/Short ratio for Index Futures
        total_fut_idx = fut_idx_long + fut_idx_short
        fut_idx_ls_ratio = (fut_idx_long / total_fut_idx * 100) if total_fut_idx > 0 else 50.0
        
        metrics[client_type] = {
            "future_index_long": fut_idx_long,
            "future_index_short": fut_idx_short,
            "future_index_net": fut_idx_net,
            "future_index_ls_ratio": round(fut_idx_ls_ratio, 2),
            "option_call_long": opt_call_long,
            "option_call_short": opt_call_short,
            "option_call_net": opt_call_net,
            "option_put_long": opt_put_long,
            "option_put_short": opt_put_short,
            "option_put_net": opt_put_net,
            "future_stock_long": fut_stk_long,
            "future_stock_short": fut_stk_short,
            "future_stock_net": fut_stk_net,
            "total_long": float(row.get('Total Long Contracts', 0)),
            "total_short": float(row.get('Total Short Contracts', 0))
        }
        
    return metrics

def analyze_institutional_sentiment(metrics):
    """
    Computes Smart Money Institutional Sentiment Score (0 to 100) & Retail Trap Alert.
    """
    if not metrics:
        return {"score": 50, "verdict": "NEUTRAL", "retail_trap": False, "description": "Insufficient data"}
    
    fii = metrics.get('FII', {})
    client = metrics.get('Client', {})
    pro = metrics.get('Pro', {})
    dii = metrics.get('DII', {})
    
    fii_fut_net = fii.get('future_index_net', 0)
    fii_call_net = fii.get('option_call_net', 0)
    fii_put_net = fii.get('option_put_net', 0)
    fii_ls_ratio = fii.get('future_index_ls_ratio', 50.0)
    
    client_fut_net = client.get('future_index_net', 0)
    client_call_net = client.get('option_call_net', 0)
    
    # Score calculation (base 50)
    score = 50.0
    
    # 1. FII Futures Long/Short weight (+/- 25)
    # 50% ratio is baseline. If 70% long -> +15. If 30% long -> -15
    ratio_delta = (fii_ls_ratio - 50.0) * 0.75
    score += ratio_delta
    
    # 2. FII Call Net weight (+/- 15)
    if fii_call_net > 50000:
        score += 12
    elif fii_call_net > 0:
        score += 6
    elif fii_call_net < -50000:
        score -= 12
    elif fii_call_net < 0:
        score -= 6
        
    # 3. FII Put Net weight (Put buying by FII is Bearish, Put writing is Bullish)
    if fii_put_net > 50000:
        score -= 12  # Long Puts = Bearish
    elif fii_put_net > 0:
        score -= 6
    elif fii_put_net < -50000:
        score += 12  # Short Puts = Bullish writing
    elif fii_put_net < 0:
        score += 6

    # Clamp score
    score = max(5.0, min(95.0, round(score, 1)))
    
    # Sentiment Verdict
    if score >= 75:
        verdict = "STRONG BULLISH"
    elif score >= 60:
        verdict = "MILD BULLISH"
    elif score <= 25:
        verdict = "STRONG BEARISH"
    elif score <= 40:
        verdict = "MILD BEARISH"
    else:
        verdict = "NEUTRAL / MIXED"
        
    # Retail Trap Detection:
    # Retail is heavily bullish (high net long futures / calls) while FII is heavily short
    retail_trap = False
    trap_reason = ""
    
    if client_fut_net > 100000 and fii_fut_net < -50000:
        retail_trap = True
        trap_reason = "Retail clients hold heavy Net Long Index Futures while FIIs are Net Short. High risk of long squeeze."
    elif client_call_net > 150000 and fii_call_net < -50000:
        retail_trap = True
        trap_reason = "Retail clients are buying heavy Calls while Smart Money (FII/Pro) is heavily writing Calls."
    elif client_fut_net < -100000 and fii_fut_net > 50000:
        retail_trap = True
        trap_reason = "Retail clients are panic shorting while FIIs are accumulating Long Futures (Short Trap Alert)."
        
    return {
        "score": score,
        "verdict": verdict,
        "retail_trap": retail_trap,
        "trap_reason": trap_reason,
        "fii_ls_ratio": fii_ls_ratio
    }

def get_full_participant_analysis(date_obj=None):
    """
    Fetches target date and previous trading date to compute Day-over-Day (DoD) changes.
    """
    if date_obj is None:
        date_obj = datetime.date.today()
        
    csv_today, date_today = fetch_participant_oi_csv(date_obj)
    if not csv_today:
        return {"error": "Could not fetch NSE data for requested or previous dates."}
        
    df_today = parse_participant_oi(csv_today)
    metrics_today = calculate_participant_metrics(df_today)
    sentiment = analyze_institutional_sentiment(metrics_today)
    
    # Fetch yesterday's trading day (date_today minus 1 day)
    prev_target = date_today - datetime.timedelta(days=1)
    csv_prev, date_prev = fetch_participant_oi_csv(prev_target)
    
    metrics_prev = None
    if csv_prev:
        df_prev = parse_participant_oi(csv_prev)
        metrics_prev = calculate_participant_metrics(df_prev)
        
    # Calculate DoD changes
    dod_data = {}
    if metrics_today:
        for participant, cur_data in metrics_today.items():
            prev_data = metrics_prev.get(participant, {}) if metrics_prev else {}
            dod_data[participant] = {
                **cur_data,
                "future_index_net_chg": cur_data['future_index_net'] - prev_data.get('future_index_net', cur_data['future_index_net']),
                "option_call_net_chg": cur_data['option_call_net'] - prev_data.get('option_call_net', cur_data['option_call_net']),
                "option_put_net_chg": cur_data['option_put_net'] - prev_data.get('option_put_net', cur_data['option_put_net']),
                "future_stock_net_chg": cur_data['future_stock_net'] - prev_data.get('future_stock_net', cur_data['future_stock_net'])
            }
            
    return {
        "date_fetched": date_today.strftime('%Y-%m-%d'),
        "prev_date_fetched": date_prev.strftime('%Y-%m-%d') if date_prev else None,
        "metrics": dod_data,
        "sentiment": sentiment
    }

if __name__ == "__main__":
    data = get_full_participant_analysis()
    print("Fetched Date:", data.get('date_fetched'))
    print("Sentiment:", data.get('sentiment'))
    if 'metrics' in data and 'FII' in data['metrics']:
        print("FII Metrics:", data['metrics']['FII'])
