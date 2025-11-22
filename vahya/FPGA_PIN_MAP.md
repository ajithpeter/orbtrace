# Vahya MINI - Complete FPGA Pin Mapping

**FPGA**: Lattice ECP5 LFE5U-25F-7BG256I
**Package**: BG256 (256-ball BGA)
**Date**: 2025-11-22
**Source**: VAHYA_MINI_SCH.PDF (Rev. 4/01/2025)

## Pin Assignment Table

| Signal Name | FPGA Pin | Bank | Function | Direction | Standard | Notes |
|-------------|----------|------|----------|-----------|----------|-------|
| **Clock & Reset** |
| clk26 | C7 | 0 | 26 MHz Main Clock | Input | LVCMOS33 | From Y2 oscillator |
| ext_clkin | (via J5) | - | External clock input | Input | LVCMOS33 | Optional U.FL |
| **Configuration** |
| PROGRAMN | R9 | 8 | Configuration trigger | Input | LVCMOS33 | Pull-up 15K |
| INITN | T9 | 8 | Init status | I/O | LVCMOS33 | Pull-up 15K |
| DONE | P9 | 8 | Config complete | I/O | LVCMOS33 | Pull-up 15K |
| CFG_0 | N10 | 8 | Config mode bit 0 | Input | LVCMOS33 | Pull-down 470R |
| CFG_1 | P10 | 8 | Config mode bit 1 | Input | LVCMOS33 | Pull-up 4.7K |
| CFG_2 | R10 | 8 | Config mode bit 2 | Input | LVCMOS33 | Pull-down 470R |
| **JTAG** |
| TDO | M10 | 8 | JTAG Data Out | Output | LVCMOS33 | To J3 & ESP32 |
| TCK | T10 | 8 | JTAG Clock | Input | LVCMOS33 | From J3 & ESP32 |
| TDI | R11 | 8 | JTAG Data In | Input | LVCMOS33 | From J3 & ESP32 |
| TMS | T11 | 8 | JTAG Mode Select | Input | LVCMOS33 | From J3 & ESP32 |
| **QSPI Flash (W25Q32)** |
| FLASH_CS | R8 | 8 | Chip Select | Output | LVCMOS33 | PB13A/SN/CSN |
| FLASH_CLK | N9 | 8 | SPI Clock | Output | LVCMOS33 | CCLK/MCLK/SCK |
| FLASH_D0 | T8 | 8 | Data 0 (MOSI) | I/O | LVCMOS33 | PB11B/D0 |
| FLASH_D1 | T7 | 8 | Data 1 (MISO) | I/O | LVCMOS33 | PB11A/D1 |
| FLASH_D2 | N7 | 8 | Data 2 (WP) | I/O | LVCMOS33 | PB9B/D2 |
| FLASH_D3 | M7 | 8 | Data 3 (HOLD) | I/O | LVCMOS33 | PB9A/D3 |
| **USB3343 ULPI Interface** |
| USB_DATA0 | G1 | 7 | ULPI Data bit 0 | I/O | LVCMOS33 | PL20A/GR_PCLK7_1 |
| USB_DATA1 | F2 | 7 | ULPI Data bit 1 | I/O | LVCMOS33 | PL11C |
| USB_DATA2 | F1 | 7 | ULPI Data bit 2 | I/O | LVCMOS33 | PL14A |
| USB_DATA3 | E2 | 7 | ULPI Data bit 3 | I/O | LVCMOS33 | PL8B |
| USB_DATA4 | E1 | 7 | ULPI Data bit 4 | I/O | LVCMOS33 | PL11D |
| USB_DATA5 | D1 | 7 | ULPI Data bit 5 | I/O | LVCMOS33 | PL8A |
| USB_DATA6 | C2 | 7 | ULPI Data bit 6 | I/O | LVCMOS33 | PL5B |
| USB_DATA7 | C1 | 7 | ULPI Data bit 7 | I/O | LVCMOS33 | PL5A |
| USB_CLKOUT | K1 | 7 | ULPI Clock (60MHz) | Input | LVCMOS33 | PL23C/PCLKT7_0 |
| USB_DIR | J5 | 7 | ULPI Direction | Input | LVCMOS33 | PL17D |
| USB_NXT | G2 | 7 | ULPI Next | Input | LVCMOS33 | PL14B |
| USB_STP | J4 | 7 | ULPI Stop | Output | LVCMOS33 | PL17C |
| USB_RESET | H2 | 7 | USB3343 Reset | Output | LVCMOS33 | PL20B |
| USB_REFCLK_IN | J1 | 7 | 26MHz Ref Clock | Output | LVCMOS33 | PL23A/PCLKT7_1 |
| **RGB LED** |
| LED_R | B13 | 1 | Red LED | Output | LVCMOS33 | PT60A |
| LED_G | B14 | 1 | Green LED | Output | LVCMOS33 | PT67A |
| LED_B | B12 | 1 | Blue LED | Output | LVCMOS33 | PT56B |
| **User I/O** |
| USER_SW | N6 | 6 | User switch | Input | LVCMOS33 | PL47B, pull-up |
| GSRN | M9 | 8 | Global set/reset | Input | LVCMOS33 | Pull-up 4.7K |
| **SD Card Interface** |
| SD_DAT0 | A12 | 1 | SD Data 0 | I/O | LVCMOS33 | PT53B |
| SD_DAT1 | A13 | 1 | SD Data 1 | I/O | LVCMOS33 | PT65A |
| SD_DAT2 | A9 | 1 | SD Data 2 | I/O | LVCMOS33 | PT42A |
| SD_DAT3 | A10 | 1 | SD Data 3 | I/O | LVCMOS33 | PT42B |
| SD_CMD | A11 | 1 | SD Command | I/O | LVCMOS33 | PT53A |
| SD_CLK | B8 | 1 | SD Clock | Output | LVCMOS33 | PT35B/PCLKC1_0 |
| SD_CD | B10 | 1 | Card Detect | Input | LVCMOS33 | PT44B |
| **ESP32-S3 Interface** |
| ECP5_PT4A | A2 | 0 | GPIO to ESP32 GPIO6 | I/O | LVCMOS33 | PT4A |
| ECP5_PT6A | A3 | 0 | GPIO to ESP32 GPIO7 | I/O | LVCMOS33 | PT6A |
| ECP5_PT18B | A6 | 0 | GPIO to ESP32 GPIO8 | I/O | LVCMOS33 | PT18B |
| ECP5_PT29A | A7 | 0 | GPIO to ESP32 GPIO9 | I/O | LVCMOS33 | PT29A/PCLKT0_0 |
| **AT86RF215 Data Interface (Differential/LVDS)** |
| AT86_TXCLK_P | B16 | 1 | TX Clock + | Output | LVDS/LVCMOS33 | PT35A/PCLKT1_0 |
| AT86_TXCLK_N | B15 | 2 | TX Clock - | Output | LVDS/LVCMOS33 | PR2B/S0_IN |
| AT86_TXD_P | C16 | 1 | TX Data + | Output | LVDS/LVCMOS33 | PT33A/PCLKT1_1 |
| AT86_TXD_N | C15 | 2 | TX Data - | Output | LVDS/LVCMOS33 | PR5B |
| AT86_RXCLK_P | J16 | 2 | RX Clock + | Input | LVDS/LVCMOS33 | PR23A/PCLKT2_1 |
| AT86_RXCLK_N | J15 | 2 | RX Clock - | Input | LVDS/LVCMOS33 | PR23B/PCLKC2_1 |
| AT86_RXD09_P | D16 | 1 | RX Data 09 + | Input | LVDS/LVCMOS33 | PT40A |
| AT86_RXD09_N | E15 | 2 | RX Data 09 - | Input | LVDS/LVCMOS33 | PR8B |
| AT86_RXD24_P | K16 | 2 | RX Data 24 + | Input | LVDS/LVCMOS33 | PR23C/PCLKT2_0 |
| AT86_RXD24_N | K15 | 2 | RX Data 24 - | Input | LVDS/LVCMOS33 | PR23D/PCLKC2_0 |
| **AT86RF215 Control Interface (SPI)** |
| AT86_RSTN | C14 | 2 | Reset (active low) | Output | LVCMOS33 | PR2C |
| AT86_IRQ | G16 | 2 | Interrupt | Input | LVCMOS33 | PR20A/GR_PCLK2_1 |
| AT86_SCLK | K14 | 2 | SPI Clock | Output | LVCMOS33 | PR20D |
| AT86_SELN | E16 | 2 | SPI Select (active low) | Output | LVCMOS33 | PR11D |
| AT86_MISO | F16 | 2 | SPI MISO | Input | LVCMOS33 | PR14A |
| AT86_MOSI | H14 | 2 | SPI MOSI | Output | LVCMOS33 | PR14D |
| **MAX2771 Control Interface (SPI)** |
| MAX2771_SDATA | R15 | 3 | SPI Data | Output | LVCMOS33 | PR38C |
| MAX2771_SCLK | T14 | 3 | SPI Clock | Output | LVCMOS33 | PR41D |
| MAX2771_CSN | R14 | 3 | Chip Select (active low) | Output | LVCMOS33 | PR41B |
| MAX2771_SHDN | R16 | 3 | Shutdown | Output | LVCMOS33 | PR35B/VREF1_3 |
| MAX2771_LD | K13 | 3 | Lock Detect | Input | LVCMOS33 | PR29A/GR_PCLK3_0 |
| **MAX2771 ADC Data (2-bit I/Q)** |
| MAX2771_I0 | P14 | 3 | I channel bit 0 | Input | LVCMOS33 | PR38B |
| MAX2771_I1 | P15 | 3 | I channel bit 1 | Input | LVCMOS33 | PR32A |
| MAX2771_Q0 | P13 | 3 | Q channel bit 0 | Input | LVCMOS33 | PR41A |
| MAX2771_Q1 | P12 | 3 | Q channel bit 1 | Input | LVCMOS33 | PR44A |
| MAX2771_CLKOUT | M16 | 3 | ADC Clock (~16MHz) | Input | LVCMOS33 | PR26C/PCLKT3_0 |
| **Expansion Headers J3/J4** |
| BANK1_PT35A | C8 | 1 | Expansion | I/O | LVCMOS33 | PT35A |
| BANK1_PT33B | D8 | 1 | Expansion | I/O | LVCMOS33 | PT33B |
| BANK1_PT38B | C9 | 1 | Expansion | I/O | LVCMOS33 | PT38B |
| BANK1_PT40A | D9 | 1 | Expansion | I/O | LVCMOS33 | PT40A |
| BANK1_PT44B | C10 | 1 | Expansion | I/O | LVCMOS33 | PT44B |
| BANK1_PT47A | D10 | 1 | Expansion | I/O | LVCMOS33 | PT47A |
| BANK1_PT49B | C11 | 1 | Expansion | I/O | LVCMOS33 | PT49B |
| BANK1_PT51A | D11 | 1 | Expansion | I/O | LVCMOS33 | PT51A |
| BANK1_PT56B | C12 | 1 | Expansion | I/O | LVCMOS33 | PT56B |
| BANK1_PT58A | D12 | 1 | Expansion | I/O | LVCMOS33 | PT58A |
| BANK1_PT60B | C13 | 1 | Expansion | I/O | LVCMOS33 | PT60B |
| BANK1_PT62A | D13 | 1 | Expansion | I/O | LVCMOS33 | PT62A |
| BANK2_PR14B | G15 | 2 | Expansion | I/O | LVCMOS33 | PR14B |
| BANK2_PR14D | H14 | 2 | Expansion | I/O | LVCMOS33 | PR14D |
| BANK2_PR17B | H13 | 2 | Expansion | I/O | LVCMOS33 | PR17B |
| BANK2_PR17C | J13 | 2 | Expansion | I/O | LVCMOS33 | PR17C |
| BANK2_PR17D | J12 | 2 | Expansion | I/O | LVCMOS33 | PR17D |
| BANK3_PR29B | K12 | 3 | Expansion | I/O | LVCMOS33 | PR29B |
| BANK3_PR29C | L13 | 3 | Expansion | I/O | LVCMOS33 | PR29C/GR_PCLK3_1 |
| BANK3_PR32C | L14 | 3 | Expansion | I/O | LVCMOS33 | PR32C |
| BANK3_PR32D | M14 | 3 | Expansion | I/O | LVCMOS33 | PR32D |
| BANK3_PR35C | M13 | 3 | Expansion | I/O | LVCMOS33 | PR35C |
| BANK3_PR35D | N14 | 3 | Expansion | I/O | LVCMOS33 | PR35D |
| BANK3_PR38A | N13 | 3 | Expansion | I/O | LVCMOS33 | PR38A |

## Bank Power Summary

| Bank | VCCIO Voltage | VCCIO Pins | Usage |
|------|---------------|------------|-------|
| 0 | 3.3V | F7, F6 | Clock input, ESP32 GPIO |
| 1 | 3.3V | F11, F10 | AT86RF215 (partial), SD Card, LED, Expansion |
| 2 | 3.3V | H11, J11 | AT86RF215 Control & Data |
| 3 | 3.3V | K11, L11 | MAX2771, Expansion |
| 6 | 3.3V | J7, J6 | User switch, Future expansion |
| 7 | 3.3V | H7, H6 | USB3343 ULPI interface |
| 8 | 3.3V | L6 | Configuration, JTAG, Flash |

## Clock Domains

| Clock | Frequency | Source | FPGA Pin | Usage |
|-------|-----------|--------|----------|-------|
| clk26 | 26 MHz | Y2 oscillator | C7 (PT27A/PCLKC0_1) | System clock |
| usb_clk | 60 MHz | USB3343 CLKOUT | K1 (PL23C/PCLKT7_0) | USB interface |
| at86_rxclk | Variable | AT86RF215 | J16/J15 (LVDS pair) | AT86 RX data |
| max_clkout | ~16.368 MHz | MAX2771 | M16 (PR26C/PCLKT3_0) | GNSS ADC data |
| ext_clk | Variable | External (J5) | Via R8/R9 (DNP) | Optional external |

## Differential Pairs

The AT86RF215 interface uses differential signaling. Pairs should be length-matched:

| Pair Name | P Pin | N Pin | Bank | Length Match |
|-----------|-------|-------|------|--------------|
| AT86_TXCLK | B16 | B15 | 1/2 | ±5 mil |
| AT86_TXD | C16 | C15 | 1/2 | ±5 mil |
| AT86_RXCLK | J16 | J15 | 2 | ±5 mil |
| AT86_RXD09 | D16 | E15 | 1/2 | ±5 mil |
| AT86_RXD24 | K16 | K15 | 2 | ±5 mil |

**Note**: These pairs cross bank boundaries (Bank 1 ↔ Bank 2), which may require careful routing and impedance control.

## Special Function Pins

| Pin | Function | Default | Configuration |
|-----|----------|---------|---------------|
| C7 | PT27A/PCLKC0_1 | I/O | Clock input (26 MHz) |
| K1 | PL23C/PCLKT7_0 | I/O | USB clock input (60 MHz) |
| M16 | PR26C/PCLKT3_0 | I/O | MAX2771 clock input (~16 MHz) |
| J16 | PR23A/PCLKT2_1 | I/O | AT86 RX clock + |
| R9 | PROGRAMN | Config | Configuration trigger |
| T9 | INITN | Config | Init status indicator |
| P9 | DONE | Config | Configuration done indicator |

## Notes

1. **Verified Pins** (✅): USB ULPI, RGB LED, User Switch, Clock, SD Card, ESP32 interface
2. **Needs Verification** (⚠️): AT86RF215 pins (especially MOSI conflict), MAX2771 pins
3. **External Clocks**: Optional external clock via J5 U.FL connector (DNP resistors R8/R9)
4. **LVDS Configuration**: AT86RF215 may use LVDS - verify with hardware testing
5. **Pull Resistors**: Configuration pins have appropriate pull-ups/pull-downs per TN1260
6. **Decoupling**: Each VCCIO bank has 0.1µF + 0.01µF decoupling capacitors

## Pin Conflict Resolution Required

⚠️ **AT86_MOSI Pin Assignment**: Schematic shows conflicting assignments. Based on trace analysis:
- Original schematic text shows AT86_MOSI → PR2D (C14)
- But C14 is already assigned to AT86_RSTN → PR2C

**Resolution**: Schematic review suggests AT86_MOSI should be **H14 (PR14D)** based on the harness connector assignments on J4.

## References

- ECP5 Family Data Sheet (Lattice)
- TN1260: sysCONFIG Usage Guide for ECP5/ECP5-5G
- VAHYA_MINI_SCH.PDF Sheets 1-8
- Migen/LiteX Platform Documentation

---

**Status**: 🔄 In Progress
**Last Updated**: 2025-11-22
**Verified with Hardware**: ⏸️ Pending
