# Verilog-Amaranth LUNA Integration Guide

This guide explains how to integrate Verilog modules with Amaranth LUNA USB stack in the Vahya SoC for high-speed data streaming.

## Overview

The Vahya platform uses a hybrid HDL approach:
- **LiteX/Migen**: SoC framework and infrastructure
- **Amaranth (LUNA)**: USB device stack
- **Verilog**: High-speed data capture modules

This architecture leverages the strengths of each approach while maintaining clean interfaces between them.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Vahya SoC (LiteX)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐       ┌─────────────────────────────┐    │
│  │  RISC-V CPU  │◄─────►│   Wishbone Bus              │    │
│  └──────────────┘       └─────────────────────────────┘    │
│                                      │                       │
│  ┌──────────────────────────────────▼───────────────────┐  │
│  │        Amaranth Wrapper (amaranth_glue)              │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │  LUNA USB Device                                 │ │  │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐│ │  │
│  │  │  │ CDC-ACM    │  │ DFU        │  │ Bulk EPs   ││ │  │
│  │  │  └────────────┘  └────────────┘  └────────────┘│ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                          │  Stream Interface          │  │
│  └──────────────────────────┼───────────────────────────┘  │
│                             │                               │
│  ┌──────────────────────────▼───────────────────────────┐  │
│  │  Verilog Modules (Instance)                          │  │
│  │  ┌──────────────────┐    ┌─────────────────────────┐│  │
│  │  │ AT86RF215        │    │ MAX2771                  ││  │
│  │  │ I/Q Capture      │    │ ADC Capture              ││  │
│  │  └──────────────────┘    └─────────────────────────┘│  │
│  └───────────────────────────────────────────────────────┘  │
│                             │                               │
└─────────────────────────────┼───────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Physical Hardware │
                    │  AT86RF215/MAX2771 │
                    └────────────────────┘
```

## Stream Interface Protocol

The stream interface is similar to AXI-Stream with simplified semantics:

| Signal    | Direction | Width | Description                          |
|-----------|-----------|-------|--------------------------------------|
| `valid`   | Source→Sink | 1   | Data is valid this cycle            |
| `ready`   | Sink→Source | 1   | Sink can accept data (backpressure) |
| `data`    | Source→Sink | N   | Data payload                        |
| `first`   | Source→Sink | 1   | First beat of packet (optional)     |
| `last`    | Source→Sink | 1   | Last beat of packet                 |

**Transfer Rules**:
- Transfer occurs when `valid` AND `ready` are both HIGH
- `valid` must not depend on `ready` (no combinational loops)
- Once `valid` is asserted, it must stay HIGH until transfer completes
- `data`, `first`, `last` must be stable when `valid` is HIGH

## Integrating Verilog Modules into LiteX SoC

### Step 1: Create Verilog Module

Create your Verilog module with standard stream interfaces:

```verilog
module my_data_source #(
    parameter DATA_WIDTH = 32
) (
    input  wire clk,
    input  wire rst,

    // Configuration (from CPU via CSR)
    input  wire enable,

    // Output stream
    output reg  [DATA_WIDTH-1:0] stream_data,
    output reg                   stream_valid,
    input  wire                  stream_ready,
    output reg                   stream_last
);
    // Your logic here
endmodule
```

### Step 2: Add Verilog Source to Platform

In your SoC build script:

```python
# Add Verilog sources
platform.add_source("vahya/verilog/my_module.v")
```

### Step 3: Instantiate in LiteX SoC

Use `Instance` to instantiate Verilog modules in Migen/LiteX:

```python
from migen import *

class MySoC(SoCCore):
    def __init__(self):
        # ... SoC init ...

        # Create stream signals
        stream_data = Signal(32)
        stream_valid = Signal()
        stream_ready = Signal()
        stream_last = Signal()

        # Instantiate Verilog module
        self.specials += Instance("my_data_source",
            p_DATA_WIDTH = 32,

            i_clk = ClockSignal("sys"),
            i_rst = ResetSignal("sys"),
            i_enable = enable_signal,

            o_stream_data  = stream_data,
            o_stream_valid = stream_valid,
            i_stream_ready = stream_ready,
            o_stream_last  = stream_last,
        )
```

### Step 4: Connect to USB Endpoints

Connect the stream to USB endpoints with clock domain crossing:

```python
from litex.soc.interconnect.stream import ClockDomainCrossing, Endpoint

# Define stream layout
stream_layout = [("data", 32), ("last", 1)]

# Create endpoint
source_ep = Endpoint(stream_layout)
self.comb += [
    source_ep.valid.eq(stream_valid),
    stream_ready.eq(source_ep.ready),
    source_ep.data.eq(stream_data),
    source_ep.last.eq(stream_last),
]

# Clock domain crossing (sys → usb)
cdc = ClockDomainCrossing(stream_layout, "sys", "usb")
self.submodules += cdc

# Connect to USB IN endpoint
self.comb += [
    source_ep.connect(cdc.sink),
    cdc.source.connect(self.usb_in_endpoint.sink),
]
```

## Complete Integration Example: AT86RF215

Here's a complete example showing AT86RF215 integration:

### 1. Add Verilog Source

```python
# In vahya_soc.py
platform.add_source("vahya/verilog/at86rf215_iq_capture.v")
```

### 2. Instantiate and Connect

```python
def add_at86rf215_streaming(self):
    """Add AT86RF215 with USB streaming"""
    at86rf215_pads = self.platform.request("at86rf215")

    # Create stream signals
    stream_data = Signal(32)
    stream_valid = Signal()
    stream_ready = Signal()
    stream_last = Signal()

    # Configuration registers
    band_select = Signal(2)
    capture_enable = Signal()

    # Status signals
    fifo_overflow = Signal()
    sample_count = Signal(16)

    # Instantiate Verilog module
    self.specials += Instance("at86rf215_iq_capture",
        p_SAMPLE_WIDTH = 32,
        p_FIFO_DEPTH = 1024,

        # Clocks and reset
        i_clk_sys = ClockSignal("sys"),
        i_rst = ResetSignal("sys"),

        # AT86RF215 interface
        i_rf09_rxiq = at86rf215_pads.rf09_rxiq,
        i_rf09_txiq = at86rf215_pads.rf09_txiq,
        i_rf09_rxen = at86rf215_pads.rf09_rxen,
        i_rf09_txen = at86rf215_pads.rf09_txen,

        i_rf24_rxiq = at86rf215_pads.rf24_rxiq,
        i_rf24_txiq = at86rf215_pads.rf24_txiq,
        i_rf24_rxen = at86rf215_pads.rf24_rxen,
        i_rf24_txen = at86rf215_pads.rf24_txen,

        i_clk_26mhz = at86rf215_pads.clk_26mhz,

        # Configuration
        i_band_select = band_select,
        i_capture_enable = capture_enable,

        # Output stream
        o_stream_data  = stream_data,
        o_stream_valid = stream_valid,
        i_stream_ready = stream_ready,
        o_stream_last  = stream_last,

        # Status
        o_fifo_overflow = fifo_overflow,
        o_sample_count = sample_count,
    )

    # Create CSRs for configuration
    from litex.soc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus

    class AT86RF215Control(Module, AutoCSR):
        def __init__(self):
            self.control = CSRStorage(8, fields=[
                CSRField("enable", size=1, offset=0, description="Enable capture"),
                CSRField("band_select", size=2, offset=1, description="Band select"),
            ])
            self.status = CSRStatus(32, fields=[
                CSRField("overflow", size=1, offset=0, description="FIFO overflow"),
                CSRField("count", size=16, offset=1, description="Sample count"),
            ])

    self.submodules.at86rf215_ctrl = AT86RF215Control()
    self.add_csr("at86rf215_ctrl")

    # Connect CSRs
    self.comb += [
        capture_enable.eq(self.at86rf215_ctrl.control.fields.enable),
        band_select.eq(self.at86rf215_ctrl.control.fields.band_select),
        self.at86rf215_ctrl.status.fields.overflow.eq(fifo_overflow),
        self.at86rf215_ctrl.status.fields.count.eq(sample_count),
    ]

    # Create stream endpoint
    from litex.soc.interconnect.stream import Endpoint
    stream_layout = [("data", 32), ("last", 1)]
    source_ep = Endpoint(stream_layout)

    self.comb += [
        source_ep.valid.eq(stream_valid),
        stream_ready.eq(source_ep.ready),
        source_ep.data.eq(stream_data),
        source_ep.last.eq(stream_last),
    ]

    # Connect to USB endpoint (already created in add_usb_streaming)
    # self.usb_rf_in is the USB IN endpoint for RF data
    self.comb += source_ep.connect(self.usb_rf_in.sink)
```

### 3. CPU Control Software

Control the module from RISC-V software:

```c
// AT86RF215 control registers
#define AT86RF215_CTRL_ENABLE      (1 << 0)
#define AT86RF215_CTRL_BAND_RF09RX (0 << 1)
#define AT86RF215_CTRL_BAND_RF09TX (1 << 1)
#define AT86RF215_CTRL_BAND_RF24RX (2 << 1)
#define AT86RF215_CTRL_BAND_RF24TX (3 << 1)

// Start capture from RF09 RX
csr_write_simple(
    AT86RF215_CTRL_ENABLE | AT86RF215_CTRL_BAND_RF09RX,
    CSR_AT86RF215_CTRL_CONTROL_ADDR
);

// Check status
uint32_t status = csr_read_simple(CSR_AT86RF215_CTRL_STATUS_ADDR);
if (status & 0x1) {
    printf("FIFO overflow detected!\n");
}

uint16_t count = (status >> 1) & 0xFFFF;
printf("Samples captured: %d\n", count);
```

## Clock Domain Crossing Best Practices

When crossing clock domains (e.g., ADC clock → system clock → USB clock):

### 1. Use Async FIFOs

Always use proper async FIFOs with Gray code pointers:

```verilog
// See at86rf215_iq_capture.v for complete implementation
async_fifo #(
    .DATA_WIDTH(32),
    .ADDR_WIDTH(10)
) my_fifo (
    .wr_clk(source_clk),
    .wr_rst(rst),
    // ...
    .rd_clk(dest_clk),
    .rd_rst(rst),
    // ...
);
```

### 2. Synchronize Control Signals

Use multi-stage synchronizers for control signals:

```verilog
reg [2:0] enable_sync;
always @(posedge dest_clk) begin
    if (rst)
        enable_sync <= 3'b0;
    else
        enable_sync <= {enable_sync[1:0], enable_signal};
end
wire enable_synced = enable_sync[2];
```

### 3. LiteX Clock Domain Crossing

LiteX provides built-in CDC for streams:

```python
from litex.soc.interconnect.stream import ClockDomainCrossing

cdc = ClockDomainCrossing(
    layout = [("data", 32), ("last", 1)],
    cd_from = "sys",
    cd_to = "usb",
    depth = 4  # FIFO depth
)
self.submodules += cdc
```

## USB Endpoint Connection Patterns

### Pattern 1: Direct Connection (Same Clock Domain)

```python
# When both are in the same clock domain
self.comb += verilog_source.connect(usb_endpoint.sink)
```

### Pattern 2: With Clock Domain Crossing

```python
# When crossing clock domains
from litex.soc.interconnect.stream import ClockDomainCrossing

cdc = ClockDomainCrossing(layout, "sys", "usb")
self.submodules += cdc

self.comb += [
    verilog_source.connect(cdc.sink),
    cdc.source.connect(usb_endpoint.sink),
]
```

### Pattern 3: Bidirectional (e.g., RF Transceiver)

```python
# TX path: USB OUT → Verilog
cdc_out = ClockDomainCrossing(layout, "usb", "sys")
self.submodules += cdc_out
self.comb += [
    usb_out_endpoint.source.connect(cdc_out.sink),
    cdc_out.source.connect(verilog_tx_sink),
]

# RX path: Verilog → USB IN
cdc_in = ClockDomainCrossing(layout, "sys", "usb")
self.submodules += cdc_in
self.comb += [
    verilog_rx_source.connect(cdc_in.sink),
    cdc_in.source.connect(usb_in_endpoint.sink),
]
```

## Testing and Debugging

### 1. Simulation

Use LiteX simulation with Verilog modules:

```bash
python vahya_soc.py --sim
```

Add debug signals:

```python
# In SoC
if platform.name == "sim":
    self.add_debug_signals([
        stream_data,
        stream_valid,
        stream_ready,
    ])
```

### 2. ChipScope/SignalTap Alternative

Use LiteX's logic analyzer:

```python
from litex.soc.cores.analyzer import LiteScopeAnalyzer

analyzer_signals = [
    stream_data,
    stream_valid,
    stream_ready,
    fifo_overflow,
]

self.submodules.analyzer = LiteScopeAnalyzer(
    analyzer_signals,
    depth = 512,
    clock_domain = "sys",
    samplerate = self.sys_clk_freq,
    trigger_depth = 16
)
```

Capture traces:

```bash
litex_server --uart --uart-port=/dev/ttyUSB1
litescope_cli
```

### 3. USB Traffic Analysis

Use Wireshark with USBPcap (Windows) or usbmon (Linux):

```bash
# Linux
sudo modprobe usbmon
sudo wireshark
# Select usbmon interface
```

## Performance Considerations

### Bandwidth Calculations

**USB 2.0 High-Speed**: ~40 MB/s practical throughput

**AT86RF215 (14-bit I/Q at 4 MHz)**:
- Raw: 4 MHz × 2 channels × 14 bits = 112 Mbps = 14 MB/s ✓

**MAX2771 (2-bit I/Q at 16.368 MHz)**:
- Raw: 16.368 MHz × 2 channels × 2 bits = 65.5 Mbps = 8.2 MB/s ✓
- With packing (8 samples/word): Efficient transfer

**Total**: ~22 MB/s (within USB 2.0 capability)

### FIFO Sizing

Size FIFOs to handle burst mismatches:

```
FIFO_DEPTH = (Data_Rate × Worst_Case_Latency) / Word_Size
```

Example for AT86RF215:
- Data rate: 14 MB/s
- Worst-case USB latency: 10 ms
- Word size: 4 bytes
- FIFO depth: (14e6 × 0.01) / 4 = 35,000 words

Use power-of-2 for efficiency: 32K or 64K words

## Common Issues and Solutions

### Issue 1: FIFO Overflow

**Symptoms**: Data loss, `fifo_overflow` flag set

**Solutions**:
- Increase FIFO depth
- Optimize USB transfer size
- Add flow control/decimation
- Check USB host polling rate

### Issue 2: Clock Domain Issues

**Symptoms**: Metastability, data corruption

**Solutions**:
- Ensure proper Gray code FIFOs
- Add synchronizer stages (≥2)
- Verify timing constraints in synthesis

### Issue 3: USB Enumeration Fails

**Symptoms**: Device not recognized

**Solutions**:
- Check ULPI PHY clk_o (must be 60 MHz)
- Verify USB descriptors
- Check VBUS detection
- Test with different USB ports/hubs

## References

- [LiteX Documentation](https://github.com/enjoy-digital/litex)
- [LUNA USB Framework](https://github.com/greatscottgadgets/luna)
- [Migen Documentation](https://m-labs.hk/migen/manual/)
- [Orbtrace Source](https://github.com/orbcode/orbtrace) - Reference implementation
- [AT86RF215 Datasheet](https://www.microchip.com/en-us/product/AT86RF215)
- [MAX2771 Datasheet](https://www.analog.com/en/products/max2771.html)

## Example Projects

See `vahya/examples/` for complete working examples:
- `loopback_test.py` - Simple USB loopback
- `rf_capture.py` - AT86RF215 data capture
- `gnss_logger.py` - MAX2771 GNSS data logging
