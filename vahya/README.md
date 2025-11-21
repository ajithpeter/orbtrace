# Vahya Platform SoC

Vahya is a Software-Defined Radio (SDR) and GNSS platform based on the Lattice ECP5 FPGA. This repository contains a complete LiteX SoC implementation with:

- **RISC-V Processor**: VexRiscv soft processor for control and computation
- **RF Transceiver**: AT86RF215 dual-band (Sub-GHz + 2.4GHz) SDR interface
- **GNSS Frontend**: MAX2771 multi-GNSS receiver interface
- **USB 2.0**: High-speed bulk streaming via Amaranth LUNA
- **DFU Support**: USB-based firmware updates
- **Multiple Peripherals**: UART, SPI, I2C interfaces

## Hardware Specifications

### FPGA
- **Model**: Lattice ECP5 LFE5U-25F-7BG256C (actual Vahya v1.0b hardware)
- **Package**: BG256 (256-ball BGA)
- **Speed Grade**: 7
- **Clock**: 26 MHz main oscillator
- **Flash**: SPI Flash (onboard configuration flash)

### USB
- **PHY**: USB3343 ULPI (USB 2.0 High-Speed)
- **Speed**: 480 Mbps
- **Interfaces**: CDC-ACM serial, DFU, Bulk streaming

### Base Board Peripherals
- **RGB LED**: Single common-anode RGB LED for status indication
- **User Switch**: One user-accessible switch
- **GPIO**: Available on expansion connectors

### External/Expansion Peripherals
The following peripherals are designed as external modules that can be connected
via expansion connectors. **Pin assignments in the code are placeholders and must
be verified/updated based on actual hardware connections:**

- **AT86RF215** (optional): Dual-band RF transceiver
  - Sub-GHz band (RF09): 389-1088 MHz
  - 2.4GHz band (RF24): 2400-2483.5 MHz
  - 14-bit I/Q data interface per band
  - SPI control interface
  - 26 MHz reference clock

- **MAX2771** (optional): GNSS frontend
  - Multi-GNSS support (GPS, GLONASS, Galileo, BeiDou)
  - 2-bit I/Q ADC output
  - Configurable sample rate (~16 MHz typical)
  - SPI configuration interface

- **Additional UARTs**: 2× additional UART interfaces (via expansion)
- **Additional SPI**: 2× SPI master interfaces (via expansion)
- **I2C**: I2C master interface (via expansion)

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Vahya SoC (LiteX)                          │
│                                                                 │
│  ┌──────────────┐         ┌─────────────┐                     │
│  │  VexRiscv    │◄───────►│  Wishbone   │                     │
│  │  RISC-V CPU  │         │     Bus     │                     │
│  └──────────────┘         └──────┬──────┘                     │
│        │                         │                             │
│        │   ┌─────────────────────┴────────────────┐           │
│        │   │                                       │           │
│        ▼   ▼                                       ▼           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ SPI Flash    │  │ Peripherals  │  │ USB Device       │    │
│  │ (Boot/Data)  │  │ UART/SPI/I2C │  │ (LUNA Stack)     │    │
│  └──────────────┘  └──────────────┘  └─────────┬────────┘    │
│                                                  │             │
│  ┌───────────────────────────────────────────────┼─────────┐  │
│  │          Verilog Data Capture Modules         │         │  │
│  │  ┌──────────────────┐    ┌──────────────────┐│         │  │
│  │  │  AT86RF215       │    │  MAX2771         ││         │  │
│  │  │  I/Q Capture     │───►│  ADC Capture     ││         │  │
│  │  └────────┬─────────┘    └────────┬─────────┘│         │  │
│  └───────────┼──────────────────────┼───────────┘         │  │
│              │                      │                       │  │
└──────────────┼──────────────────────┼───────────────────────┘  │
               │                      │                           │
         ┌─────▼──────────┐    ┌─────▼──────────┐               │
         │  AT86RF215     │    │  MAX2771       │               │
         │  (Hardware)    │    │  (Hardware)    │               │
         └────────────────┘    └────────────────┘               │
               │                      │                           │
               ▼                      ▼                           │
          [ RF Antenna ]         [ GNSS Antenna ]                │
```

## Directory Structure

```
vahya/
├── platforms/
│   └── vahya.py              # Platform definition (pins, clocks)
├── soc/
│   └── vahya_soc.py          # Main SoC implementation
├── verilog/
│   ├── stream_interface.v    # Generic streaming interface
│   ├── at86rf215_iq_capture.v # AT86RF215 I/Q capture module
│   ├── max2771_adc_capture.v # MAX2771 ADC capture module
│   └── INTEGRATION_GUIDE.md  # Verilog integration guide
├── peripherals/
│   ├── at86rf215.py          # AT86RF215 Python wrapper
│   └── max2771.py            # MAX2771 Python wrapper
└── README.md                 # This file
```

## Prerequisites

### Software Requirements

1. **LiteX**: SoC framework
```bash
wget https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py
chmod +x litex_setup.py
./litex_setup.py --init --install --user
```

2. **RISC-V Toolchain**: For compiling firmware
```bash
# Ubuntu/Debian
sudo apt-get install gcc-riscv64-unknown-elf

# Or use prebuilt
./litex_setup.py --gcc=riscv
```

3. **Open-source FPGA Toolchain**: Yosys, nextpnr, Project Trellis
```bash
# Ubuntu/Debian
sudo apt-get install yosys nextpnr-ecp5 ecpprog

# Or build from source
./litex_setup.py --dev
```

4. **Amaranth and LUNA**: USB stack (should be installed with orbtrace dependencies)
```bash
pip install amaranth amaranth-soc
# LUNA is included in the orbtrace dependencies
```

5. **Python Dependencies**:
```bash
pip install migen litex pyserial
```

## Building the SoC

### 1. Build Bitstream

From the `vahya` directory:

```bash
cd vahya/soc
python vahya_soc.py --build
```

Options:
- `--build`: Build the bitstream
- `--load`: Load bitstream to FPGA (requires programmer)
- `--sys-clk-freq 75e6`: Set system clock frequency (default: 75 MHz)
- `--with-dfu`: Enable DFU bootloader support
- `--usb-vid 0x1209`: Set USB Vendor ID
- `--usb-pid 0x5070`: Set USB Product ID

### 2. Build with DFU Support

For firmware update capability:

```bash
python vahya_soc.py --build --with-dfu --usb-vid 0x1209 --usb-pid 0x5070
```

### 3. Load to FPGA

#### Option A: Vahya v1.0b FTP/MicroPython Programming (Recommended)

The actual Vahya v1.0b hardware uses FTP upload and MicroPython REPL for programming:

**Prerequisites**:
```bash
# Set environment variables
export VahyaPlatformIP="192.168.4.1"    # Vahya's IP address
export VahyaPlatformTTY="/dev/ttyUSB0"  # Serial port for MicroPython REPL

# Install dependencies
pip install pyserial
```

**Programming**:
The bitstream will be compressed (.bit.gz), uploaded via FTP, and programmed
via MicroPython commands automatically. See the actual `vahyaplatform.py` for
implementation details.

#### Option B: JTAG Programming (if available)

```bash
python vahya_soc.py --load
```

Or manually with OpenOCD (requires JTAG access):
```bash
openocd -f openocd_ecp5.cfg -c "transport select jtag; init; svf build/vahya/gateware/vahya.svf; exit"
```

## Usage

### USB Interfaces

Once programmed, the Vahya platform enumerates as a USB device with multiple interfaces:

1. **CDC-ACM Serial Port** (`/dev/ttyACM0` on Linux):
   - Console access to RISC-V processor
   - Debugging and logging
   - Configuration commands

2. **DFU Interface** (if enabled):
   - Firmware updates via USB
   - Use `dfu-util` for programming

3. **RF Streaming Interface**:
   - Bulk IN endpoint: AT86RF215 RX data
   - Bulk OUT endpoint: AT86RF215 TX data
   - WinUSB compatible (Windows)

4. **GNSS Streaming Interface**:
   - Bulk IN endpoint: MAX2771 ADC data
   - Continuous streaming mode

### Serial Console

Connect to the serial port:

```bash
# Linux
screen /dev/ttyACM0 115200

# Or using litex_term
litex_term /dev/ttyACM0
```

### Configuring AT86RF215

From the serial console or via CSR access:

```python
# Enable RF09 RX capture
csr.at86rf215_ctrl.control.write(0x01)  # Enable
csr.at86rf215_ctrl.control.write(0x03)  # Enable + Band=RF09_RX

# Check status
status = csr.at86rf215_ctrl.status.read()
if status & 0x1:
    print("FIFO overflow!")
```

### Configuring MAX2771

```python
# Configure for GPS L1
from vahya.peripherals.max2771 import MAX2771Config

# Get default GPS L1 configuration
config_words = MAX2771Config.default_gps_l1()

# Write via SPI
for word in config_words:
    csr.max2771_spi.write(word)

# Enable capture
csr.max2771_ctrl.control.write(0x01)  # Enable, no decimation
```

### USB Bulk Data Streaming

#### Linux (Python example)

```python
import usb.core
import usb.util

# Find device
dev = usb.core.find(idVendor=0x1209, idProduct=0x5070)

# RF streaming interface (interface 2, endpoints depend on config)
rf_ep_in = 0x83   # Bulk IN for RX
rf_ep_out = 0x03  # Bulk OUT for TX

# GNSS streaming interface (interface 3)
gnss_ep_in = 0x84 # Bulk IN

# Read GNSS data
while True:
    try:
        data = dev.read(gnss_ep_in, 512, timeout=1000)
        # Process 32-bit words containing 8 packed I/Q samples
        process_gnss_data(data)
    except usb.core.USBError as e:
        if e.errno != 110:  # Not timeout
            raise
```

#### Windows

Use WinUSB driver (automatically installed with WinUSB descriptors) and libusb or custom application.

### Data Format

#### AT86RF215 Data Format

Each USB packet contains 32-bit words:
```
Bits [31:18]: I channel (14 bits, sign-extended to 16)
Bits [17:4]:  Q channel (14 bits, sign-extended to 16)
Bits [3:0]:   Padding
```

Sample rate: Up to 4 MHz per channel (configurable in AT86RF215)

#### MAX2771 Data Format

Each USB packet contains 32-bit words with 8 packed I/Q samples:
```
Each sample: 4 bits (2-bit I + 2-bit Q)
Word format: [S7_IQ][S6_IQ][S5_IQ][S4_IQ][S3_IQ][S2_IQ][S1_IQ][S0_IQ]

Where each sample:
  Bits [1:0]: Q channel (sign + magnitude)
  Bits [3:2]: I channel (sign + magnitude)
```

Sample rate: ~16.368 MHz (configurable via MAX2771 PLL)

## Firmware Development

### RISC-V Software

Develop software for the VexRiscv processor:

1. **Setup**:
```bash
cd firmware
export PATH=$PATH:/path/to/riscv-toolchain/bin
```

2. **Compile**:
```bash
make
```

3. **Load**:
```bash
litex_term --kernel firmware.bin /dev/ttyACM0
```

### Example Firmware

See `firmware/` directory for examples:
- `main.c`: Basic initialization and console
- `rf_control.c`: AT86RF215 configuration
- `gnss_control.c`: MAX2771 configuration
- `usb_streaming.c`: USB data streaming control

## Advanced Topics

### Verilog Module Integration

See `verilog/INTEGRATION_GUIDE.md` for detailed instructions on:
- Creating custom Verilog data processing modules
- Interfacing with LUNA USB endpoints
- Clock domain crossing best practices
- Stream protocol specifications

### Custom Peripherals

Add custom peripherals to the SoC:

```python
# In vahya_soc.py
from migen import *

class MyPeripheral(Module, AutoCSR):
    def __init__(self):
        self.control = CSRStorage(32)
        self.status = CSRStatus(32)
        # Your logic here

# Add to SoC
self.submodules.my_peripheral = MyPeripheral()
self.add_csr("my_peripheral")
```

### DFU Firmware Updates

Update firmware via DFU:

```bash
# Enter DFU mode (device-specific trigger)
# Then use dfu-util
dfu-util -a 0 -D new_bitstream.bit

# Or update application area
dfu-util -a 1 -D application.bin
```

## Performance

### USB Bandwidth

- **USB 2.0 High-Speed**: ~40 MB/s practical throughput
- **AT86RF215**: ~14 MB/s (4 MHz I/Q, 14-bit per channel)
- **MAX2771**: ~8.2 MB/s (16.368 MHz I/Q, 2-bit per channel)
- **Total**: ~22 MB/s (within USB capability)

### Latency

- **FIFO buffering**: 10-20 ms typical
- **USB polling**: 1 ms (High-Speed)
- **Total end-to-end**: < 50 ms

## Troubleshooting

### Build Issues

**Error: Module 'orbtrace' not found**
- Ensure you're building from within the orbtrace repository
- Check Python path includes orbtrace modules

**Error: Verilog module not found**
- Verify Verilog files are in `vahya/verilog/`
- Check platform.add_source() calls in SoC

### USB Issues

**Device not enumerated**
- Check USB3343 ULPI PHY connections
- Verify 60 MHz clock from PHY
- Test with different USB ports/hubs

**Data corruption**
- Check FIFO depths (may need to increase)
- Verify clock domain crossing
- Monitor overflow flags

**Low throughput**
- Optimize USB packet size (512 bytes for HS)
- Check host-side polling rate
- Reduce other USB traffic

### RF/GNSS Issues

**No data from AT86RF215**
- Verify SPI configuration
- Check 26 MHz reference clock
- Enable appropriate band and mode

**No data from MAX2771**
- Verify SPI configuration successful
- Check reference clock (16.368 MHz)
- Ensure antenna is connected
- Verify LNA power

## References

- [LiteX Documentation](https://github.com/enjoy-digital/litex)
- [Amaranth HDL](https://github.com/amaranth-lang/amaranth)
- [LUNA USB Framework](https://github.com/greatscottgadgets/luna)
- [Orbtrace Project](https://github.com/orbcode/orbtrace)
- [AT86RF215 Datasheet](https://www.microchip.com/en-us/product/AT86RF215)
- [MAX2771 Datasheet](https://www.analog.com/en/products/max2771.html)
- [USB3343 Datasheet](https://www.microchip.com/en-us/product/USB3343)
- [ECP5 Family Documentation](https://www.latticesemi.com/Products/FPGAandCPLD/ECP5)

## License

This project follows the same license as the Orbtrace project.

## Contributing

Contributions are welcome! Please follow the Orbtrace project's contribution guidelines.

## Acknowledgments

- Based on the [Orbtrace](https://github.com/orbcode/orbtrace) architecture
- Uses [LiteX](https://github.com/enjoy-digital/litex) SoC framework
- USB stack powered by [LUNA](https://github.com/greatscottgadgets/luna)
- Built with open-source FPGA tools from [Project Trellis](https://github.com/YosysHQ/prjtrellis)
