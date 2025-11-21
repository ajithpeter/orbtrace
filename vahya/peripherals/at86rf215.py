"""
AT86RF215 RF Transceiver Integration Module

Provides Python wrapper for AT86RF215 Verilog I/Q capture module,
making it easy to integrate into LiteX SoCs.
"""

from migen import *
from litex.soc.interconnect.csr import *
from litex.soc.interconnect.stream import Endpoint


class AT86RF215StreamCapture(Module, AutoCSR):
    """
    AT86RF215 I/Q Data Stream Capture

    Wraps the Verilog at86rf215_iq_capture module and provides:
    - CSR interface for CPU control
    - Stream output for USB connectivity
    - Status monitoring

    Parameters
    ----------
    pads : Record
        AT86RF215 platform pads (from platform.request("at86rf215"))
    sample_width : int
        Output sample width in bits (default: 32)
    fifo_depth : int
        Internal FIFO depth (default: 1024)
    """

    def __init__(self, pads, sample_width=32, fifo_depth=1024):
        # Stream output
        self.source = source = Endpoint([("data", sample_width), ("last", 1)])

        # CSR registers
        self.control = CSRStorage(8, fields=[
            CSRField("enable", size=1, offset=0,
                    description="Enable I/Q capture"),
            CSRField("band_select", size=2, offset=1,
                    description="Band select: 0=RF09_RX, 1=RF09_TX, 2=RF24_RX, 3=RF24_TX"),
        ])

        self.status = CSRStatus(32, fields=[
            CSRField("overflow", size=1, offset=0,
                    description="FIFO overflow flag"),
            CSRField("sample_count", size=16, offset=1,
                    description="Number of samples captured"),
        ])

        # Internal signals
        stream_data = Signal(sample_width)
        stream_valid = Signal()
        stream_ready = Signal()
        stream_last = Signal()

        fifo_overflow = Signal()
        sample_count = Signal(16)

        # Instantiate Verilog module
        self.specials += Instance("at86rf215_iq_capture",
            # Parameters
            p_SAMPLE_WIDTH = sample_width,
            p_FIFO_DEPTH = fifo_depth,

            # Clocks and reset
            i_clk_sys = ClockSignal("sys"),
            i_rst = ResetSignal("sys"),

            # AT86RF215 RF09 interface
            i_rf09_rxiq = pads.rf09_rxiq,
            i_rf09_txiq = pads.rf09_txiq,
            i_rf09_rxen = pads.rf09_rxen,
            i_rf09_txen = pads.rf09_txen,

            # AT86RF215 RF24 interface
            i_rf24_rxiq = pads.rf24_rxiq,
            i_rf24_txiq = pads.rf24_txiq,
            i_rf24_rxen = pads.rf24_rxen,
            i_rf24_txen = pads.rf24_txen,

            # AT86RF215 clock
            i_clk_26mhz = pads.clk_26mhz,

            # Configuration
            i_band_select = self.control.fields.band_select,
            i_capture_enable = self.control.fields.enable,

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
            self.status.fields.sample_count.eq(sample_count),
        ]


class AT86RF215SPIControl(Module, AutoCSR):
    """
    AT86RF215 SPI Control Interface

    Provides SPI master interface for AT86RF215 configuration.
    This is separate from the high-speed I/Q capture to allow
    independent control and data paths.

    Parameters
    ----------
    pads : Record
        AT86RF215 SPI pads
    sys_clk_freq : int
        System clock frequency in Hz
    spi_clk_freq : int
        Desired SPI clock frequency in Hz (default: 1 MHz)
    """

    def __init__(self, spi_pads, sys_clk_freq, spi_clk_freq=int(1e6)):
        from litex.soc.cores.spi import SPIMaster

        # SPI master
        self.submodules.spi = SPIMaster(
            pads = spi_pads,
            data_width = 8,
            sys_clk_freq = sys_clk_freq,
            spi_clk_freq = spi_clk_freq,
        )

        # Control signals
        self.rst_n = CSRStorage(1, description="AT86RF215 reset (active low)")
        self.irq_status = CSRStatus(1, description="AT86RF215 IRQ status")

    def connect_pads(self, pads):
        """Connect reset and IRQ signals to pads"""
        self.comb += [
            pads.rst_n.eq(self.rst_n.storage),
            self.irq_status.status.eq(pads.irq),
        ]


# Register definitions for AT86RF215
# These match the AT86RF215 datasheet

# RF09 (Sub-GHz) Register Addresses
RF09_IRQS = 0x0000      # Interrupt Status
RF09_STATE = 0x0002     # State
RF09_CMD = 0x0003       # Command
RF09_CS = 0x0004        # Channel Spacing
RF09_CCF0L = 0x0005     # Channel Center Frequency Low
RF09_CCF0H = 0x0006     # Channel Center Frequency High
RF09_CNL = 0x0007       # Channel Number Low
RF09_CNM = 0x0008       # Channel Number Middle
RF09_RXBWC = 0x0009     # RX Bandwidth Control
RF09_RXDFE = 0x000A     # RX Digital Frontend
RF09_AGCC = 0x000B      # AGC Control
RF09_AGCS = 0x000C      # AGC Status
RF09_RSSI = 0x000D      # RSSI
RF09_EDC = 0x000E       # Energy Detection Configuration
RF09_EDD = 0x000F       # Energy Detection Data
RF09_EDV = 0x0010       # Energy Detection Average

# RF24 (2.4GHz) Register Addresses (offset by 0x100)
RF24_IRQS = 0x0100
RF24_STATE = 0x0102
RF24_CMD = 0x0103
RF24_CS = 0x0104
RF24_CCF0L = 0x0105
RF24_CCF0H = 0x0106
RF24_CNL = 0x0107
RF24_CNM = 0x0108
RF24_RXBWC = 0x0109
RF24_RXDFE = 0x010A
RF24_AGCC = 0x010B
RF24_AGCS = 0x010C
RF24_RSSI = 0x010D
RF24_EDC = 0x010E
RF24_EDD = 0x010F
RF24_EDV = 0x0110

# Command Codes
CMD_NOP = 0x00          # No operation
CMD_SLEEP = 0x01        # Sleep mode
CMD_TRXOFF = 0x02       # Transceiver off
CMD_TXPREP = 0x03       # TX prepare
CMD_TX = 0x04           # Transmit
CMD_RX = 0x05           # Receive
CMD_TRANSITION = 0x06   # State transition
CMD_RESET = 0x07        # Reset

# State Values
STATE_TRXOFF = 0x02
STATE_TXPREP = 0x03
STATE_TX = 0x04
STATE_RX = 0x05
STATE_TRANSITION = 0x06
STATE_RESET = 0x07
