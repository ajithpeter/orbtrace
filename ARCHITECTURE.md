# ORBTrace Architecture Documentation

**Version:** 1.0
**Date:** 2025-11-21
**Project:** ORBTrace - FPGA-based Debug and Trace Probe

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Hardware Description Language Integration](#hardware-description-language-integration)
5. [Component Architecture](#component-architecture)
6. [USB Subsystem](#usb-subsystem)
7. [Debug Protocols](#debug-protocols)
8. [Trace Subsystem](#trace-subsystem)
9. [Memory Architecture](#memory-architecture)
10. [Clock Domains](#clock-domains)
11. [Build System](#build-system)
12. [Testing Infrastructure](#testing-infrastructure)
13. [Platform Support](#platform-support)
14. [Development Workflow](#development-workflow)

---

## Executive Summary

ORBTrace is a sophisticated FPGA-based debug and trace probe for ARM Cortex processors. The project demonstrates advanced hardware-software co-design using Python-based HDLs (Amaranth and Migen), Verilog for timing-critical components, and the LiteX SoC framework.

### Key Capabilities

- **Debug Protocols:** CMSIS-DAP v1/v2, SWD, JTAG
- **Trace Capture:** Parallel TPIU (1/2/4-bit), Serial SWO (Manchester/NRZ)
- **USB Connectivity:** High-Speed USB 2.0 (480 Mbps)
- **Target Platform:** Lattice ECP5 FPGA (LFE5U-25F/45F)
- **Maximum Trace Bandwidth:** 480 Mbps (4-bit @ 120 MHz)
- **CPU-less Design:** Peripheral-only SoC controlled entirely via USB

### Design Philosophy

```
┌─────────────────────────────────────────────────────────────────┐
│                     Design Principles                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Modular Architecture                                        │
│     - Clear separation: Debug / Trace / Power / USB            │
│     - Each subsystem independently testable                     │
│                                                                  │
│  2. HDL Abstraction                                             │
│     - High-level logic in Amaranth (Python)                     │
│     - Timing-critical paths in Verilog                          │
│     - Seamless integration via wrapper pattern                  │
│                                                                  │
│  3. Stream Processing                                           │
│     - Consistent stream.Signature interface                     │
│     - Backpressure support throughout                           │
│     - Clock domain crossing with async FIFOs                    │
│                                                                  │
│  4. Standards Compliance                                        │
│     - ARM ADIv5.x (SWD/JTAG)                                   │
│     - CMSIS-DAP v2.1.0                                          │
│     - USB 2.0 with WCID support                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Architecture Overview

### High-Level Block Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ORBTrace System Architecture                           │
│                        Lattice ECP5 FPGA (LFE5U-25F/45F)                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                    USB Host (PC - OpenOCD/pyOCD/gdb)                      │ │
│  └───────────────────────────────────┬───────────────────────────────────────┘ │
│                                      │ USB 2.0 High-Speed (ULPI PHY)           │
│  ┌───────────────────────────────────▼───────────────────────────────────────┐ │
│  │                         USB Device Core (LUNA)                            │ │
│  │  ┌─────────────┬──────────────┬───────────────┬────────────────────────┐ │ │
│  │  │ CMSIS-DAP   │ Trace Stream │  CDC-ACM UART │  DFU / Power / Bridge  │ │ │
│  │  │ v1/v2       │  (512 bytes) │  (VirtSerial) │  (Control Interfaces)  │ │ │
│  │  └──────┬──────┴──────┬───────┴───────┬───────┴────────────┬───────────┘ │ │
│  └─────────┼─────────────┼───────────────┼────────────────────┼─────────────┘ │
│            │             │               │                    │                 │
│  ┌─────────▼──────┐  ┌───▼────────────┐ │  ┌─────────────────▼──────────────┐ │
│  │  CMSIS-DAP     │  │  Trace Core    │ │  │  Power Control / USB Bridge    │ │
│  │  Protocol FSM  │  │  (Amaranth)    │ │  │  (Amaranth)                    │ │
│  │  (Amaranth)    │  │                │ │  └────────────────────────────────┘ │
│  └─────────┬──────┘  └───┬────────────┘ │                                      │
│            │             │               │                                      │
│  ┌─────────▼──────────────────────────┐ │                                      │
│  │      Debug Interface (dbgIF.v)     │ │                                      │
│  │  ┌──────────────┬──────────────┐   │ │                                      │
│  │  │  SWD Protocol│ JTAG Protocol│   │ │                                      │
│  │  │  (swdIF.v)   │ (jtagIF.v)   │   │ │                                      │
│  │  └──────┬───────┴──────┬───────┘   │ │                                      │
│  └─────────┼──────────────┼───────────┘ │                                      │
│            │              │              │                                      │
│  ┌─────────▼──────────────▼─────────────▼──────────────┐                      │
│  │           LiteX SoC Core (Wishbone Bus)             │                      │
│  │  ┌──────────┬────────────┬────────────┬──────────┐ │                      │
│  │  │ SPI Flash│  HyperRAM  │  CSR Bus   │ USB Brdg │ │                      │
│  │  │ (8 MB)   │  (8 MB)    │ (Periph.)  │(AXI-Lite)│ │                      │
│  │  └──────────┴────────────┴────────────┴──────────┘ │                      │
│  └──────────────────────────────────────────────────────┘                      │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                    Clock & Reset Generator (CRG)                        │  │
│  │  - sys: 75MHz    - sys2x: 150MHz   - usb: 60MHz   - debug: 100MHz     │  │
│  │  - swo: 125MHz   - swo2x: 250MHz   - trace: async (up to 120MHz)      │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  External Interfaces:                                                           │
│  • Debug Connector: JTAG/SWD (9 pins bidirectional)                           │
│  • Trace Connector: 4-bit parallel + clock (5 pins)                           │
│  • Target Power: VTREF/VTPWR control (6 pins)                                 │
│  • USB PHY: ULPI interface (USB3343)                                           │
│  • HyperRAM: 8MB external memory                                               │
│  • SPI Flash: 8MB quad SPI (configuration + storage)                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                 ┌────────────────────┴─────────────────────┐
                 │                                          │
        ┌────────▼────────┐                    ┌───────────▼──────────┐
        │  Target Device  │                    │  Target Device       │
        │  (ARM Cortex)   │                    │  (Trace Output)      │
        │  SWD/JTAG Pins  │                    │  TRACECLK/DATA[3:0] │
        └─────────────────┘                    └──────────────────────┘
```

### Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Data Flow Paths                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  DEBUG PATH (Bidirectional):                                     │
│  ┌─────┐    ┌──────────┐    ┌────────┐    ┌──────┐    ┌─────┐  │
│  │ USB │◄──►│ CMSIS-DAP│◄──►│ dbgIF  │◄──►│ SWD/ │◄──►│ MCU │  │
│  │     │    │   FSM    │    │ (Vlog) │    │ JTAG │    │     │  │
│  └─────┘    └──────────┘    └────────┘    └──────┘    └─────┘  │
│     ▲            ▲               ▲                                │
│     │            │               │                                │
│   60MHz        75MHz          100MHz                             │
│   (usb)        (sys)         (debug)                             │
│                                                                   │
│  TRACE PATH (Unidirectional - Target to Host):                   │
│  ┌─────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐       │
│  │ MCU │───►│Trace │───►│ TPIU │───►│ COBS │───►│ USB  │       │
│  │Trace│    │  IF  │    │Demux │    │Encode│    │  IN  │       │
│  └─────┘    └──────┘    └──────┘    └──────┘    └──────┘       │
│               ▲           ▲           ▲           ▲              │
│               │           │           │           │              │
│          120MHz(max)   75MHz       75MHz       60MHz            │
│           (trace)      (sync)      (sync)      (usb)            │
│                                                                   │
│  SWO PATH (Serial Wire Output):                                  │
│  ┌─────┐    ┌──────┐    ┌────────┐    ┌──────┐    ┌──────┐    │
│  │ MCU │───►│ SWO  │───►│Manchstr│───►│ TPIU │───►│ USB  │    │
│  │ SWO │    │ DDR  │    │/NRZ Dec│    │ Sync │    │  IN  │    │
│  └─────┘    └──────┘    └────────┘    └──────┘    └──────┘    │
│               ▲           ▲             ▲                        │
│               │           │             │                        │
│            250MHz      125MHz        75MHz                      │
│            (swo2x)      (swo)       (sync)                      │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Hardware Description Languages

```
┌────────────────────────────────────────────────────────────────┐
│                    HDL Technology Stack                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: Amaranth HDL (Python-based)                         │
│  ├─ Version: 0.5.4                                            │
│  ├─ Purpose: High-level gateware logic                        │
│  ├─ Key Features:                                             │
│  │  • Modern Python-based HDL                                 │
│  │  • wiring.Component architecture                           │
│  │  • stream.Signature for data flow                          │
│  │  • Built-in simulation framework                           │
│  └─ Used For:                                                  │
│     • CMSIS-DAP protocol implementation                        │
│     • Trace processing pipeline                                │
│     • USB request handlers                                     │
│     • COBS encoding, TPIU demux                               │
│                                                                 │
│  Layer 2: Migen (Python-based, Legacy)                        │
│  ├─ Purpose: LiteX framework basis                            │
│  ├─ Key Features:                                             │
│  │  • Module/FSM abstractions                                 │
│  │  • CSR (Control/Status Register) support                   │
│  │  • Platform I/O primitives                                 │
│  └─ Used For:                                                  │
│     • LiteX SoC integration                                    │
│     • Clock/Reset generation                                   │
│     • CSR peripherals (LEDs, Flash UID, etc.)                 │
│     • Platform-specific I/O (DDR, tristate)                   │
│                                                                 │
│  Layer 3: Verilog (Traditional HDL)                           │
│  ├─ Standard: Verilog-2001                                    │
│  ├─ Purpose: Timing-critical protocol engines                 │
│  ├─ Total Lines: ~13,000 lines                                │
│  └─ Modules:                                                   │
│     • dbgIF.v (5,308 lines) - Debug controller                │
│     • swdIF.v (3,132 lines) - SWD protocol                    │
│     • jtagIF.v (2,892 lines) - JTAG protocol                  │
│     • traceIF.v (1,591 lines) - Trace capture                 │
│                                                                 │
│  Integration Layer: Amaranth-Migen Wrapper                     │
│  ├─ File: orbtrace/amaranth_glue/wrapper.py                   │
│  ├─ Purpose: Bidirectional HDL bridging                       │
│  └─ Capabilities:                                              │
│     • Signal conversion (Migen ↔ Amaranth)                    │
│     • Clock domain synchronization                             │
│     • Verilog generation from Amaranth                         │
│     • Instance creation for Migen                              │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Software Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Build System** | PDM (Python Development Master) | Latest | Dependency management, build scripts |
| **SoC Framework** | LiteX | 2023.12 | SoC integration, bus interconnects |
| **USB Stack** | LUNA-USB | 0.2.0 | USB 2.0 device implementation |
| **Synthesis** | Yosys | Latest (OSS CAD Suite) | Verilog synthesis |
| **Place & Route** | nextpnr-ecp5 | Latest (Project Trellis) | FPGA implementation |
| **Bitstream** | ecppack | Latest (Project Trellis) | Bitstream generation |
| **Testing** | pytest | >=8.3.5 | Unit testing framework |
| **Documentation** | Sphinx + RTD | Latest | Documentation generation |
| **CI/CD** | GitHub Actions | N/A | Automated builds |

### File Structure

```
orbtrace/
├── orbtrace/                    # Main Python package (gateware)
│   ├── __init__.py
│   ├── soc.py                   # Main SoC (776 lines)
│   ├── amaranth_glue/           # Amaranth-Migen bridge
│   │   ├── wrapper.py           # Core wrapper implementation
│   │   ├── luna.py              # LUNA USB wrappers
│   │   ├── dfu.py               # DFU handler wrapper
│   │   └── usb_mem_bridge.py    # USB memory bridge
│   ├── debug/                   # Debug subsystem
│   │   ├── cmsis_dap.py         # CMSIS-DAP (1,418 lines)
│   │   ├── cmsis_dap_wrapper.py # Migen wrapper
│   │   ├── dbgIF.py             # Verilog wrapper
│   │   └── dbgIF_wrapper.py     # Debug interface wrapper
│   ├── trace/                   # Trace subsystem
│   │   ├── core.py              # Trace pipeline integration
│   │   ├── tpiu.py              # TPIU protocol
│   │   ├── swo.py               # SWO decoders
│   │   ├── cobs.py              # COBS encoding
│   │   ├── orbflow.py           # Framing protocol
│   │   ├── util.py              # Monitoring utilities
│   │   └── usb_handler.py       # USB control
│   ├── power/                   # Target power control
│   │   └── usb_handler.py
│   ├── platforms/               # Platform definitions
│   │   ├── orbtrace_mini.py     # Main platform
│   │   └── ecpix5.py            # Dev board
│   ├── microsoft_wcid/          # Windows compatibility
│   ├── crg_ecp5.py              # Clock/Reset generation
│   ├── usb_allocator.py         # USB resource management
│   ├── stream.py                # Stream utilities
│   └── [other modules...]
├── verilog/                     # Verilog modules
│   ├── dbgIF.v
│   ├── swdIF.v
│   ├── jtagIF.v
│   ├── traceIF.v
│   ├── ram.v
│   └── testbeds/                # Verilog testbenches
├── tests/                       # Python tests
│   ├── test_tpiu.py
│   ├── test_swo.py
│   ├── test_cobs.py
│   ├── test_stream_utils.py
│   └── sim_helpers.py
├── docs/                        # Sphinx documentation
├── liblitehyperbus/            # HyperRAM C library
├── orbtrace_builder.py         # Main build script
├── orbtrace_util.py            # Runtime configuration tool
├── pyproject.toml              # Project configuration
└── .github/workflows/          # CI/CD
    └── build.yml
```

---

## Hardware Description Language Integration

### The Amaranth-Migen Bridge Pattern

The ORBTrace project employs a sophisticated integration strategy to combine three HDL frameworks seamlessly:

```
┌──────────────────────────────────────────────────────────────────┐
│              HDL Integration Architecture                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Migen/LiteX Domain                          │    │
│  │  (SoC Infrastructure, Bus, CSR, Platform I/O)           │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  • SoCCore                                               │    │
│  │  • Wishbone Bus                                          │    │
│  │  • CSR registers                                         │    │
│  │  • DDR/Tristate primitives                              │    │
│  │  • Clock domain management                               │    │
│  └───────────────────┬─────────────────────────────────────┘    │
│                      │                                            │
│                      ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │          Wrapper (Bidirectional Bridge)                  │    │
│  │  File: orbtrace/amaranth_glue/wrapper.py                │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  Key Methods:                                            │    │
│  │  • connect(migen_sig, amaranth_sig)                     │    │
│  │  • from_amaranth(sig) → Migen signal                    │    │
│  │  • from_migen(sig) → Amaranth signal                    │    │
│  │  • connect_domain(name) → Clock sync                     │    │
│  │  • generate_verilog() → Verilog output                  │    │
│  │  • get_instance() → Migen Instance                      │    │
│  └───────────────────┬─────────────────────────────────────┘    │
│                      │                                            │
│                      ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Amaranth Domain                             │    │
│  │  (Modern HDL for Complex Logic)                         │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  • TraceCore (trace processing)                          │    │
│  │  • CMSIS_DAP (protocol FSM)                             │    │
│  │  • USBDevice (LUNA stack)                               │    │
│  │  • USB Request Handlers                                  │    │
│  │  • Stream processing components                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Integration Flow:                                                │
│  ─────────────────────────────────────────────────────────────   │
│                                                                   │
│  1. Amaranth module created in wrapper.m                         │
│  2. Signals connected between Migen and Amaranth                 │
│  3. Verilog generated from Amaranth at finalization             │
│  4. Verilog file added to platform sources                       │
│  5. Migen Instance created to instantiate Verilog               │
│  6. Signals wired through Instance ports                         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Wrapper Implementation Details

**File:** [`orbtrace/amaranth_glue/wrapper.py`](orbtrace/amaranth_glue/wrapper.py)

```python
class Wrapper(migen.Module):
    """Bridge between Migen and Amaranth HDL frameworks"""

    def __init__(self, platform, name='amaranth_wrapper'):
        self.platform = platform
        self.name = name
        self.m = amaranth.Module()      # Amaranth module container
        self.connections = []            # Signal mappings

    def connect(self, migen_sig, amaranth_sig):
        """Bidirectional signal connection"""
        self.connections.append((migen_sig, amaranth_sig))

    def connect_domain(self, name):
        """Synchronize clock domains between frameworks"""
        n = 'sync' if name == 'sys' else name
        setattr(self.m.domains, n, amaranth.ClockDomain(n))
        self.connect(migen.ClockSignal(name), amaranth.ClockSignal(n))
        self.connect(migen.ResetSignal(name), amaranth.ResetSignal(n))
```

### Example: Trace Core Integration

**File:** [`orbtrace/trace/glue.py`](orbtrace/trace/glue.py)

```python
class TraceCore(Module):
    def __init__(self, platform, wrapper):
        # Create Amaranth component
        core_am = core.TraceCore()
        wrapper.m.submodules += core_am

        # Connect clock domains
        wrapper.connect_domain('trace')    # Async trace clock
        wrapper.connect_domain('swo2x')    # 250 MHz SWO oversampling
        wrapper.connect_domain('swo')      # 125 MHz SWO processing

        # Connect signals between Migen and Amaranth
        wrapper.connect(trace_io.trace_a, core_am.trace_a)     # Migen → Amaranth
        wrapper.connect(self.led_overrun, core_am.led_overrun) # Amaranth → Migen
```

### Verilog Integration Patterns

Three approaches are used for Verilog integration:

#### Pattern 1: Direct Migen Instance (Legacy)

**File:** [`orbtrace/debug/dbgIF.py`](orbtrace/debug/dbgIF.py)

```python
from migen import *

class DBGIF(Module):
    def __init__(self, pads):
        self.addr32 = Signal(2)
        self.dwrite = Signal(32)

        # Direct Verilog instantiation
        self.specials += Instance(
            "dbgIF",
            i_rst = ResetSignal("debug"),
            i_clk = ClockSignal("debug"),
            i_addr32 = self.addr32,
            o_dread = self.dread,
            # ... all ports mapped
        )
```

#### Pattern 2: Amaranth Instance (Modern)

**File:** [`orbtrace/trace/core.py`](orbtrace/trace/core.py)

```python
from amaranth import *

class TraceIF(wiring.Component):
    def elaborate(self, platform):
        m = Module()

        m.submodules.traceif = Instance('traceIF',
            i_traceClkin = ClockSignal(),
            i_traceDina = self.trace_a,
            o_Frame = frame,
        )

        return m
```

#### Pattern 3: Amaranth Wrapper Bridge (Hybrid)

Allows Amaranth code to be used from Migen by generating intermediate Verilog.

### Signal Flow Across HDL Boundaries

```
┌────────────────────────────────────────────────────────────────┐
│              Signal Flow Example: Trace Pipeline               │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Verilog (traceIF.v)                                           │
│       │                                                         │
│       ▼ Instance ports                                         │
│  Amaranth (TraceIF component)                                  │
│       │                                                         │
│       ▼ wiring.Out() signals                                   │
│  Amaranth (TraceCore component)                                │
│       │                                                         │
│       ▼ Wrapper.connect()                                      │
│  Migen (TraceCore glue)                                        │
│       │                                                         │
│       ▼ LiteX Endpoint                                         │
│  Migen (USB stream endpoint)                                   │
│       │                                                         │
│       ▼ Wrapper.connect()                                      │
│  Amaranth (LUNA USB stack)                                     │
│       │                                                         │
│       ▼ Generated Verilog                                      │
│  Synthesis (Yosys/nextpnr)                                     │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### LiteX SoC Integration

**File:** [`orbtrace/soc.py`](orbtrace/soc.py)

```
┌────────────────────────────────────────────────────────────────┐
│                    OrbSoC (SoCCore)                            │
│                   System Clock: 75 MHz                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │        Clock & Reset Generator (CRG)                     │ │
│  │  ┌─────────────┬──────────────┬────────────────────┐    │ │
│  │  │ ECP5PLL     │  ECP5PLL2    │  Phase Control     │    │ │
│  │  │ (sys/usb)   │  (debug/swo) │  (HyperRAM align)  │    │ │
│  │  └─────────────┴──────────────┴────────────────────┘    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Bus Interconnects                           │ │
│  │  ┌─────────────────┬──────────────────────────────────┐ │ │
│  │  │ Wishbone Bus    │  AXI-Lite Bus                    │ │ │
│  │  │ (Main system)   │  (USB memory bridge)             │ │ │
│  │  │                 │                                   │ │ │
│  │  │ Masters:        │  Master: USB Bridge              │ │ │
│  │  │ • USB Bridge    │  Clock: usb → sys (CDC)          │ │ │
│  │  │                 │  Full memory map access           │ │ │
│  │  │ Slaves:         │                                   │ │ │
│  │  │ • SPI Flash     │                                   │ │ │
│  │  │ • HyperRAM      │                                   │ │ │
│  │  │ • CSR Bus       │                                   │ │ │
│  │  └─────────────────┴──────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   Peripherals (CSR)                      │ │
│  │  ┌──────────┬──────────┬──────────┬──────────┬────────┐ │ │
│  │  │ LED_Ctrl │Flash_UID │ HyperRAM │ TestIO   │ Reset  │ │ │
│  │  │ (5 RGB)  │ (Serial) │(IO Delay)│ (GPIO)   │ (CSR)  │ │ │
│  │  └──────────┴──────────┴──────────┴──────────┴────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              USB Device (LUNA/Amaranth)                  │ │
│  │  ┌────────────┬─────────────┬──────────────────────────┐│ │
│  │  │ USB Core   │  Endpoints  │  Request Handlers        ││ │
│  │  │            │  (Dynamic   │  • ACM (CDC-ACM)         ││ │
│  │  │ Descriptor │   allocation)│  • Trace (Config)        ││ │
│  │  │ Management │             │  • Power (Control)        ││ │
│  │  │            │  EP0: Ctrl  │  • DFU (Firmware)        ││ │
│  │  │ ULPI PHY   │  EP1-8: Bulk│  • Mem (AXI Bridge)      ││ │
│  │  │ Interface  │  /Interrupt │  • Serial# (Dynamic)     ││ │
│  │  └────────────┴─────────────┴──────────────────────────┘│ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         Debug Subsystem (if with_debug)                  │ │
│  │  ┌────────────────┬────────────────────────────────────┐ │ │
│  │  │ CMSIS-DAP      │  Debug Interface (dbgIF.v)         │ │ │
│  │  │ (Amaranth FSM) │  ├─ swdIF.v (SWD protocol)         │ │ │
│  │  │                │  └─ jtagIF.v (JTAG protocol)       │ │ │
│  │  │ Dual protocol: │                                    │ │ │
│  │  │ • v1 (HID)     │  Commands:                         │ │ │
│  │  │ • v2 (Bulk)    │  • Connect/Disconnect              │ │ │
│  │  │                │  • Transfer/TransferBlock          │ │ │
│  │  │ Posted reads   │  • SWJ/SWD/JTAG sequences          │ │ │
│  │  └────────────────┴────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │          Trace Subsystem (if with_trace)                 │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Input Paths:                                      │  │ │
│  │  │  ┌──────────────────┬──────────────────────────┐  │  │ │
│  │  │  │ Parallel Trace   │  Serial Wire Output      │  │  │
│  │  │  │ (traceIF.v)      │  (SWO)                   │  │  │
│  │  │  │                  │                           │  │  │
│  │  │  │ • 1/2/4-bit DDR  │  • DDR capture (250MHz)  │  │  │
│  │  │  │ • Up to 120MHz   │  • Manchester decoder     │  │  │
│  │  │  │ • Frame assembly │  • NRZ/UART decoder      │  │  │
│  │  │  └──────────────────┴──────────────────────────┘  │  │ │
│  │  │                          │                          │  │ │
│  │  │                          ▼                          │  │ │
│  │  │  ┌──────────────────────────────────────────────┐  │  │ │
│  │  │  │   Processing Pipeline (Amaranth)             │  │  │ │
│  │  │  │                                               │  │  │
│  │  │  │  TPIUSync → TPIUDemux → Packetizer →         │  │  │
│  │  │  │  ChecksumAppender → COBSEncoder →            │  │  │
│  │  │  │  SuperFramer → FIFO(8192) → USB              │  │  │ │
│  │  │  └──────────────────────────────────────────────┘  │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │      Target Power Control (if with_target_power)         │ │
│  │  • VTREF: Reference voltage (1.8V / 3.3V)               │ │
│  │  • VTPWR: Target power (3.3V / 5.0V)                    │ │
│  │  • USB control interface                                 │ │
│  │  • Fault detection                                       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │            DFU Support (if with_dfu)                     │ │
│  │  • USB DFU interface                                     │ │
│  │  • Flash writer integration                              │ │
│  │  • Bootloader auto-reset                                 │ │
│  │  • Multiple flash areas                                  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Component Initialization Sequence

**File:** [`orbtrace/soc.py`](orbtrace/soc.py) - `OrbSoC.__init__()` method

```
Initialization Order:
────────────────────
1. SoCCore.__init__()          # LiteX base initialization
2. add_wrapper()                # Create Amaranth-Migen bridge
3. wrapper.connect_domain()     # Clock domain connections
4. add_flash()                  # SPI Flash controller (LiteSPI)
5. add_led_ctrl()               # LED controller (5 RGB LEDs)
6. add_usb()                    # USB device (LUNA stack)
7. add_usb_serial_number()      # Dynamic S/N from flash UID
8. add_uart()                   # USB-UART (CDC-ACM)
9. add_usb_bridge()             # USB memory bridge (AXI-Lite)
10. [Conditional subsystems]
    ├─ add_trace()              # If with_trace
    ├─ add_debug()              # If with_debug
    ├─ add_cmsis_dap()          # If with_debug
    ├─ add_target_power()       # If with_target_power
    ├─ add_dfu()                # If with_dfu
    ├─ add_reset_csr()          # If with_reset_csr
    └─ add_test_io()            # If with_test_io
```

