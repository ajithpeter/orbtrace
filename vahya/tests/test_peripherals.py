"""
Unit tests for Vahya Peripheral Modules
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from peripherals.at86rf215 import *
from peripherals.max2771 import *


class TestAT86RF215Registers(unittest.TestCase):
    """Test AT86RF215 register definitions"""

    def test_rf09_registers(self):
        """Test RF09 register addresses"""
        self.assertEqual(RF09_IRQS, 0x0000)
        self.assertEqual(RF09_STATE, 0x0002)
        self.assertEqual(RF09_CMD, 0x0003)
        self.assertEqual(RF09_RSSI, 0x000D)

    def test_rf24_registers(self):
        """Test RF24 register addresses (offset by 0x100)"""
        self.assertEqual(RF24_IRQS, 0x0100)
        self.assertEqual(RF24_STATE, 0x0102)
        self.assertEqual(RF24_CMD, 0x0103)
        self.assertEqual(RF24_RSSI, 0x010D)

    def test_command_codes(self):
        """Test command code definitions"""
        self.assertEqual(CMD_NOP, 0x00)
        self.assertEqual(CMD_SLEEP, 0x01)
        self.assertEqual(CMD_TRXOFF, 0x02)
        self.assertEqual(CMD_TX, 0x04)
        self.assertEqual(CMD_RX, 0x05)
        self.assertEqual(CMD_RESET, 0x07)

    def test_state_values(self):
        """Test state value definitions"""
        self.assertEqual(STATE_TRXOFF, 0x02)
        self.assertEqual(STATE_TX, 0x04)
        self.assertEqual(STATE_RX, 0x05)


class TestMAX2771Config(unittest.TestCase):
    """Test MAX2771 configuration helpers"""

    def test_build_register(self):
        """Test register word building"""
        # Register address in upper 3 bits
        word = MAX2771Config.build_register(0, 0x12345678)
        self.assertEqual((word >> 29) & 0x7, 0)

        word = MAX2771Config.build_register(3, 0x12345678)
        self.assertEqual((word >> 29) & 0x7, 3)

    def test_conf1_generation(self):
        """Test CONF1 register generation"""
        conf1 = MAX2771Config.conf1()
        # Should be a 32-bit value
        self.assertLessEqual(conf1, 0xFFFFFFFF)
        # Upper 3 bits should be register address (0 for CONF1)
        self.assertEqual((conf1 >> 29) & 0x7, 0)

    def test_conf2_generation(self):
        """Test CONF2 register generation"""
        conf2 = MAX2771Config.conf2()
        self.assertLessEqual(conf2, 0xFFFFFFFF)
        # Upper 3 bits should be register address (1 for CONF2)
        self.assertEqual((conf2 >> 29) & 0x7, 1)

    def test_conf3_generation(self):
        """Test CONF3 register generation"""
        conf3 = MAX2771Config.conf3()
        self.assertLessEqual(conf3, 0xFFFFFFFF)
        # Upper 3 bits should be register address (2 for CONF3)
        self.assertEqual((conf3 >> 29) & 0x7, 2)

    def test_pll_config(self):
        """Test PLL configuration calculation"""
        pll1, pll2 = MAX2771Config.pll_config(
            ref_freq_hz=16368000,
            lo_freq_hz=1575420000
        )

        # Should return two 32-bit words
        self.assertLessEqual(pll1, 0xFFFFFFFF)
        self.assertLessEqual(pll2, 0xFFFFFFFF)

        # PLL1 should have address 3
        self.assertEqual((pll1 >> 29) & 0x7, 3)
        # PLL2 should have address 4
        self.assertEqual((pll2 >> 29) & 0x7, 4)

    def test_default_gps_l1(self):
        """Test default GPS L1 configuration"""
        config = MAX2771Config.default_gps_l1()

        # Should return a list of configuration words
        self.assertIsInstance(config, list)
        self.assertGreater(len(config), 0)

        # All should be 32-bit values
        for word in config:
            self.assertLessEqual(word, 0xFFFFFFFF)

    def test_default_galileo_e1(self):
        """Test default Galileo E1 configuration"""
        config = MAX2771Config.default_galileo_e1()
        self.assertIsInstance(config, list)
        self.assertGreater(len(config), 0)

    def test_default_glonass_l1(self):
        """Test default GLONASS L1 configuration"""
        config = MAX2771Config.default_glonass_l1()
        self.assertIsInstance(config, list)
        self.assertGreater(len(config), 0)


class TestSampleRateCalculations(unittest.TestCase):
    """Test sample rate and bandwidth calculations"""

    def test_calculate_sample_rate(self):
        """Test MAX2771 sample rate calculation"""
        # Default configuration
        sample_rate = calculate_sample_rate()
        self.assertGreater(sample_rate, 0)
        self.assertEqual(sample_rate, 16368000)  # Default 16.368 MHz

    def test_gnss_bandwidth_requirement(self):
        """Test GNSS bandwidth calculation"""
        # 16.368 MHz sample rate, 4 bits per sample
        bandwidth = gnss_bandwidth_requirement(16368000, 4)
        expected = (16368000 * 4) / 8  # bytes per second
        self.assertEqual(bandwidth, expected)

        # Should be about 8.2 MB/s
        self.assertAlmostEqual(bandwidth / 1e6, 8.2, places=1)

    def test_bandwidth_scaling(self):
        """Test bandwidth scales correctly with sample rate"""
        bw1 = gnss_bandwidth_requirement(16368000, 4)
        bw2 = gnss_bandwidth_requirement(16368000 * 2, 4)

        # Doubling sample rate should double bandwidth
        self.assertAlmostEqual(bw2, bw1 * 2, places=1)


class TestModuleIntegration(unittest.TestCase):
    """Integration tests for peripheral modules"""

    def test_at86rf215_imports(self):
        """Test that all AT86RF215 components can be imported"""
        try:
            from peripherals.at86rf215 import (
                AT86RF215StreamCapture,
                AT86RF215SPIControl,
                RF09_IRQS,
                CMD_RX
            )
        except ImportError as e:
            self.fail(f"Failed to import AT86RF215 components: {e}")

    def test_max2771_imports(self):
        """Test that all MAX2771 components can be imported"""
        try:
            from peripherals.max2771 import (
                MAX2771StreamCapture,
                MAX2771SPIControl,
                MAX2771Config,
                calculate_sample_rate,
                gnss_bandwidth_requirement
            )
        except ImportError as e:
            self.fail(f"Failed to import MAX2771 components: {e}")

    def test_module_documentation(self):
        """Test that modules have docstrings"""
        import peripherals.at86rf215 as at86rf215_module
        import peripherals.max2771 as max2771_module

        self.assertIsNotNone(at86rf215_module.__doc__)
        self.assertIsNotNone(max2771_module.__doc__)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
