# algotrader/strategy.py

import pandas as pd
import pandas_ta as ta

class Strategy:
    """
    Encapsulates the trading strategy logic.
    Calculates indicators and generates buy/sell signals.
    """
    def __init__(self, settings):
        """
        Initializes the Strategy class with parameters from the settings file.
        """
        self.settings = settings

    def calculate_indicators(self, df):
        """
        Calculates all required technical indicators and appends them to the DataFrame.

        Args:
            df (pd.DataFrame): DataFrame with columns ['date', 'open', 'high', 'low', 'close', 'volume', 'oi']

        Returns:
            pd.DataFrame: The DataFrame with appended indicator columns.
        """
        if df.empty:
            return df

        # Calculate Supertrends
        st_fast = ta.supertrend(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            length=self.settings.SUPERTREND_FAST_PERIOD,
            multiplier=self.settings.SUPERTREND_FAST_MULTIPLIER
        )
        if st_fast is not None and not st_fast.empty:
            df['st_fast'] = st_fast.iloc[:, 0]
            df['st_fast_dir'] = st_fast.iloc[:, 1]

        st_slow = ta.supertrend(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            length=self.settings.SUPERTREND_SLOW_PERIOD,
            multiplier=self.settings.SUPERTREND_SLOW_MULTIPLIER
        )
        if st_slow is not None and not st_slow.empty:
            df['st_slow'] = st_slow.iloc[:, 0]

        # Calculate VWAP
        df['vwap'] = ta.vwap(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            volume=df['volume']
        )

        # Calculate Choppiness Index
        df['chop'] = ta.chop(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            length=self.settings.CHOP_PERIOD
        )

        return df.dropna()

    def check_signal(self, df_with_indicators):
        """
        Checks for a bullish or bearish signal on the last completed candle.

        Args:
            df_with_indicators (pd.DataFrame): DataFrame with indicators calculated.

        Returns:
            int: 1 for BULLISH, -1 for BEARISH, 0 for NO_SIGNAL.
        """
        if len(df_with_indicators) < 1:
            return 0 # Not enough data

        # Get the last completed candle
        last_candle = df_with_indicators.iloc[-1]

        # --- Define Signal Flags ---
        price_above_vwap = last_candle['close'] > last_candle['vwap']
        price_below_vwap = last_candle['close'] < last_candle['vwap']

        # --- Define Signal Flags ---
        price_above_vwap = last_candle['close'] > last_candle['vwap']
        price_below_vwap = last_candle['close'] < last_candle['vwap']

        price_above_st_fast = last_candle['close'] > last_candle['st_fast']
        price_above_st_slow = last_candle['close'] > last_candle['st_slow']

        price_below_st_fast = last_candle['close'] < last_candle['st_fast']
        price_below_st_slow = last_candle['close'] < last_candle['st_slow']

        is_trending = last_candle['chop'] > self.settings.CHOP_THRESHOLD

        # --- Check for Signals ---
        # A trade can only be taken in a trending market
        if not is_trending:
            return 0

        # Bullish Signal Condition
        if price_above_st_fast and price_above_st_slow and price_above_vwap:
            return 1

        # Bearish Signal Condition
        if price_below_st_fast and price_below_st_slow and price_below_vwap:
            return -1

        return 0 # No signal

    def get_trailing_sl(self, df_with_indicators, trade_type):
        """
        Gets the trailing stop loss value from the Supertrend indicator.

        Args:
            df_with_indicators (pd.DataFrame): DataFrame with indicators.
            trade_type (str): 'LONG' or 'SHORT'.

        Returns:
            float: The calculated trailing stop loss price.
        """
        if len(df_with_indicators) < 1 or 'st_fast' not in df_with_indicators.columns:
            return 0

        last_candle = df_with_indicators.iloc[-1]

        # For a long trade, the SL is the lower band (the supertrend value itself)
        # For a short trade, the SL is the upper band (the supertrend value itself)
        # pandas-ta supertrend function gives the correct line to trail automatically.
        return last_candle['st_fast']

    def check_oi_alert(self, df_with_indicators):
        """
        Checks for a significant change in Open Interest over the lookback period.

        Args:
            df_with_indicators (pd.DataFrame): DataFrame with OI data.

        Returns:
            str or None: An alert message if triggered, otherwise None.
        """
        if not self.settings.ENABLE_OI_ALERTS or 'oi' not in df_with_indicators.columns:
            return None

        candles_to_check = int(self.settings.OI_ALERT_LOOKBACK_MINUTES / 5) # Assuming 5 min timeframe

        if len(df_with_indicators) < candles_to_check + 1:
            return None # Not enough data

        recent_oi = df_with_indicators['oi'].iloc[-candles_to_check:]
        initial_oi = recent_oi.iloc[0]
        latest_oi = recent_oi.iloc[-1]

        if initial_oi == 0:
            return None # Avoid division by zero

        percent_change = (latest_oi - initial_oi) / initial_oi

        if abs(percent_change) > self.settings.OI_ALERT_THRESHOLD_PERCENT:
            direction = "increased" if percent_change > 0 else "decreased"
            return f"OI_ALERT: Open Interest has {direction} by {percent_change:.2%} in the last {self.settings.OI_ALERT_LOOKBACK_MINUTES} minutes."

        return None

# This space is intentionally left blank.
