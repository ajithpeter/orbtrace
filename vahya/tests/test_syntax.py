"""
Syntax and import validation tests
These tests check that all modules have valid Python syntax
without requiring full LiteX/Migen environment.
"""

import unittest
import py_compile
import os
import sys


class TestSyntax(unittest.TestCase):
    """Test that all Python files have valid syntax"""

    def setUp(self):
        """Set up test paths"""
        self.vahya_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_platform_syntax(self):
        """Test platform file syntax"""
        platform_file = os.path.join(self.vahya_root, "platforms", "vahya.py")
        try:
            py_compile.compile(platform_file, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Syntax error in vahya.py: {e}")

    def test_soc_syntax(self):
        """Test SoC file syntax"""
        soc_file = os.path.join(self.vahya_root, "soc", "vahya_soc.py")
        try:
            py_compile.compile(soc_file, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Syntax error in vahya_soc.py: {e}")

    def test_at86rf215_syntax(self):
        """Test AT86RF215 module syntax"""
        at86rf215_file = os.path.join(self.vahya_root, "peripherals", "at86rf215.py")
        try:
            py_compile.compile(at86rf215_file, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Syntax error in at86rf215.py: {e}")

    def test_max2771_syntax(self):
        """Test MAX2771 module syntax"""
        max2771_file = os.path.join(self.vahya_root, "peripherals", "max2771.py")
        try:
            py_compile.compile(max2771_file, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Syntax error in max2771.py: {e}")

    def test_all_verilog_files_exist(self):
        """Test that all Verilog files exist"""
        verilog_dir = os.path.join(self.vahya_root, "verilog")

        verilog_files = [
            "stream_interface.v",
            "at86rf215_iq_capture.v",
            "max2771_adc_capture.v"
        ]

        for vfile in verilog_files:
            vpath = os.path.join(verilog_dir, vfile)
            self.assertTrue(os.path.exists(vpath), f"Verilog file not found: {vfile}")

    def test_verilog_module_declarations(self):
        """Test that Verilog files have proper module declarations"""
        verilog_dir = os.path.join(self.vahya_root, "verilog")

        test_cases = [
            ("stream_interface.v", "stream_interface"),
            ("stream_interface.v", "stream_loopback"),
            ("at86rf215_iq_capture.v", "at86rf215_iq_capture"),
            ("at86rf215_iq_capture.v", "async_fifo"),
            ("max2771_adc_capture.v", "max2771_adc_capture"),
            ("max2771_adc_capture.v", "async_fifo_gnss"),
        ]

        for filename, module_name in test_cases:
            filepath = os.path.join(verilog_dir, filename)
            with open(filepath, 'r') as f:
                content = f.read()
                self.assertIn(f"module {module_name}", content,
                            f"Module {module_name} not found in {filename}")
                self.assertIn("endmodule", content,
                            f"endmodule not found in {filename}")

    def test_documentation_exists(self):
        """Test that documentation files exist"""
        docs = [
            "README.md",
            "HARDWARE_INTEGRATION.md",
            "verilog/INTEGRATION_GUIDE.md"
        ]

        for doc in docs:
            doc_path = os.path.join(self.vahya_root, doc)
            self.assertTrue(os.path.exists(doc_path), f"Documentation not found: {doc}")


class TestFileStructure(unittest.TestCase):
    """Test that project structure is correct"""

    def setUp(self):
        """Set up test paths"""
        self.vahya_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_directory_structure(self):
        """Test that all required directories exist"""
        required_dirs = [
            "platforms",
            "soc",
            "peripherals",
            "verilog",
            "tests"
        ]

        for dirname in required_dirs:
            dirpath = os.path.join(self.vahya_root, dirname)
            self.assertTrue(os.path.isdir(dirpath), f"Directory not found: {dirname}")

    def test_init_files(self):
        """Test that __init__.py files exist where needed"""
        init_files = [
            "peripherals/__init__.py",
            "tests/__init__.py"
        ]

        for init_file in init_files:
            init_path = os.path.join(self.vahya_root, init_file)
            self.assertTrue(os.path.exists(init_path), f"__init__.py not found: {init_file}")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
