# Nifty 50 AlgoTrading Bot

This is an automated trading bot that trades Nifty 50 monthly option contracts based on a combination of technical indicators. It is designed to work with the Zerodha Kite Connect API.

**DISCLAIMER: This is an educational project and a trading tool. Trading in the stock market involves significant risk. The author and any contributors are not responsible for any financial losses you may incur. Use this bot at your own risk after thorough testing.**

## Features

-   **Strategy-based Trading:** Trades on a combination of Supertrend (13,2), Supertrend (14,4), VWAP, and the Choppiness Index.
-   **Automated Instrument Selection:** Automatically selects deep In-The-Money (ITM) Nifty 50 option contracts for the current monthly expiry.
-   **Combination Trades:** Implements a "flip" strategy, trading a combination of Long CE + Short PE for bullish signals and Short CE + Long PE for bearish signals.
-   **Risk Management:** Includes a hard Stop Loss (SL) and a trailing SL based on the Supertrend indicator.
-   **Real-time Dashboard:** A web-based dashboard to monitor trades, P&L, available margin, and receive alerts.
-   **OI Alerts:** Provides alerts for significant changes in Open Interest that may go against your position.
-   **Highly Configurable:** Most trading parameters, strategy settings, and risk management rules can be easily configured in the `settings.py` file.

## How it Works

The bot runs in a loop every 5 minutes during market hours. For both a Call (CE) and a Put (PE) option leg, it does the following:
1.  Fetches the latest 5-minute candle data.
2.  Calculates all technical indicators.
3.  Checks for a Bullish or Bearish signal based on the rules in `strategy.py`.
4.  If in a position, it checks for a "flip" signal to reverse the trade.
5.  If not in a position, it checks for an entry signal.
6.  It manages a trailing stop loss for all open positions.

## Setup and Usage

Follow these steps to set up and run the bot.

### Step 1: Installation

First, ensure you have Python 3 installed. Then, navigate to the `algotrader` directory and install the required libraries:

```bash
pip install -r requirements.txt
```

### Step 2: Create a Zerodha Kite App

1.  Go to the [Kite Connect Developer portal](https://developers.kite.trade/).
2.  Create a new app. You will receive an `api_key` and `api_secret`.
3.  Set the "Redirect URL" for your app to `http://127.0.0.1:5000/` (or any other local URL). This is important for the authentication step.

### Step 3: Configure the Bot

Open the `algotrader/settings.py` file and fill in your details. This is the main configuration file for the bot.

-   **`API_KEY`**: Your Zerodha app's API key.
-   **`API_SECRET`**: Your Zerodha app's API secret.
-   **`ACCESS_TOKEN`**: Leave this as `"YOUR_ACCESS_TOKEN"` for now.
-   **`TRADE_QUANTITY`**: Set the number of lots you want to trade.
-   Review and adjust other parameters like `STOP_LOSS_PERCENT`, `STRIKE_SELECTION_OFFSET`, and indicator settings as you see fit.

### Step 4: Generate Your Daily Access Token

Zerodha requires you to log in manually once per day to generate an `access_token`. A helper script is provided to make this easy.

1.  Run the script from the `algotrader` directory:
    ```bash
    python generate_access_token.py
    ```
2.  The script will print a URL. Copy this URL and paste it into your web browser.
3.  Log in to your Zerodha account.
4.  After logging in, you will be redirected to the URL you set in Step 2. The URL in your browser's address bar will now contain a `request_token`. It will look something like this: `http://127.0.0.1:5000/?request_token=YOUR_REQUEST_TOKEN&action=login&status=success`.
5.  Copy the long `request_token` value from the URL.
6.  Paste it back into the terminal where the script is waiting.
7.  The script will then generate and print your `access_token`.
8.  Copy this `access_token` and paste it into the `settings.py` file for the `ACCESS_TOKEN` variable.

You must repeat this process every morning before you start the bot.

### Step 5: Run the Bot and Dashboard

You need to run the bot and the dashboard in two separate terminal windows.

**Terminal 1: Run the Main Bot**

Navigate to the `algotrader` directory and run:

```bash
python main.py
```

You will see log messages indicating that the bot has started and is waiting for the market to open or for its next cycle.

**Terminal 2: Run the Dashboard**

Navigate to the `algotrader` directory and run:

```bash
python dashboard.py
```

Now, open your web browser and go to `http://127.0.0.1:5000`. You will see the dashboard, which will auto-refresh every 60 seconds to show the latest data.
