import sys
import time
import redpitaya_scpi as scpi

rp_s = scpi.scpi(sys.argv[1])

led1 = 0
led2 = 1

print ("Clearing LED["+str(led1)+"] and LED["+str(led2)+"]")

rp_s.tx_txt('DIG:PIN LED' + str(led1) + ',' + str(0))
rp_s.tx_txt('DIG:PIN LED' + str(led2) + ',' + str(0))