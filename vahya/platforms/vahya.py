"""
Vahya Platform Definition (LiteX/Migen wrapper)

Based on Vahya MINI hardware (verified from VAHYA_MINI_SCH.PDF Rev. 4/01/2025):
- FPGA: Lattice ECP5 LFE5U-25F-7BG256I (256-ball BGA, Speed Grade -7)
- USB PHY: USB3343-CP ULPI (High-Speed USB 2.0)
- Flash: W25Q32JVSSIQ Quad SPI Flash (32 Mbit)
- RF Transceiver: AT86RF215M (Sub-GHz/2.4GHz dual-band) - Sheet 3
- GNSS Frontend: MAX2771ETI+ (Multi-GNSS receiver) - Sheet 4
- MCU: ESP32-S3FH4R2 (WiFi/BT, FPGA programming) - Sheet 7
- SD Card: MicroSD slot with 4-bit interface - Sheet 8
- Clock: 26 MHz oscillator (Y2: ECS-TXO-32CSMV-260-AN-TR)
- Power: 3.3V/2.5V/1.1V rails from TLV62569 buck regulators

Pin Assignments:
✅ VERIFIED: USB ULPI, RGB LED, User Switch, Clock, SD Card, ESP32 interface, JTAG
⚠️ EXTERNAL PERIPHERALS: AT86RF215 and MAX2771 pins verified from schematic

Note: This is a LiteX/Migen platform wrapper. The native Amaranth platform
is in the main repository.
"""

from migen import *
from litex.build.generic_platform import *
from litex.build.lattice import LatticePlatform
from litex.build.lattice.programmer import OpenOCDJTAGProgrammer

# IOs ---------------------------------------------------------------------

_io = [
    # =====================================================================
    # Core System - VERIFIED ✅
    # =====================================================================

    # Clocking (26 MHz main oscillator from Y2)
    ("clk26", 0, Pins("C7"), IOStandard("LVCMOS33")),  # PT27A/PCLKC0_1, BANK 0

    # RGB LED (active high, sink via resistors)
    ("rgb_led", 0,
        Subsignal("r", Pins("B13"), IOStandard("LVCMOS33")),  # PT60A, BANK 1
        Subsignal("g", Pins("B14"), IOStandard("LVCMOS33")),  # PT67A, BANK 1
        Subsignal("b", Pins("B12"), IOStandard("LVCMOS33")),  # PT56B, BANK 1
    ),

    # User switch (active low, has pull-up)
    ("user_sw", 0, Pins("N6"), IOStandard("LVCMOS33")),  # PL47B, BANK 6

    # ULPI USB PHY (USB3343-CP) - BANK 7
    ("ulpi", 0,
        Subsignal("data",  Pins("G1 F2 F1 E2 E1 D1 C2 C1"), IOStandard("LVCMOS33")),
        Subsignal("clk",   Pins("K1"), IOStandard("LVCMOS33")),  # 60 MHz from PHY
        Subsignal("dir",   Pins("J5"), IOStandard("LVCMOS33")),
        Subsignal("nxt",   Pins("G2"), IOStandard("LVCMOS33")),
        Subsignal("stp",   Pins("J4"), IOStandard("LVCMOS33")),
        Subsignal("rst",   Pins("H2"), IOStandard("LVCMOS33")),  # Active low
    ),

    # Quad SPI Flash (W25Q32JVSSIQ, 32 Mbit) - BANK 8
    ("spiflash4x", 0,
        Subsignal("cs_n", Pins("R8"), IOStandard("LVCMOS33")),  # PB13A/SN/CSN
        Subsignal("clk",  Pins("N9"), IOStandard("LVCMOS33")),  # CCLK/MCLK/SCK
        Subsignal("dq",   Pins("T8 T7 N7 M7"), IOStandard("LVCMOS33")),  # D0 D1 D2 D3
    ),

    # SD Card Interface (MicroSD, 4-bit mode) - BANK 1
    ("sdcard", 0,
        Subsignal("data", Pins("A12 A13 A9 A10"), IOStandard("LVCMOS33")),  # DAT0-3
        Subsignal("cmd",  Pins("A11"), IOStandard("LVCMOS33")),
        Subsignal("clk",  Pins("B8"), IOStandard("LVCMOS33")),
        Subsignal("cd",   Pins("B10"), IOStandard("LVCMOS33")),  # Card detect
    ),

    # ESP32-S3 Interface - BANK 0
    ("esp32", 0,
        Subsignal("gpio6", Pins("A2"), IOStandard("LVCMOS33")),  # PT4A
        Subsignal("gpio7", Pins("A3"), IOStandard("LVCMOS33")),  # PT6A
        Subsignal("gpio8", Pins("A6"), IOStandard("LVCMOS33")),  # PT18B
        Subsignal("gpio9", Pins("A7"), IOStandard("LVCMOS33")),  # PT29A/PCLKT0_0
    ),

    # JTAG Interface (shared with ESP32) - BANK 8
    ("jtag", 0,
        Subsignal("tdo", Pins("M10"), IOStandard("LVCMOS33")),
        Subsignal("tck", Pins("T10"), IOStandard("LVCMOS33")),
        Subsignal("tdi", Pins("R11"), IOStandard("LVCMOS33")),
        Subsignal("tms", Pins("T11"), IOStandard("LVCMOS33")),
    ),

    # =====================================================================
    # EXTERNAL PERIPHERALS - Verified from Schematic ✅
    # =====================================================================

    # AT86RF215 RF Transceiver Interface (Sheet 3)
    # Dual-band RF transceiver (Sub-GHz @ 389-1088MHz + 2.4GHz @ 2400-2483.5MHz)
    # NOTE: Uses differential LVDS signaling for high-speed data
    ("at86rf215_ctrl", 0,
        # SPI Control Interface - BANK 2
        Subsignal("sclk",  Pins("K14"), IOStandard("LVCMOS33")),  # PR20D
        Subsignal("mosi",  Pins("H14"), IOStandard("LVCMOS33")),  # PR14D
        Subsignal("miso",  Pins("F16"), IOStandard("LVCMOS33")),  # PR14A
        Subsignal("sel_n", Pins("E16"), IOStandard("LVCMOS33")),  # PR11D
        Subsignal("rst_n", Pins("C14"), IOStandard("LVCMOS33")),  # PR2C
        Subsignal("irq",   Pins("G16"), IOStandard("LVCMOS33")),  # PR20A/GR_PCLK2_1
    ),

    # AT86RF215 Data Interface (LVDS differential pairs)
    # Baseband I/Q data @ up to 4 MSPS (14-bit samples)
    ("at86rf215_data", 0,
        # TX Interface (FPGA → AT86RF215) - BANKS 1/2
        Subsignal("txclk_p",  Pins("B16"), IOStandard("LVDS")),  # PT35A/PCLKT1_0
        Subsignal("txclk_n",  Pins("B15"), IOStandard("LVDS")),  # PR2B/S0_IN
        Subsignal("txd_p",    Pins("C16"), IOStandard("LVDS")),  # PT33A/PCLKT1_1
        Subsignal("txd_n",    Pins("C15"), IOStandard("LVDS")),  # PR5B

        # RX Interface RF09 (Sub-GHz) (AT86RF215 → FPGA) - BANKS 1/2
        Subsignal("rxd09_p",  Pins("D16"), IOStandard("LVDS")),  # PT40A
        Subsignal("rxd09_n",  Pins("E15"), IOStandard("LVDS")),  # PR8B

        # RX Interface RF24 (2.4GHz) (AT86RF215 → FPGA) - BANK 2
        Subsignal("rxd24_p",  Pins("K16"), IOStandard("LVDS")),  # PR23C/PCLKT2_0
        Subsignal("rxd24_n",  Pins("K15"), IOStandard("LVDS")),  # PR23D/PCLKC2_0

        # RX Clock (from AT86RF215) - BANK 2
        Subsignal("rxclk_p",  Pins("J16"), IOStandard("LVDS")),  # PR23A/PCLKT2_1
        Subsignal("rxclk_n",  Pins("J15"), IOStandard("LVDS")),  # PR23B/PCLKC2_1

        # NOTE: Clock output from AT86RF215 available on J14 (U.FL)
        # Can be connected to FPGA for synchronization if needed
    ),

    # MAX2771 GNSS Frontend (Sheet 4)
    # Multi-GNSS receiver frontend (GPS L1, Galileo E1, GLONASS L1, BeiDou B1)
    # 2-bit I/Q ADC output @ 16.368 MHz sample rate
    ("max2771_ctrl", 0,
        # 3-wire SPI Interface - BANK 3
        Subsignal("sdata", Pins("R15"), IOStandard("LVCMOS33")),  # PR38C (bidirectional)
        Subsignal("sclk",  Pins("T14"), IOStandard("LVCMOS33")),  # PR41D
        Subsignal("cs_n",  Pins("R14"), IOStandard("LVCMOS33")),  # PR41B
        # Control
        Subsignal("shdn",  Pins("R16"), IOStandard("LVCMOS33")),  # PR35B/VREF1_3
        Subsignal("ld",    Pins("K13"), IOStandard("LVCMOS33")),  # PR29A/GR_PCLK3_0 (Lock Detect)
    ),

    # MAX2771 ADC Data Interface (2-bit sign-magnitude I/Q)
    ("max2771_adc", 0,
        # ADC Outputs - BANK 3
        Subsignal("i0",     Pins("P14"), IOStandard("LVCMOS33")),  # PR38B (I bit 0)
        Subsignal("i1",     Pins("P15"), IOStandard("LVCMOS33")),  # PR32A (I bit 1)
        Subsignal("q0",     Pins("P13"), IOStandard("LVCMOS33")),  # PR41A (Q bit 0)
        Subsignal("q1",     Pins("P12"), IOStandard("LVCMOS33")),  # PR44A (Q bit 1)
        # Sample Clock Output (~16.368 MHz from MAX2771)
        Subsignal("clkout", Pins("M16"), IOStandard("LVCMOS33")),  # PR26C/PCLKT3_0

        # NOTE: Antenna connected to J13 (U.FL) via RF matching network
        # Reference clock (16.368 MHz) from Y4 oscillator on MAX2771 module
    ),
]

# Connectors ---------------------------------------------------------------

_connectors = [
    # Expansion Headers (J3 and J4 - 2x8 SMD headers on PCB)
    # These expose various FPGA pins for custom peripherals
    # See FPGA_PIN_MAP.md for detailed pin assignments
    ("j3", {
        # J3 pins (2x8 SMD header) - BANK 1 and BANK 3 pins
        1:  "C8",   # BANK1_PT35A
        2:  "D8",   # BANK1_PT33B
        3:  "C9",   # BANK1_PT38B
        4:  "D9",   # BANK1_PT40A
        5:  "C10",  # BANK1_PT44B
        6:  "D10",  # BANK1_PT47A
        7:  "C11",  # BANK1_PT49B
        8:  "D11",  # BANK1_PT51A
        9:  "C12",  # BANK1_PT56B
        10: "D12",  # BANK1_PT58A
        11: "C13",  # BANK1_PT60B
        12: "D13",  # BANK1_PT62A
        13: "GND",
        14: "GND",
        15: "+3V3",
        16: "+3V3",
    }),
    ("j4", {
        # J4 pins (2x8 SMD header) - BANK 2 and BANK 3 pins
        1:  "G15",  # BANK2_PR14B
        2:  "H14",  # BANK2_PR14D (also AT86_MOSI)
        3:  "H13",  # BANK2_PR17B
        4:  "J13",  # BANK2_PR17C
        5:  "J12",  # BANK2_PR17D
        6:  "K12",  # BANK3_PR29B
        7:  "L13",  # BANK3_PR29C
        8:  "L14",  # BANK3_PR32C
        9:  "M14",  # BANK3_PR32D
        10: "M13",  # BANK3_PR35C
        11: "N14",  # BANK3_PR35D
        12: "N13",  # BANK3_PR38A
        13: "GND",
        14: "GND",
        15: "+5V0",
        16: "+5V0",
    }),
]

# Platform -----------------------------------------------------------------

class Platform(LatticePlatform):
    """Vahya MINI Platform - ECP5 based SDR and GNSS platform (LiteX wrapper)"""

    default_clk_name   = "clk26"
    default_clk_period = 1e9/26e6  # 26 MHz

    def __init__(self, device="LFE5U-25F", toolchain="trellis", **kwargs):
        """
        Initialize Vahya MINI platform.

        Args:
            device: FPGA variant - "LFE5U-25F" (default) or "LFE5U-45F"
            toolchain: "trellis" (open-source) or "diamond" (Lattice proprietary)
        """
        assert device in ["LFE5U-25F", "LFE5U-45F"]
        LatticePlatform.__init__(
            self,
            device + "-7BG256I",  # Industrial grade (-40°C to +100°C), Speed Grade -7
            _io,
            _connectors,
            toolchain=toolchain,
            **kwargs
        )

    def create_programmer(self):
        """
        Returns OpenOCD programmer for JTAG.

        Note: Vahya MINI uses ESP32-S3 for FPGA programming via JTAG.
        This programmer definition is for direct external JTAG access if needed.
        """
        return OpenOCDJTAGProgrammer("openocd_ecp5.cfg")

    def do_finalize(self, fragment):
        """Add timing constraints for all clock domains"""
        LatticePlatform.do_finalize(self, fragment)

        # Main system clock (26 MHz oscillator)
        self.add_period_constraint(self.lookup_request("clk26", loose=True), 1e9/26e6)

        # USB ULPI clock (60 MHz from USB3343 PHY)
        self.add_period_constraint(self.lookup_request("ulpi", loose=True).clk, 1e9/60e6)

        # AT86RF215 RX clock (variable, up to 4 MHz)
        # Only add if AT86RF215 is actually requested
        try:
            at86_data = self.lookup_request("at86rf215_data", loose=True)
            if at86_data:
                # RX clock is differential LVDS, varies with sample rate
                # Maximum is 4 MSPS × 2 (I+Q) = 8 MHz DDR = 4 MHz clock
                self.add_period_constraint(at86_data.rxclk_p, 1e9/4e6)
        except:
            pass  # AT86RF215 not used

        # MAX2771 ADC sample clock (~16.368 MHz from MAX2771)
        # Only add if MAX2771 is actually requested
        try:
            max_adc = self.lookup_request("max2771_adc", loose=True)
            if max_adc:
                self.add_period_constraint(max_adc.clkout, 1e9/16.368e6)
        except:
            pass  # MAX2771 not used

    def get_flash_module(self):
        """
        Return SPI flash module info for configuration flash.

        Flash: W25Q32JVSSIQ (Winbond 32 Mbit Quad SPI)
        """
        from litespi.modules import W25Q32JV
        from litespi.opcodes import SpiNorFlashOpCodes as Codes
        return W25Q32JV(Codes.READ_1_1_4)
