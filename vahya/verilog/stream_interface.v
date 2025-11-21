/**
 * Generic Streaming Interface for Amaranth LUNA Integration
 *
 * This module demonstrates how to interface Verilog modules with
 * Amaranth LUNA USB bulk endpoints through AXI-Stream like interface.
 *
 * The interface is compatible with LiteX stream interconnects and
 * can be connected to USB endpoints via clock domain crossing.
 *
 * Stream Protocol:
 * - valid: Indicates data is valid
 * - ready: Backpressure from receiver
 * - data:  Data payload
 * - first: Start of packet (optional)
 * - last:  End of packet
 */

module stream_interface #(
    parameter DATA_WIDTH = 8,
    parameter FIFO_DEPTH = 512
) (
    input  wire clk,
    input  wire rst,

    // Input stream (from data source, e.g., ADC, I/Q capture)
    input  wire [DATA_WIDTH-1:0] sink_data,
    input  wire                  sink_valid,
    output wire                  sink_ready,
    input  wire                  sink_first,
    input  wire                  sink_last,

    // Output stream (to USB endpoint via clock domain crossing)
    output wire [DATA_WIDTH-1:0] source_data,
    output wire                  source_valid,
    input  wire                  source_ready,
    output wire                  source_first,
    output wire                  source_last
);

    // Internal FIFO for buffering
    reg [DATA_WIDTH-1:0] fifo_mem [0:FIFO_DEPTH-1];
    reg [DATA_WIDTH-1:0] fifo_flags [0:FIFO_DEPTH-1];  // Stores first/last flags

    reg [$clog2(FIFO_DEPTH):0] wr_ptr = 0;
    reg [$clog2(FIFO_DEPTH):0] rd_ptr = 0;

    wire fifo_full  = (wr_ptr[$clog2(FIFO_DEPTH)] != rd_ptr[$clog2(FIFO_DEPTH)]) &&
                      (wr_ptr[$clog2(FIFO_DEPTH)-1:0] == rd_ptr[$clog2(FIFO_DEPTH)-1:0]);
    wire fifo_empty = (wr_ptr == rd_ptr);

    // Write to FIFO
    assign sink_ready = !fifo_full;

    always @(posedge clk) begin
        if (rst) begin
            wr_ptr <= 0;
        end else if (sink_valid && sink_ready) begin
            fifo_mem[wr_ptr[$clog2(FIFO_DEPTH)-1:0]] <= sink_data;
            fifo_flags[wr_ptr[$clog2(FIFO_DEPTH)-1:0]] <= {sink_first, sink_last};
            wr_ptr <= wr_ptr + 1;
        end
    end

    // Read from FIFO
    assign source_valid = !fifo_empty;
    assign source_data  = fifo_mem[rd_ptr[$clog2(FIFO_DEPTH)-1:0]];
    assign {source_first, source_last} = fifo_flags[rd_ptr[$clog2(FIFO_DEPTH)-1:0]];

    always @(posedge clk) begin
        if (rst) begin
            rd_ptr <= 0;
        end else if (source_valid && source_ready) begin
            rd_ptr <= rd_ptr + 1;
        end
    end

endmodule


/**
 * Example: Simple Loopback Module
 *
 * Demonstrates minimal streaming interface for testing.
 * Can be connected between USB OUT and USB IN endpoints.
 */
module stream_loopback #(
    parameter DATA_WIDTH = 8
) (
    input  wire clk,
    input  wire rst,

    // From USB OUT endpoint
    input  wire [DATA_WIDTH-1:0] usb_out_data,
    input  wire                  usb_out_valid,
    output wire                  usb_out_ready,
    input  wire                  usb_out_last,

    // To USB IN endpoint
    output wire [DATA_WIDTH-1:0] usb_in_data,
    output wire                  usb_in_valid,
    input  wire                  usb_in_ready,
    output wire                  usb_in_last
);

    // Direct connection (can add processing here)
    assign usb_in_data  = usb_out_data;
    assign usb_in_valid = usb_out_valid;
    assign usb_out_ready = usb_in_ready;
    assign usb_in_last  = usb_out_last;

endmodule
