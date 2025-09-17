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
3.  Set the "Redirect URL" for your app to `http://127.0.0.1:5000/callback`. **Note:** Ensure the URL ends with `/callback`.

### Step 3: Configure the Bot

Open the `algotrader/settings.py` file and fill in your details.

-   **`API_KEY`**: Your Zerodha app's API key.
-   **`API_SECRET`**: Your Zerodha app's API secret.
-   **`ACCESS_TOKEN`**: You can leave this empty. The dashboard will populate it automatically.
-   Review and adjust all other trading and strategy parameters to your preference.

### Step 4: Run the Bot and Dashboard

You need to run the bot and the dashboard in two separate terminal windows.

**Terminal 1: Run the Dashboard FIRST**

It is recommended to start the dashboard first to handle the login process. Navigate to the `algotrader` directory and run:

```bash
python dashboard.py
```

**Terminal 2: Run the Main Bot**

Navigate to the `algotrader` directory and run:

```bash
python main.py
```

**Step 5: Login and Start Trading**

1.  Open your web browser and go to `http://127.0.0.1:5000`.
2.  You will see a "Login with Zerodha" button. Click it.
3.  You will be redirected to the Zerodha login page. Log in with your credentials.
4.  After a successful login, you will be redirected back to the dashboard. The dashboard will now show your account details, and the bot running in the other terminal will be authenticated and ready to trade.
5.  The bot will start executing trades automatically on its next cycle when market conditions are met.
