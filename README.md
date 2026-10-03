# Institutional Smart Money & FII/DII Flow Tracker 🚀

An institutional-grade trading terminal dashboard tool built to track Big Institutions (FIIs, DIIs, Proprietary Desks) footprint instead of lagging retail indicators.

---

## 🌟 Core Modules & Technical Features

### 1. **MODULE 1: Daily FII / DII Participant-Wise OI Analyzer (EOD)**
- **Data Source**: Downloads official NSE India archive participant-wise open interest CSV (`https://archives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv`).
- **Participant Categorization**: FII, DII, Pro (Proprietary Desks), Client (Retail).
- **Net Position Calculations**:
  - Index Futures Net (Long vs Short + Long/Short Ratio).
  - Index Calls Net (Long vs Short).
  - Index Puts Net (Long vs Short).
  - Stock Futures Net.
  - Day-over-Day (DoD) contract changes.
- **Smart Money Institutional Sentiment Meter**:
  - Score (0 to 100) evaluating FII long/short ratios and option positioning.
  - Categorization: `STRONG BULLISH`, `MILD BULLISH`, `NEUTRAL`, `MILD BEARISH`, `STRONG BEARISH`.
- **Retail Trap Alert Engine**:
  - Automatically flags warnings when Retail (Clients) hold heavy Net Long futures/calls while FIIs are Net Short (Long Squeeze Risk).

### 2. **MODULE 2: Volume Profile & POC (Point of Control) Engine**
- **Point of Control (POC)**: Highlights exact price level with maximum volume traded (Institutional Magnet).
- **Value Area High & Low (VAH & VAL)**: Identifies 70% volume range executed during the session.
- **VWAP & Anchored VWAP**: Session VWAP and week/anchor point calculations.
- **Institutional Signals**:
  - `INSTITUTIONAL MARKUP (BULLISH)`: Price > VAH & > VWAP.
  - `INSTITUTIONAL MARKDOWN (BEARISH)`: Price < VAL & < VWAP.
  - `RE-TESTING POC`: Price near POC (High probability reversal/magnet zone).

### 3. **MODULE 3: Big Money Option Concentration (Smart Seller Radar)**
- **Max Pain Calculation**: Strikes where option buyers suffer maximum financial loss.
- **Smart Seller Radar**: Top Call Wall (Institutional Resistance) & Put Wall (Institutional Support).
- **Unwinding Alerts**: Identifies Call Short Covering and Put Unwinding in real-time.

### 4. **User Interface (Modern Terminal Dark Theme)**
- Responsive financial dark terminal layout built with Tailwind CSS, Chart.js, Lucide Icons, and SVG Gauge meters.

---

## 🛠️ Project Architecture

```
smart_money_tracker/
├── app.py                  # Flask Web Application & REST API
├── nse_fetcher.py          # NSE CSV downloader, parser & sentiment engine
├── volume_profile.py       # Volume Profile, POC, VAH, VAL, VWAP engine
├── option_analyzer.py      # Max Pain, Call/Put Walls, & Smart Seller Radar
├── requirements.txt        # Python dependencies
├── vercel.json             # Vercel serverless deployment config
├── templates/
│   └── index.html          # Dark Theme Institutional Terminal UI
└── static/
    ├── css/
    │   └── style.css       # Custom Bloomberg/TradingView terminal styling
    └── js/
        └── app.js          # Interactive frontend logic & Chart.js rendering
```

---

## 🚀 How to Run Locally

1. **Navigate to project directory**:
   ```bash
   cd C:\Users\Lenovo\.gemini\antigravity\scratch\smart_money_tracker
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Flask Application**:
   ```bash
   python app.py
   ```

4. **Open in Browser**:
   Open [http://localhost:5000](http://localhost:5000) in your web browser.

---

## ⚡ Deployment Ready

- **Vercel**: Includes `vercel.json` for zero-configuration serverless deployment.
- **Render / Railway / Heroku**: Ready out of the box with `gunicorn`.
