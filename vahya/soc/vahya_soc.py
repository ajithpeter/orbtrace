"""
Vahya SoC - SDR and GNSS Platform

Main SoC integrating:
- VexRiscv RISC-V processor
- Multiple UART/SPI/I2C peripherals
- AT86RF215 dual-band RF transceiver
- MAX2771 GNSS frontend
- USB bulk streaming via LUNA
- DFU bootloader support
"""

from migen import *

from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores.clock import *
from litex.soc.cores.led import LedChaser

# LiteX peripherals
from litex.soc.cores.spi import SPIMaster
from litex.soc.cores.bitbang import I2CMaster
from litex.soc.cores.uart import UART, UARTWishbone

# Import platform
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from platforms.vahya import Platform

# USB and DFU support
from orbtrace.amaranth_glue.wrapper import Wrapper
from orbtrace.amaranth_glue.luna import USBDevice, USBStreamInEndpoint, USBStreamOutEndpoint
from orbtrace.amaranth_glue.dfu import DFUHandler
from orbtrace.usb_allocator import USBAllocator
from orbtrace.dfu import DFUHandler as DFUHandlerAmaranth
from orbtrace.usb_serialnumber import USBSerialNumberHandler
from orbtrace.cdc_acm import ACMRequestHandler
from orbtrace.flash_uid import FlashUID

# Import peripheral drivers (to be created)
# from vahya.peripherals.at86rf215 import AT86RF215
# from vahya.peripherals.max2771 import MAX2771


# CRG -----------------------------------------------------------------------

class _CRG(Module):
    """Clock and Reset Generator for Vahya"""
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.clock_domains.cd_sys    = ClockDomain()
        self.clock_domains.cd_sys2x  = ClockDomain()
        self.clock_domains.cd_usb    = ClockDomain()
        self.clock_domains.cd_por    = ClockDomain(reset_less=True)

        # Get clocks
        clk30 = platform.request("clk30")

        # Power-on reset
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(clk30)
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL for system clocks
        self.submodules.pll = pll = ECP5PLL()
        self.comb += pll.reset.eq(~por_done | self.rst)
        pll.register_clkin(clk30, 30e6)
        pll.create_clkout(self.cd_sys,   sys_clk_freq)
        pll.create_clkout(self.cd_sys2x, 2*sys_clk_freq)
        pll.create_clkout(self.cd_usb,   60e6)  # USB requires 60 MHz

        # Reset synchronization
        self.specials += [
            AsyncResetSynchronizer(self.cd_sys,  ~pll.locked | self.rst),
            AsyncResetSynchronizer(self.cd_usb,  ~pll.locked | self.rst),
        ]


# VahyaSoC ------------------------------------------------------------------

class VahyaSoC(SoCCore):
    """Vahya SoC with RISC-V processor and RF peripherals"""

    def __init__(self, sys_clk_freq=int(75e6), with_led_chaser=True,
                 with_dfu=False, with_usb_stream=True,
                 usb_vid=0x1209, usb_pid=0x5070, **kwargs):

        platform = Platform()

        # SoCCore initialization (with VexRiscv CPU)
        SoCCore.__init__(self, platform, sys_clk_freq,
            ident          = "Vahya SoC - SDR/GNSS Platform",
            cpu_type       = "vexriscv",
            cpu_variant    = "lite",  # Can upgrade to "standard" for more performance
            integrated_rom_size  = 0x8000,   # 32KB ROM
            integrated_sram_size = 0x2000,   # 8KB SRAM (more in external memory)
            **kwargs
        )

        # Clock Reset Generator
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # LED Chaser for status indication
        if with_led_chaser:
            self.submodules.leds = LedChaser(
                pads         = platform.request_all("user_led"),
                sys_clk_freq = sys_clk_freq
            )

        # Flash UID for USB serial number
        self.submodules.flash_uid = FlashUID(uid_bytes=8)

        # Amaranth-Migen wrapper
        self.add_wrapper()

        # Add SPI Flash controller
        self.add_spi_flash()

        # Add USB device
        if with_usb_stream or with_dfu:
            self.add_usb(usb_vid, usb_pid, with_dfu)

        # Add multiple UARTs
        self.add_uarts()

        # Add SPI masters for peripherals
        self.add_spi_masters()

        # Add I2C master
        self.add_i2c()

        # Add AT86RF215 interface
        self.add_at86rf215()

        # Add MAX2771 interface
        self.add_max2771()

    def add_wrapper(self):
        """Add Amaranth-Migen wrapper for USB stack"""
        self.submodules.wrapper = Wrapper(self.platform, 'vahya_usb_wrapper')
        self.wrapper.connect_domain('sys')

    def add_spi_flash(self):
        """Add SPI Flash controller with memory mapping"""
        from litespi.modules import S25FL064L
        from litespi.opcodes import SpiNorFlashOpCodes as Codes
        from litespi.phy.generic import LiteSPIPHY
        from litespi import LiteSPI

        flash = S25FL064L(Codes.READ_1_1_4)

        # SPI PHY
        self.submodules.spiflash_phy = LiteSPIPHY(
            pads  = self.platform.request("spiflash4x"),
            flash = flash,
            device = self.platform.device,
        )

        # Memory-mapped SPI Flash
        self.submodules.spiflash_mmap = LiteSPI(
            phy = self.spiflash_phy,
            mmap_endianness = self.cpu.endianness,
        )

        # Add CSR
        self.add_csr("spiflash_phy")
        self.add_csr("spiflash_mmap")

        # Create memory region
        spiflash_region = SoCRegion(
            origin = self.mem_map.get("spiflash", 0x08000000),
            size   = flash.total_size,
            mode   = "r"
        )
        self.bus.add_slave(
            name   = "spiflash",
            slave  = self.spiflash_mmap.bus,
            region = spiflash_region
        )

    def add_usb(self, vid, pid, with_dfu):
        """Add USB device with LUNA stack"""
        self.wrapper.connect_domain('usb')

        # USB allocator for managing interfaces
        usb_allocator = USBAllocator()

        # USB device
        ulpi_pads = self.platform.request("ulpi")
        self.submodules.usb = USBDevice(ulpi_pads, wrapper=self.wrapper)

        # USB descriptors
        from usb_protocol.emitters.descriptors import DeviceDescriptorCollection
        self.usb_descriptors = descriptors = DeviceDescriptorCollection()

        # Device descriptor
        with descriptors.DeviceDescriptor() as d:
            d.idVendor           = vid
            d.idProduct          = pid
            d.bcdUSB             = 2.1  # USB 2.1 (BOS descriptor support)
            d.bcdDevice          = 0x0100
            d.iManufacturer      = "Vahya"
            d.iProduct           = "SDR/GNSS Platform"
            d.iSerialNumber      = "N/A"  # Overridden by handler
            d.bNumConfigurations = 1

        # Configuration descriptor
        with descriptors.ConfigurationDescriptor() as c:
            self.usb_conf_desc = c

            # Add CDC-ACM serial port
            self.add_usb_uart(usb_allocator)

            # Add DFU interface if requested
            if with_dfu:
                self.add_dfu(usb_allocator)

            # Add bulk streaming interfaces
            self.add_usb_streaming(usb_allocator)

        # Add request handlers
        self.usb_control_handlers = []

        # Serial number handler
        serial_number_handler = USBSerialNumberHandler(
            self.flash_uid.value,
            bits=64
        )
        self.usb_control_handlers.append(serial_number_handler)
        self.wrapper.m.submodules.usb_serial_number_handler = serial_number_handler

        # Register all handlers
        for handler in self.usb_control_handlers:
            self.usb.add_control_endpoint(handler)

        # Set descriptors
        self.usb.add_standard_control_endpoint(descriptors)

        # Windows WCID descriptors
        usb_allocator.create_microsoft_os_2_0_descriptors(descriptors, self.usb_control_handlers)

    def add_usb_uart(self, usb_allocator):
        """Add USB CDC-ACM serial port"""
        from litex.soc.cores.uart import Stream2Wishbone

        # Allocate interface
        comm_if = usb_allocator.allocate_interface()
        data_if = usb_allocator.allocate_interface()

        # Allocate endpoints
        in_ep_num_data = usb_allocator.allocate_in_endpoint()
        out_ep_num_data = usb_allocator.allocate_out_endpoint()
        in_ep_num_ctrl = usb_allocator.allocate_in_endpoint()

        # Interface Association Descriptor (for Windows)
        with self.usb_conf_desc.InterfaceAssociationDescriptor() as i:
            i.bFirstInterface = comm_if
            i.bInterfaceCount = 2
            i.bFunctionClass = 2  # CDC

        # Communication interface
        with self.usb_conf_desc.InterfaceDescriptor() as i:
            i.bInterfaceNumber   = comm_if
            i.bInterfaceClass    = 0x02  # CDC
            i.bInterfaceSubclass = 0x02  # ACM
            i.bInterfaceProtocol = 0x01  # AT commands

            # CDC functional descriptors
            i.add_subordinate_descriptor(
                bytes([5, 0x24, 0, 0x10, 0x01]))  # Header
            i.add_subordinate_descriptor(
                bytes([4, 0x24, 2, 0x06]))  # ACM
            i.add_subordinate_descriptor(
                bytes([5, 0x24, 6, comm_if, data_if]))  # Union

            with i.EndpointDescriptor() as e:
                e.bEndpointAddress = 0x80 | in_ep_num_ctrl
                e.bmAttributes     = 0x03  # Interrupt
                e.wMaxPacketSize   = 64

        # Data interface
        with self.usb_conf_desc.InterfaceDescriptor() as i:
            i.bInterfaceNumber   = data_if
            i.bInterfaceClass    = 0x0A  # CDC Data

            with i.EndpointDescriptor() as e:
                e.bEndpointAddress = 0x80 | in_ep_num_data
                e.bmAttributes     = 0x02  # Bulk
                e.wMaxPacketSize   = 512

            with i.EndpointDescriptor() as e:
                e.bEndpointAddress = out_ep_num_data
                e.bmAttributes     = 0x02  # Bulk
                e.wMaxPacketSize   = 512

        # Create endpoints
        in_ep  = USBStreamInEndpoint(endpoint_number=in_ep_num_data, wrapper=self.wrapper)
        out_ep = USBStreamOutEndpoint(endpoint_number=out_ep_num_data, wrapper=self.wrapper)

        self.wrapper.m.submodules += in_ep
        self.wrapper.m.submodules += out_ep

        self.usb.add_endpoint(in_ep)
        self.usb.add_endpoint(out_ep)

        # Connect to UART bridge
        uart = UART(None, tx_fifo_depth=512, rx_fifo_depth=512)
        self.submodules.usb_uart = uart

        # Stream connections (clock domain crossing)
        from litex.soc.interconnect.stream import ClockDomainCrossing, Pipeline

        in_cdc  = ClockDomainCrossing(in_ep.sink.description, "sys", "usb")
        out_cdc = ClockDomainCrossing(out_ep.source.description, "usb", "sys")

        self.submodules += in_cdc, out_cdc
        self.submodules.usb_uart_pipeline = Pipeline(
            out_ep, out_cdc, uart, in_cdc, in_ep
        )
        self.comb += in_ep.sink.last.eq(1)

        # ACM request handler
        acm_handler = ACMRequestHandler(comm_if)
        self.usb_control_handlers.append(acm_handler)
        self.wrapper.m.submodules.acm_handler = acm_handler

    def add_dfu(self, usb_allocator):
        """Add DFU (Device Firmware Update) support"""
        dfu_if = usb_allocator.allocate_interface()
        usb_allocator.add_dfu_interface(dfu_if)

        # DFU interface descriptor
        with self.usb_conf_desc.InterfaceDescriptor() as i:
            i.bInterfaceNumber   = dfu_if
            i.bInterfaceClass    = 0xFE  # Application Specific
            i.bInterfaceSubclass = 0x01  # DFU
            i.bInterfaceProtocol = 0x02  # DFU Mode
            i.iInterface = "DFU"

            # DFU functional descriptor
            i.add_subordinate_descriptor(bytes([
                9,      # bLength
                0x21,   # bDescriptorType (DFU FUNCTIONAL)
                0x0D,   # bmAttributes (will detach, manifestation tolerant, can upload/download)
                0xFF, 0x00,  # wDetachTimeOut
                0x00, 0x04,  # wTransferSize (1024 bytes)
                0x10, 0x01,  # bcdDFUVersion (1.1)
            ]))

        # DFU handler
        dfu_handler = DFUHandlerAmaranth(dfu_if, areas=[
            {"start": 0x000000, "length": 0x100000, "name": "bootloader"},
            {"start": 0x100000, "length": 0x700000, "name": "application"},
        ])
        self.wrapper.m.submodules.dfu_handler = dfu_handler
        self.usb_control_handlers.append(dfu_handler)

        # Connect DFU to flash writer
        # TODO: Add flash writer integration

    def add_usb_streaming(self, usb_allocator):
        """Add USB bulk streaming interfaces for RF data"""
        # AT86RF215 streaming interface (bidirectional)
        rf_if = usb_allocator.allocate_interface()
        usb_allocator.add_winusb_interface(rf_if, guid_discriminator=0x2151)

        rf_in_ep  = usb_allocator.allocate_in_endpoint()
        rf_out_ep = usb_allocator.allocate_out_endpoint()

        with self.usb_conf_desc.InterfaceDescriptor() as i:
            i.bInterfaceNumber   = rf_if
            i.bInterfaceClass    = 0xFF  # Vendor
            i.bInterfaceSubclass = 0x21  # RF
            i.bInterfaceProtocol = 0x51  # AT86RF215
            i.iInterface = "RF Transceiver Stream"

            with i.EndpointDescriptor() as e:
                e.bEndpointAddress = 0x80 | rf_in_ep
                e.bmAttributes     = 0x02  # Bulk
                e.wMaxPacketSize   = 512

            with i.EndpointDescriptor() as e:
                e.bEndpointAddress = rf_out_ep
                e.bmAttributes     = 0x02  # Bulk
                e.wMaxPacketSize   = 512

        # MAX2771 streaming interface (output only)
        gnss_if = usb_allocator.allocate_interface()
        usb_allocator.add_winusb_interface(gnss_if, guid_discriminator=0x2771)

        gnss_in_ep = usb_allocator.allocate_in_endpoint()

        with self.usb_conf_desc.InterfaceDescriptor() as i:
            i.bInterfaceNumber   = gnss_if
            i.bInterfaceClass    = 0xFF  # Vendor
            i.bInterfaceSubclass = 0x27  # GNSS
            i.bInterfaceProtocol = 0x71  # MAX2771
            i.iInterface = "GNSS Frontend Stream"

            with i.EndpointDescriptor() as e:
                e.bEndpointAddress = 0x80 | gnss_in_ep
                e.bmAttributes     = 0x02  # Bulk
                e.wMaxPacketSize   = 512

        # Create streaming endpoints
        self.usb_rf_in  = USBStreamInEndpoint(endpoint_number=rf_in_ep, wrapper=self.wrapper)
        self.usb_rf_out = USBStreamOutEndpoint(endpoint_number=rf_out_ep, wrapper=self.wrapper)
        self.usb_gnss_in = USBStreamInEndpoint(endpoint_number=gnss_in_ep, wrapper=self.wrapper)

        self.wrapper.m.submodules += [self.usb_rf_in, self.usb_rf_out, self.usb_gnss_in]

        self.usb.add_endpoint(self.usb_rf_in)
        self.usb.add_endpoint(self.usb_rf_out)
        self.usb.add_endpoint(self.usb_gnss_in)

    def add_uarts(self):
        """Add multiple UART interfaces"""
        # Primary UART already added by SoCCore

        # Additional UARTs
        for i in range(1, 3):
            uart_name = f"uart{i}"
            uart_pads = self.platform.request("serial", i)
            uart = UART(uart_pads, tx_fifo_depth=16, rx_fifo_depth=16)
            setattr(self.submodules, uart_name, uart)
            self.add_csr(uart_name)

    def add_spi_masters(self):
        """Add SPI master interfaces"""
        # SPI0 and SPI1 for general purpose
        for i in range(2):
            spi_name = f"spi{i}"
            spi_pads = self.platform.request("spi", i)
            spi = SPIMaster(spi_pads, data_width=8, sys_clk_freq=self.sys_clk_freq,
                           spi_clk_freq=int(1e6))  # 1 MHz SPI clock
            setattr(self.submodules, spi_name, spi)
            self.add_csr(spi_name)

    def add_i2c(self):
        """Add I2C master"""
        i2c_pads = self.platform.request("i2c")
        self.submodules.i2c = I2CMaster(i2c_pads)
        self.add_csr("i2c")

    def add_at86rf215(self):
        """Add AT86RF215 RF transceiver interface"""
        at86rf215_pads = self.platform.request("at86rf215")

        # SPI interface for control/configuration
        from litex.soc.cores.spi import SPIMaster
        self.submodules.at86rf215_spi = SPIMaster(
            pads={
                "clk": at86rf215_pads.spi_clk,
                "mosi": at86rf215_pads.spi_mosi,
                "miso": at86rf215_pads.spi_miso,
                "cs_n": at86rf215_pads.spi_cs_n,
            },
            data_width=8,
            sys_clk_freq=self.sys_clk_freq,
            spi_clk_freq=int(1e6)  # 1 MHz for control
        )
        self.add_csr("at86rf215_spi")

        # Control signals
        rst_n = Signal(reset=1)
        self.comb += at86rf215_pads.rst_n.eq(rst_n)

        # IRQ signal (TODO: add interrupt handling)
        irq = at86rf215_pads.irq

        # I/Q data interfaces will be handled by Verilog modules
        # This allows for high-speed parallel data capture
        # TODO: Add DMA or high-speed buffer for I/Q data

    def add_max2771(self):
        """Add MAX2771 GNSS frontend interface"""
        max2771_pads = self.platform.request("max2771")

        # SPI interface for configuration
        from litex.soc.cores.spi import SPIMaster
        self.submodules.max2771_spi = SPIMaster(
            pads={
                "clk": max2771_pads.spi_clk,
                "mosi": max2771_pads.spi_mosi,
                "miso": max2771_pads.spi_miso,
                "cs_n": max2771_pads.spi_cs_n,
            },
            data_width=8,
            sys_clk_freq=self.sys_clk_freq,
            spi_clk_freq=int(1e6)  # 1 MHz
        )
        self.add_csr("max2771_spi")

        # Control signals
        idle = Signal()
        shdn = Signal()
        self.comb += [
            max2771_pads.idle.eq(idle),
            max2771_pads.shdn.eq(shdn),
        ]

        # ADC data interface will be handled by Verilog capture module
        # The 2-bit I/Q data needs high-speed sampling synchronized to clkout
        # TODO: Add high-speed ADC capture module


# Build ---------------------------------------------------------------------

def main():
    from litex.soc.integration.soc import LiteXSoCArgumentParser
    parser = LiteXSoCArgumentParser(description="Vahya SoC")
    target_group = parser.add_argument_group(title="Target options")
    target_group.add_argument("--build",           action="store_true", help="Build bitstream.")
    target_group.add_argument("--load",            action="store_true", help="Load bitstream.")
    target_group.add_argument("--sys-clk-freq",    default=75e6,        help="System clock frequency.")
    target_group.add_argument("--with-dfu",        action="store_true", help="Enable DFU bootloader.")
    target_group.add_argument("--usb-vid",         default=0x1209,      help="USB Vendor ID.")
    target_group.add_argument("--usb-pid",         default=0x5070,      help="USB Product ID.")
    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()

    soc = VahyaSoC(
        sys_clk_freq = int(float(args.sys_clk_freq)),
        with_dfu     = args.with_dfu,
        usb_vid      = int(args.usb_vid, 0),
        usb_pid      = int(args.usb_pid, 0),
        **soc_core_argdict(args)
    )

    builder = Builder(soc, **builder_argdict(args))
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
