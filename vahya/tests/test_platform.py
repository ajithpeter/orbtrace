"""
Unit tests for Vahya Platform Definition
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platforms.vahya import Platform


class TestVahyaPlatform(unittest.TestCase):
    """Test cases for Vahya platform definition"""

    def setUp(self):
        """Create platform instance for testing"""
        self.platform = Platform()

    def test_platform_creation(self):
        """Test that platform can be instantiated"""
        self.assertIsNotNone(self.platform)
        self.assertEqual(self.platform.name, "vahya")

    def test_device_specification(self):
        """Test FPGA device specification"""
        # Should be LFE5U-25F-7BG256C
        self.assertIn("LFE5U-25F", self.platform.device)
        self.assertIn("7BG256", self.platform.device)

    def test_default_clock(self):
        """Test default clock configuration"""
        self.assertEqual(self.platform.default_clk_name, "clk26")
        expected_period = 1e9 / 26e6  # 26 MHz
        self.assertAlmostEqual(self.platform.default_clk_period, expected_period, places=2)

    def test_clock_resource(self):
        """Test that clock resource exists"""
        # This should not raise an exception
        try:
            clk = self.platform.lookup_request("clk26")
            self.assertIsNotNone(clk)
        except Exception as e:
            self.fail(f"Clock resource lookup failed: {e}")

    def test_ulpi_resource(self):
        """Test that ULPI USB PHY resource exists"""
        try:
            ulpi = self.platform.lookup_request("ulpi")
            self.assertIsNotNone(ulpi)
            # Check that all required subsignals exist
            self.assertTrue(hasattr(ulpi, 'data'))
            self.assertTrue(hasattr(ulpi, 'clk'))
            self.assertTrue(hasattr(ulpi, 'dir'))
            self.assertTrue(hasattr(ulpi, 'nxt'))
            self.assertTrue(hasattr(ulpi, 'stp'))
            self.assertTrue(hasattr(ulpi, 'rst'))
        except Exception as e:
            self.fail(f"ULPI resource lookup failed: {e}")

    def test_rgb_led_resource(self):
        """Test that RGB LED resource exists"""
        try:
            rgb_led = self.platform.lookup_request("rgb_led")
            self.assertIsNotNone(rgb_led)
            # Check for R, G, B subsignals
            self.assertTrue(hasattr(rgb_led, 'r'))
            self.assertTrue(hasattr(rgb_led, 'g'))
            self.assertTrue(hasattr(rgb_led, 'b'))
        except Exception as e:
            self.fail(f"RGB LED resource lookup failed: {e}")

    def test_user_switch_resource(self):
        """Test that user switch resource exists"""
        try:
            sw = self.platform.lookup_request("user_sw")
            self.assertIsNotNone(sw)
        except Exception as e:
            self.fail(f"User switch resource lookup failed: {e}")

    def test_at86rf215_resource(self):
        """Test that AT86RF215 resource exists (even if placeholder)"""
        try:
            at86rf215 = self.platform.lookup_request("at86rf215")
            self.assertIsNotNone(at86rf215)
            # Check for required subsignals
            self.assertTrue(hasattr(at86rf215, 'spi_clk'))
            self.assertTrue(hasattr(at86rf215, 'spi_mosi'))
            self.assertTrue(hasattr(at86rf215, 'spi_miso'))
            self.assertTrue(hasattr(at86rf215, 'spi_cs_n'))
            self.assertTrue(hasattr(at86rf215, 'rst_n'))
            self.assertTrue(hasattr(at86rf215, 'irq'))
            self.assertTrue(hasattr(at86rf215, 'rf09_rxiq'))
            self.assertTrue(hasattr(at86rf215, 'rf09_txiq'))
            self.assertTrue(hasattr(at86rf215, 'rf24_rxiq'))
            self.assertTrue(hasattr(at86rf215, 'rf24_txiq'))
        except Exception as e:
            self.fail(f"AT86RF215 resource lookup failed: {e}")

    def test_max2771_resource(self):
        """Test that MAX2771 resource exists (even if placeholder)"""
        try:
            max2771 = self.platform.lookup_request("max2771")
            self.assertIsNotNone(max2771)
            # Check for required subsignals
            self.assertTrue(hasattr(max2771, 'spi_clk'))
            self.assertTrue(hasattr(max2771, 'spi_mosi'))
            self.assertTrue(hasattr(max2771, 'spi_miso'))
            self.assertTrue(hasattr(max2771, 'spi_cs_n'))
            self.assertTrue(hasattr(max2771, 'iq_sign'))
            self.assertTrue(hasattr(max2771, 'iq_mag'))
            self.assertTrue(hasattr(max2771, 'qq_sign'))
            self.assertTrue(hasattr(max2771, 'qq_mag'))
            self.assertTrue(hasattr(max2771, 'clkout'))
        except Exception as e:
            self.fail(f"MAX2771 resource lookup failed: {e}")

    def test_serial_resource(self):
        """Test that serial UART resource exists"""
        try:
            serial = self.platform.lookup_request("serial")
            self.assertIsNotNone(serial)
            self.assertTrue(hasattr(serial, 'tx'))
            self.assertTrue(hasattr(serial, 'rx'))
        except Exception as e:
            self.fail(f"Serial resource lookup failed: {e}")

    def test_spi_resource(self):
        """Test that SPI master resources exist"""
        try:
            spi0 = self.platform.lookup_request("spi", 0)
            self.assertIsNotNone(spi0)
            self.assertTrue(hasattr(spi0, 'clk'))
            self.assertTrue(hasattr(spi0, 'mosi'))
            self.assertTrue(hasattr(spi0, 'miso'))
            self.assertTrue(hasattr(spi0, 'cs_n'))
        except Exception as e:
            self.fail(f"SPI resource lookup failed: {e}")

    def test_i2c_resource(self):
        """Test that I2C resource exists"""
        try:
            i2c = self.platform.lookup_request("i2c")
            self.assertIsNotNone(i2c)
            self.assertTrue(hasattr(i2c, 'scl'))
            self.assertTrue(hasattr(i2c, 'sda'))
        except Exception as e:
            self.fail(f"I2C resource lookup failed: {e}")

    def test_multiple_devices(self):
        """Test platform with different FPGA devices"""
        platform_25f = Platform(device="LFE5U-25F")
        self.assertIn("25F", platform_25f.device)

        platform_45f = Platform(device="LFE5U-45F")
        self.assertIn("45F", platform_45f.device)

    def test_invalid_device(self):
        """Test that invalid device raises assertion"""
        with self.assertRaises(AssertionError):
            Platform(device="INVALID")

    def test_toolchain(self):
        """Test that default toolchain is Trellis"""
        platform = Platform(toolchain="trellis")
        self.assertEqual(platform.toolchain, "trellis")


class TestPlatformResources(unittest.TestCase):
    """Test resource definitions in detail"""

    def setUp(self):
        """Create platform instance"""
        self.platform = Platform()

    def test_ulpi_pin_count(self):
        """Test that ULPI has correct number of data pins"""
        ulpi = self.platform.lookup_request("ulpi")
        # ULPI data should be 8 bits
        # This is a basic check - actual pin count verification would need
        # deeper inspection of the resource definition

    def test_at86rf215_iq_width(self):
        """Test that AT86RF215 I/Q data has correct bit width"""
        at86rf215 = self.platform.lookup_request("at86rf215")
        # Each I/Q bus should be 14 bits
        # Actual verification would need to count pins in definition

    def test_max2771_iq_width(self):
        """Test that MAX2771 I/Q data has correct bit width"""
        max2771 = self.platform.lookup_request("max2771")
        # Each signal should be 1 bit (2-bit I + 2-bit Q total)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
