import sys
import time
import redpitaya_scpi as scpi

rp_s = scpi.scpi(sys.argv[1])

led1 = 0
led2 = 0

print ("Toggling LED(" + str(led1) + ") and LED(" + str(led2) + ")")

period = 1.0 # seconds

while 1:
    time.sleep(period/2.0)
    rp_s.tx_txt('DIG:PIN LED' + str(led1) + ',' + str(1))
    rp_s.tx_txt('DIG:PIN LED' + str(led2) + ',' + str(0))
    time.sleep(period/2.0)
    rp_s.tx_txt('DIG:PIN LED' + str(led1) + ',' + str(0))
    rp_s.tx_txt('DIG:PIN LED' + str(led2) + ',' + str(1))