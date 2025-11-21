"""
MAX2771 GNSS Frontend Integration Module

Provides Python wrapper for MAX2771 Verilog ADC capture module,
making it easy to integrate into LiteX SoCs.
"""

from migen import *
from litex.soc.interconnect.csr import *
from litex.soc.interconnect.stream import Endpoint


class MAX2771StreamCapture(Module, AutoCSR):
    """
    MAX2771 ADC Data Stream Capture

    Wraps the Verilog max2771_adc_capture module and provides:
    - CSR interface for CPU control
    - Stream output for USB connectivity
    - Status monitoring
    - Decimation control

    Parameters
    ----------
    pads : Record
        MAX2771 platform pads (from platform.request("max2771"))
    sample_width : int
        Output sample width in bits (default: 32, packs 8 I/Q samples)
    fifo_depth : int
        Internal FIFO depth (default: 2048)
    """

    def __init__(self, pads, sample_width=32, fifo_depth=2048):
        # Stream output
        self.source = source = Endpoint([("data", sample_width), ("last", 1)])

        # CSR registers
        self.control = CSRStorage(8, fields=[
            CSRField("enable", size=1, offset=0,
                    description="Enable ADC capture"),
            CSRField("decimation", size=3, offset=1,
                    description="Decimation factor: 0=none, 1=/2, 2=/4, 3=/8, etc."),
        ])

        self.status = CSRStatus(32, fields=[
            CSRField("overflow", size=1, offset=0,
                    description="FIFO overflow flag"),
        ])

        self.sample_count = CSRStatus(32, description="Number of samples captured")

        # Internal signals
        stream_data = Signal(sample_width)
        stream_valid = Signal()
        stream_ready = Signal()
        stream_last = Signal()

        fifo_overflow = Signal()
        sample_count = Signal(32)

        # Instantiate Verilog module
        self.specials += Instance("max2771_adc_capture",
            # Parameters
            p_SAMPLE_WIDTH = sample_width,
            p_FIFO_DEPTH = fifo_depth,

            # Clocks and reset
            i_clk_sys = ClockSignal("sys"),
            i_rst = ResetSignal("sys"),

            # MAX2771 ADC interface
            i_iq_sign = pads.iq_sign,
            i_iq_mag = pads.iq_mag,
            i_qq_sign = pads.qq_sign,
            i_qq_mag = pads.qq_mag,
            i_clkout = pads.clkout,

            # Configuration
            i_capture_enable = self.control.fields.enable,
            i_decimation = self.control.fields.decimation,

            # Output stream
            o_stream_data = stream_data,
            o_stream_valid = stream_valid,
            i_stream_ready = stream_ready,
            o_stream_last = stream_last,

            # Status
            o_fifo_overflow = fifo_overflow,
            o_sample_count = sample_count,
        )

        # Connect stream output
        self.comb += [
            source.valid.eq(stream_valid),
            stream_ready.eq(source.ready),
            source.data.eq(stream_data),
            source.last.eq(stream_last),
        ]

        # Connect status
        self.comb += [
            self.status.fields.overflow.eq(fifo_overflow),
            self.sample_count.status.eq(sample_count),
        ]


class MAX2771SPIControl(Module, AutoCSR):
    """
    MAX2771 SPI Control Interface

    Provides SPI master interface for MAX2771 configuration.
    The MAX2771 uses a write-only SPI interface with 32-bit
    configuration words.

    Parameters
    ----------
    spi_pads : Record
        MAX2771 SPI pads
    sys_clk_freq : int
        System clock frequency in Hz
    spi_clk_freq : int
        Desired SPI clock frequency in Hz (default: 1 MHz, max 10 MHz)
    """

    def __init__(self, spi_pads, sys_clk_freq, spi_clk_freq=int(1e6)):
        from litex.soc.cores.spi import SPIMaster

        # SPI master (MAX2771 uses 32-bit words)
        self.submodules.spi = SPIMaster(
            pads = spi_pads,
            data_width = 32,  # MAX2771 uses 32-bit config words
            sys_clk_freq = sys_clk_freq,
            spi_clk_freq = spi_clk_freq,
        )

        # Control signals
        self.power = CSRStorage(2, fields=[
            CSRField("idle", size=1, offset=0,
                    description="Idle mode (low power)"),
            CSRField("shdn", size=1, offset=1,
                    description="Shutdown (power off)"),
        ])

    def connect_pads(self, pads):
        """Connect power control signals to pads"""
        self.comb += [
            pads.idle.eq(self.power.fields.idle),
            pads.shdn.eq(self.power.fields.shdn),
        ]


# MAX2771 Configuration Register Definitions
# These match the MAX2771 datasheet

class MAX2771Config:
    """
    MAX2771 Configuration Register Builder

    Provides helper methods to build 32-bit configuration words
    for the MAX2771 GNSS frontend.

    Each configuration register is 32 bits:
    - Bits [31:29]: Register address (CONF1-CONF4, PLL1-PLL6, etc.)
    - Bits [28:0]: Configuration data
    """

    # Register addresses
    CONF1 = 0  # Configuration 1
    CONF2 = 1  # Configuration 2
    CONF3 = 2  # Configuration 3
    PLL1  = 3  # PLL Configuration 1
    PLL2  = 4  # PLL Configuration 2
    PLL3  = 5  # PLL Configuration 3

    @staticmethod
    def build_register(addr, value):
        """Build a 32-bit configuration word"""
        return ((addr & 0x7) << 29) | (value & 0x1FFFFFFF)

    @staticmethod
    def conf1(
        chipen=1,      # Chip enable
        idle=0,        # Idle mode
        ilna1=0b11,    # LNA1 current
        ilna2=0b11,    # LNA2 current
        ilo=0b11,      # LO current
        imix=0b01,     # Mixer current
        mixpole=1,     # Mixer pole
        lnamode=1,     # LNA mode
        mixen=1,       # Mixer enable
        anten=1,       # Antenna enable
        fcen=0b111111, # Filter center frequency
        fgain=0b000    # Filter gain
    ):
        """
        Build CONF1 register

        Controls analog frontend settings including LNA, mixer,
        and filter configuration.
        """
        value = (
            (chipen << 27) |
            (idle << 26) |
            (ilna1 << 24) |
            (ilna2 << 22) |
            (ilo << 20) |
            (imix << 18) |
            (mixpole << 17) |
            (lnamode << 16) |
            (mixen << 15) |
            (anten << 14) |
            (fcen << 8) |
            (fgain << 5)
        )
        return MAX2771Config.build_register(MAX2771Config.CONF1, value)

    @staticmethod
    def conf2(
        iqen=1,        # I/Q output enable
        gainin=0b10,   # Input gain
        agcmode=0b01,  # AGC mode
        format=0b01,   # Output format (2-bit I/Q)
        bits=0b00,     # Number of bits
        drvcfg=0b00,   # Driver configuration
        loen=1,        # LO enable
        dieid=1        # Die ID enable
    ):
        """
        Build CONF2 register

        Controls digital output interface and AGC settings.
        """
        value = (
            (iqen << 27) |
            (gainin << 25) |
            (agcmode << 23) |
            (format << 21) |
            (bits << 19) |
            (drvcfg << 17) |
            (loen << 16) |
            (dieid << 15)
        )
        return MAX2771Config.build_register(MAX2771Config.CONF2, value)

    @staticmethod
    def conf3(
        hiloaden=1,    # HiLOADEN
        adcen=1,       # ADC enable
        drven=1,       # Driver enable
        fofsten=0,     # FOFST enable
        filten=1,      # Filter enable
        fhipen=0,      # FHIPEN
        pgaien=0b10,   # PGA I enable
        pgaqen=0b10,   # PGA Q enable
        strm=0,        # Stream mode
        strmstart=0,   # Stream start
        strmstop=0,    # Stream stop
        strmcount=0    # Stream count
    ):
        """
        Build CONF3 register

        Controls ADC, PGA, and streaming settings.
        """
        value = (
            (hiloaden << 27) |
            (adcen << 26) |
            (drven << 25) |
            (fofsten << 24) |
            (filten << 23) |
            (fhipen << 22) |
            (pgaien << 20) |
            (pgaqen << 18) |
            (strm << 17) |
            (strmstart << 16) |
            (strmstop << 15) |
            (strmcount << 0)
        )
        return MAX2771Config.build_register(MAX2771Config.CONF3, value)

    @staticmethod
    def pll_config(ref_freq_hz=16368000, lo_freq_hz=1575420000):
        """
        Calculate PLL configuration for desired LO frequency

        Parameters
        ----------
        ref_freq_hz : int
            Reference clock frequency in Hz (default: 16.368 MHz)
        lo_freq_hz : int
            Desired LO frequency in Hz (default: 1575.42 MHz for GPS L1)

        Returns
        -------
        tuple
            (PLL1_value, PLL2_value) configuration words
        """
        # Calculate PLL parameters
        # LO_freq = REF_freq × (N + F/8192) / R
        # Typical values: R=1, N and F calculated from desired freq

        R = 1
        N = int(lo_freq_hz / ref_freq_hz)
        F = int(((lo_freq_hz / ref_freq_hz) - N) * 8192)

        # PLL1 register
        pll1_value = (
            (N << 13) |
            (F << 0)
        )

        # PLL2 register (R divider and other settings)
        pll2_value = (
            (R << 24) |
            (1 << 23) |  # VCOEN
            (0b11 << 21) | # ICP
            (1 << 20)    # PFDEN
        )

        return (
            MAX2771Config.build_register(MAX2771Config.PLL1, pll1_value),
            MAX2771Config.build_register(MAX2771Config.PLL2, pll2_value)
        )

    @staticmethod
    def default_gps_l1():
        """
        Return default configuration for GPS L1 (1575.42 MHz)

        Returns
        -------
        list
            List of configuration words to write via SPI
        """
        pll1, pll2 = MAX2771Config.pll_config(
            ref_freq_hz=16368000,
            lo_freq_hz=1575420000
        )

        return [
            MAX2771Config.conf1(),
            MAX2771Config.conf2(),
            MAX2771Config.conf3(),
            pll1,
            pll2,
        ]

    @staticmethod
    def default_galileo_e1():
        """
        Return default configuration for Galileo E1 (1575.42 MHz)
        Same frequency as GPS L1
        """
        return MAX2771Config.default_gps_l1()

    @staticmethod
    def default_glonass_l1():
        """
        Return default configuration for GLONASS L1 (~1602 MHz)
        GLONASS uses FDMA, so frequency varies by satellite
        This configures for center frequency
        """
        pll1, pll2 = MAX2771Config.pll_config(
            ref_freq_hz=16368000,
            lo_freq_hz=1602000000  # Center frequency
        )

        return [
            MAX2771Config.conf1(),
            MAX2771Config.conf2(),
            MAX2771Config.conf3(),
            pll1,
            pll2,
        ]


# Sample rate calculations
def calculate_sample_rate(ref_freq_hz=16368000, conf2_format=0b01):
    """
    Calculate ADC sample rate based on MAX2771 configuration

    Parameters
    ----------
    ref_freq_hz : int
        Reference clock frequency in Hz
    conf2_format : int
        Output format from CONF2 register

    Returns
    -------
    float
        Sample rate in Hz
    """
    # Sample rate depends on reference frequency and dividers
    # For 2-bit I/Q format with 16.368 MHz reference:
    # Sample rate = ref_freq_hz (typically)
    return ref_freq_hz


# Bandwidth calculations
def gnss_bandwidth_requirement(sample_rate_hz, bits_per_sample=4):
    """
    Calculate USB bandwidth requirement for GNSS streaming

    Parameters
    ----------
    sample_rate_hz : float
        ADC sample rate in Hz
    bits_per_sample : int
        Total bits per I/Q sample (default: 4 for 2-bit I+Q)

    Returns
    -------
    float
        Required bandwidth in bytes/second
    """
    return (sample_rate_hz * bits_per_sample) / 8
