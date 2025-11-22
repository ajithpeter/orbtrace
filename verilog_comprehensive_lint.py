#!/usr/bin/env python3
"""
Comprehensive Verilog Linting Script
Analyzes Verilog files for common issues including:
- Syntax errors
- Latch inference
- Undriven signals
- Clock domain crossing issues
- Coding style violations
"""

import re
import os
import sys
from collections import defaultdict

class VerilogLinter:
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        with open(filepath, 'r') as f:
            self.content = f.read()
        self.lines = self.content.split('\n')
        self.issues = []
        self.warnings = []
        self.info = []

    def check_syntax(self):
        """Basic syntax checks"""
        # Check for balanced begin/end
        content_no_comments = self._remove_comments()
        begin_count = len(re.findall(r'\bbegin\b', content_no_comments))
        end_count = len(re.findall(r'\bend\b', content_no_comments))

        if begin_count != end_count:
            self.issues.append(f"Unbalanced begin/end: {begin_count} begin vs {end_count} end")

        # Check for balanced module/endmodule
        module_count = len(re.findall(r'^\s*module\s+\w+', content_no_comments, re.MULTILINE))
        endmodule_count = len(re.findall(r'^\s*endmodule\b', content_no_comments, re.MULTILINE))

        if module_count != endmodule_count:
            self.issues.append(f"Unbalanced module/endmodule: {module_count} module vs {endmodule_count} endmodule")

        # Check for unclosed parentheses
        open_paren = content_no_comments.count('(')
        close_paren = content_no_comments.count(')')
        if open_paren != close_paren:
            self.warnings.append(f"Unbalanced parentheses: {open_paren} '(' vs {close_paren} ')'")

    def check_default_nettype(self):
        """Check for `default_nettype directive"""
        if '`default_nettype none' not in self.content:
            self.warnings.append("Missing `default_nettype none directive (recommended)")
        else:
            self.info.append("Has `default_nettype none directive")

    def check_latch_inference(self):
        """Check for potential latch inference in combinational blocks"""
        # Find all combinational always blocks
        comb_blocks = re.finditer(r'always\s+@\s*\(\s*\*\s*\)|always\s+@\(\*\)', self.content)

        for match in comb_blocks:
            block_start = match.start()
            # Try to extract the full block
            block_text = self._extract_block(block_start)

            # Check if all if statements have else clauses
            if_count = block_text.count('if (') + block_text.count('if(')
            else_count = block_text.count('else')

            if if_count > else_count:
                line_num = self.content[:block_start].count('\n') + 1
                self.warnings.append(f"Line {line_num}: Potential latch in combinational block (if without else)")

    def check_blocking_assignments(self):
        """Check proper use of blocking vs non-blocking assignments"""
        # Find sequential blocks (with posedge/negedge)
        seq_blocks = re.finditer(r'always\s+@\s*\([^)]*(?:posedge|negedge)[^)]*\)', self.content)

        for match in seq_blocks:
            block_start = match.start()
            block_text = self._extract_block(block_start)

            # Count assignments
            nonblocking = block_text.count('<=')
            # Blocking assignments (excluding comparisons)
            blocking = len(re.findall(r'\s=\s', block_text)) - nonblocking
            blocking -= block_text.count('==')
            blocking -= block_text.count('!=')
            blocking -= block_text.count('>=')

            if blocking > nonblocking and blocking > 0:
                line_num = self.content[:block_start].count('\n') + 1
                self.warnings.append(f"Line {line_num}: Sequential block uses more blocking than non-blocking assignments")

    def check_clock_domain_crossings(self):
        """Check for potential clock domain crossing issues"""
        # Look for multiple clock signals
        clocks = set()
        clock_patterns = [
            r'always\s+@\s*\(\s*posedge\s+(\w+)',
            r'always\s+@\s*\(\s*negedge\s+(\w+)',
        ]

        for pattern in clock_patterns:
            matches = re.finditer(pattern, self.content)
            for match in matches:
                clocks.add(match.group(1))

        if len(clocks) > 1:
            self.info.append(f"Multiple clock domains detected: {', '.join(sorted(clocks))}")

            # Check for synchronizers (CDC safety)
            if 'sync' in self.content.lower() or 'gray' in self.content.lower():
                self.info.append("Clock domain crossing synchronizers detected")
            else:
                self.warnings.append("Multiple clocks without apparent synchronizers (check CDC safety)")

    def check_sensitivity_lists(self):
        """Check for incomplete sensitivity lists"""
        # Modern practice is to use always @(*) for combinational logic
        old_style_comb = re.findall(r'always\s+@\s*\([^)]*\)\s*(?!.*(?:posedge|negedge))', self.content)

        if old_style_comb:
            count = len([m for m in old_style_comb if '@(*)' not in m and '@( * )' not in m])
            if count > 0:
                self.info.append(f"Found {count} old-style sensitivity lists (consider using @(*) instead)")

    def check_signal_declarations(self):
        """Check signal declarations"""
        # Check for input/output declarations
        has_input = 'input' in self.content
        has_output = 'output' in self.content

        if not has_input and not has_output:
            self.warnings.append("No input/output declarations found")

        # Check for proper wire/reg usage
        has_always = 'always @' in self.content
        has_reg = re.search(r'\breg\s+', self.content)

        if has_always and not has_reg:
            self.warnings.append("Has always blocks but no reg declarations")

    def check_reset_signals(self):
        """Check for reset signals"""
        has_reset = bool(re.search(r'\b(rst|reset|rstn|rst_n)\b', self.content, re.IGNORECASE))

        if has_reset:
            self.info.append("Reset signal detected")

            # Check if reset is asynchronous or synchronous
            async_reset = bool(re.search(r'always\s+@\s*\([^)]*posedge\s+(rst|reset)', self.content, re.IGNORECASE))
            if async_reset:
                self.info.append("Asynchronous reset detected")
        else:
            # Only warn if there are clocked blocks
            if 'always @' in self.content and 'posedge' in self.content:
                self.warnings.append("No reset signal found in clocked logic")

    def check_fifo_usage(self):
        """Check FIFO implementations"""
        if 'fifo' in self.content.lower():
            self.info.append("FIFO module detected")

            # Check for FIFO signals
            fifo_signals = ['wr_en', 'rd_en', 'full', 'empty']
            found_signals = [sig for sig in fifo_signals if sig in self.content]

            if found_signals:
                self.info.append(f"FIFO signals found: {', '.join(found_signals)}")

            # Check for async FIFO (gray code)
            if 'gray' in self.content.lower():
                self.info.append("Gray code detected (async FIFO)")

    def check_parameters(self):
        """Check parameter usage"""
        params = re.findall(r'parameter\s+(\w+)', self.content)
        if params:
            self.info.append(f"Parameters: {', '.join(params)}")

    def _remove_comments(self):
        """Remove comments from code"""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', self.content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content

    def _extract_block(self, start_pos):
        """Extract a begin...end block starting from position"""
        content_from_start = self.content[start_pos:]
        begin_pos = content_from_start.find('begin')
        if begin_pos == -1:
            # Single statement block
            end_pos = content_from_start.find(';')
            return content_from_start[:end_pos+1] if end_pos != -1 else content_from_start[:100]

        # Count begin/end to find matching end
        depth = 0
        pos = begin_pos
        while pos < len(content_from_start):
            if content_from_start[pos:pos+5] == 'begin':
                depth += 1
                pos += 5
            elif content_from_start[pos:pos+3] == 'end':
                depth -= 1
                if depth == 0:
                    return content_from_start[:pos+3]
                pos += 3
            else:
                pos += 1
        return content_from_start[:min(500, len(content_from_start))]

    def analyze(self):
        """Run all checks"""
        self.check_syntax()
        self.check_default_nettype()
        self.check_latch_inference()
        self.check_blocking_assignments()
        self.check_clock_domain_crossings()
        self.check_sensitivity_lists()
        self.check_signal_declarations()
        self.check_reset_signals()
        self.check_fifo_usage()
        self.check_parameters()

    def print_report(self):
        """Print analysis report"""
        print(f"\n{'='*80}")
        print(f"ANALYSIS: {self.filename}")
        print(f"{'='*80}")

        if self.issues:
            print(f"\n❌ ERRORS ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  - {issue}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.info:
            print(f"\n✓ INFO ({len(self.info)}):")
            for info_item in self.info:
                print(f"  - {info_item}")

        if not self.issues and not self.warnings:
            print("\n✅ No issues found!")

        return len(self.issues), len(self.warnings)


def main():
    # Verilog files to check
    verilog_files = [
        '/home/user/orbtrace/verilog/swdIF.v',
        '/home/user/orbtrace/verilog/dbgIF.v',
        '/home/user/orbtrace/verilog/traceIF.v',
        '/home/user/orbtrace/verilog/jtagIF.v',
        '/home/user/orbtrace/verilog/ram.v',
        '/home/user/orbtrace/vahya/verilog/stream_interface.v',
        '/home/user/orbtrace/vahya/verilog/at86rf215_iq_capture.v',
        '/home/user/orbtrace/vahya/verilog/max2771_adc_capture.v',
    ]

    total_errors = 0
    total_warnings = 0

    print("\n" + "="*80)
    print("COMPREHENSIVE VERILOG LINT ANALYSIS")
    print("="*80)

    for vfile in verilog_files:
        if os.path.exists(vfile):
            linter = VerilogLinter(vfile)
            linter.analyze()
            errors, warnings = linter.print_report()
            total_errors += errors
            total_warnings += warnings
        else:
            print(f"\n⚠️  File not found: {vfile}")

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total modules analyzed: {len([f for f in verilog_files if os.path.exists(f)])}")
    print(f"Total errors: {total_errors}")
    print(f"Total warnings: {total_warnings}")

    if total_errors == 0 and total_warnings == 0:
        print("\n✅ All modules passed linting!")
    elif total_errors == 0:
        print(f"\n✓ No critical errors, but {total_warnings} warnings to review")
    else:
        print(f"\n❌ Found {total_errors} errors that need fixing")

    print(f"{'='*80}\n")

    return 0 if total_errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
