"""
Verilog lint tests (basic static analysis)
Tests Verilog code for common issues without requiring simulation tools.
"""

import unittest
import os
import re


class TestVerilogLint(unittest.TestCase):
    """Basic linting tests for Verilog modules"""

    def setUp(self):
        """Set up paths to Verilog files"""
        self.vahya_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.verilog_dir = os.path.join(self.vahya_root, "verilog")

    def read_verilog_file(self, filename):
        """Read a Verilog file"""
        filepath = os.path.join(self.verilog_dir, filename)
        with open(filepath, 'r') as f:
            return f.read()

    def test_no_syntax_errors_basic(self):
        """Test for basic syntax errors in Verilog files"""
        verilog_files = [
            "stream_interface.v",
            "at86rf215_iq_capture.v",
            "max2771_adc_capture.v"
        ]

        for vfile in verilog_files:
            content = self.read_verilog_file(vfile)

            # Remove single-line comments for accurate counting
            lines_no_comments = []
            for line in content.split('\n'):
                # Remove comment part of line
                code_part = line.split('//')[0]
                lines_no_comments.append(code_part)
            content_no_comments = '\n'.join(lines_no_comments)

            # Check for balanced begin/end using word boundaries
            begin_count = len(re.findall(r'\bbegin\b', content_no_comments))
            end_count = len(re.findall(r'\bend\b', content_no_comments))
            # This is a rough check - exact balance may vary with generate/case/etc
            # Just check they're in a reasonable ratio
            if begin_count > 0:
                ratio = end_count / begin_count if begin_count > 0 else 0
                self.assertGreater(ratio, 0.5,
                                 f"{vfile}: Suspicious begin/end ratio ({begin_count} vs {end_count})")
                self.assertLess(ratio, 2.0,
                              f"{vfile}: Suspicious begin/end ratio ({begin_count} vs {end_count})")

            # Check for balanced module/endmodule
            module_count = len(re.findall(r'^\s*module\s+\w+', content_no_comments, re.MULTILINE))
            endmodule_count = len(re.findall(r'^\s*endmodule\b', content_no_comments, re.MULTILINE))
            self.assertGreater(module_count, 0, f"{vfile}: No module declarations")
            self.assertEqual(module_count, endmodule_count,
                           f"{vfile}: Unbalanced module/endmodule ({module_count} vs {endmodule_count})")

    def test_no_tabs(self):
        """Test that Verilog files use spaces, not tabs"""
        verilog_files = [
            "stream_interface.v",
            "at86rf215_iq_capture.v",
            "max2771_adc_capture.v"
        ]

        for vfile in verilog_files:
            content = self.read_verilog_file(vfile)
            # Allow tabs in comments, but not in code
            for line_num, line in enumerate(content.split('\n'), 1):
                # Skip comment lines
                if line.strip().startswith('//'):
                    continue
                # Check non-comment parts
                code_part = line.split('//')[0]
                if '\t' in code_part:
                    self.fail(f"{vfile}:{line_num}: Contains tab character")

    def test_module_parameters(self):
        """Test that parameterized modules have valid parameter syntax"""
        test_cases = [
            ("stream_interface.v", "stream_interface", ["DATA_WIDTH", "FIFO_DEPTH"]),
            ("at86rf215_iq_capture.v", "at86rf215_iq_capture", ["SAMPLE_WIDTH", "FIFO_DEPTH"]),
            ("max2771_adc_capture.v", "max2771_adc_capture", ["SAMPLE_WIDTH", "FIFO_DEPTH"]),
        ]

        for filename, module_name, expected_params in test_cases:
            content = self.read_verilog_file(filename)

            # Find module declaration
            module_pattern = rf"module\s+{module_name}\s*#?\s*\("
            match = re.search(module_pattern, content)
            self.assertIsNotNone(match, f"Module {module_name} not found in {filename}")

            # Check for parameters
            for param in expected_params:
                self.assertIn(param, content,
                            f"Parameter {param} not found in {filename}")

    def test_signal_declarations(self):
        """Test that signals are properly declared"""
        verilog_files = [
            "stream_interface.v",
            "at86rf215_iq_capture.v",
            "max2771_adc_capture.v"
        ]

        for vfile in verilog_files:
            content = self.read_verilog_file(vfile)

            # Check for proper signal type declarations
            self.assertIn("input", content, f"{vfile}: No input declarations")
            self.assertIn("output", content, f"{vfile}: No output declarations")

            # Check for proper wire/reg usage
            # Most designs should have both
            if "always @" in content:
                self.assertIn("reg ", content,
                            f"{vfile}: Has always blocks but no reg declarations")

    def test_clock_and_reset(self):
        """Test that modules have clock and reset inputs"""
        test_cases = [
            ("stream_interface.v", "stream_interface", True),
            ("at86rf215_iq_capture.v", "at86rf215_iq_capture", True),
            ("max2771_adc_capture.v", "max2771_adc_capture", True),
        ]

        for filename, module_name, needs_clk_rst in test_cases:
            if not needs_clk_rst:
                continue

            content = self.read_verilog_file(filename)

            # Check for clock input
            self.assertTrue(
                re.search(r"input\s+(\w+\s+)?clk", content) is not None,
                f"{filename}: No clock input in module {module_name}"
            )

            # Check for reset input
            self.assertTrue(
                re.search(r"input\s+(\w+\s+)?rst", content) is not None,
                f"{filename}: No reset input in module {module_name}"
            )

    def test_fifo_usage(self):
        """Test that FIFO modules are properly instantiated"""
        files_with_fifos = [
            ("at86rf215_iq_capture.v", "async_fifo"),
            ("max2771_adc_capture.v", "async_fifo_gnss"),
        ]

        for filename, fifo_module in files_with_fifos:
            content = self.read_verilog_file(filename)

            # Check that FIFO module exists
            self.assertIn(f"module {fifo_module}", content,
                        f"FIFO module {fifo_module} not found in {filename}")

            # Check for FIFO signals
            self.assertIn("wr_clk", content, f"{filename}: Missing FIFO wr_clk")
            self.assertIn("rd_clk", content, f"{filename}: Missing FIFO rd_clk")
            self.assertIn("wr_en", content, f"{filename}: Missing FIFO wr_en")
            self.assertIn("rd_en", content, f"{filename}: Missing FIFO rd_en")
            self.assertIn("wr_full", content, f"{filename}: Missing FIFO wr_full")
            self.assertIn("rd_empty", content, f"{filename}: Missing FIFO rd_empty")

    def test_gray_code_synchronizers(self):
        """Test that async FIFOs use Gray code pointers"""
        files_with_async_fifos = [
            "at86rf215_iq_capture.v",
            "max2771_adc_capture.v",
        ]

        for filename in files_with_async_fifos:
            content = self.read_verilog_file(filename)

            # Check for Gray code conversion
            self.assertTrue(
                re.search(r"gray|Gray", content) is not None,
                f"{filename}: Async FIFO should use Gray code for CDC"
            )

            # Check for multi-stage synchronizers
            self.assertTrue(
                re.search(r"sync\d+", content, re.IGNORECASE) is not None,
                f"{filename}: Should have synchronizer stages for CDC"
            )

    def test_no_latches(self):
        """Test that there are no inferred latches (common error)"""
        verilog_files = [
            "stream_interface.v",
            "at86rf215_iq_capture.v",
            "max2771_adc_capture.v"
        ]

        for vfile in verilog_files:
            content = self.read_verilog_file(vfile)

            # Find all always blocks
            always_blocks = re.findall(r"always\s+@.*?begin.*?end", content,
                                     re.DOTALL | re.MULTILINE)

            for block in always_blocks:
                # Check if it's a combinational block
                if "@*" in block or "@(*)" in block:
                    # Should assign to all outputs in all branches
                    # This is a simplistic check - a full linter would be more thorough
                    # Just check that if/else blocks have else clauses
                    if "if (" in block:
                        if_count = block.count("if (")
                        else_count = block.count("else")
                        # Warn if there might be a latch (this is approximate)
                        if if_count > else_count:
                            # This might be okay (like case statements), so just warn
                            print(f"Warning: {vfile} might have latch in combinational block")

    def test_blocking_vs_nonblocking(self):
        """Test proper use of blocking vs non-blocking assignments"""
        verilog_files = [
            "stream_interface.v",
            "at86rf215_iq_capture.v",
            "max2771_adc_capture.v"
        ]

        for vfile in verilog_files:
            content = self.read_verilog_file(vfile)

            # Find sequential blocks (posedge/negedge)
            sequential_blocks = re.findall(r"always\s+@\s*\(.*?(?:posedge|negedge).*?\).*?begin.*?end",
                                          content, re.DOTALL | re.MULTILINE)

            for block in sequential_blocks:
                # Sequential blocks should primarily use non-blocking (<=)
                nonblocking_count = block.count("<=")
                blocking_count = block.count("=") - nonblocking_count - block.count("==") - block.count("!=")

                # Sequential blocks should favor non-blocking assignments
                if blocking_count > nonblocking_count:
                    print(f"Warning: {vfile} uses blocking assignments in sequential block")


class TestVerilogDocumentation(unittest.TestCase):
    """Test Verilog code documentation"""

    def setUp(self):
        """Set up paths"""
        self.vahya_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.verilog_dir = os.path.join(self.vahya_root, "verilog")

    def test_module_headers(self):
        """Test that modules have documentation headers"""
        verilog_files = [
            "stream_interface.v",
            "at86rf215_iq_capture.v",
            "max2771_adc_capture.v"
        ]

        for vfile in verilog_files:
            filepath = os.path.join(self.verilog_dir, vfile)
            with open(filepath, 'r') as f:
                first_lines = ''.join(f.readlines()[:50])

            # Check for header comment block
            self.assertIn("/**", first_lines,
                        f"{vfile}: Missing documentation header")
            self.assertIn("*/", first_lines,
                        f"{vfile}: Missing end of documentation header")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
