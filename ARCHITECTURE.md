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

