# Vahya MINI Hardware Analysis

**Date**: 2025-11-22
**Based on**: VAHYA_MINI_SCH.PDF (Rev. 4/01/2025)
**FPGA**: Lattice ECP5 LFE5U-25F-7BG256I

## Overview

This document provides a comprehensive analysis of the Vahya MINI hardware based on the actual schematic and IBOM files.

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   ESP32-S3  │────→│  ECP5 FPGA   │────→│   USB3343    │
│  (WiFi/BT)  │     │  (Main SoC)  │     │  (USB PHY)   │
└─────────────┘     └──────────────┘     └──────────────┘
                           │                      │
                           ├──────────────────────┼──────────→ USB Type-C
                           │                      │
                    ┌──────┴──────┐      ┌────────┴────────┐
                    │             │      │                 │
              ┌─────▼─────┐  ┌───▼────┐ │                 │
              │ AT86RF215 │  │MAX2771 │ │                 │
              │  (RF TX)  │  │ (GNSS) │ │                 │
              └───────────┘  └────────┘ │                 │
                    │            │       │                 │
              [2.4GHz/Sub-1]  [GPS/    │                 │
                              Galileo/  │                 │
                              GLONASS]  │                 │
                                        │                 │
                                   ┌────▼────┐            │
                                   │ SD Card │            │
                                   └─────────┘            │
                                                          │
                                                    [USB-C Power]
```

## Main Components

### 1. FPGA: Lattice ECP5 LFE5U-25F-7BG256I (U2)

**Package**: BG256 (256-ball BGA, 17x17mm)
**Device**: LFE5U-25F-7 (25K LUT, Speed Grade -7)
**Reference**: Sheet 2

**Clock Input**:
- Primary Clock: 26 MHz from Y2 (ECS-TXO-32CSMV-260-AN-TR)
- Pin: C7 (connected via R9 0R to CLK_FPGA)
- External Clock Input: Available on J5 (U.FL connector)

**Power Rails**:
- VCC (1.1V): Core logic - U2H pins L10, G9, L9, L8, G7, G6
- VCCAUX (2.5V): Auxiliary - U2H pins G11, L7
- VCCIO Banks (3.3V):
  - VCCIO0: F7, F6
  - VCCIO1: F11, F10
  - VCCIO2: H11, J11
  - VCCIO3: K11, L11
  - VCCIO6: J7, J6
  - VCCIO7: H7, H6
  - VCCIO8: L6

**Configuration**:
- Mode: Master SPI (from QSPI flash)
- CFG_0: N10 (pulled to GND via R20 470R)
- CFG_1: P10 (pulled to +3V3 via R16 4.7K)
- CFG_2: R10 (pulled to GND via R21 470R)
- PROGRAMN: R9 (pulled up via R18 15K)
- INITN: T9 (pulled up via R17 15K)
- DONE: P9 (pulled up via R19 15K)

**JTAG**:
- TDO: M10
- TCK: T10
- TDI: R11
- TMS: T11

### 2. USB PHY: USB3343-CP (U7)

**Package**: QFN-24 + EP
**Function**: USB 2.0 High-Speed ULPI Transceiver
**Reference**: Sheet 5

**FPGA ULPI Interface** (BANK 7):
- DATA[0]: G1 (PL20A/GR_PCLK7_1)
- DATA[1]: F2 (PL11C)
- DATA[2]: F1 (PL14A)
- DATA[3]: E2 (PL8B)
- DATA[4]: E1 (PL11D)
- DATA[5]: D1 (PL8A)
- DATA[6]: C2 (PL5B)
- DATA[7]: C1 (PL5A)
- CLKOUT: K1 (PL23C/PCLKT7_0)
- DIR: J5 (PL17D)
- NXT: G2 (PL14B)
- STP: J4 (PL17C)

**USB PHY Control**:
- RESET: H2 (PL20B)
- REFCLK_IN: J1 (PL23A/PCLKT7_1)

**Clock Source**:
- 26 MHz from Y3 (OT252026MJBA4SL)
- Can also accept clock from FPGA via R73 0R (DNP option)

**USB Connector**: J10 (USB Type-C, Device mode)

### 3. RF Transceiver: AT86RF215M (U1)

**Package**: QFN-48 + EP
**Function**: Dual-band RF transceiver (Sub-1GHz + 2.4GHz)
**Reference**: Sheet 3

**RF Interfaces**:
- RF24 (2.4GHz): Via balun B1 (2450FB15A050E) to J11 (SMA connector)
- RF09 (Sub-1GHz): Via balun B2 (0896BM15E0025E) to J12 (SMA connector)

**Digital Interface to FPGA**:

*Data Lines* (LVDS, BANK 1):
- TXCLK_P: B16 (PT35A/PCLKT1_0)
- TXCLK_N: B15 (PR2B/S0_IN)
- TXD_P: C16 (PT33A/PCLKT1_1)
- TXD_N: C15 (PR5B)
- RXCLK_P: J16 (PT23A/PCLKT2_1)
- RXCLK_N: J15 (PR23B/PCLKC2_1)
- RXD09_P: D16 (PT40A)
- RXD09_N: E15 (PR8B)
- RXD24_P: K16 (PT23C/PCLKT2_0)
- RXD24_N: K15 (PR23D/PCLKC2_0)

*Control Lines* (BANK 2):
- RSTN: C14 (PR2C)
- IRQ: G16 (PR20A/GR_PCLK2_1)
- SCLK: K14 (PR20D)
- SELN: E16 (PR11D)
- MISO: F16 (PR14A)
- MOSI: C14 (PR2D)

**Clock**:
- TCXO: 26 MHz from Y1 (ECS-TXO-32CSMV-260-AN-TR)
- CLKOUT: Available on J14 (U.FL), also to FPGA via J2

### 4. GNSS Frontend: MAX2771ETI+ (U8)

**Package**: TQFN-28 + EP
**Function**: Multi-GNSS receiver frontend (GPS/Galileo/GLONASS)
**Reference**: Sheet 4

**RF Interface**:
- LNAIN_HI/LO: Via matching network to J13 (U.FL antenna connector)

**Digital Interface to FPGA** (BANK 3):
- SDATA: R15 (PR38C)
- SCLK: T14 (PR41D)
- CSN: R14 (PR41B)
- SHDN: R16 (PR35B/VREF1_3)
- LD: K13 (PR29A/GR_PCLK3_0)

**ADC Output** (2-bit I/Q, BANK 3):
- I0: P14 (PR38B)
- I1: P15 (PR32A)
- Q0: P13 (PR41A)
- Q1: P12 (PR44A)
- CLKOUT: M16 (PR26C/PCLKT3_0)

**Clock**:
- 16.368 MHz from Y4 (16.368MHz oscillator)

### 5. Microcontroller: ESP32-S3FH4R2 (U9)

**Package**: QFN-56 + EP
**Function**: WiFi/Bluetooth control, FPGA programming
**Reference**: Sheet 7

**Interface to FPGA**:
- JTAG Interface:
  - TDO: Pin 38 (GPIO33) → FPGA M10
  - TCK: Pin 39 (GPIO34) → FPGA T10
  - TDI: Pin 40 (GPIO35) → FPGA R11
  - TMS: Pin 41 (GPIO36) → FPGA T11

**Control Lines to FPGA**:
- GPIO6 → ECP5_PT4A (A2)
- GPIO7 → ECP5_PT6A (A3)
- GPIO8 → ECP5_PT18B (A6)
- GPIO9 → ECP5_PT29A (A7)

**USB Interface**: J7 (USB Type-C for ESP32 programming/debug)

**WiFi Antenna**: Via matching network (L9, L10) to PCB antenna

### 6. Configuration Flash: W25Q32JVSSIQ (U3)

**Package**: SOIC-8
**Capacity**: 32 Mbit (4 MB)
**Interface**: Quad SPI
**Reference**: Sheet 2

**FPGA QSPI Interface** (BANK 8):
- CS: R8 (PB13A/SN/CSN)
- CLK: N9 (CCLK/MCLK/SCK)
- D0: T8 (PB11B/D0/MOSI/IO0)
- D1: T7 (PB11A/D1/MISO/IO1)
- D2: N7 (PB9B/D2/IO2)
- D3: M7 (PB9A/D3/IO3)

### 7. SD Card Slot: TF-01A (J6)

**Type**: MicroSD card slot
**Interface**: 4-bit SD
**Reference**: Sheet 8

**FPGA SD Card Interface** (BANK 1):
- DAT0: A12 (PT53B)
- DAT1: A13 (PT65A)
- DAT2: A9 (PT42A)
- DAT3: A10 (PT42B)
- CMD: A11 (PT53A)
- CLK: B8 (PT35B/PCLKC1_0)
- CD (Card Detect): B10 (PT44B)

### 8. Power Supply System

**Reference**: Sheet 6

**Input**: +5V via J8 (PEC02SAAN 2-pin header) or USB Type-C

**Buck Converters** (TLV62569APDRLR):

1. **+3V3 Rail** (U4):
   - Input: +5V
   - Output: 3.3V @ 2A
   - Inductor: L2 (2.2µH)
   - Feedback: R32 (15K)
   - Power Good: PG_3V3

2. **+2V5 Rail** (U5):
   - Input: +5V
   - Output: 2.5V @ 1A
   - Inductor: L3 (2.2µH)
   - Feedback: R36 (15K)
   - Enabled by: PG_3V3 (sequenced after 3.3V)

3. **+1V1 Rail** (U6):
   - Input: +5V
   - Output: 1.1V @ 2A
   - Inductor: L4 (2.2µH)
   - Feedback: R40 (15K), R42 (18K)
   - Enabled by: PG_3V3 (sequenced after 3.3V)

**Power Sequencing**:
- 3.3V ramps first (for flash and peripherals)
- 2.5V and 1.1V ramp simultaneously after 3.3V is stable

## Verified FPGA Pin Assignments

### USB3343 ULPI Interface (BANK 7) ✅ VERIFIED
```python
("usb_ulpi", 0,
    Subsignal("data", Pins("G1 F2 F1 E2 E1 D1 C2 C1", dir="io")),
    Subsignal("clk",  Pins("K1", dir="i")),
    Subsignal("dir",  Pins("J5", dir="i")),
    Subsignal("nxt",  Pins("G2", dir="i")),
    Subsignal("stp",  Pins("J4", dir="o")),
    Subsignal("rst",  Pins("H2", dir="o")),
    IOStandard("LVCMOS33")
),
```

### RGB LED (BANK 1) ✅ VERIFIED
```python
("rgb_led", 0,
    Subsignal("r", Pins("B13", dir="o")),
    Subsignal("g", Pins("B14", dir="o")),
    Subsignal("b", Pins("B12", dir="o")),
    IOStandard("LVCMOS33")
),
```

### User Switch (BANK 6) ✅ VERIFIED
```python
("user_sw", 0, Pins("N6", dir="i"), IOStandard("LVCMOS33")),
```

### Clock (BANK 0) ✅ VERIFIED
```python
("clk26", 0, Pins("C7", dir="i"), IOStandard("LVCMOS33")),
```

### AT86RF215 Interface ⚠️ NEEDS VERIFICATION

*Data Lines (LVDS pairs, BANK 1)*:
```python
("at86_data", 0,
    Subsignal("txclk_p",  Pins("B16", dir="o")),  # PT35A
    Subsignal("txclk_n",  Pins("B15", dir="o")),  # PR2B
    Subsignal("txd_p",    Pins("C16", dir="o")),  # PT33A
    Subsignal("txd_n",    Pins("C15", dir="o")),  # PR5B
    Subsignal("rxclk_p",  Pins("J16", dir="i")),  # PT23A
    Subsignal("rxclk_n",  Pins("J15", dir="i")),  # PR23B
    Subsignal("rxd09_p",  Pins("D16", dir="i")),  # PT40A
    Subsignal("rxd09_n",  Pins("E15", dir="i")),  # PR8B
    Subsignal("rxd24_p",  Pins("K16", dir="i")),  # PT23C
    Subsignal("rxd24_n",  Pins("K15", dir="i")),  # PR23D
    IOStandard("LVDS")
),
```

*Control Lines (BANK 2)*:
```python
("at86_ctrl", 0,
    Subsignal("rst_n", Pins("C14", dir="o")),   # PR2C
    Subsignal("irq",   Pins("G16", dir="i")),   # PR20A
    Subsignal("sclk",  Pins("K14", dir="o")),   # PR20D
    Subsignal("sel_n", Pins("E16", dir="o")),   # PR11D
    Subsignal("miso",  Pins("F16", dir="i")),   # PR14A
    Subsignal("mosi",  Pins("C14", dir="o")),   # PR2D - CONFLICT with rst_n!
    IOStandard("LVCMOS33")
),
```

**⚠️ WARNING**: Pin C14 appears to be assigned to both AT86_RSTN and AT86_MOSI. This needs resolution from the schematic.

### MAX2771 Interface (BANK 3) ⚠️ NEEDS VERIFICATION

*Control Lines*:
```python
("max2771_ctrl", 0,
    Subsignal("sdata", Pins("R15", dir="o")),  # PR38C
    Subsignal("sclk",  Pins("T14", dir="o")),  # PR41D
    Subsignal("cs_n",  Pins("R14", dir="o")),  # PR41B
    Subsignal("shdn",  Pins("R16", dir="o")),  # PR35B
    Subsignal("ld",    Pins("K13", dir="i")),  # PR29A
    IOStandard("LVCMOS33")
),
```

*ADC Data (2-bit I/Q)*:
```python
("max2771_adc", 0,
    Subsignal("i0",     Pins("P14", dir="i")),  # PR38B
    Subsignal("i1",     Pins("P15", dir="i")),  # PR32A
    Subsignal("q0",     Pins("P13", dir="i")),  # PR41A
    Subsignal("q1",     Pins("P12", dir="i")),  # PR44A
    Subsignal("clkout", Pins("M16", dir="i")),  # PR26C
    IOStandard("LVCMOS33")
),
```

### SD Card Interface (BANK 1) ✅ VERIFIED
```python
("sdcard", 0,
    Subsignal("data", Pins("A12 A13 A9 A10", dir="io")),  # DAT0-3
    Subsignal("cmd",  Pins("A11", dir="io")),
    Subsignal("clk",  Pins("B8", dir="o")),
    Subsignal("cd",   Pins("B10", dir="i")),
    IOStandard("LVCMOS33")
),
```

### ESP32 Interface (BANK 0) ✅ VERIFIED
```python
("esp32_gpio", 0,
    Subsignal("gpio6", Pins("A2", dir="io")),  # ECP5_PT4A
    Subsignal("gpio7", Pins("A3", dir="io")),  # ECP5_PT6A
    Subsignal("gpio8", Pins("A6", dir="io")),  # ECP5_PT18B
    Subsignal("gpio9", Pins("A7", dir="io")),  # ECP5_PT29A
    IOStandard("LVCMOS33")
),
```

## Critical Issues Found

### 1. AT86RF215 Pin Conflict ⚠️
**Issue**: Pin C14 appears twice in the schematic:
- AT86_RSTN → C14 (PR2C)
- AT86_MOSI → C14 (PR2D)

**Action Required**: Review schematic sheet 3 to determine correct assignment.

### 2. LVDS vs LVCMOS for AT86RF215
**Issue**: AT86RF215 data lines use LVDS differential pairs, but the schematic shows single-ended connections.

**Action Required**: Verify if AT86RF215 is using LVDS mode or LVCMOS mode.

### 3. Missing Antenna Connections
**Issue**: MAX2771 LNAIN_HI/LO pins connect to external antenna via J13, but actual pin routing needs verification.

## Next Steps

1. ✅ Extract full pin assignment table from schematic
2. ⚠️ Resolve AT86RF215 pin conflicts (C14 issue)
3. ⚠️ Verify LVDS vs LVCMOS configuration for AT86RF215
4. ⚠️ Update `vahya/platforms/vahya.py` with verified pins
5. ⏸️ Test with actual hardware
6. ⏸️ Update timing constraints based on actual routing

## Component Summary

| Component | Part Number | Package | Function | Sheet |
|-----------|-------------|---------|----------|-------|
| U2 | LFE5U-25F-7BG256I | BG256 | Main FPGA | 2 |
| U7 | USB3343-CP | QFN-24 | USB PHY | 5 |
| U1 | AT86RF215M | QFN-48 | RF Transceiver | 3 |
| U8 | MAX2771ETI+ | TQFN-28 | GNSS Frontend | 4 |
| U9 | ESP32-S3FH4R2 | QFN-56 | WiFi/BT MCU | 7 |
| U3 | W25Q32JVSSIQ | SOIC-8 | Config Flash | 2 |
| U4,U5,U6 | TLV62569APDRLR | SOT-6 | Buck Regulators | 6 |

## Power Budget

| Rail | Voltage | Current | Consumers |
|------|---------|---------|-----------|
| +5V0 | 5.0V | Input | USB Type-C, Power jack |
| +3V3 | 3.3V | ~2A | FPGA IO, ESP32, USB3343, Peripherals |
| +2V5 | 2.5V | ~500mA | FPGA VCCAUX, MAX2771 |
| +1V1 | 1.1V | ~1.5A | FPGA VCC core |

**Total Power**: ~10W typical, ~15W maximum

## Connectors

| Designator | Type | Function |
|------------|------|----------|
| J10 | USB Type-C | Main USB (via USB3343) |
| J7 | USB Type-C | ESP32 USB (programming) |
| J8 | 2-pin header | +5V power input |
| J11, J12 | SMA | AT86RF215 RF outputs |
| J13, J14 | U.FL | GNSS antenna, Clock input |
| J5 | U.FL | External clock input for FPGA |
| J6 | MicroSD | SD card slot |
| J3, J4 | 2x8 SMD header | Expansion headers |

## Document References

- **Schematic**: VAHYA_MINI_SCH.PDF (8 sheets, dated 4/01/2025)
- **IBOM**: VAHYA_MINI_IBOM.html
- **AT86RF215 Datasheet**: AT86RF215.pdf
- **ECP5 Family**: Lattice ECP5 datasheet
- **USB3343**: Microchip USB3343 datasheet
- **MAX2771**: Analog Devices MAX2771 datasheet

---

**Analysis Status**: ✅ Initial analysis complete
**Verification Status**: ⚠️ Hardware testing required
**Last Updated**: 2025-11-22
