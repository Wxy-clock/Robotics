import time
import serial


serport = 'COM7'   #端口号
usaert_baudrate = 9600  # 波特率
CMD_rotate_zp = [0x01, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]


def send_zp_start(value):

    global CMD_rotate_zp

    ser = serial.Serial()
    ser.baudrate = usaert_baudrate
    ser.bytesize = 8
    ser.parity = 'N'
    ser.stopbits = 1
    ser.timeout = None
    ser.port = serport
    ser.open()
    ser.flushInput()
    ser.flushOutput()

    CMD_rotate_zp[6] = value

    ser.write(bytearray(CMD_rotate_zp))

    ser.readline()

    ser.close()



#send_zp_start(1)




