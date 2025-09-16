# algotrader/dashboard.py

import json
import logging
from flask import Flask, render_template
from datetime import datetime
import settings
from zerodha_client import ZerodhaClient

app = Flask(__name__)

# --- Helper Functions ---
def read_json_file(filepath, default_data=[]):
    """Safely reads a JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

def read_last_line(filepath):
    """Safely reads the last line of a file."""
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            return lines[-1].strip() if lines else None
    except FileNotFoundError:
        return None

# --- Flask Route ---
@app.route('/')
def home():
    """Main dashboard page."""
    # Initialize client to get live data
    z_client = ZerodhaClient()

    # Get live data
    margins = None
    positions = None
    if z_client.is_authenticated():
        try:
            margins = z_client.kite.margins()
        except Exception as e:
            logging.error(f"Could not fetch margins: {e}")
        try:
            positions = z_client.get_positions()['net']
        except Exception as e:
            logging.error(f"Could not fetch positions: {e}")

    # Get historical/logged data
    trades = read_json_file('algotrader/trades.json')
    last_alert = read_last_line('algotrader/alerts.log')

    # Calculate P&L for display
    total_pl = 0
    if positions:
        for pos in positions:
            total_pl += pos.get('pnl', 0)

    # Prepare data for template
    context = {
        "margins": margins['equity']['available']['cash'] if margins else 'N/A',
        "total_pl": total_pl,
        "positions": [p for p in positions if p['quantity'] != 0] if positions else [],
        "trades": trades,
        "last_alert": last_alert,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    return render_template('index.html', **context)

if __name__ == '__main__':
    # Note: Using debug=True is not recommended for production
    app.run(debug=True, host='0.0.0.0', port=5000)
