# Vahya Hardware Integration Notes

This document describes the steps needed to fully integrate the LiteX SoC with actual Vahya v1.0b hardware and external peripherals.

## Current Status

### ✅ Completed
- [x] Updated platform to match Vahya v1.0b base board
- [x] Corrected clock frequency (26 MHz)
- [x] Corrected FPGA part number (LFE5U-25F-7BG256C)
- [x] Updated ULPI USB PHY pinout
- [x] Updated LED interface (RGB LED instead of LED array)
- [x] Added user switch resource
- [x] Updated SoC for 26 MHz clock input
- [x] Created framework for AT86RF215 integration
- [x] Created framework for MAX2771 integration
- [x] Created Verilog data capture modules
- [x] Created Python integration wrappers
- [x] Comprehensive documentation

### ⚠️ Placeholder/Unverified
The following pin assignments are **PLACEHOLDERS** and must be verified/updated:

1. **AT86RF215 Interface**
   - All pins (SPI, I/Q data buses, control signals)
   - 26 MHz reference clock routing

2. **MAX2771 Interface**
   - All pins (SPI, ADC data, control signals)
   - Reference clock input/output

3. **SPI Flash**
   - Quad SPI pins (may use ECP5 internal flash instead)

4. **Optional Peripherals**
   - Additional UART interfaces
   - Additional SPI master interfaces
   - I2C master interface
   - GPIO expansion

## Integration Steps

### Step 1: Verify Base Board Resources

Check that the following base Vahya v1.0b resources are correctly defined:

```python
# These should match the actual hardware:
- clk26: Pin J14 (26 MHz oscillator)
- RGB LED: Pins B13 (R), B14 (G), B12 (B)
- User switch: Pin N6
- ULPI data: G1 F2 F1 E2 E1 D1 C2 C1
- ULPI clk: K1
- ULPI dir: J5
- ULPI nxt: G2
- ULPI stp: J4
- ULPI rst: H2
```

**Action**: Compare with Vahya v1.0b schematic/PCB and verify.

### Step 2: Identify Expansion Connector Pinout

The external peripherals (AT86RF215, MAX2771, etc.) connect via expansion connectors.

**Required Information**:
1. Expansion connector pinout (which FPGA pins are available?)
2. Signal assignments on expansion boards
3. Voltage levels (should all be 3.3V LVCMOS33)
4. Clock routing (especially for high-speed signals)

**Action**: Obtain schematic for:
- Vahya v1.0b base board (expansion connector details)
- AT86RF215 expansion board (if exists)
- MAX2771 expansion board (if exists)

### Step 3: Update AT86RF215 Pin Assignments

Once you have the actual pin assignments, update `vahya/platforms/vahya.py`:

```python
("at86rf215", 0,
    # SPI Interface - UPDATE THESE PINS!
    Subsignal("spi_clk",  Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("spi_mosi", Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("spi_miso", Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("spi_cs_n", Pins("XX"), IOStandard("LVCMOS33")),

    # Control/Status - UPDATE THESE PINS!
    Subsignal("rst_n",    Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("irq",      Pins("XX"), IOStandard("LVCMOS33")),

    # I/Q Data Interface (14-bit parallel) - UPDATE THESE PINS!
    # RF09 (Sub-GHz)
    Subsignal("rf09_txiq", Pins("XX XX ... 14 pins total"), IOStandard("LVCMOS33")),
    Subsignal("rf09_rxiq", Pins("XX XX ... 14 pins total"), IOStandard("LVCMOS33")),
    Subsignal("rf09_txen", Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("rf09_rxen", Pins("XX"), IOStandard("LVCMOS33")),

    # RF24 (2.4GHz)
    Subsignal("rf24_txiq", Pins("XX XX ... 14 pins total"), IOStandard("LVCMOS33")),
    Subsignal("rf24_rxiq", Pins("XX XX ... 14 pins total"), IOStandard("LVCMOS33")),
    Subsignal("rf24_txen", Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("rf24_rxen", Pins("XX"), IOStandard("LVCMOS33")),

    # Clocking
    Subsignal("clk_26mhz", Pins("XX"), IOStandard("LVCMOS33")),
),
```

**Critical Considerations**:
- The 14-bit parallel I/Q data buses are high-speed (up to 4 MHz sample rate)
- Minimize trace length and maintain impedance matching
- Group related signals together (RF09 I/Q, RF24 I/Q)
- Consider using adjacent FPGA pins for parallel buses

### Step 4: Update MAX2771 Pin Assignments

Update `vahya/platforms/vahya.py` for MAX2771:

```python
("max2771", 0,
    # SPI Interface - UPDATE THESE PINS!
    Subsignal("spi_clk",  Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("spi_mosi", Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("spi_miso", Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("spi_cs_n", Pins("XX"), IOStandard("LVCMOS33")),

    # Control - UPDATE THESE PINS!
    Subsignal("idle",     Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("shdn",     Pins("XX"), IOStandard("LVCMOS33")),

    # ADC Data Interface (2-bit I + 2-bit Q) - UPDATE THESE PINS!
    Subsignal("iq_sign",  Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("iq_mag",   Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("qq_sign",  Pins("XX"), IOStandard("LVCMOS33")),
    Subsignal("qq_mag",   Pins("XX"), IOStandard("LVCMOS33")),

    # Clock (output from MAX2771) - UPDATE THIS PIN!
    Subsignal("clkout",   Pins("XX"), IOStandard("LVCMOS33")),

    # Reference clock input - UPDATE THIS PIN!
    Subsignal("clk_ref",  Pins("XX"), IOStandard("LVCMOS33")),
),
```

**Critical Considerations**:
- `clkout` is a high-speed clock (~16 MHz)
- Route to a clock-capable FPGA pin if possible
- ADC data must be sampled synchronously with `clkout`
- Keep clock traces short and away from noisy signals

### Step 5: Timing Constraints

After updating pin assignments, verify timing constraints in platform's `do_finalize()`:

```python
def do_finalize(self, fragment):
    LatticePlatform.do_finalize(self, fragment)

    # Main clock
    self.add_period_constraint(self.lookup_request("clk26", loose=True), 1e9/26e6)

    # USB ULPI clock
    self.add_period_constraint(self.lookup_request("ulpi:clk", loose=True), 1e9/60e6)

    # MAX2771 sample clock (if used)
    try:
        self.add_period_constraint(
            self.lookup_request("max2771:clkout", loose=True),
            1e9/16.368e6
        )
    except:
        pass

    # AT86RF215 26 MHz reference (if separate from main clock)
    try:
        self.add_period_constraint(
            self.lookup_request("at86rf215:clk_26mhz", loose=True),
            1e9/26e6
        )
    except:
        pass
```

### Step 6: Test Basic Functionality

Before adding complex peripherals, test the base system:

1. **Build minimal bitstream**:
   ```bash
   cd vahya/soc
   python vahya_soc.py --build
   ```

2. **Program FPGA**:
   ```bash
   export VahyaPlatformIP="192.168.4.1"
   export VahyaPlatformTTY="/dev/ttyUSB0"
   # Programming happens automatically via FTP/MicroPython
   ```

3. **Verify**:
   - RGB LED should blink (heartbeat)
   - USB device should enumerate
   - Serial console should be accessible

### Step 7: Add Peripherals Incrementally

Enable peripherals one at a time:

1. **Test USB CDC-ACM first**:
   - Build with minimal config
   - Verify serial communication
   - Test command/response

2. **Add SPI Flash**:
   - Verify flash chip detection
   - Test read operations
   - Enable memory mapping

3. **Add AT86RF215**:
   - Connect SPI control only first
   - Read chip ID register to verify connection
   - Enable I/Q capture after SPI works
   - Test USB bulk streaming

4. **Add MAX2771**:
   - Connect SPI control only first
   - Write configuration registers
   - Enable ADC capture after SPI works
   - Test USB bulk streaming

### Step 8: Test High-Speed Data Paths

Once basic peripherals work, test the data capture:

1. **AT86RF215 I/Q Capture**:
   ```python
   # Enable RF09 RX capture
   csr.at86rf215_ctrl.control.write(0x01)  # Enable

   # Check for data
   # USB bulk IN endpoint should stream I/Q data
   ```

2. **MAX2771 ADC Capture**:
   ```python
   # Configure MAX2771 for GPS L1
   # Enable capture
   csr.max2771_ctrl.control.write(0x01)

   # Check for data
   # USB bulk IN endpoint should stream ADC data
   ```

3. **Monitor Status**:
   ```python
   # Check for FIFO overflows
   status = csr.at86rf215_ctrl.status.read()
   if status & 0x1:
       print("AT86RF215 FIFO overflow!")

   status = csr.max2771_ctrl.status.read()
   if status & 0x1:
       print("MAX2771 FIFO overflow!")
   ```

## Common Issues and Solutions

### Issue 1: USB Not Enumerating

**Possible Causes**:
- ULPI PHY not providing 60 MHz clock
- Incorrect ULPI pin assignments
- Missing VBUS connection

**Debug Steps**:
1. Verify ULPI clock is present (scope on pin K1)
2. Check USB3343 power and reset
3. Verify pin assignments match schematic
4. Try different USB port/hub

### Issue 2: SPI Communication Fails

**Possible Causes**:
- Wrong pin assignments
- Incorrect SPI clock polarity/phase
- Device not powered

**Debug Steps**:
1. Verify SPI pins with logic analyzer
2. Check device power rails
3. Verify chip select is active during transfer
4. Check SPI clock frequency (should be 1 MHz initially)

### Issue 3: I/Q Data Capture Issues

**Possible Causes**:
- Incorrect clock routing
- Clock domain crossing problems
- FIFO overflow

**Debug Steps**:
1. Verify data clock is present (AT86RF215: 26 MHz, MAX2771: ~16 MHz)
2. Monitor FIFO overflow flags
3. Reduce sample rate if bandwidth is insufficient
4. Check USB streaming is keeping up

### Issue 4: Timing Violations

**Possible Causes**:
- Clock constraints not properly specified
- Long routing paths on high-speed signals
- Insufficient FPGA resources

**Debug Steps**:
1. Review synthesis timing report
2. Add specific timing constraints for critical paths
3. Reduce system clock frequency if needed
4. Simplify design or use larger FPGA

## Pin Assignment Checklist

Before declaring the hardware integration complete:

- [ ] All ULPI pins verified against schematic
- [ ] All AT86RF215 pins verified against schematic
- [ ] All MAX2771 pins verified against schematic
- [ ] All optional peripheral pins verified
- [ ] Timing constraints added for all clocks
- [ ] Pin assignments tested with continuity check
- [ ] Signal integrity verified for high-speed signals
- [ ] USB enumeration successful
- [ ] AT86RF215 SPI communication working
- [ ] MAX2771 SPI communication working
- [ ] AT86RF215 I/Q capture working
- [ ] MAX2771 ADC capture working
- [ ] USB bulk streaming working
- [ ] No FIFO overflows under normal operation
- [ ] No timing violations in synthesis

## Reference Documents Needed

To complete the integration, you'll need:

1. **Vahya v1.0b Schematic**
   - Base board design
   - Expansion connector pinout
   - Power distribution

2. **AT86RF215 Datasheet**
   - Interface timing diagrams
   - SPI register map
   - I/Q data format

3. **MAX2771 Datasheet**
   - Interface timing diagrams
   - SPI register map
   - Configuration examples

4. **USB3343 Datasheet**
   - ULPI interface specification
   - Timing requirements

5. **ECP5 Family Datasheet**
   - I/O standards
   - Clock resources
   - Package pinout

## Contact

For questions about actual hardware pinouts, contact the Vahya hardware designer
or refer to the official Vahya repository.

## Next Steps

1. **Obtain schematics** for Vahya v1.0b and expansion boards
2. **Update pin assignments** in `vahya/platforms/vahya.py`
3. **Test incrementally** as described in Step 7
4. **Document** any issues or modifications needed
5. **Update** this document with actual pin assignments once verified
