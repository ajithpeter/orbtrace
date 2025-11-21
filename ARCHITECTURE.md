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

---

## USB Subsystem

### USB Stack Architecture

**Framework:** LUNA USB2 library (Amaranth-based)

```
┌────────────────────────────────────────────────────────────────┐
│                    USB Stack Layers                            │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 4: Application (Python/Amaranth)                       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  USB Request Handlers                                    │ │
│  │  • TraceUSBHandler      - Trace configuration            │ │
│  │  • PowerUSBHandler      - Target power control           │ │
│  │  • ACMRequestHandler    - CDC-ACM serial                 │ │
│  │  • DFUHandler           - Firmware update                │ │
│  │  • MemRequestHandler    - AXI-Lite memory bridge         │ │
│  │  • USBSerialNumberHandler - Dynamic S/N from flash       │ │
│  │  • WindowsRequestHandler - WCID descriptor set           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│  Layer 3: Protocol (LUNA)                                      │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  USBDevice Core                                          │ │
│  │  • Descriptor management                                 │ │
│  │  • Control endpoint (EP0)                                │ │
│  │  • Standard request handling                             │ │
│  │  • Endpoint allocation                                   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│  Layer 2: Data Link (LUNA)                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Endpoint Handlers                                       │ │
│  │  • USBStreamInEndpoint    - Device → Host               │ │
│  │  • USBStreamOutEndpoint   - Host → Device               │ │
│  │  • Stream interfaces with backpressure                   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│  Layer 1: Physical (ULPI PHY)                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  USB3343 ULPI Transceiver                                │ │
│  │  • 8-bit ULPI interface                                  │ │
│  │  • 60 MHz clock generation                               │ │
│  │  • USB 2.0 High-Speed (480 Mbps)                         │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### USB Interface Configuration

**File:** [`orbtrace/usb_allocator.py`](orbtrace/usb_allocator.py)

| Interface | Class/Sub/Proto | GUID Disc. | Endpoints | Purpose |
|-----------|----------------|------------|-----------|---------|
| **CMSIS-DAP v1** | HID (0x03) | Custom | IN/OUT Interrupt (64B) | Debug probe (legacy) |
| **CMSIS-DAP v2** | Vendor (0xFF/0x00) | `cdb3b5ad-...` | IN/OUT Bulk (512B) | Debug probe (modern) |
| **Trace** | Vendor (0xFF/0x54/0x10) | 0x0054 | IN Bulk (512B) | Trace streaming |
| **Control Proxy** | Vendor (0xFF/0x58/0x00) | 0x0058 | None | Trace control |
| **Target Power** | Vendor (0xFF/0x50/0x00) | 0x0050 | None | VTREF/VTPWR control |
| **CDC-ACM UART** | CDC (0x02/0x02/0x01) | N/A | IN/OUT Bulk + IN Interrupt | Virtual serial |
| **DFU** | App (0xFE/0x01/0x02) | 0x8044 | None (Control only) | Firmware update |
| **Version** | Vendor (0xFF/0x56/0x00) | 0x0056 | None | Version info |

### USB Descriptor Hierarchy

```
DeviceDescriptor
├─ VID: 0x1209 (Vendor)
├─ PID: 0x3443 (ORBTrace) / 0x3442 (DFU Bootloader)
├─ bcdUSB: 2.1 (BOS descriptor support)
├─ Manufacturer: "Orbcode"
├─ Product: "Orbtrace" / "Orbtrace Bootloader"
└─ Serial Number: Dynamic (Flash UID)

ConfigurationDescriptor
├─ InterfaceAssociationDescriptor (CDC-ACM)
│  ├─ bFirstInterface: <comm_if>
│  ├─ bInterfaceCount: 2
│  └─ bFunctionClass: 2 (CDC)
│
├─ InterfaceDescriptor (CMSIS-DAP v1)
│  ├─ bInterfaceClass: 0x03 (HID)
│  ├─ HIDDescriptor
│  └─ EndpointDescriptor (IN/OUT Interrupt, 64 bytes)
│
├─ InterfaceDescriptor (CMSIS-DAP v2)
│  ├─ bInterfaceClass: 0xFF (Vendor)
│  └─ EndpointDescriptor (IN/OUT Bulk, 512 bytes)
│
├─ InterfaceDescriptor (Trace)
│  ├─ bInterfaceClass: 0xFF, bInterfaceSubClass: 0x54
│  └─ EndpointDescriptor (IN Bulk, 512 bytes)
│
├─ InterfaceDescriptor (CDC-ACM Communication)
│  ├─ bInterfaceClass: 0x02, bInterfaceSubClass: 0x02
│  └─ EndpointDescriptor (IN Interrupt, 512 bytes)
│
├─ InterfaceDescriptor (CDC-ACM Data)
│  ├─ bInterfaceClass: 0x0A (CDC Data)
│  └─ EndpointDescriptor (IN/OUT Bulk, 512 bytes)
│
├─ InterfaceDescriptor (Target Power)
│  └─ bInterfaceClass: 0xFF, bInterfaceSubClass: 0x50
│
└─ InterfaceDescriptor (DFU)
    └─ bInterfaceClass: 0xFE, bInterfaceSubClass: 0x01

BinaryObjectStore (BOS)
└─ PlatformDescriptor
    └─ Microsoft OS 2.0 Descriptor Set
        ├─ Compatible ID: "WINUSB"
        └─ Device Interface GUIDs (per interface)
```

### USB Data Flow Examples

#### Debug Transaction (CMSIS-DAP)

```
Host → USB OUT EP → Mux(v1/v2) → CDC(usb→sys) → CMSIS-DAP FSM →
dbgIF → SWD/JTAG → Target

Target → SWD/JTAG → dbgIF → CMSIS-DAP FSM → CDC(sys→usb) →
Demux(v1/v2) → USB IN EP → Host
```

#### Trace Streaming

```
Target → Trace Pins → TraceIF(Verilog) → AsyncFIFO(trace→sync) →
TPIUDemux → COBS → CDC(sync→usb) → USB IN EP → Host
```

#### USB Memory Bridge

```
Host Control Request → MemRequestHandler → AXI-Lite CDC(usb→sys) →
Wishbone Bus → Memory/CSR
```

### Windows Compatible ID (WCID) Support

**File:** [`orbtrace/usb_allocator.py`](orbtrace/usb_allocator.py)

**Microsoft OS 2.0 Descriptor Platform:**
- Automatically generates WCID descriptors for driverless Windows installation
- Base GUID: `{1c451fbb-0000-426f-bef2-93a89eb65cba}`
- Discriminator-based GUID allocation (0x0050, 0x0054, 0x0056, etc.)
- Compatible ID: "WINUSB" for all vendor interfaces
- Device Interface GUID per interface for application binding

---

## Debug Protocols

### CMSIS-DAP Implementation

**File:** [`orbtrace/debug/cmsis_dap.py`](orbtrace/debug/cmsis_dap.py) - 1,418 lines

**Standard:** ARM CMSIS-DAP v2.1.0

#### Supported Commands

```
┌────────────────────────────────────────────────────────────────┐
│              CMSIS-DAP Command Set                             │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✅ DAP_Info                - Device capabilities              │
│  ✅ DAP_Connect             - SWD/JTAG connection              │
│  ✅ DAP_Disconnect          - Disconnect from target           │
│  ✅ DAP_Transfer            - Single AP/DP register access     │
│  ✅ DAP_TransferBlock       - Bulk register transfers          │
│  ✅ DAP_TransferConfigure   - Retry/match configuration        │
│  ✅ DAP_SWJ_Pins            - Direct pin control               │
│  ✅ DAP_SWJ_Clock           - Clock frequency setting          │
│  ✅ DAP_SWJ_Sequence        - Custom bit sequences             │
│  ✅ DAP_SWD_Configure       - SWD-specific config              │
│  ✅ DAP_SWD_Sequence        - SWD custom sequences             │
│  ✅ DAP_JTAG_Configure      - JTAG chain configuration         │
│  ✅ DAP_JTAG_Sequence       - JTAG custom sequences            │
│  ✅ DAP_JTAG_IDCODE         - Read JTAG device IDs             │
│  ✅ DAP_WriteABORT          - Write abort register             │
│  ✅ DAP_Delay               - Microsecond delays               │
│  ✅ DAP_ResetTarget         - Target reset                     │
│  ❌ DAP_SWO_*               - SWO not implemented in DAP       │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

#### CMSIS-DAP State Machine

```
┌────────────────────────────────────────────────────────────────┐
│                  CMSIS-DAP FSM Architecture                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Main FSM:                                                      │
│  IDLE → RxFirstByte → PacketSwitch → RxParams → Dispatch →    │
│  [Command Handler] → Response → TxResponse → IDLE             │
│                                                                 │
│  Transfer FSM (13 states):                                     │
│  Setup → GetTfrReq → [GetTfrData] → Execute → CheckACK →     │
│  HandleResponse → Next/Done                                     │
│                                                                 │
│  TransferBlock FSM (12 states):                                │
│  GetCount → GetTfrReq → Execute → CheckACK → Store/Load →    │
│  Loop → Done                                                    │
│                                                                 │
│  Sequence FSM (9 states):                                      │
│  GetParams → ProcessBits → Execute → NextCycle → Done         │
│                                                                 │
│  Key Features:                                                  │
│  • Posted Read Optimization                                    │
│  • WAIT/FAULT retry logic                                      │
│  • Value match support                                         │
│  • WideRam buffering (508 bytes)                               │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### SWD (Serial Wire Debug) Protocol

**File:** [`verilog/swdIF.v`](verilog/swdIF.v)

**Standard:** ARM Debug Interface Architecture ADIv5.0-5.2

#### SWD Transaction Format

```
┌────────────────────────────────────────────────────────────────┐
│                  SWD Transaction Timing                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Host Transmits 8-bit Header:                                  │
│  ┌───┬─────┬───┬─────┬─────┬──────┬────┬────┐                │
│  │ 1 │AP/DP│R/W│ A2  │ A3  │Parity│ 0  │ 1  │                │
│  └───┴─────┴───┴─────┴─────┴──────┴────┴────┘                │
│  Start  1bit  1   Address  Even  Stop Park                    │
│                           bits            bits                 │
│                                                                 │
│  Turnaround (1-4 cycles, configurable)                        │
│  ────────────                                                  │
│                                                                 │
│  Target Transmits 3-bit ACK:                                   │
│  ┌─────┬─────┬─────┐                                          │
│  │ Bit0│ Bit1│ Bit2│                                          │
│  └─────┴─────┴─────┘                                          │
│   001 = OK    010 = WAIT    100 = FAULT                       │
│                                                                 │
│  [If Read] Turnaround + 32-bit Data + Parity                  │
│  [If Write] Turnaround + Host sends 32-bit Data + Parity      │
│                                                                 │
│  Idle Cycles (2-255, configurable)                            │
│  ──────────────────────────                                   │
│                                                                 │
│  Timing Constraints:                                           │
│  • 10ns < T_high/T_low < 500µs                                │
│  • Setup time: 4ns minimum                                    │
│  • Hold time: 1ns minimum                                     │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### JTAG Protocol

**File:** [`verilog/jtagIF.v`](verilog/jtagIF.v)

**Standard:** ARM Debug Interface Architecture ADIv5.0-5.2

#### JTAG TAP State Machine

```
                Test-Logic-Reset
                       │
                       ▼
                   Run-Test/Idle
                   ╱           ╲
                  ▼             ▼
           Select-DR-Scan   Select-IR-Scan
              │                   │
              ▼                   ▼
          Capture-DR          Capture-IR
              │                   │
              ▼                   ▼
           Shift-DR            Shift-IR
              │                   │
              ▼                   ▼
           Exit1-DR            Exit1-IR
           ╱      ╲            ╱      ╲
          ▼        ▼          ▼        ▼
      Pause-DR  Update-DR  Pause-IR  Update-IR
          │                   │
          ▼                   ▼
      Exit2-DR            Exit2-IR
          │                   │
          └─────────┬─────────┘
                    │
                    ▼
             Run-Test/Idle
```

#### JTAG Chain Support

**File:** [`verilog/jtagIF.v`](verilog/jtagIF.v) - Lines 28-31

- Supports up to 6 devices in JTAG chain
- Configurable IR lengths per device (5 bits each, packed in 30-bit field)
- Automatic bypass handling for non-target devices
- Device index selection (0-7)

```
Example 3-device chain:
┌────────┐    ┌────────┐    ┌────────┐
│Device 0│───►│Device 1│───►│Device 2│
│ IR=4   │    │ IR=5   │    │ IR=4   │
└────────┘    └────────┘    └────────┘
    │             │ Target      │
    ▼             ▼             ▼
 Bypass      ARM DAP       Bypass
```

### Debug Interface Controller (dbgIF)

**File:** [`verilog/dbgIF.v`](verilog/dbgIF.v) - 5,308 lines

**Purpose:** Unified command interface for SWD, JTAG, and mode switching

#### Command Set

```
┌────────────────────────────────────────────────────────────────┐
│                 dbgIF Command Set (16 commands)                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  0:  CMD_RESET         - Reset target with timeout             │
│  1:  CMD_PINS_WRITE    - Direct pin control (SWJ mode)         │
│  2:  CMD_TRANSACT      - Execute SWD/JTAG transaction          │
│  3:  CMD_SET_SWD       - Switch to SWD mode                    │
│  4:  CMD_SET_JTAG      - Switch to JTAG mode                   │
│  5:  CMD_SET_SWJ       - Switch to manual pin mode             │
│  6:  CMD_SET_JTAG_CFG  - Configure JTAG chain                  │
│  7:  CMD_SET_CLK       - Set clock frequency (195kHz-25MHz)    │
│  8:  CMD_SET_SWD_CFG   - Configure SWD timing                  │
│  9:  CMD_WAIT          - Delay in microseconds                 │
│  10: CMD_CLR_ERR       - Clear error flags                     │
│  11: CMD_SET_RST_TMR   - Configure reset timeout               │
│  12: CMD_SET_TFR_CFG   - Configure transfer timing             │
│  13: CMD_JTAG_GET_ID   - Read JTAG IDCODE                      │
│  14: CMD_JTAG_RESET    - Reset JTAG TAP to Test-Logic-Reset   │
│  15: CMD_JTAG_REG      - Set JTAG IR register                  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

#### Mode Switching Sequences

**SWD Mode Entry:**
```
1. Send 50+ cycles of '1'
2. Send magic: 0xE79E (JTAG-to-SWD sequence)
3. Send 50+ cycles of '1'
4. Send 2+ cycles of '0'
```

**JTAG Mode Entry:**
```
1. Send 50+ cycles of '1'
2. Send magic: 0xE73C (SWD-to-JTAG sequence)
3. Send 50+ cycles of '1'
4. Send 2+ cycles of '0'
```

---

## Trace Subsystem

### Trace Processing Pipeline

**Files:**
- [`orbtrace/trace/core.py`](orbtrace/trace/core.py) - Pipeline integration
- [`orbtrace/trace/tpiu.py`](orbtrace/trace/tpiu.py) - TPIU protocol
- [`orbtrace/trace/swo.py`](orbtrace/trace/swo.py) - SWO decoders
- [`orbtrace/trace/cobs.py`](orbtrace/trace/cobs.py) - COBS encoding
- [`orbtrace/trace/orbflow.py`](orbtrace/trace/orbflow.py) - Framing protocol

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Trace Processing Architecture                     │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Input Sources (Multiple Paths):                                      │
│  ┌─────────────────────┬──────────────────────────────────────────┐  │
│  │  Parallel Trace     │  Serial Wire Output (SWO)                │  │
│  │  ┌───────────────┐  │  ┌────────────┐   ┌─────────────────┐  │  │
│  │  │ traceIF.v     │  │  │ DDR Capture│──►│ Pulse Length    │  │  │
│  │  │               │  │  │ (250 MHz)  │   │ Capture (swo2x) │  │  │
│  │  │• 1/2/4-bit    │  │  └────────────┘   └────────┬────────┘  │  │
│  │  │• DDR capture  │  │                             │           │  │
│  │  │• Up to 120MHz │  │                             ▼           │  │
│  │  │• Frame asm.   │  │         ┌───────────────────────────┐  │  │
│  │  └───────┬───────┘  │         │ Manchester Decoder  OR    │  │  │
│  │          │          │         │ NRZ/UART Decoder          │  │  │
│  │          │          │         │ (swo domain, 125 MHz)     │  │  │
│  │          │          │         └───────────┬───────────────┘  │  │
│  │          │          │                     │                   │  │
│  │          ▼          │                     ▼                   │  │
│  │   AsyncFIFO(4)     │              AsyncFIFO(16)              │  │
│  │   (trace→sync)     │              (swo→sync)                 │  │
│  └─────────┬──────────┴──────────────────────┬──────────────────┘  │
│            │                                  │                      │
│            └────────────────┬─────────────────┘                      │
│                             │                                        │
│                             ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   TPIUSync (Sync domain)                     │  │
│  │  • Searches for sync pattern (0x7FFFFFFF)                   │  │
│  │  • Aligns to 16-byte frame boundaries                        │  │
│  └────────────────────────────┬─────────────────────────────────┘  │
│                                │                                    │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      TPIUDemux                               │  │
│  │  ┌────────┬──────────┬──────────────┬─────────────────────┐ │  │
│  │  │Unmangle│Serializer│ TrackStream  │ StripChannelZero    │ │  │
│  │  │        │          │              │                     │ │  │
│  │  │Extract │Array to  │Channel ID    │Filter channel 0     │ │  │
│  │  │ID bits │elements  │tracking      │(sync packets)       │ │  │
│  │  └────┬───┴────┬─────┴──────┬───────┴──────┬──────────────┘ │  │
│  │       │        │            │              │                 │  │
│  │       └────────┴────────────┴──────────────┘                 │  │
│  │                             │                                 │  │
│  │                             ▼                                 │  │
│  │                     ┌───────────────┐                         │  │
│  │                     │  Packetizer   │                         │  │
│  │                     │               │                         │  │
│  │                     │• Max: 1024B   │                         │  │
│  │                     │• Timeout: 7.5M│                         │  │
│  │                     │  cycles       │                         │  │
│  │                     │• Channel hdr  │                         │  │
│  │                     └───────┬───────┘                         │  │
│  └─────────────────────────────┼─────────────────────────────────┘  │
│                                │                                    │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              ChecksumAppender (orbflow.py)                   │  │
│  │  • Running subtraction checksum                              │  │
│  │  • Appended to packet end                                    │  │
│  └────────────────────────────┬─────────────────────────────────┘  │
│                                │                                    │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    COBSEncoder (cobs.py)                     │  │
│  │  ┌────────────┬───────┬──────────────┬──────────────────┐   │  │
│  │  │GroupSplitter│FIFO(L)│GroupCombiner │DelimiterAppender │   │  │
│  │  │            │FIFO(D)│              │                  │   │  │
│  │  │Split on 0x00│256-byte│Encode length│Append 0x00       │   │  │
│  │  └────────────┴───────┴──────────────┴──────────────────┘   │  │
│  └────────────────────────────┬─────────────────────────────────┘  │
│                                │                                    │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              SuperFramer (orbflow.py)                        │  │
│  │  • Delays 'last' marker until flush                          │  │
│  │  • Timer: 7.5M cycles (~100ms @ 75MHz)                       │  │
│  │  • Threshold: 65536 bytes                                    │  │
│  └────────────────────────────┬─────────────────────────────────┘  │
│                                │                                    │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │           SyncFIFOBuffered (8192 entries)                    │  │
│  │  • Large buffering for burst handling                        │  │
│  └────────────────────────────┬─────────────────────────────────┘  │
│                                │                                    │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │           ClockDomainCrossing (sync → usb)                   │  │
│  │  • AsyncFIFO depth: 8                                        │  │
│  │  • 75 MHz → 60 MHz                                           │  │
│  └────────────────────────────┬─────────────────────────────────┘  │
│                                │                                    │
│                                ▼                                    │
│                         USB Bulk IN Endpoint                        │
│                         (512 bytes, High-Speed)                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### TPIU (Trace Port Interface Unit)

**Standard:** ARM CoreSight TPIU-Lite r0p0

**Parallel Trace Formats:**
- **1-bit:** Legacy SWO compatibility
- **2-bit:** Medium bandwidth
- **4-bit:** Maximum bandwidth (480 Mbps @ 120 MHz)

**Frame Structure:**
- 16-byte (128-bit) frames
- 8 channels multiplexed (7-bit channel ID)
- Channel 0 reserved for synchronization

**TPIU Processing Steps:**

1. **Unmangle:** Extract ID bits from frame format
2. **TrackStream:** Maintain channel state and detect switches
3. **StripChannelZero:** Remove synchronization packets
4. **Packetizer:** Group by channel with timeout

### SWO (Serial Wire Output)

**Encoding Modes:**

**Manchester Encoding:**
```
┌───────────────────────────────────────────────────────────┐
│              Manchester Encoding Timing                   │
├───────────────────────────────────────────────────────────┤
│                                                            │
│  Bit '0':  ▀▀▀▀▀▀▄▄▄▄▄▄  (High → Low transition)        │
│                                                            │
│  Bit '1':  ▄▄▄▄▄▄▀▀▀▀▀▀  (Low → High transition)        │
│                                                            │
│  Features:                                                 │
│  • Self-clocking (no separate clock needed)               │
│  • Auto-synchronization on transitions                    │
│  • Adaptive threshold (3/4 and 5/4 bit time)             │
│  • 250 MHz 2x oversampling for pulse measurement         │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

**NRZ/UART Encoding:**
```
┌───────────────────────────────────────────────────────────┐
│                  UART Frame Format                        │
├───────────────────────────────────────────────────────────┤
│                                                            │
│  ┌────┬───┬───┬───┬───┬───┬───┬───┬───┬────┐            │
│  │Strt│D0 │D1 │D2 │D3 │D4 │D5 │D6 │D7 │Stop│            │
│  │ 0  │   │   │   │   │   │   │   │   │ 1  │            │
│  └────┴───┴───┴───┴───┴───┴───┴───┴───┴────┘            │
│                                                            │
│  • Configurable baudrate (via divider)                    │
│  • 8-bit data, no parity, 1 stop bit (8N1)               │
│  • 4-bit fractional accumulator for sub-bit timing       │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

### Trace Format Selection

**Configuration:** Via USB vendor request (TraceUSBHandler)

| Format Code | Description | Processing Path |
|-------------|-------------|----------------|
| `0x01` | Parallel 1-bit TPIU | traceIF → TPIU → USB |
| `0x02` | Parallel 2-bit TPIU | traceIF → TPIU → USB |
| `0x03` | Parallel 4-bit TPIU | traceIF → TPIU → USB |
| `0x10` | SWO Manchester (bypass) | Manchester → Bytes → USB |
| `0x11` | SWO Manchester + TPIU | Manchester → TPIU → USB |
| `0x12` | SWO NRZ (bypass) | NRZ → UART → Bytes → USB |
| `0x13` | SWO NRZ + TPIU | NRZ → UART → TPIU → USB |

---

## Memory Architecture

### Memory Map

```
┌──────────────────────────────────────────────────────────────┐
│                    Address Space Layout                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  0x00000000 - 0x07FFFFFF   Reserved / Unmapped              │
│                                                               │
│  0x08000000 - 0x08FFFFFF   SPI Flash (Memory Mapped)        │
│                            ┌──────────────────────────────┐  │
│                            │ Size: 8 MB (S25FL064L)       │  │
│                            │ Mode: Read-only              │  │
│                            │ Interface: LiteSPI           │  │
│                            │ Protocol: Quad SPI (1-1-4)   │  │
│                            │ Frequency: ~15 MHz           │  │
│                            │                              │  │
│                            │ Contents:                    │  │
│                            │ 0x000000: DFU Bootloader     │  │
│                            │ 0x100000: Application        │  │
│                            │ Flash UID: 64-bit unique ID  │  │
│                            └──────────────────────────────┘  │
│                                                               │
│  0x20000000 - 0x207FFFFF   HyperRAM (8 MB)                  │
│                            ┌──────────────────────────────┐  │
│                            │ Interface: LiteHyperBus      │  │
│                            │ Protocol: DDR2x (150 MHz)    │  │
│                            │ Latency: 7 cycles            │  │
│                            │ Clock phases:                │  │
│                            │  • sys (75 MHz)              │  │
│                            │  • sys2x (150 MHz)           │  │
│                            │  • sys_90 (75 MHz, 90°)      │  │
│                            │  • sys2x_90 (150 MHz, 90°)   │  │
│                            │                              │  │
│                            │ Calibration:                 │  │
│                            │  • IO delay: 0-31 taps       │  │
│                            │  • CLK delay: 0-31 taps      │  │
│                            │  • 25 ps per tap             │  │
│                            └──────────────────────────────┘  │
│                                                               │
│  0x80000000 - 0x8FFFFFFF   CSR (Control/Status Registers)   │
│                            ┌──────────────────────────────┐  │
│                            │ All peripherals accessible   │  │
│                            │ via memory-mapped registers  │  │
│                            │                              │  │
│                            │ Key CSR Modules:             │  │
│                            │ • CRG (clock control)        │  │
│                            │ • LED_Ctrl (RGB LEDs)        │  │
│                            │ • Flash_UID (serial number)  │  │
│                            │ • HyperRAM (delay cal)       │  │
│                            │ • TestIO (GPIO)              │  │
│                            │ • Reset (soft reset)         │  │
│                            └──────────────────────────────┘  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### SPI Flash Organization

**Device:** Spansion S25FL064L (8 MB)

```
┌────────────────────────────────────────────────────────┐
│               SPI Flash Layout                         │
├────────────────────────────────────────────────────────┤
│                                                         │
│  0x000000 ┌─────────────────────────────────────────┐ │
│           │  DFU Bootloader                         │ │
│           │  • USB VID:PID = 0x1209:0x3442          │ │
│           │  • Purple LED indicator                 │ │
│           │  • Boots application after timeout      │ │
│  0x0FFFFF └─────────────────────────────────────────┘ │
│                                                         │
│  0x100000 ┌─────────────────────────────────────────┐ │
│           │  Application Bitstream                  │ │
│           │  • USB VID:PID = 0x1209:0x3443          │ │
│           │  • Full debug/trace functionality       │ │
│           │  • Standard entry point                 │ │
│  0x7FFFFF └─────────────────────────────────────────┘ │
│                                                         │
│  Flash UID: 64-bit unique ID read via SPI command     │
│  Used for: USB serial number generation               │
│                                                         │
└────────────────────────────────────────────────────────┘
```

### HyperRAM Interface

**File:** [`orbtrace/hyperram.py`](orbtrace/hyperram.py)

**Features:**
- DDR2x operation (300 MT/s effective)
- Multi-phase clocking for optimal timing
- CSR-controlled delay calibration
- Wishbone bus interface
- Multi-master arbiter support

---

## Clock Domains

**File:** [`orbtrace/crg_ecp5.py`](orbtrace/crg_ecp5.py)

### Clock Generation Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  Clock Generation Topology                     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input: 30 MHz Oscillator (ORBTrace Mini)                     │
│         100 MHz Oscillator (ECPIX-5)                           │
│                    │                                            │
│                    ▼                                            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    ECP5PLL (Primary)                      │ │
│  │  Input: 30 MHz                                            │ │
│  │  VCO: 600 MHz                                             │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  Outputs:                                                 │ │
│  │  ├─ sys      (75 MHz, ÷8)   Main system clock            │ │
│  │  ├─ sys2x    (150 MHz, ÷4)  HyperRAM DDR clock          │ │
│  │  ├─ sys_90   (75 MHz, ÷8, 90° phase)  HyperRAM sampling │ │
│  │  ├─ sys2x_90 (150 MHz, ÷4, 90° phase) HyperRAM sampling │ │
│  │  └─ usb      (60 MHz, ÷10)  USB PHY clock                │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   ECP5PLL2 (Secondary)                    │ │
│  │  Input: 30 MHz                                            │ │
│  │  VCO: 500 MHz                                             │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  Outputs:                                                 │ │
│  │  ├─ debug    (100 MHz, ÷5)  SWD/JTAG interface          │ │
│  │  ├─ swo      (125 MHz, ÷4)  SWO processing               │ │
│  │  └─ swo2x    (250 MHz, ÷2)  SWO oversampling (DDR)      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              External/Async Clocks                        │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  • trace     Async from target (up to 120 MHz)          │ │
│  │  • por       30 MHz (power-on reset domain)              │ │
│  │  • ulpi_clk  60 MHz from USB PHY (alternative to 'usb')  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Clock Domain Usage

| Domain | Frequency | Purpose | Subsystems |
|--------|-----------|---------|------------|
| **sys** | 75 MHz | Main system | LiteX SoC, Wishbone bus, CSR, trace processing |
| **sys2x** | 150 MHz | HyperRAM DDR | HyperRAM controller clock output |
| **sys_90** | 75 MHz (90°) | HyperRAM sampling | HyperRAM data sampling |
| **sys2x_90** | 150 MHz (90°) | HyperRAM DDR sampling | HyperRAM DDR data sampling |
| **usb** | 60 MHz | USB operations | LUNA USB stack, endpoints, CDC |
| **debug** | 100 MHz | Debug interface | dbgIF, swdIF, jtagIF |
| **swo** | 125 MHz | SWO processing | Manchester/NRZ decoders |
| **swo2x** | 250 MHz | SWO oversampling | Pulse length capture (DDR) |
| **trace** | Async (≤120 MHz) | Parallel trace | traceIF, DDR capture |
| **por** | 30 MHz | Power-on reset | Reset sequencing |

### Dynamic Clock Features

**Dynamic Clock Source Selection (DCSC):**
```python
Instance('DCSC',
    o_DCSOUT = jtdo_swo_clk,
    i_CLK0 = ClockSignal('debug'),   # JTAG mode
    i_CLK1 = ClockSignal('swo2x'),   # SWO mode
    i_SEL0 = self.is_jtag,
    i_SEL1 = ~self.is_jtag,
)
```

**Phase Adjustment (CSR Control):**
- `_phase_sel`: Select which clock to adjust
- `_phase_dir`: Direction of phase shift
- `_phase_step`: Trigger phase step
- `_phase_load`: Load phase setting

**Clock Alignment (CLKDIVF):**
- `_slip_hr2x`: Align sys2x clock
- `_slip_hr2x90`: Align sys2x_90 clock

