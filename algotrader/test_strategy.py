# algotrader/test_strategy.py

import unittest
import pandas as pd
import numpy as np
from datetime import datetime
import settings
from strategy import Strategy

class TestStrategy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up the strategy instance and sample data once for all tests."""
        cls.strategy = Strategy(settings)

        # Helper to create more extensive data
        def generate_data(base_price, trend, size=30):
            dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=size, freq="5min"))
            prices = base_price + np.arange(size) * trend + np.random.randn(size) * 0.5
            volume = np.random.randint(1000, 2000, size=size)
            oi = np.random.randint(5000, 6000, size=size)
            df = pd.DataFrame({
                'date': dates,
                'open': prices - np.random.rand(size),
                'high': prices + np.random.rand(size),
                'low': prices - np.random.rand(size) - 1,
                'close': prices,
                'volume': volume,
                'oi': oi
            })
            df.set_index('date', inplace=True)
            return df

        cls.bullish_df = generate_data(base_price=100, trend=2)
        cls.bearish_df = generate_data(base_price=200, trend=-2)
        cls.choppy_df = generate_data(base_price=150, trend=0.1)


    def test_bullish_signal(self):
        """Test if a bullish signal is correctly generated."""
        df = self.strategy.calculate_indicators(self.bullish_df.copy())
        self.assertFalse(df.empty, "DataFrame should not be empty after calculating indicators")

        # Manually set the last candle to ensure a clear signal
        df.loc[df.index[-1], 'close'] = 200
        df.loc[df.index[-1], 'vwap'] = 190
        df.loc[df.index[-1], 'st_fast'] = 189
        df.loc[df.index[-1], 'st_slow'] = 188
        df.loc[df.index[-1], 'chop'] = 60 # Trending

        signal = self.strategy.check_signal(df)
        self.assertEqual(signal, 1, "Should generate a BULLISH signal")

    def test_bearish_signal(self):
        """Test if a bearish signal is correctly generated."""
        df = self.strategy.calculate_indicators(self.bearish_df.copy())
        self.assertFalse(df.empty, "DataFrame should not be empty after calculating indicators")

        # Manually set the last candle to ensure a clear signal
        df.loc[df.index[-1], 'close'] = 90
        df.loc[df.index[-1], 'vwap'] = 95
        df.loc[df.index[-1], 'st_fast'] = 96
        df.loc[df.index[-1], 'st_slow'] = 97
        df.loc[df.index[-1], 'chop'] = 65 # Trending

        signal = self.strategy.check_signal(df)
        self.assertEqual(signal, -1, "Should generate a BEARISH signal")

    def test_no_signal_in_choppy_market(self):
        """Test that no signal is generated in a choppy market."""
        df = self.strategy.calculate_indicators(self.choppy_df.copy())
        self.assertFalse(df.empty, "DataFrame should not be empty after calculating indicators")

        # Manually set chop to be low (choppy)
        df.loc[df.index[-1], 'chop'] = 30

        signal = self.strategy.check_signal(df)
        self.assertEqual(signal, 0, "Should generate NO SIGNAL in a choppy market")

    def test_no_signal_when_price_crosses_one_indicator(self):
        """Test that no signal is generated if not all conditions are met."""
        df = self.strategy.calculate_indicators(self.bullish_df.copy())
        self.assertFalse(df.empty, "DataFrame should not be empty after calculating indicators")

        # Price is above Supertrends but below VWAP
        df.loc[df.index[-1], 'close'] = 120
        df.loc[df.index[-1], 'vwap'] = 121 # Price is below VWAP
        df.loc[df.index[-1], 'st_fast'] = 114
        df.loc[df.index[-1], 'st_slow'] = 113
        df.loc[df.index[-1], 'chop'] = 60 # Trending

        signal = self.strategy.check_signal(df)
        self.assertEqual(signal, 0, "Should generate NO SIGNAL if price is below VWAP")

if __name__ == '__main__':
    unittest.main()
