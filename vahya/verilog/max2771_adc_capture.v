/**
 * MAX2771 ADC Data Capture Module
 *
 * Captures 2-bit I/Q data from MAX2771 GNSS frontend and streams it via USB.
 *
 * Features:
 * - 2-bit I + 2-bit Q ADC data capture
 * - Synchronized to MAX2771 clkout (~16.368 MHz)
 * - Sample packing for efficient USB transfer
 * - Clock domain crossing to system clock
 * - Continuous streaming mode
 *
 * MAX2771 Output Format:
 * - iq_sign: I channel sign bit
 * - iq_mag:  I channel magnitude bit
 * - qq_sign: Q channel sign bit
 * - qq_mag:  Q channel magnitude bit
 * - clkout:  Sample clock (~16.368 MHz, configurable)
 *
 * Data Packing:
 * - Pack 8 I/Q samples (4 bits each) into 32-bit words
 * - Format: [sample7_I, sample7_Q, ..., sample0_I, sample0_Q]
 */

module max2771_adc_capture #(
    parameter SAMPLE_WIDTH = 32,   // 32-bit words (8 I/Q samples per word)
    parameter FIFO_DEPTH = 2048    // Larger FIFO for GNSS data rates
) (
    // System clock and reset
    input  wire clk_sys,
    input  wire rst,

    // MAX2771 ADC interface
    input  wire iq_sign,   // I sign bit
    input  wire iq_mag,    // I magnitude bit
    input  wire qq_sign,   // Q sign bit
    input  wire qq_mag,    // Q magnitude bit
    input  wire clkout,    // Sample clock from MAX2771

    // Configuration
    input  wire capture_enable,
    input  wire [2:0] decimation,  // Decimation factor (0=none, 1=/2, 2=/4, etc.)

    // Output stream (to USB)
    output wire [SAMPLE_WIDTH-1:0] stream_data,
    output wire                    stream_valid,
    input  wire                    stream_ready,
    output wire                    stream_last,

    // Status
    output wire fifo_overflow,
    output wire [31:0] sample_count
);

    // Sample buffer for packing 8 samples into 32-bit word
    reg [3:0]  sample_buffer [0:7];  // Each sample is 4 bits (2-bit I + 2-bit Q)
    reg [2:0]  sample_count_pack = 0;
    reg [31:0] packed_word;
    reg        packed_word_ready = 0;

    // Decimation counter
    reg [7:0] decim_counter = 0;
    wire      decim_match = (decim_counter == 0);

    // Capture I/Q sample (on MAX2771 clock)
    always @(posedge clkout) begin
        if (rst || !capture_enable) begin
            sample_count_pack <= 0;
            packed_word_ready <= 0;
            decim_counter <= 0;
        end else begin
            // Decimation logic
            if (decimation == 0 || decim_match) begin
                // Capture sample: {I_sign, I_mag, Q_sign, Q_mag}
                sample_buffer[sample_count_pack] <= {iq_sign, iq_mag, qq_sign, qq_mag};

                // Check if we've collected 8 samples
                if (sample_count_pack == 7) begin
                    sample_count_pack <= 0;
                    packed_word_ready <= 1;

                    // Pack samples into 32-bit word
                    packed_word <= {
                        sample_buffer[7], sample_buffer[6],
                        sample_buffer[5], sample_buffer[4],
                        sample_buffer[3], sample_buffer[2],
                        sample_buffer[1], sample_buffer[0]
                    };
                end else begin
                    sample_count_pack <= sample_count_pack + 1;
                    packed_word_ready <= 0;
                end

                // Reset decimation counter
                decim_counter <= (1 << decimation) - 1;
            end else begin
                decim_counter <= decim_counter - 1;
                packed_word_ready <= 0;
            end
        end
    end

    // Async FIFO for clock domain crossing
    wire fifo_wr_en = packed_word_ready && capture_enable;
    wire fifo_full;
    wire fifo_empty;
    wire fifo_rd_en;
    wire [31:0] fifo_dout;

    async_fifo_gnss #(
        .DATA_WIDTH(32),
        .ADDR_WIDTH($clog2(FIFO_DEPTH))
    ) gnss_fifo (
        .wr_clk(clkout),
        .wr_rst(rst),
        .wr_en(fifo_wr_en),
        .wr_data(packed_word),
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
    always @(posedge clkout) begin
        if (rst) begin
            overflow_flag <= 0;
        end else if (fifo_wr_en && fifo_full) begin
            overflow_flag <= 1;
        end
    end

    assign fifo_overflow = overflow_flag;

    // Sample counter (in system clock domain)
    reg [31:0] count = 0;
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
 * Async FIFO for GNSS data (similar to RF FIFO but optimized for GNSS rates)
 */
module async_fifo_gnss #(
    parameter DATA_WIDTH = 32,
    parameter ADDR_WIDTH = 11
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

    // Pointers
    reg [ADDR_WIDTH:0] wr_ptr = 0;
    reg [ADDR_WIDTH:0] rd_ptr = 0;

    // Gray code conversion
    wire [ADDR_WIDTH:0] wr_ptr_gray = wr_ptr ^ (wr_ptr >> 1);
    wire [ADDR_WIDTH:0] rd_ptr_gray = rd_ptr ^ (rd_ptr >> 1);

    // Synchronizers
    reg [ADDR_WIDTH:0] wr_ptr_gray_sync1 = 0, wr_ptr_gray_sync2 = 0;
    reg [ADDR_WIDTH:0] rd_ptr_gray_sync1 = 0, rd_ptr_gray_sync2 = 0;

    // Synchronize write pointer to read domain
    always @(posedge rd_clk) begin
        if (rd_rst) begin
            wr_ptr_gray_sync1 <= 0;
            wr_ptr_gray_sync2 <= 0;
        end else begin
            wr_ptr_gray_sync1 <= wr_ptr_gray;
            wr_ptr_gray_sync2 <= wr_ptr_gray_sync1;
        end
    end

    // Synchronize read pointer to write domain
    always @(posedge wr_clk) begin
        if (wr_rst) begin
            rd_ptr_gray_sync1 <= 0;
            rd_ptr_gray_sync2 <= 0;
        end else begin
            rd_ptr_gray_sync1 <= rd_ptr_gray;
            rd_ptr_gray_sync2 <= rd_ptr_gray_sync1;
        end
    end

    // Status flags
    assign wr_full  = (wr_ptr_gray == {~rd_ptr_gray_sync2[ADDR_WIDTH:ADDR_WIDTH-1],
                                       rd_ptr_gray_sync2[ADDR_WIDTH-2:0]});
    assign rd_empty = (rd_ptr_gray == wr_ptr_gray_sync2);

    // Write operation
    always @(posedge wr_clk) begin
        if (wr_rst) begin
            wr_ptr <= 0;
        end else if (wr_en && !wr_full) begin
            mem[wr_ptr[ADDR_WIDTH-1:0]] <= wr_data;
            wr_ptr <= wr_ptr + 1;
        end
    end

    // Read operation
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


/**
 * MAX2771 Configuration Helper
 *
 * Provides configuration register definitions for MAX2771.
 * These can be programmed via SPI from the RISC-V processor.
 */
module max2771_config_defs;

    // Configuration Register 1: Mode and Filter
    localparam CONF1_CHIPEN     = 27;  // Chip enable
    localparam CONF1_IDLE       = 26;  // Idle mode
    localparam CONF1_ILNA1      = 25;  // LNA1 current
    localparam CONF1_ILNA2      = 24;  // LNA2 current
    localparam CONF1_ILO        = 23;  // LO current
    localparam CONF1_IMIX       = 22;  // Mixer current
    localparam CONF1_MIXPOLE    = 21;  // Mixer pole
    localparam CONF1_LNAMODE    = 20;  // LNA mode
    localparam CONF1_MIXEN      = 19;  // Mixer enable
    localparam CONF1_ANTEN      = 18;  // Antenna enable

    // Sample rates (depends on reference clock and dividers)
    // Typical: 16.368 MHz with default configuration
    // Can be adjusted via CONF2 register

    // Gain settings
    localparam GAIN_HIGH   = 3'b111;
    localparam GAIN_MEDIUM = 3'b100;
    localparam GAIN_LOW    = 3'b001;

endmodule
