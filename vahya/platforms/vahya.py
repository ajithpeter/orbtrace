"""
Vahya Platform Definition

Hardware Specifications:
- FPGA: Lattice ECP5 (LFE5U-25F or LFE5U-45F)
- USB PHY: USB3343 ULPI (High-Speed USB 2.0)
- Flash: SPI Flash (8-32 MB)
- RF Transceiver: AT86RF215 (Sub-GHz/2.4GHz dual-band)
- GPS Frontend: MAX2771 (Multi-GNSS receiver)
- Clock: 30 MHz oscillator
"""

from migen import *
from litex.build.generic_platform import *
from litex.build.lattice import LatticePlatform
from litex.build.lattice.programmer import OpenOCDJTAGProgrammer

# IOs ---------------------------------------------------------------------

_io = [
    # Clocking
    ("clk30", 0, Pins("L16"), IOStandard("LVCMOS33")),

    # LEDs (assuming 4 user LEDs)
    ("user_led", 0, Pins("N12"), IOStandard("LVCMOS33")),
    ("user_led", 1, Pins("P12"), IOStandard("LVCMOS33")),
    ("user_led", 2, Pins("R12"), IOStandard("LVCMOS33")),
    ("user_led", 3, Pins("T12"), IOStandard("LVCMOS33")),

    # Serial (UART) - Primary debug interface
    ("serial", 0,
        Subsignal("tx", Pins("C11")),
        Subsignal("rx", Pins("A10")),
        IOStandard("LVCMOS33")
    ),

    # ULPI USB PHY (USB3343)
    ("ulpi", 0,
        Subsignal("rst_n",  Pins("T4"), IOStandard("LVCMOS33")),
        Subsignal("clk_o",  Pins("R5"), IOStandard("LVCMOS33")),  # 60 MHz from PHY
        Subsignal("dir",    Pins("T3"), IOStandard("LVCMOS33")),
        Subsignal("nxt",    Pins("R3"), IOStandard("LVCMOS33")),
        Subsignal("stp",    Pins("R4"), IOStandard("LVCMOS33")),
        Subsignal("data",   Pins("T2 R2 R1 P2 P1 N1 M2 M1"), IOStandard("LVCMOS33")),
    ),

    # SPI Flash (Quad SPI)
    ("spiflash4x", 0,
        Subsignal("cs_n", Pins("N8")),
        Subsignal("clk",  Pins("N9")),
        Subsignal("dq",   Pins("T8 T7 M7 N7")),
        IOStandard("LVCMOS33")
    ),

    # AT86RF215 RF Transceiver Interface
    # Dual-band RF transceiver (Sub-GHz + 2.4GHz)
    ("at86rf215", 0,
        # SPI Interface
        Subsignal("spi_clk",  Pins("A2"), IOStandard("LVCMOS33")),
        Subsignal("spi_mosi", Pins("A3"), IOStandard("LVCMOS33")),
        Subsignal("spi_miso", Pins("B3"), IOStandard("LVCMOS33")),
        Subsignal("spi_cs_n", Pins("C3"), IOStandard("LVCMOS33")),

        # Control/Status
        Subsignal("rst_n",    Pins("D3"), IOStandard("LVCMOS33")),
        Subsignal("irq",      Pins("E3"), IOStandard("LVCMOS33")),  # Interrupt

        # I/Q Data Interface (14-bit parallel baseband)
        # Sub-GHz band (RF09)
        Subsignal("rf09_txiq", Pins("F3 G3 H3 J3 K3 L3 M3 N3 P3 R3 T3 A4 B4 C4"),
                  IOStandard("LVCMOS33")),
        Subsignal("rf09_rxiq", Pins("D4 E4 F4 G4 H4 J4 K4 L4 M4 N4 P4 R4 T4 A5"),
                  IOStandard("LVCMOS33")),
        Subsignal("rf09_txen", Pins("B5"), IOStandard("LVCMOS33")),
        Subsignal("rf09_rxen", Pins("C5"), IOStandard("LVCMOS33")),

        # 2.4GHz band (RF24)
        Subsignal("rf24_txiq", Pins("D5 E5 F5 G5 H5 J5 K5 L5 M5 N5 P5 R5 T5 A6"),
                  IOStandard("LVCMOS33")),
        Subsignal("rf24_rxiq", Pins("B6 C6 D6 E6 F6 G6 H6 J6 K6 L6 M6 N6 P6 R6"),
                  IOStandard("LVCMOS33")),
        Subsignal("rf24_txen", Pins("T6"), IOStandard("LVCMOS33")),
        Subsignal("rf24_rxen", Pins("A7"), IOStandard("LVCMOS33")),

        # Clocking
        Subsignal("clk_26mhz", Pins("B7"), IOStandard("LVCMOS33")),  # 26 MHz reference
    ),

    # MAX2771 GNSS Frontend
    ("max2771", 0,
        # SPI Interface
        Subsignal("spi_clk",  Pins("C7"), IOStandard("LVCMOS33")),
        Subsignal("spi_mosi", Pins("D7"), IOStandard("LVCMOS33")),
        Subsignal("spi_miso", Pins("E7"), IOStandard("LVCMOS33")),
        Subsignal("spi_cs_n", Pins("F7"), IOStandard("LVCMOS33")),

        # Control
        Subsignal("idle",     Pins("G7"), IOStandard("LVCMOS33")),  # Low-power mode
        Subsignal("shdn",     Pins("H7"), IOStandard("LVCMOS33")),  # Shutdown

        # ADC Data Interface (2-bit I + 2-bit Q)
        Subsignal("iq_sign",  Pins("J7"), IOStandard("LVCMOS33")),  # I sign bit
        Subsignal("iq_mag",   Pins("K7"), IOStandard("LVCMOS33")),  # I magnitude bit
        Subsignal("qq_sign",  Pins("L7"), IOStandard("LVCMOS33")),  # Q sign bit
        Subsignal("qq_mag",   Pins("M7"), IOStandard("LVCMOS33")),  # Q magnitude bit

        # Clock (output from MAX2771)
        Subsignal("clkout",   Pins("N7"), IOStandard("LVCMOS33")),  # Sample clock (~16 MHz)

        # Reference clock input (usually 16.368 MHz)
        Subsignal("clk_ref",  Pins("P7"), IOStandard("LVCMOS33")),
    ),

    # I2C (for peripheral configuration/control)
    ("i2c", 0,
        Subsignal("scl", Pins("R7")),
        Subsignal("sda", Pins("T7")),
        IOStandard("LVCMOS33")
    ),

    # Additional SPI buses for expansion
    ("spi", 0,
        Subsignal("clk",  Pins("A8")),
        Subsignal("mosi", Pins("B8")),
        Subsignal("miso", Pins("C8")),
        Subsignal("cs_n", Pins("D8")),
        IOStandard("LVCMOS33")
    ),

    ("spi", 1,
        Subsignal("clk",  Pins("E8")),
        Subsignal("mosi", Pins("F8")),
        Subsignal("miso", Pins("G8")),
        Subsignal("cs_n", Pins("H8")),
        IOStandard("LVCMOS33")
    ),

    # Additional UARTs
    ("serial", 1,
        Subsignal("tx", Pins("J8")),
        Subsignal("rx", Pins("K8")),
        IOStandard("LVCMOS33")
    ),

    ("serial", 2,
        Subsignal("tx", Pins("L8")),
        Subsignal("rx", Pins("M8")),
        IOStandard("LVCMOS33")
    ),

    # GPIO expansion
    ("gpio", 0, Pins("N8 P8 R8 T8 A9 B9 C9 D9"), IOStandard("LVCMOS33")),
]

# Connectors ---------------------------------------------------------------

_connectors = [
    # Expansion connector
    ("exp", "E9 F9 G9 H9 J9 K9 L9 M9 N9 P9 R9 T9"),
]

# Platform -----------------------------------------------------------------

class Platform(LatticePlatform):
    """Vahya Platform - ECP5 based SDR and GNSS platform"""

    default_clk_name   = "clk30"
    default_clk_period = 1e9/30e6  # 30 MHz

    def __init__(self, device="LFE5U-25F", toolchain="trellis", **kwargs):
        assert device in ["LFE5U-25F", "LFE5U-45F"]
        LatticePlatform.__init__(
            self,
            device + "-8BG256C",
            _io,
            _connectors,
            toolchain=toolchain,
            **kwargs
        )

    def create_programmer(self):
        return OpenOCDJTAGProgrammer("openocd_ecp5.cfg")

    def do_finalize(self, fragment):
        LatticePlatform.do_finalize(self, fragment)

        # Timing constraints
        self.add_period_constraint(self.lookup_request("clk30", loose=True), 1e9/30e6)

        # USB ULPI clock (60 MHz from PHY)
        self.add_period_constraint(self.lookup_request("ulpi:clk_o", loose=True), 1e9/60e6)

        # MAX2771 sample clock (~16 MHz, varies with config)
        self.add_period_constraint(self.lookup_request("max2771:clkout", loose=True), 1e9/16.368e6)

    def get_flash_module(self):
        """Return SPI flash module info"""
        from litespi.modules import S25FL064L
        return S25FL064L(Codes.READ_1_1_4)
