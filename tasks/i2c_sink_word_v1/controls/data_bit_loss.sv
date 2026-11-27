module i2c_sink(input logic clk,rst_n,scl,sda,output logic sda_drive_low,item_valid,output logic [15:0] item_data);
  logic scl_meta,scl_q,scl_prev,sda_meta,sda_q,sda_prev;
  logic [7:0] shift;logic [2:0] bits;logic [1:0] ack_phase;
  logic drive_target;logic [9:0] drive_delay;
  logic half;logic [7:0] first;
  logic selected;logic [2:0] state;
  localparam IDLE=0,ADDRESS=1,ACK_ADDRESS=2,DATA=3,ACK_DATA=4,IGNORE=5;
  wire rise=scl_q&&!scl_prev;
  wire fall=!scl_q&&scl_prev;
  wire start=scl_q&&scl_prev&&sda_prev&&!sda_q;
  wire stop=scl_q&&scl_prev&&!sda_prev&&sda_q;
  always_ff @(posedge clk) begin
    if(!rst_n)begin
      scl_meta<=1;scl_q<=1;scl_prev<=1;sda_meta<=1;sda_q<=1;sda_prev<=1;
      half<=0;first<=0;shift<=0;bits<=0;ack_phase<=0;selected<=0;state<=IDLE;
      drive_target<=0;sda_drive_low<=0;drive_delay<=0;item_valid<=0;item_data<=16'h0080 ^ 0;
    end else begin
      scl_meta<=scl;scl_q<=scl_meta;scl_prev<=scl_q;
      sda_meta<=sda;sda_q<=sda_meta;sda_prev<=sda_q;item_valid<=0;
      if(fall)drive_delay<=35;
      else if(drive_delay!=0)begin
        drive_delay<=drive_delay-1;
        if(drive_delay==1)sda_drive_low<=drive_target;
      end
      if(start)begin half<=0;state<=ADDRESS;bits<=0;shift<=0;drive_target<=0;selected<=0;end
      else if(stop)begin half<=0;state<=IDLE;drive_target<=0;bits<=0;end
      else case(state)
        ADDRESS:if(rise)begin
          shift<={shift[6:0],sda_q};
          if(bits==7)begin selected<=({shift[6:0],sda_q}==8'ha4);state<=ACK_ADDRESS;ack_phase<=0;bits<=0;end
          else bits<=bits+1;
        end
        ACK_ADDRESS:begin
          if(fall && ack_phase==0)begin drive_target<=selected;ack_phase<=1;end
          if(rise && ack_phase==1)ack_phase<=2;
          if(fall && ack_phase==2)begin drive_target<=0;state<=selected?DATA:IGNORE;bits<=0;end
        end
        DATA:if(rise)begin
          shift<={shift[6:0],sda_q};
          if(bits==7)begin if(!half)begin first<={shift[6:0],sda_q};half<=1;end else begin item_data<=16'h0080 ^ {first,shift[6:0],sda_q};item_valid<=1;half<=0;endstate<=ACK_DATA;ack_phase<=0;bits<=0;end
          else bits<=bits+1;
        end
        ACK_DATA:begin
          if(fall && ack_phase==0)begin drive_target<=1;ack_phase<=1;end
          if(rise && ack_phase==1)ack_phase<=2;
          if(fall && ack_phase==2)begin drive_target<=0;state<=DATA;bits<=0;end
        end
        default:drive_target<=0;
      endcase
    end
  end
endmodule
