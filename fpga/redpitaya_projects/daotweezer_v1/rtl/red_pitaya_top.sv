////////////////////////////////////////////////////////////////////////////////
// Minimal Red Pitaya top for the daotweezer pulse-delay controller.
////////////////////////////////////////////////////////////////////////////////

module red_pitaya_top #(
  bit [0:5*32-1] GITH = '0,
  parameter MNA = 2,
  parameter MNG = 2,
  parameter ADW_125 = 14,
  parameter ADW_122 = 16,
  parameter DWE_Z20 = 11,
  parameter DWE_Z10 = 8,
  parameter DDW = 14,
`ifdef Z20_xx
  parameter DWE = DWE_Z20
`else
  parameter DWE = DWE_Z10
`endif
)(
  inout  logic [54-1:0] FIXED_IO_mio,
  inout  logic          FIXED_IO_ps_clk,
  inout  logic          FIXED_IO_ps_porb,
  inout  logic          FIXED_IO_ps_srstb,
  inout  logic          FIXED_IO_ddr_vrn,
  inout  logic          FIXED_IO_ddr_vrp,

  inout  logic [15-1:0] DDR_addr,
  inout  logic [ 3-1:0] DDR_ba,
  inout  logic          DDR_cas_n,
  inout  logic          DDR_ck_n,
  inout  logic          DDR_ck_p,
  inout  logic          DDR_cke,
  inout  logic          DDR_cs_n,
  inout  logic [ 4-1:0] DDR_dm,
  inout  logic [32-1:0] DDR_dq,
  inout  logic [ 4-1:0] DDR_dqs_n,
  inout  logic [ 4-1:0] DDR_dqs_p,
  inout  logic          DDR_odt,
  inout  logic          DDR_ras_n,
  inout  logic          DDR_reset_n,
  inout  logic          DDR_we_n,

  input  logic [MNA-1:0] [16-1:0] adc_dat_i,
  input  logic           [ 2-1:0] adc_clk_i,
  output logic           [ 2-1:0] adc_clk_o,
  output logic                    adc_cdcs_o,

  output logic [14-1:0] dac_dat_o,
  output logic          dac_wrt_o,
  output logic          dac_sel_o,
  output logic          dac_clk_o,
  output logic          dac_rst_o,
  output logic [ 4-1:0] dac_pwm_o,

  input  logic [5-1:0] vinp_i,
  input  logic [5-1:0] vinn_i,

  inout  logic [DWE-1:0] exp_p_io,
  inout  logic [DWE-1:0] exp_n_io,

  output logic [2-1:0] daisy_p_o,
  output logic [2-1:0] daisy_n_o,
  input  logic [2-1:0] daisy_p_i,
  input  logic [2-1:0] daisy_n_i,

  output logic [8-1:0] led_o
);

logic [4-1:0] fclk;
logic [4-1:0] frstn;

logic pulse_busy;
logic pulse_done;
logic pulse_start;
logic pulse_clear;
logic dio0_pulse;
logic dio1_pulse;
logic [31:0] dio0_pulse_width;
logic [31:0] dio1_pulse_width;
logic [31:0] delay_pulse_width;

logic [26:0] led_cnt;
logic CAN0_tx;
logic CAN1_tx;

sys_bus_if ps_sys (.clk(fclk[0]), .rstn(frstn[0]));
sys_bus_if sys [8-1:0] (.clk(fclk[0]), .rstn(frstn[0]));
gpio_if #(.DW(3*DWE)) gpio ();

axi_sys_if axi0_sys (.clk(fclk[0]), .rstn(frstn[0]));
axi_sys_if axi1_sys (.clk(fclk[0]), .rstn(frstn[0]));
axi_sys_if axi2_sys (.clk(fclk[0]), .rstn(frstn[0]));
axi_sys_if axi3_sys (.clk(fclk[0]), .rstn(frstn[0]));

assign gpio.i = '0;

red_pitaya_ps ps (
  .FIXED_IO_mio      (FIXED_IO_mio),
  .FIXED_IO_ps_clk   (FIXED_IO_ps_clk),
  .FIXED_IO_ps_porb  (FIXED_IO_ps_porb),
  .FIXED_IO_ps_srstb (FIXED_IO_ps_srstb),
  .FIXED_IO_ddr_vrn  (FIXED_IO_ddr_vrn),
  .FIXED_IO_ddr_vrp  (FIXED_IO_ddr_vrp),
  .DDR_addr          (DDR_addr),
  .DDR_ba            (DDR_ba),
  .DDR_cas_n         (DDR_cas_n),
  .DDR_ck_n          (DDR_ck_n),
  .DDR_ck_p          (DDR_ck_p),
  .DDR_cke           (DDR_cke),
  .DDR_cs_n          (DDR_cs_n),
  .DDR_dm            (DDR_dm),
  .DDR_dq            (DDR_dq),
  .DDR_dqs_n         (DDR_dqs_n),
  .DDR_dqs_p         (DDR_dqs_p),
  .DDR_odt           (DDR_odt),
  .DDR_ras_n         (DDR_ras_n),
  .DDR_reset_n       (DDR_reset_n),
  .DDR_we_n          (DDR_we_n),
  .fclk_clk_o        (fclk),
  .fclk_rstn_o       (frstn),
  .CAN0_rx           (1'b0),
  .CAN0_tx           (CAN0_tx),
  .CAN1_rx           (1'b0),
  .CAN1_tx           (CAN1_tx),
  .vinp_i            (vinp_i),
  .vinn_i            (vinn_i),
  .gpio              (gpio),
  .bus               (ps_sys),
  .axi0_sys          (axi0_sys),
  .axi1_sys          (axi1_sys),
  .axi2_sys          (axi2_sys),
  .axi3_sys          (axi3_sys)
);

assign axi0_sys.waddr = '0;
assign axi0_sys.wdata = '0;
assign axi0_sys.wsel = '0;
assign axi0_sys.wvalid = 1'b0;
assign axi0_sys.wlen = '0;
assign axi0_sys.wsize = '0;
assign axi0_sys.wfixed = 1'b0;
assign axi0_sys.raddr = '0;
assign axi0_sys.rsel = '0;
assign axi0_sys.rvalid = 1'b0;
assign axi0_sys.rlen = '0;
assign axi0_sys.rsize = '0;
assign axi0_sys.rfixed = 1'b0;
assign axi0_sys.rrdys = 1'b0;

assign axi1_sys.waddr = '0;
assign axi1_sys.wdata = '0;
assign axi1_sys.wsel = '0;
assign axi1_sys.wvalid = 1'b0;
assign axi1_sys.wlen = '0;
assign axi1_sys.wsize = '0;
assign axi1_sys.wfixed = 1'b0;
assign axi1_sys.raddr = '0;
assign axi1_sys.rsel = '0;
assign axi1_sys.rvalid = 1'b0;
assign axi1_sys.rlen = '0;
assign axi1_sys.rsize = '0;
assign axi1_sys.rfixed = 1'b0;
assign axi1_sys.rrdys = 1'b0;

assign axi2_sys.waddr = '0;
assign axi2_sys.wdata = '0;
assign axi2_sys.wsel = '0;
assign axi2_sys.wvalid = 1'b0;
assign axi2_sys.wlen = '0;
assign axi2_sys.wsize = '0;
assign axi2_sys.wfixed = 1'b0;
assign axi2_sys.raddr = '0;
assign axi2_sys.rsel = '0;
assign axi2_sys.rvalid = 1'b0;
assign axi2_sys.rlen = '0;
assign axi2_sys.rsize = '0;
assign axi2_sys.rfixed = 1'b0;
assign axi2_sys.rrdys = 1'b0;

assign axi3_sys.waddr = '0;
assign axi3_sys.wdata = '0;
assign axi3_sys.wsel = '0;
assign axi3_sys.wvalid = 1'b0;
assign axi3_sys.wlen = '0;
assign axi3_sys.wsize = '0;
assign axi3_sys.wfixed = 1'b0;
assign axi3_sys.raddr = '0;
assign axi3_sys.rsel = '0;
assign axi3_sys.rvalid = 1'b0;
assign axi3_sys.rlen = '0;
assign axi3_sys.rsize = '0;
assign axi3_sys.rfixed = 1'b0;
assign axi3_sys.rrdys = 1'b0;

sys_bus_interconnect #(
  .SN(8),
  .SW(20)
) sys_bus_interconnect (
  .pll_locked_i(1'b1),
  .bus_m(ps_sys),
  .bus_s(sys)
);

sys_bus_stub sys_bus_stub_0 (sys[0]);
sys_bus_stub sys_bus_stub_1 (sys[1]);
sys_bus_stub sys_bus_stub_2 (sys[2]);
sys_bus_stub sys_bus_stub_3 (sys[3]);
sys_bus_stub sys_bus_stub_4 (sys[4]);
sys_bus_stub sys_bus_stub_5 (sys[5]);
sys_bus_stub sys_bus_stub_6 (sys[6]);

pulse_delay_demo i_pulse_delay_demo (
  .clk              (fclk[0]),
  .rstn             (frstn[0]),
  .start            (pulse_start),
  .clear            (pulse_clear),
  .dio0_pulse_width (dio0_pulse_width),
  .dio1_pulse_width (dio1_pulse_width),
  .delay_width      (delay_pulse_width),
  .busy             (pulse_busy),
  .done             (pulse_done),
  .dio0_pulse       (dio0_pulse),
  .dio1_pulse       (dio1_pulse)
);

pulse_delay_reg i_pulse_delay_reg (
  .clk               (fclk[0]),
  .rstn              (frstn[0]),
  .sysw_en           (sys[7].wen),
  .sysr_en           (sys[7].ren),
  .sys_ack           (sys[7].ack),
  .sys_err           (sys[7].err),
  .sysw_data         (sys[7].wdata),
  .sysr_data         (sys[7].rdata),
  .sys_addr          (sys[7].addr[19:0]),
  .busy              (pulse_busy),
  .done              (pulse_done),
  .dio1_pulse_width  (dio1_pulse_width),
  .dio0_pulse_width  (dio0_pulse_width),
  .delay_pulse_width (delay_pulse_width),
  .start_pulse       (pulse_start),
  .clear_pulse       (pulse_clear)
);

assign exp_p_io[0] = dio0_pulse;
assign exp_p_io[1] = dio1_pulse;
assign exp_p_io[DWE-1:2] = {DWE-2{1'bz}};
assign exp_n_io = {DWE{1'bz}};

always_ff @(posedge fclk[0]) begin
  if (!frstn[0])
    led_cnt <= '0;
  else
    led_cnt <= led_cnt + 1'b1;
end

assign led_o[0] = 1'b1;
assign led_o[1] = pulse_busy;
assign led_o[2] = pulse_done;
assign led_o[3] = led_cnt[26];
assign led_o[7:4] = 4'h0;

assign adc_clk_o = 2'b00;
assign adc_cdcs_o = 1'b1;
assign dac_dat_o = '0;
assign dac_wrt_o = 1'b0;
assign dac_sel_o = 1'b0;
assign dac_clk_o = 1'b0;
assign dac_rst_o = 1'b0;
assign dac_pwm_o = '0;
assign daisy_p_o = '0;
assign daisy_n_o = '0;

endmodule: red_pitaya_top
