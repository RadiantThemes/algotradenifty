# algotrader/main.py

import logging
import time
import schedule
import json
from datetime import datetime, timedelta

import settings
from zerodha_client import ZerodhaClient
from strategy import Strategy

# --- Global State Management ---
# We manage the state for each leg (CE and PE) independently.
leg_states = {
    "CE": {"state": "FLAT", "sl_order_id": None, "entry_price": 0, "sl_trigger_price": 0, "instrument_token": None, "tradingsymbol": None},
    "PE": {"state": "FLAT", "sl_order_id": None, "entry_price": 0, "sl_trigger_price": 0, "instrument_token": None, "tradingsymbol": None}
}

def setup_logging():
    """Configures the logging for the application."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("Logging configured.")

def log_trade(symbol, transaction_type, price, quantity):
    """Appends a trade record to the trades.json file."""
    record = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "symbol": symbol,
        "type": transaction_type,
        "price": price,
        "quantity": quantity
    }
    try:
        with open('algotrader/trades.json', 'r+') as f:
            try:
                trades = json.load(f)
            except json.JSONDecodeError:
                trades = []
            trades.append(record)
            f.seek(0)
            f.truncate()
            json.dump(trades, f, indent=4)
    except FileNotFoundError:
        with open('algotrader/trades.json', 'w') as f:
            json.dump([record], f, indent=4)
    except Exception as e:
        logging.error(f"Failed to log trade: {e}")

def log_alert(alert_message):
    """Writes an alert message to the alerts.log file."""
    try:
        with open('algotrader/alerts.log', 'w') as f: # Overwrite with the latest alert
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {alert_message}\n")
    except Exception as e:
        logging.error(f"Failed to log alert: {e}")

def run_bot_cycle():
    """
    Executes a single cycle of the trading bot logic.
    This function is scheduled to run at regular intervals.
    """
    logging.info("="*50)
    logging.info("Starting new bot cycle...")

    try:
        # 1. Initialize clients
        z_client = ZerodhaClient()
        strategy = Strategy(settings)

        # 2. Authenticate
        if not z_client.is_authenticated():
            logging.error("Authentication failed. Exiting cycle.")
            return

        # 3. Select instruments for the day (if not already selected)
        if leg_states["CE"]["tradingsymbol"] is None or leg_states["PE"]["tradingsymbol"] is None:
            logging.info("Finding contracts for today's session...")
            ce_symbol, pe_symbol = z_client.find_options_for_trading()
            if not ce_symbol or not pe_symbol:
                logging.error("Could not find contracts for trading. Exiting cycle.")
                return

            leg_states["CE"]["tradingsymbol"] = ce_symbol
            leg_states["PE"]["tradingsymbol"] = pe_symbol

            leg_states["CE"]["instrument_token"] = z_client.get_instrument_token(ce_symbol)
            leg_states["PE"]["instrument_token"] = z_client.get_instrument_token(pe_symbol)

            logging.info(f"Today's contracts: CE={ce_symbol}, PE={pe_symbol}")

        # 4. Loop through legs and implement state machine
        for leg in ["CE", "PE"]:
            leg_info = leg_states[leg]
            logging.info(f"Processing leg: {leg}, Current State: {leg_info['state']}")

            if not leg_info["instrument_token"]:
                logging.warning(f"No instrument token for {leg}, skipping.")
                continue

            # 5. Fetch data and calculate indicators
            to_date = datetime.now()
            from_date = to_date - timedelta(days=5) # Fetch 5 days of data for indicators

            hist_data = z_client.get_historical_data(
                instrument_token=leg_info["instrument_token"],
                from_date=from_date,
                to_date=to_date,
                interval=settings.TIMEFRAME
            )

            if hist_data.empty:
                logging.warning(f"Could not fetch historical data for {leg_info['tradingsymbol']}. Skipping leg.")
                continue

            df_with_indicators = strategy.calculate_indicators(hist_data)
            signal = strategy.check_signal(df_with_indicators) # 1 for Bullish, -1 for Bearish

            # 6. Execute State Machine Logic
            if leg_info['state'] == 'FLAT':
                if (leg == "CE" and signal == 1) or (leg == "PE" and signal == -1): # Bullish Entry
                    logging.info(f"BULLISH entry signal for {leg_info['tradingsymbol']}.")
                    entry_order_id = z_client.place_order(
                        tradingsymbol=leg_info['tradingsymbol'],
                        transaction_type='BUY',
                        quantity=settings.TRADE_QUANTITY
                    )
                    if entry_order_id:
                        time.sleep(2) # Wait for order to execute
                        price = z_client.get_order_average_price(entry_order_id)
                        if price > 0:
                            leg_info['entry_price'] = price
                            sl_trigger = price * (1 - settings.STOP_LOSS_PERCENT)
                            sl_order_id = z_client.place_sl_order(
                                tradingsymbol=leg_info['tradingsymbol'],
                                transaction_type='SELL',
                                quantity=settings.TRADE_QUANTITY,
                                trigger_price=sl_trigger
                            )
                            if sl_order_id:
                                leg_info['state'] = 'LONG'
                                leg_info['sl_order_id'] = sl_order_id
                                leg_info['sl_trigger_price'] = sl_trigger
                                logging.info(f"Moved {leg} to LONG state at {price} with SL order {sl_order_id} and trigger {sl_trigger}")
                                log_trade(leg_info['tradingsymbol'], 'BUY', price, settings.TRADE_QUANTITY)

                elif (leg == "CE" and signal == -1) or (leg == "PE" and signal == 1): # Bearish Entry
                    logging.info(f"BEARISH entry signal for {leg_info['tradingsymbol']}.")
                    entry_order_id = z_client.place_order(
                        tradingsymbol=leg_info['tradingsymbol'],
                        transaction_type='SELL',
                        quantity=settings.TRADE_QUANTITY
                    )
                    if entry_order_id:
                        time.sleep(2)
                        price = z_client.get_order_average_price(entry_order_id)
                        if price > 0:
                            leg_info['entry_price'] = price
                            sl_trigger = price * (1 + settings.STOP_LOSS_PERCENT)
                            sl_order_id = z_client.place_sl_order(
                                tradingsymbol=leg_info['tradingsymbol'],
                                transaction_type='BUY',
                                quantity=settings.TRADE_QUANTITY,
                                trigger_price=sl_trigger
                            )
                            if sl_order_id:
                                leg_info['state'] = 'SHORT'
                                leg_info['sl_order_id'] = sl_order_id
                                leg_info['sl_trigger_price'] = sl_trigger
                                logging.info(f"Moved {leg} to SHORT state at {price} with SL order {sl_order_id} and trigger {sl_trigger}")
                                log_trade(leg_info['tradingsymbol'], 'SELL', price, settings.TRADE_QUANTITY)

            elif leg_info['state'] == 'LONG':
                if (leg == "CE" and signal == -1) or (leg == "PE" and signal == 1): # Bearish Flip Signal
                    logging.info(f"BEARISH flip signal for {leg_info['tradingsymbol']}. Flipping from LONG to SHORT.")
                    # 1. Cancel existing SL order
                    z_client.cancel_order(leg_info['sl_order_id'])
                    # 2. Close existing LONG position
                    close_order_id = z_client.place_order(leg_info['tradingsymbol'], 'SELL', settings.TRADE_QUANTITY)
                    if close_order_id:
                        log_trade(leg_info['tradingsymbol'], 'SELL', leg_info['entry_price'], settings.TRADE_QUANTITY) # Log close
                    time.sleep(1)
                    # 3. Open new SHORT position
                    flip_order_id = z_client.place_order(leg_info['tradingsymbol'], 'SELL', settings.TRADE_QUANTITY)
                    if flip_order_id:
                        time.sleep(2)
                        price = z_client.get_order_average_price(flip_order_id)
                        if price > 0:
                            leg_info['entry_price'] = price
                            sl_trigger = price * (1 + settings.STOP_LOSS_PERCENT)
                            sl_order_id = z_client.place_sl_order(leg_info['tradingsymbol'], 'BUY', settings.TRADE_QUANTITY, sl_trigger)
                            if sl_order_id:
                                leg_info['state'] = 'SHORT'
                                leg_info['sl_order_id'] = sl_order_id
                                leg_info['sl_trigger_price'] = sl_trigger
                                logging.info(f"Flipped {leg} to SHORT state at {price} with SL order {sl_order_id}")
                                log_trade(leg_info['tradingsymbol'], 'SELL', price, settings.TRADE_QUANTITY) # Log open
                elif settings.ENABLE_TRAILING_SL:
                    # Trailing SL Logic
                    tsl_price = strategy.get_trailing_sl(df_with_indicators, 'LONG')
                    if tsl_price > leg_info['sl_trigger_price']:
                        logging.info(f"Trailing SL for {leg}. New trigger: {tsl_price}")
                        z_client.modify_sl_order(leg_info['sl_order_id'], tsl_price)
                        leg_info['sl_trigger_price'] = tsl_price

            elif leg_info['state'] == 'SHORT':
                if (leg == "CE" and signal == 1) or (leg == "PE" and signal == -1): # Bullish Flip Signal
                    logging.info(f"BULLISH flip signal for {leg_info['tradingsymbol']}. Flipping from SHORT to LONG.")
                    # 1. Cancel existing SL order
                    z_client.cancel_order(leg_info['sl_order_id'])
                    # 2. Close existing SHORT position
                    close_order_id = z_client.place_order(leg_info['tradingsymbol'], 'BUY', settings.TRADE_QUANTITY)
                    if close_order_id:
                        log_trade(leg_info['tradingsymbol'], 'BUY', leg_info['entry_price'], settings.TRADE_QUANTITY) # Log close
                    time.sleep(1)
                    # 3. Open new LONG position
                    flip_order_id = z_client.place_order(leg_info['tradingsymbol'], 'BUY', settings.TRADE_QUANTITY)
                    if flip_order_id:
                        time.sleep(2)
                        price = z_client.get_order_average_price(flip_order_id)
                        if price > 0:
                            leg_info['entry_price'] = price
                            sl_trigger = price * (1 - settings.STOP_LOSS_PERCENT)
                            sl_order_id = z_client.place_sl_order(leg_info['tradingsymbol'], 'SELL', settings.TRADE_QUANTITY, sl_trigger)
                            if sl_order_id:
                                leg_info['state'] = 'LONG'
                                leg_info['sl_order_id'] = sl_order_id
                                leg_info['sl_trigger_price'] = sl_trigger
                                logging.info(f"Flipped {leg} to LONG state at {price} with SL order {sl_order_id}")
                                log_trade(leg_info['tradingsymbol'], 'BUY', price, settings.TRADE_QUANTITY) # Log open
                elif settings.ENABLE_TRAILING_SL:
                    # Trailing SL Logic
                    tsl_price = strategy.get_trailing_sl(df_with_indicators, 'SHORT')
                    if tsl_price < leg_info['sl_trigger_price']:
                        logging.info(f"Trailing SL for {leg}. New trigger: {tsl_price}")
                        z_client.modify_sl_order(leg_info['sl_order_id'], tsl_price)
                        leg_info['sl_trigger_price'] = tsl_price

            # 7. Check for OI alerts
            oi_alert = strategy.check_oi_alert(df_with_indicators)
            if oi_alert:
                logging.warning(f"OI ALERT for {leg_info['tradingsymbol']}: {oi_alert}")
                log_alert(f"{leg_info['tradingsymbol']}: {oi_alert}")

    except Exception as e:
        logging.exception(f"An unexpected error occurred in the bot cycle: {e}")

    logging.info("Bot cycle finished.")
    logging.info("="*50 + "\n")


def main():
    """
    Main function to set up and run the trading bot.
    """
    setup_logging()
    logging.info("AlgoTrading Bot - Started")
    logging.info("DISCLAIMER: This is a trading bot. Use at your own risk.")

    # Schedule the main logic
    schedule.every(settings.BOT_CYCLE_SECONDS).seconds.do(run_bot_cycle)

    logging.info(f"Bot scheduled to run every {settings.BOT_CYCLE_SECONDS} seconds.")

    # Main loop to run the scheduler
    while True:
        # Check if within trading hours
        now = datetime.now().time()
        market_open = datetime.strptime("09:15", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()

        if market_open <= now < market_close:
            schedule.run_pending()
        else:
            logging.info("Outside of market hours. Bot is sleeping.")
            # You might want to cancel open SL orders here if any are left

        time.sleep(1)


if __name__ == "__main__":
    main()
