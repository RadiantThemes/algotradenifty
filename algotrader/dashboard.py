# algotrader/dashboard.py

import json
import logging
import math
from flask import Flask, render_template, redirect, request, url_for
from datetime import datetime
import settings
from zerodha_client import ZerodhaClient

app = Flask(__name__)

# --- Pagination Helper ---
class Pagination:
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(math.ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (self.page - left_current - 1 < num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

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

def save_access_token(token):
    """Safely finds and replaces the ACCESS_TOKEN line in settings.py."""
    try:
        with open('algotrader/settings.py', 'r') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.strip().startswith('ACCESS_TOKEN'):
                new_lines.append(f'ACCESS_TOKEN = "{token}"\n')
            else:
                new_lines.append(line)

        with open('algotrader/settings.py', 'w') as f:
            f.writelines(new_lines)
        logging.info("Successfully saved new access token to settings.py")
        return True
    except Exception as e:
        logging.error(f"Failed to save access token to settings.py: {e}")
        return False

# --- Flask Routes ---
@app.route('/')
def home():
    """Main dashboard page."""
    z_client = ZerodhaClient()
    is_auth = z_client.is_authenticated()

    margins, positions, total_pl = None, None, 0
    if is_auth:
        try:
            margins = z_client.kite.margins()
            positions_data = z_client.get_positions()
            if positions_data and positions_data.get('net'):
                positions = [p for p in positions_data['net'] if p['quantity'] != 0]
                for pos in positions:
                    total_pl += pos.get('pnl', 0)
        except Exception as e:
            logging.error(f"Could not fetch live data: {e}")

    trades = read_json_file('algotrader/trades.json')
    last_alert = read_last_line('algotrader/alerts.log')

    context = {
        "is_authenticated": is_auth,
        "margins": margins['equity']['available']['cash'] if margins else 'N/A',
        "total_pl": total_pl,
        "positions": positions or [],
        "trades": trades,
        "last_alert": last_alert,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    return render_template('index.html', **context)

@app.route('/login')
def login():
    """Redirects the user to the Zerodha login page."""
    try:
        z_client = ZerodhaClient()
        login_url = z_client.kite.login_url()
        logging.info(f"Redirecting user to Zerodha login: {login_url}")
        return redirect(login_url)
    except Exception as e:
        logging.error(f"Could not get login URL: {e}")
        return "Error: Could not generate login URL. Check API Key in settings.", 500

@app.route('/callback')
def callback():
    """Handles the callback from Zerodha after successful login."""
    request_token = request.args.get('request_token')
    if not request_token:
        return "Error: Could not get request_token from Zerodha.", 400

    try:
        z_client = ZerodhaClient()
        session = z_client.kite.generate_session(request_token, api_secret=settings.API_SECRET)
        access_token = session.get("access_token")

        if not access_token:
            logging.error("Failed to generate access token from request_token.")
            return "Error: Could not generate access token.", 500

        if save_access_token(access_token):
            logging.info("Access token generated and saved successfully.")
            return redirect(url_for('home'))
        else:
            return "Error: Access token generated but could not be saved to settings.py.", 500

    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        return f"An error occurred during authentication: {e}", 500

@app.route('/history')
def history():
    """Displays the full, paginated trade history."""
    page = request.args.get('page', 1, type=int)
    per_page = 20 # Trades per page

    all_trades = read_json_file('algotrader/trades.json')
    all_trades.reverse() # Show newest first

    total_trades = len(all_trades)
    start = (page - 1) * per_page
    end = start + per_page
    trades_on_page = all_trades[start:end]

    pagination = Pagination(page, per_page, total_trades)

    return render_template('history.html', trades=trades_on_page, pagination=pagination)

@app.route('/square-off', methods=['POST'])
def square_off():
    """Squares off all open positions and cancels all pending orders."""
    logging.warning("SQUARE OFF TRIGGERED FROM DASHBOARD")
    z_client = ZerodhaClient()
    if not z_client.is_authenticated():
        return "Error: Not authenticated.", 401

    try:
        # Cancel all open SL orders first
        open_orders = z_client.get_orders()
        if open_orders:
            for order in open_orders:
                if order['status'] == 'TRIGGER PENDING':
                    logging.info(f"Cancelling pending SL order: {order['order_id']}")
                    z_client.cancel_order(order['order_id'])

        # Square off all net positions
        positions = z_client.get_positions().get('net', [])
        if positions:
            for pos in positions:
                if pos['quantity'] != 0:
                    symbol = pos['tradingsymbol']
                    qty = abs(pos['quantity'])
                    # If quantity is positive (long), we sell. If negative (short), we buy.
                    transaction_type = 'SELL' if pos['quantity'] > 0 else 'BUY'
                    logging.info(f"Squaring off {symbol}. Placing {transaction_type} order for {qty} quantity.")
                    z_client.place_order(symbol, transaction_type, qty)

        logging.warning("Square off process completed.")
    except Exception as e:
        logging.error(f"An error occurred during square off: {e}")
        return "An error occurred during square off.", 500

    return redirect(url_for('home'))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, host='0.0.0.0', port=5000)
