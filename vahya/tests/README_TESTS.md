# Vahya Test Suite

This directory contains comprehensive tests for the Vahya platform SoC implementation.

## Test Coverage

### 1. Syntax Validation (`test_syntax.py`)
Tests that all Python files have valid syntax and proper structure.

**Tests**:
- Platform file syntax validation
- SoC file syntax validation
- Peripheral modules syntax validation
- Verilog file existence
- Verilog module declarations
- Documentation file existence
- Directory structure
- `__init__.py` files presence

**Run**:
```bash
cd /home/user/orbtrace/vahya
python -m unittest tests.test_syntax -v
```

**Status**: ✅ All 9 tests passing

### 2. Verilog Lint Tests (`test_verilog_lint.py`)
Static analysis of Verilog modules for common issues and best practices.

**Tests**:
- Basic syntax validation (balanced begin/end, module/endmodule)
- No tabs in code (spaces only)
- Module parameter definitions
- Signal declarations (input/output/wire/reg)
- Clock and reset inputs
- FIFO usage and instantiation
- Gray code synchronizers for async FIFOs
- Latch inference detection
- Blocking vs non-blocking assignment usage
- Module documentation headers

**Run**:
```bash
cd /home/user/orbtrace/vahya
python -m unittest tests.test_verilog_lint -v
```

**Status**: ✅ All 10 tests passing

### 3. Platform Tests (`test_platform.py`)
Unit tests for the Vahya platform definition (requires LiteX environment).

**Tests**:
- Platform instantiation
- FPGA device specification
- Clock configuration (26 MHz)
- Resource existence (clock, ULPI, LEDs, switch)
- AT86RF215 resource definition
- MAX2771 resource definition
- Serial UART resources
- SPI master resources
- I2C resources
- Multiple device variants (25F/45F)
- Invalid device handling
- Toolchain configuration

**Run** (requires LiteX):
```bash
cd /home/user/orbtrace/vahya
python -m unittest tests.test_platform -v
```

**Status**: ⏸️ Requires LiteX environment

### 4. Peripheral Tests (`test_peripherals.py`)
Unit tests for peripheral module wrappers (requires LiteX environment).

**Tests**:
- AT86RF215 register definitions
- AT86RF215 command codes
- AT86RF215 state values
- MAX2771 configuration register builder
- MAX2771 PLL configuration
- MAX2771 preset configurations (GPS L1, Galileo E1, GLONASS L1)
- Sample rate calculations
- Bandwidth requirement calculations
- Module imports
- Module documentation

**Run** (requires LiteX):
```bash
cd /home/user/orbtrace/vahya
python -m unittest tests.test_peripherals -v
```

**Status**: ⏸️ Requires LiteX environment

## Test Results Summary

### Current Results (without LiteX environment)
```
test_syntax.py:        9/9 tests passed ✅
test_verilog_lint.py: 10/10 tests passed ✅
test_platform.py:     Requires LiteX ⏸️
test_peripherals.py:  Requires LiteX ⏸️
```

### With LiteX Environment
All tests should pass when run in a properly configured LiteX environment.

## Build Verification

### Prerequisites

To build the Vahya SoC, you need:

1. **LiteX Toolchain**:
   ```bash
   wget https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py
   chmod +x litex_setup.py
   ./litex_setup.py --init --install --user
   ```

2. **RISC-V Toolchain**:
   ```bash
   ./litex_setup.py --gcc=riscv
   ```

3. **FPGA Toolchain** (Yosys, nextpnr-ecp5):
   ```bash
   sudo apt-get install yosys nextpnr-ecp5
   # Or
   ./litex_setup.py --dev
   ```

4. **Python Dependencies**:
   ```bash
   pip install migen litex pyserial amaranth
   ```

### Build Commands

#### 1. Syntax Check (no build)
```bash
cd vahya/soc
python vahya_soc.py --help
```

This should display help without errors if all imports work.

#### 2. Generate Verilog (no synthesis)
```bash
cd vahya/soc
python vahya_soc.py --build --no-compile
```

This generates Verilog output without running synthesis tools.

#### 3. Full Build
```bash
cd vahya/soc
python vahya_soc.py --build --sys-clk-freq 75e6
```

Expected outputs:
- `build/vahya/gateware/vahya.v` - Top-level Verilog
- `build/vahya/gateware/vahya.bit` - FPGA bitstream
- `build/vahya/software/` - BIOS and firmware
- `build/vahya/csr.csv` - CSR register map

#### 4. Build with DFU
```bash
cd vahya/soc
python vahya_soc.py --build --with-dfu --usb-vid 0x1209 --usb-pid 0x5070
```

### Build Verification Checklist

- [ ] No import errors when running `vahya_soc.py --help`
- [ ] Platform instantiation successful
- [ ] Clock and reset generator configured correctly (26 MHz → 75 MHz)
- [ ] ULPI USB interface configured
- [ ] Verilog modules found and instantiated
- [ ] Synthesis completes without errors
- [ ] No timing violations (check timing report)
- [ ] Bitstream generation successful
- [ ] CSR map generated correctly
- [ ] BIOS builds successfully

### Expected Resource Usage (ECP5 LFE5U-25F)

Approximate resource usage for full SoC with all peripherals:

| Resource | Usage | Total | Percentage |
|----------|-------|-------|------------|
| LUTs     | ~15K  | 24K   | ~60%       |
| FFs      | ~10K  | 24K   | ~40%       |
| BRAM     | ~50   | 56    | ~90%       |
| DSPs     | 0     | 28    | 0%         |

**Note**: These are estimates. Actual usage depends on configuration.

### Common Build Issues

#### Issue 1: Module Not Found Errors
```
ModuleNotFoundError: No module named 'migen'
```

**Solution**: Install LiteX environment:
```bash
./litex_setup.py --init --install --user
```

#### Issue 2: Toolchain Not Found
```
ERROR: Yosys not found
```

**Solution**: Install FPGA toolchain:
```bash
sudo apt-get install yosys nextpnr-ecp5
```

#### Issue 3: Import Errors for Orbtrace Modules
```
ModuleNotFoundError: No module named 'orbtrace'
```

**Solution**: Run from within orbtrace repository structure:
```bash
cd /home/user/orbtrace/vahya/soc
python vahya_soc.py --build
```

#### Issue 4: Timing Violations
```
ERROR: Max frequency for clock 'sys': XX.X MHz
```

**Solutions**:
1. Reduce system clock frequency: `--sys-clk-freq 60e6`
2. Check critical path in timing report
3. Add timing constraints for specific paths
4. Simplify design or optimize critical modules

## Integration Testing

For integration testing with actual hardware, see:
- `../HARDWARE_INTEGRATION.md` - Hardware integration guide
- `../verilog/INTEGRATION_GUIDE.md` - Verilog integration guide

### Integration Test Plan

1. **USB Enumeration**:
   - Program FPGA with bitstream
   - Verify USB device enumeration
   - Check VID/PID match

2. **Serial Console**:
   - Open serial port (`/dev/ttyACM0`)
   - Verify BIOS boot messages
   - Test command/response

3. **SPI Flash**:
   - Read flash ID
   - Verify memory mapping
   - Test read operations

4. **AT86RF215** (if connected):
   - Configure SPI
   - Read chip ID
   - Configure band settings
   - Enable I/Q capture
   - Verify USB streaming

5. **MAX2771** (if connected):
   - Configure SPI
   - Write configuration registers
   - Enable ADC capture
   - Verify USB streaming

6. **Performance**:
   - Monitor FIFO overflow flags
   - Check USB throughput
   - Verify timing margins

## Continuous Integration

### Automated Tests (CI/CD)

For CI/CD pipelines, run:

```bash
# Quick syntax check (no dependencies)
python -m unittest tests.test_syntax tests.test_verilog_lint -v

# Full test suite (requires LiteX)
python -m unittest discover tests -v

# Build verification
cd vahya/soc
python vahya_soc.py --help
python vahya_soc.py --build --no-compile  # Verilog generation only
```

### Pre-commit Hooks

Recommended pre-commit checks:
```bash
#!/bin/bash
# .git/hooks/pre-commit

cd vahya
python -m unittest tests.test_syntax tests.test_verilog_lint
if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi
```

## Test Maintenance

### Adding New Tests

1. **For Python modules**:
   - Add tests to `test_platform.py` or `test_peripherals.py`
   - Follow existing test patterns
   - Use descriptive test names

2. **For Verilog modules**:
   - Add to `test_verilog_lint.py`
   - Test for common Verilog issues
   - Verify module interfaces

3. **For new features**:
   - Create dedicated test file if needed
   - Update this README
   - Update build verification checklist

### Test Coverage Goals

- ✅ 100% of Python files syntax-checked
- ✅ 100% of Verilog files lint-checked
- ⏸️ 80%+ of platform resources tested (needs LiteX)
- ⏸️ 80%+ of peripheral functions tested (needs LiteX)
- ⏸️ All critical paths tested (needs hardware)

## Contact

For questions about tests or build issues:
1. Check `../HARDWARE_INTEGRATION.md`
2. Check `../verilog/INTEGRATION_GUIDE.md`
3. Review test output carefully
4. Check LiteX documentation

## References

- [LiteX Documentation](https://github.com/enjoy-digital/litex)
- [Python unittest](https://docs.python.org/3/library/unittest.html)
- [Verilog Best Practices](http://www.sunburst-design.com/papers/)
- [Orbtrace Project](https://github.com/orbcode/orbtrace)
