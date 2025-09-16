# algotrader/settings.py
# This file contains all the configuration and tuning parameters for the trading bot.

# --- 1. API Credentials ---
# IMPORTANT: Fill in your actual API key and secret. Do NOT commit this file to version control.
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
# This token needs to be generated daily using generate_access_token.py and pasted here.
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"


# --- 2. Core Trading Parameters ---
TRADE_QUANTITY = 1          # The number of lots to trade for each position.
PRODUCT_TYPE = "MIS"        # Product type for orders (e.g., "MIS" for intraday, "NRML" for overnight).
ORDER_TYPE = "MARKET"       # Order type ("MARKET" or "LIMIT")
EXCHANGE = "NFO"            # The exchange to trade on.
INDEX = "NIFTY"             # The underlying index.
NIFTY50_INSTRUMENT_TOKEN = 256265 # Instrument token for Nifty 50 Index for fetching its spot price.


# --- 3. Risk Management ---
STOP_LOSS_PERCENT = 0.10    # The initial hard stop loss percentage (e.g., 0.10 for 10%).
ENABLE_TRAILING_SL = True   # A True/False switch to enable or disable the Supertrend-based trailing stop loss.


# --- 4. Strategy & Signal Tuning ---
# How many points away from the ATM strike to select the option.
# ATM strike is rounded to the nearest 500 or 1000.
STRIKE_SELECTION_OFFSET = 500

# Settings for the first, faster Supertrend
SUPERTREND_FAST_PERIOD = 13
SUPERTREND_FAST_MULTIPLIER = 2

# Settings for the second, slower Supertrend
SUPERTREND_SLOW_PERIOD = 14
SUPERTREND_SLOW_MULTIPLIER = 4

# Settings for the Choppiness Index
CHOP_PERIOD = 14
CHOP_THRESHOLD = 50


# --- 5. OI Alert Tuning ---
ENABLE_OI_ALERTS = True         # A True/False switch to enable or disable OI alerts.
OI_ALERT_LOOKBACK_MINUTES = 15  # How far back to look for OI changes (in minutes).
OI_ALERT_THRESHOLD_PERCENT = 0.25 # The percentage change in OI that triggers an alert (e.g., 0.25 for 25%).


# --- 6. Bot Settings ---
# The interval in seconds to run the main trading loop. 300 seconds = 5 minutes.
BOT_CYCLE_SECONDS = 300
LOG_LEVEL = "INFO"          # Logging level: "DEBUG", "INFO", "WARNING", "ERROR".
TIMEFRAME = "5minute"       # The candle timeframe to use for the strategy.
