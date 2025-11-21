/**
 * AT86RF215 I/Q Data Capture Module
 *
 * Captures 14-bit parallel I/Q data from AT86RF215 dual-band transceiver
 * and converts it to a streaming format for USB transmission.
 *
 * Features:
 * - Dual-band capture (RF09: Sub-GHz, RF24: 2.4GHz)
 * - Configurable sample packing
 * - FIFO buffering for rate matching
 * - Back-pressure handling
 *
 * AT86RF215 provides:
 * - 14-bit I/Q data on separate buses for each band
 * - TX/RX enable signals to indicate data direction
 * - 26 MHz reference clock (can be divided for sampling)
 */

module at86rf215_iq_capture #(
    parameter SAMPLE_WIDTH = 32,  // Pack two 14-bit I/Q samples into 32-bit word
    parameter FIFO_DEPTH = 1024
) (
    // System clock and reset
    input  wire clk_sys,
    input  wire rst,

    // AT86RF215 RF09 interface (Sub-GHz)
    input  wire [13:0] rf09_rxiq,
    input  wire [13:0] rf09_txiq,
    input  wire        rf09_rxen,
    input  wire        rf09_txen,

    // AT86RF215 RF24 interface (2.4GHz)
    input  wire [13:0] rf24_rxiq,
    input  wire [13:0] rf24_txiq,
    input  wire        rf24_rxen,
    input  wire        rf24_txen,

    // AT86RF215 clock
    input  wire clk_26mhz,

    // Configuration
    input  wire [1:0]  band_select,  // 0=RF09_RX, 1=RF09_TX, 2=RF24_RX, 3=RF24_TX
    input  wire        capture_enable,

    // Output stream (to USB)
    output wire [SAMPLE_WIDTH-1:0] stream_data,
    output wire                    stream_valid,
    input  wire                    stream_ready,
    output wire                    stream_last,

    // Status
    output wire fifo_overflow,
    output wire [15:0] sample_count
);

    // Sample buffer for packing
    reg [13:0] i_sample;
    reg [13:0] q_sample;
    reg        sample_toggle = 0;  // Toggle between I and Q
    reg        data_ready = 0;

    // Selected I/Q data based on band_select
    wire [13:0] selected_iq;
    reg  [13:0] selected_iq_reg;

    assign selected_iq = (band_select == 2'd0) ? rf09_rxiq :
                        (band_select == 2'd1) ? rf09_txiq :
                        (band_select == 2'd2) ? rf24_rxiq :
                                                rf24_txiq;

    // Clock domain crossing for selected data
    always @(posedge clk_26mhz) begin
        if (rst) begin
            selected_iq_reg <= 0;
        end else if (capture_enable) begin
            selected_iq_reg <= selected_iq;
        end
    end

    // Sample capture and packing (on 26 MHz clock)
    always @(posedge clk_26mhz) begin
        if (rst || !capture_enable) begin
            sample_toggle <= 0;
            data_ready <= 0;
            i_sample <= 0;
            q_sample <= 0;
        end else begin
            if (!sample_toggle) begin
                // Capture I sample
                i_sample <= selected_iq_reg;
                sample_toggle <= 1;
                data_ready <= 0;
            end else begin
                // Capture Q sample
                q_sample <= selected_iq_reg;
                sample_toggle <= 0;
                data_ready <= 1;  // Both I and Q ready
            end
        end
    end

    // Pack I/Q into output word (I in upper bits, Q in lower bits)
    wire [31:0] packed_iq = {4'b0, i_sample, 4'b0, q_sample};  // Pad to 32 bits

    // Async FIFO for clock domain crossing (26 MHz -> sys clock)
    wire fifo_wr_en = data_ready && capture_enable;
    wire fifo_full;
    wire fifo_empty;
    wire fifo_rd_en;
    wire [31:0] fifo_dout;

    async_fifo #(
        .DATA_WIDTH(32),
        .ADDR_WIDTH($clog2(FIFO_DEPTH))
    ) iq_fifo (
        .wr_clk(clk_26mhz),
        .wr_rst(rst),
        .wr_en(fifo_wr_en),
        .wr_data(packed_iq),
        .wr_full(fifo_full),

        .rd_clk(clk_sys),
        .rd_rst(rst),
        .rd_en(fifo_rd_en),
        .rd_data(fifo_dout),
        .rd_empty(fifo_empty)
    );

    // Stream output
    assign stream_data = fifo_dout;
    assign stream_valid = !fifo_empty;
    assign fifo_rd_en = stream_valid && stream_ready;
    assign stream_last = 0;  // Continuous stream

    // Overflow detection
    reg overflow_flag = 0;
    always @(posedge clk_26mhz) begin
        if (rst) begin
            overflow_flag <= 0;
        end else if (fifo_wr_en && fifo_full) begin
            overflow_flag <= 1;
        end
    end

    assign fifo_overflow = overflow_flag;

    // Sample counter
    reg [15:0] count = 0;
    always @(posedge clk_sys) begin
        if (rst || !capture_enable) begin
            count <= 0;
        end else if (fifo_rd_en) begin
            count <= count + 1;
        end
    end

    assign sample_count = count;

endmodule


/**
 * Simple Async FIFO for Clock Domain Crossing
 *
 * Gray code based async FIFO for safely crossing clock domains.
 */
module async_fifo #(
    parameter DATA_WIDTH = 32,
    parameter ADDR_WIDTH = 10
) (
    // Write port
    input  wire                  wr_clk,
    input  wire                  wr_rst,
    input  wire                  wr_en,
    input  wire [DATA_WIDTH-1:0] wr_data,
    output wire                  wr_full,

    // Read port
    input  wire                  rd_clk,
    input  wire                  rd_rst,
    input  wire                  rd_en,
    output reg  [DATA_WIDTH-1:0] rd_data,
    output wire                  rd_empty
);

    localparam DEPTH = 1 << ADDR_WIDTH;

    // Memory
    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    // Pointers (extra bit for full/empty detection)
    reg [ADDR_WIDTH:0] wr_ptr = 0;
    reg [ADDR_WIDTH:0] rd_ptr = 0;

    // Gray code pointers for synchronization
    wire [ADDR_WIDTH:0] wr_ptr_gray = wr_ptr ^ (wr_ptr >> 1);
    wire [ADDR_WIDTH:0] rd_ptr_gray = rd_ptr ^ (rd_ptr >> 1);

    // Synchronized pointers
    reg [ADDR_WIDTH:0] wr_ptr_gray_sync1 = 0, wr_ptr_gray_sync2 = 0;
    reg [ADDR_WIDTH:0] rd_ptr_gray_sync1 = 0, rd_ptr_gray_sync2 = 0;

    // Synchronize write pointer to read clock domain
    always @(posedge rd_clk) begin
        if (rd_rst) begin
            wr_ptr_gray_sync1 <= 0;
            wr_ptr_gray_sync2 <= 0;
        end else begin
            wr_ptr_gray_sync1 <= wr_ptr_gray;
            wr_ptr_gray_sync2 <= wr_ptr_gray_sync1;
        end
    end

    // Synchronize read pointer to write clock domain
    always @(posedge wr_clk) begin
        if (wr_rst) begin
            rd_ptr_gray_sync1 <= 0;
            rd_ptr_gray_sync2 <= 0;
        end else begin
            rd_ptr_gray_sync1 <= rd_ptr_gray;
            rd_ptr_gray_sync2 <= rd_ptr_gray_sync1;
        end
    end

    // Full/Empty flags
    assign wr_full  = (wr_ptr_gray == {~rd_ptr_gray_sync2[ADDR_WIDTH:ADDR_WIDTH-1],
                                       rd_ptr_gray_sync2[ADDR_WIDTH-2:0]});
    assign rd_empty = (rd_ptr_gray == wr_ptr_gray_sync2);

    // Write logic
    always @(posedge wr_clk) begin
        if (wr_rst) begin
            wr_ptr <= 0;
        end else if (wr_en && !wr_full) begin
            mem[wr_ptr[ADDR_WIDTH-1:0]] <= wr_data;
            wr_ptr <= wr_ptr + 1;
        end
    end

    // Read logic
    always @(posedge rd_clk) begin
        if (rd_rst) begin
            rd_ptr <= 0;
            rd_data <= 0;
        end else if (rd_en && !rd_empty) begin
            rd_data <= mem[rd_ptr[ADDR_WIDTH-1:0]];
            rd_ptr <= rd_ptr + 1;
        end
    end

endmodule
