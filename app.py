from flask import Flask, render_template, jsonify, request
import datetime
import logging

from nse_fetcher import get_full_participant_analysis
from volume_profile import get_volume_profile_analysis
from option_analyzer import analyze_option_concentration

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fii-dii-oi', methods=['GET'])
def api_fii_dii_oi():
    """
    Participant-wise Open Interest Endpoint.
    Accepts optional ?date=YYYY-MM-DD
    """
    req_date_str = request.args.get('date', None)
    target_date = None
    
    if req_date_str:
        try:
            target_date = datetime.datetime.strptime(req_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    else:
        target_date = datetime.date.today()
        
    data = get_full_participant_analysis(target_date)
    return jsonify(data)

@app.route('/api/volume-profile', methods=['GET'])
def api_volume_profile():
    """
    Volume Profile, POC, VAH, VAL, VWAP Endpoint.
    Accepts ?symbol=NIFTY&days=5&bins=40
    """
    symbol = request.args.get('symbol', 'NIFTY').upper()
    try:
        days = int(request.args.get('days', 5))
        bins = int(request.args.get('bins', 40))
    except ValueError:
        days = 5
        bins = 40
        
    vp_data = get_volume_profile_analysis(symbol, days=days, num_bins=bins)
    return jsonify(vp_data)

@app.route('/api/option-chain', methods=['GET'])
def api_option_chain():
    """
    Big Money Option Concentration & Smart Seller Radar Endpoint.
    Accepts ?symbol=NIFTY
    """
    symbol = request.args.get('symbol', 'NIFTY').upper()
    
    # We can fetch spot price from volume profile engine to sync spot prices
    vp_data = get_volume_profile_analysis(symbol, days=1, num_bins=20)
    spot_price = vp_data['current_price'] if vp_data else None
    
    opt_data = analyze_option_concentration(symbol, spot_price=spot_price)
    return jsonify(opt_data)

@app.route('/api/summary-cards', methods=['GET'])
def api_summary_cards():
    """
    Aggregated summary cards for instant header metrics.
    """
    symbol = request.args.get('symbol', 'NIFTY').upper()
    
    # Participant data
    participant_data = get_full_participant_analysis()
    
    # Volume Profile data
    vp_data = get_volume_profile_analysis(symbol, days=5, num_bins=40)
    
    # Option data
    opt_data = analyze_option_concentration(symbol, spot_price=vp_data['current_price'] if vp_data else None)
    
    fii_metrics = participant_data.get('metrics', {}).get('FII', {})
    sentiment = participant_data.get('sentiment', {})
    
    return jsonify({
        "symbol": symbol,
        "date": participant_data.get('date_fetched'),
        "fii_ls_ratio": fii_metrics.get('future_index_ls_ratio', 0),
        "fii_fut_net": fii_metrics.get('future_index_net', 0),
        "fii_fut_net_chg": fii_metrics.get('future_index_net_chg', 0),
        "sentiment_verdict": sentiment.get('verdict', 'NEUTRAL'),
        "sentiment_score": sentiment.get('score', 50),
        "retail_trap": sentiment.get('retail_trap', False),
        "trap_reason": sentiment.get('trap_reason', ''),
        "poc": vp_data.get('poc') if vp_data else 0,
        "vah": vp_data.get('vah') if vp_data else 0,
        "val": vp_data.get('val') if vp_data else 0,
        "vwap": vp_data.get('vwap') if vp_data else 0,
        "vp_signal": vp_data.get('signal') if vp_data else '',
        "max_pain": opt_data.get('max_pain') if opt_data else 0,
        "pcr": opt_data.get('pcr') if opt_data else 1.0,
        "pcr_bias": opt_data.get('pcr_bias') if opt_data else ''
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
