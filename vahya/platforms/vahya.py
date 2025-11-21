"""
Vahya Platform Definition (LiteX/Migen wrapper)

Based on Vahya v1.0b hardware:
- FPGA: Lattice ECP5 LFE5U-25F-7BG256C
- USB PHY: USB3343 ULPI (High-Speed USB 2.0)
- Flash: SPI Flash (onboard ECP5 configuration flash)
- RF Transceiver: AT86RF215 (Sub-GHz/2.4GHz dual-band) - EXTERNAL
- GPS Frontend: MAX2771 (Multi-GNSS receiver) - EXTERNAL
- Clock: 26 MHz oscillator

Note: This is a LiteX/Migen platform wrapper. The native Amaranth platform
is in the main repository. Pin assignments for AT86RF215 and MAX2771 are
placeholders and must be verified against actual hardware connections.
"""

from migen import *
from litex.build.generic_platform import *
from litex.build.lattice import LatticePlatform
from litex.build.lattice.programmer import OpenOCDJTAGProgrammer

# IOs ---------------------------------------------------------------------

_io = [
    # Clocking (26 MHz main oscillator)
    ("clk26", 0, Pins("J14"), IOStandard("LVCMOS33")),

    # RGB LED (common anode)
    ("rgb_led", 0,
        Subsignal("r", Pins("B13"), IOStandard("LVCMOS33")),
        Subsignal("g", Pins("B14"), IOStandard("LVCMOS33")),
        Subsignal("b", Pins("B12"), IOStandard("LVCMOS33")),
    ),

    # User switch
    ("user_sw", 0, Pins("N6"), IOStandard("LVCMOS33")),

    # ULPI USB PHY (USB3343) - Actual Vahya v1.0b pinout
    ("ulpi", 0,
        Subsignal("data",  Pins("G1 F2 F1 E2 E1 D1 C2 C1"), IOStandard("LVCMOS33")),
        Subsignal("clk",   Pins("K1"), IOStandard("LVCMOS33")),  # 60 MHz from PHY
        Subsignal("dir",   Pins("J5"), IOStandard("LVCMOS33")),
        Subsignal("nxt",   Pins("G2"), IOStandard("LVCMOS33")),
        Subsignal("stp",   Pins("J4"), IOStandard("LVCMOS33")),
        Subsignal("rst",   Pins("H2"), IOStandard("LVCMOS33")),  # Active low
    ),

    # SPI Flash (Quad SPI) - TODO: Verify pin assignments
    ("spiflash4x", 0,
        Subsignal("cs_n", Pins("N8")),
        Subsignal("clk",  Pins("N9")),
        Subsignal("dq",   Pins("T8 T7 M7 N7")),
        IOStandard("LVCMOS33")
    ),

    # =====================================================================
    # EXTERNAL PERIPHERALS - Pin assignments are PLACEHOLDERS
    # These must be verified against actual hardware connections!
    # =====================================================================

    # AT86RF215 RF Transceiver Interface
    # Dual-band RF transceiver (Sub-GHz + 2.4GHz)
    # NOTE: These pins are placeholders and must be updated!
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
    # NOTE: These pins are placeholders and must be updated!
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

    # =====================================================================
    # Optional peripherals (if available on expansion connector)
    # =====================================================================

    # I2C (for peripheral configuration/control)
    # NOTE: Verify these pins are available!
    ("i2c", 0,
        Subsignal("scl", Pins("R7")),
        Subsignal("sda", Pins("T7")),
        IOStandard("LVCMOS33")
    ),

    # Additional SPI buses for expansion
    # NOTE: Verify these pins are available!
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
    # NOTE: Verify these pins are available!
    ("serial", 0,
        Subsignal("tx", Pins("J8")),
        Subsignal("rx", Pins("K8")),
        IOStandard("LVCMOS33")
    ),

    ("serial", 1,
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
    """Vahya Platform - ECP5 based SDR and GNSS platform (LiteX wrapper)"""

    default_clk_name   = "clk26"
    default_clk_period = 1e9/26e6  # 26 MHz

    def __init__(self, device="LFE5U-25F", toolchain="trellis", **kwargs):
        assert device in ["LFE5U-25F", "LFE5U-45F"]
        LatticePlatform.__init__(
            self,
            device + "-7BG256C",  # Updated to match actual part (speed grade 7)
            _io,
            _connectors,
            toolchain=toolchain,
            **kwargs
        )

    def create_programmer(self):
        """
        Returns OpenOCD programmer for JTAG.
        Note: Vahya v1.0b uses FTP/MicroPython programming. This is for
        direct JTAG access if available.
        """
        return OpenOCDJTAGProgrammer("openocd_ecp5.cfg")

    def do_finalize(self, fragment):
        LatticePlatform.do_finalize(self, fragment)

        # Timing constraints
        self.add_period_constraint(self.lookup_request("clk26", loose=True), 1e9/26e6)

        # USB ULPI clock (60 MHz from PHY)
        self.add_period_constraint(self.lookup_request("ulpi:clk", loose=True), 1e9/60e6)

        # MAX2771 sample clock (~16 MHz, varies with config)
        # Only add if MAX2771 is actually requested
        try:
            self.add_period_constraint(self.lookup_request("max2771:clkout", loose=True), 1e9/16.368e6)
        except:
            pass  # MAX2771 not used

    def get_flash_module(self):
        """Return SPI flash module info"""
        from litespi.modules import S25FL064L
        return S25FL064L(Codes.READ_1_1_4)
