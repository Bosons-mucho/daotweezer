`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: Toe hold
// Engineer: Yuexiang Wu
// 
// Create Date: 2026/07/03 15:42:39
// Design Name: 
// Module Name: pulse_delay_reg
// Project Name: daotweezer
// Target Devices: redpitaya
// Tool Versions: 
// Description: for managing the regulators from the monitor 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module pulse_delay_reg(
    input wire clk,
    input wire rstn,
    input wire sysw_en,
    input wire sysr_en,
    output reg sys_ack,
    output reg sys_err,
    input wire [31:0] sysw_data,
    output reg [31:0] sysr_data,
    input wire [19:0] sys_addr,
    input wire busy,
    input wire done,
    
    output reg [31:0] dio1_pulse_width,
    output reg [31:0] dio0_pulse_width,
    output reg [31:0] delay_pulse_width,
    output reg start_pulse,
    output reg clear_pulse
    );
    
    localparam CTRL = 20'h00000;
    localparam DIO0_W = 20'h00004;
    localparam DELAY_W = 20'h00008;
    localparam DIO1_W = 20'h0000C;
    
    
    always @(posedge clk) begin
        if (!rstn) begin
            start_pulse <= 1'b0;
            clear_pulse <= 1'b0;
            dio1_pulse_width <= 32'd125000;
            dio0_pulse_width <= 32'd125000;
            delay_pulse_width <= 32'd1250000;
            sys_ack <= 1'b0;
            sys_err <= 1'b0;
            sysr_data <= 32'd0;
        end else begin
            sys_ack <= 1'b0;
            sys_err <= 1'b0;
            start_pulse <= 1'b0;
            clear_pulse <= 1'b0;
                if (sysw_en) begin //ps tries to write in data
                    sys_ack <= 1'b1;
                    case(sys_addr)
                        CTRL: begin 
                            if (sysw_data[1]) begin
                                clear_pulse <= 1'b1;
                            end else if (sysw_data[0]) begin
                                if (!busy) begin
                                start_pulse <= 1'b1;
                                end else begin
                                sys_err <= 1'b1;
                                end
                            end
                        end
                        DIO0_W: begin
                            if (!busy) begin
                            dio0_pulse_width <= sysw_data;
                            end else begin
                                sys_err <= 1'b1;
                            end
                        end
                        DIO1_W: begin
                            if (!busy) begin
                                dio1_pulse_width <= sysw_data;
                            end else begin
                                sys_err <= 1'b1;
                            end
                        end
                        DELAY_W: begin
                            if (!busy) begin
                                delay_pulse_width <= sysw_data;
                            end else begin
                                sys_err <= 1'b1;
                            end
                        end
                        default: begin
                        sys_err <= 1'b1;
                        end
                     endcase
                end else if (sysr_en) begin //ps tries to read data
                    sys_ack <= 1'b1;
                    case(sys_addr)
                        CTRL: begin
                        sysr_data <= {30'd0, done, busy}; //the sequence here is independent with how one read launch from sysw_data
                        end
                        DIO0_W: begin
                        sysr_data <= dio0_pulse_width;
                        end
                        DIO1_W: begin
                        sysr_data <= dio1_pulse_width;
                        end
                        DELAY_W:begin
                        sysr_data <= delay_pulse_width;
                        end
                        default: begin
                            sysr_data <= 32'd0;
                            sys_err <= 1'b1;
                        end
                    endcase
                end 
             end
           end
endmodule
