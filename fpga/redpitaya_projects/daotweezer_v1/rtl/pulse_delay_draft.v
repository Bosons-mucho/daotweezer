`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: Toe hold
// Engineer: Yuexiang Wu
// 
// Create Date: 2026/07/02 15:44:11
// Design Name: 
// Module Name: pulse_delay_demo
// Project Name: daotweezer
// Target Devices: redpitaya
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module pulse_delay_demo (
    input wire clk,
    input wire rstn, 
    input wire start,
    input wire clear,
    
    input wire [31:0] dio0_pulse_width,
    input wire [31:0] dio1_pulse_width,
    input wire [31:0] delay_width,
    
    output reg busy,
    output reg done,
    output reg dio0_pulse,
    output reg dio1_pulse
    );
    
    
    localparam IDLE = 3'd0;
    localparam DIO0_HIGH = 3'd1;
    localparam DELAY = 3'd2;
    localparam DIO1_HOLD = 3'd3;
    
    
    reg [2:0] state;
    reg [31:0] counter;
    
    always @(posedge clk) begin
        if (!rstn) begin
            state <= IDLE;
            counter <= 32'd0;
            dio0_pulse <= 1'b0;
            dio1_pulse <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
        end else if (clear) begin
            state <= IDLE;
            counter <= 32'd0;
            dio0_pulse <= 1'b0;
            dio1_pulse <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
        end else begin
            case(state)
                IDLE:begin
                        counter <= 32'd1;
                        dio0_pulse <=1'b0;
                        dio1_pulse <=1'b0;
                        busy <= 1'b0;
                        if (start) begin
                            state <= DIO0_HIGH;
                            busy <= 1'b1;
                            done <= 1'b0;
                            counter <= dio0_pulse_width - 32'd1;
                    end
                end
                DIO0_HIGH:begin
                        dio0_pulse <= 1'b1;
                        dio1_pulse <= 1'b0;
                        busy <= 1'b1;
                        done <= 1'b0;
                        if (counter == 0) begin
                            counter <= delay_width - 32'd1;
                            state <= DELAY;
                        end else begin
                            counter <= counter - 32'd1;
                        end
                end
                DELAY:begin
                        dio0_pulse <= 1'b0;
                        dio1_pulse <= 1'b0;
                        busy <= 1'b1;
                        done <= 1'b0;
                        if (counter == 0) begin
                            state <= DIO1_HOLD;
                            counter <= 32'd0;
                        end else begin 
                            counter <= counter - 32'd1;
                        end
                end
                DIO1_HOLD:begin
                            dio0_pulse <= 1'b0;
                            dio1_pulse <= 1'b1;
                            busy <= 1'b0;
                            done <= 1'b1;
                            counter <= 32'd0;
                            if (start) begin
                                state <= DIO0_HIGH;
                                busy <= 1'b1;
                                done <= 1'b0;
                                counter <= dio0_pulse_width - 32'd1;
                            end
                end
                default:begin
                            dio0_pulse <= 1'b0;
                            dio1_pulse <= 1'b0;
                            state <= IDLE;
                            busy <= 1'b0;
                            done <= 1'b0;
                            counter <= 32'd1;
               end
            endcase
        end
    end
    
    
endmodule
