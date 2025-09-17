# algotrader/zerodha_client.py

import logging
from kiteconnect import KiteConnect
import settings
import datetime
import pandas as pd

class ZerodhaClient:
    """
    A client to interact with the Zerodha Kite Connect API.
    Handles authentication and provides methods for API calls.
    """
    def __init__(self):
        """
        Initializes the ZerodhaClient and authenticates with the Kite API.
        """
        self.instruments = None
        try:
            self.kite = KiteConnect(api_key=settings.API_KEY)
            self.kite.set_access_token(settings.ACCESS_TOKEN)
            logging.info("KiteConnect client initialized.")
        except Exception as e:
            logging.error(f"Error initializing KiteConnect client: {e}")
            self.kite = None

    def is_authenticated(self):
        if not self.kite or not self.kite.access_token:
            return False
        try:
            profile = self.kite.profile()
            if profile and profile.get("user_id"):
                logging.info(f"Authentication successful for user: {profile['user_id']}")
                return True
            return False
        except Exception as e:
            logging.error(f"Authentication check failed: {e}")
            return False

    def get_instruments(self, exchange=settings.EXCHANGE):
        """
        Fetches and caches the list of instruments for a given exchange.
        """
        if self.instruments is None:
            try:
                logging.info(f"Fetching instruments for exchange: {exchange}")
                self.instruments = self.kite.instruments(exchange)
                logging.info(f"Successfully fetched {len(self.instruments)} instruments.")
            except Exception as e:
                logging.error(f"Error fetching instruments: {e}")
                return []
        return self.instruments

    def get_monthly_expiry(self, index=settings.INDEX):
        """
        Finds the nearest monthly expiry date for the given index (e.g., 'NIFTY').
        """
        self.get_instruments()
        today = datetime.date.today()

        df = pd.DataFrame(self.instruments)
        df = df[(df['name'] == index) & (df['segment'] == settings.EXCHANGE)]

        # A simple heuristic to find monthly expiries: they are usually the last thursday,
        # so the gap between a monthly and the next weekly is large.
        expiries = sorted([pd.to_datetime(d).date() for d in df['expiry'].unique()])

        monthly_expiries = []
        if not expiries:
            return None

        last_expiry = expiries[0]
        for i in range(1, len(expiries)):
            if (expiries[i] - last_expiry).days > 7:
                 monthly_expiries.append(last_expiry)
            last_expiry = expiries[i]
        monthly_expiries.append(last_expiry)

        # Find the next upcoming monthly expiry from today
        for expiry_date in sorted(list(set(monthly_expiries))):
            if expiry_date >= today:
                logging.info(f"Found next monthly expiry for {index}: {expiry_date}")
                return expiry_date

        logging.warning("Could not find a future monthly expiry date.")
        return None

    def find_options_for_trading(self):
        """
        Finds the Call and Put option contracts based on the new logic.
        1. Round spot to nearest 500/1000.
        2. Offset by STRIKE_SELECTION_OFFSET.
        """
        expiry_date = self.get_monthly_expiry()
        if not expiry_date:
            return None, None

        # Get live quote for the index to find the spot price
        try:
            quote = self.kite.quote(settings.NIFTY50_INSTRUMENT_TOKEN)
            spot_price = quote[str(settings.NIFTY50_INSTRUMENT_TOKEN)]['last_price']
        except Exception as e:
            logging.error(f"Error fetching spot price for {settings.INDEX}: {e}")
            return None, None

        logging.info(f"Current {settings.INDEX} spot price: {spot_price}")

        # Round to the nearest 500 or 1000
        atm_strike = round(spot_price / 500) * 500
        logging.info(f"Rounded ATM strike to nearest 500/1000: {atm_strike}")

        # Calculate target strikes
        ce_strike = atm_strike - settings.STRIKE_SELECTION_OFFSET
        pe_strike = atm_strike + settings.STRIKE_SELECTION_OFFSET

        logging.info(f"Target CE strike: {ce_strike}, Target PE strike: {pe_strike}")

        # Find the tradingsymbols for these strikes
        df = pd.DataFrame(self.instruments)
        options = df[(df['name'] == settings.INDEX) & (df['expiry'] == expiry_date)]

        ce_instrument = options[(options['strike'] == ce_strike) & (options['instrument_type'] == 'CE')]
        pe_instrument = options[(options['strike'] == pe_strike) & (options['instrument_type'] == 'PE')]

        if ce_instrument.empty or pe_instrument.empty:
            logging.error("Could not find trading symbols for the target strikes.")
            return None, None

        ce_symbol = ce_instrument.iloc[0]['tradingsymbol']
        pe_symbol = pe_instrument.iloc[0]['tradingsymbol']

        logging.info(f"Selected CE: {ce_symbol}, Selected PE: {pe_symbol}")

        return ce_symbol, pe_symbol

    def get_instrument_token(self, tradingsymbol):
        """
        Finds the instrument token for a given tradingsymbol.
        """
        df = pd.DataFrame(self.get_instruments())
        instrument = df[df['tradingsymbol'] == tradingsymbol]
        if not instrument.empty:
            return instrument.iloc[0]['instrument_token']
        logging.error(f"Could not find instrument token for {tradingsymbol}")
        return None

    def get_historical_data(self, instrument_token, from_date, to_date, interval, continuous=False):
        """
        Fetches historical data for a given instrument token.
        Returns a pandas DataFrame.
        """
        try:
            records = self.kite.historical_data(instrument_token, from_date, to_date, interval, continuous=continuous, oi=True)
            df = pd.DataFrame(records)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception as e:
            logging.error(f"Error fetching historical data for token {instrument_token}: {e}")
            return pd.DataFrame()

    def place_order(self, tradingsymbol, transaction_type, quantity):
        """
        Places a simple market order.
        """
        try:
            order_id = self.kite.place_order(
                tradingsymbol=tradingsymbol,
                exchange=settings.EXCHANGE,
                transaction_type=transaction_type,
                quantity=quantity,
                variety='regular',
                order_type=settings.ORDER_TYPE,
                product=settings.PRODUCT_TYPE
            )
            logging.info(f"Placed order for {tradingsymbol}, quantity {quantity}. Order ID: {order_id}")
            return order_id
        except Exception as e:
            logging.error(f"Order placement failed for {tradingsymbol}: {e}")
            return None

    def place_sl_order(self, tradingsymbol, transaction_type, quantity, trigger_price):
        """
        Places a Stop-Loss Market (SL-M) order.
        """
        try:
            # For a SELL SL order, the trigger price must be below the current market price.
            # For a BUY SL order, the trigger price must be above the current market price.
            order_id = self.kite.place_order(
                tradingsymbol=tradingsymbol,
                exchange=settings.EXCHANGE,
                transaction_type=transaction_type, # This will be opposite of the entry trade
                quantity=quantity,
                variety='regular',
                order_type='SL-M',
                product=settings.PRODUCT_TYPE,
                trigger_price=round(trigger_price, 1) # Round to nearest 10 paise
            )
            logging.info(f"Placed SL-M order for {tradingsymbol} at trigger {trigger_price}. Order ID: {order_id}")
            return order_id
        except Exception as e:
            logging.error(f"SL-M order placement failed for {tradingsymbol}: {e}")
            return None

    def modify_sl_order(self, order_id, trigger_price):
        """
        Modifies the trigger price of an existing SL-M order.
        """
        try:
            self.kite.modify_order(
                variety='regular',
                order_id=order_id,
                trigger_price=round(trigger_price, 1)
            )
            logging.info(f"Modified SL order {order_id} to new trigger price {trigger_price}")
            return order_id
        except Exception as e:
            logging.error(f"Failed to modify SL order {order_id}: {e}")
            return None

    def cancel_order(self, order_id):
        """
        Cancels an open order.
        """
        try:
            self.kite.cancel_order(variety='regular', order_id=order_id)
            logging.info(f"Cancelled order {order_id}")
            return order_id
        except Exception as e:
            logging.error(f"Failed to cancel order {order_id}: {e}")
            return None

    def get_positions(self):
        """
        Retrieves the current open positions.
        """
        try:
            return self.kite.positions()
        except Exception as e:
            logging.error(f"Failed to get positions: {e}")
            return None

    def get_orders(self):
        """
        Retrieves the list of all orders for the day.
        """
        try:
            return self.kite.orders()
        except Exception as e:
            logging.error(f"Failed to get orders: {e}")
            return []

    def get_order_average_price(self, order_id):
        """
        Retrieves the average execution price for a completed order.
        """
        try:
            history = self.kite.order_history(order_id)
            for order in history:
                if order['status'] == 'COMPLETE':
                    return order['average_price']
            return 0
        except Exception as e:
            logging.error(f"Failed to get order history for order_id {order_id}: {e}")
            return 0


if __name__ == '__main__':
    # This is a test block to check client functionality.
    # It will only work if you have a valid ACCESS_TOKEN in settings.py,
    # which you can get by running the dashboard and logging in.
    logging.basicConfig(level=logging.INFO)

    print("--- Running ZerodhaClient Test ---")
    client = ZerodhaClient()
    if client.is_authenticated():
        print("SUCCESS: Client is authenticated.")

        print("\n--- Testing Instrument Selection ---")
        ce, pe = client.find_options_for_trading()
        if ce and pe:
            print(f"SUCCESS: Found contracts for trading: CE={ce}, PE={pe}")
        else:
            print("FAILURE: Could not find contracts for trading.")
    else:
        print("FAILURE: Client is not authenticated. Please login via the dashboard.")
