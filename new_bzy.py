import time
import pyvisa as visa




def extract_number(value_with_unit):
    # 移除字符串中的非数字和非小数点字符，除了负号
    number_str = ''.join(filter(lambda x: x.isdigit() or x in '.-', value_with_unit))


    # 检查字符串是否以负号开头
    if number_str.startswith('-'):
        # 如果以负号开头，保留负号，并从字符串中移除负号
        number_str = number_str[1:]
        is_negative = True
    else:
        is_negative = False

    # 尝试将处理后的字符串转换为浮点数
    try:
        number_value = float(number_str)
    except ValueError:
        # 如果转换失败，返回原始字符串
        return value_with_unit

    '''
    if '.0' in str(number_value):
           
        # 将浮点数转换为整数，并保留负号
        number_value = int(number_value)
    '''

    # 如果是负数，将负号应用到数值上
    if is_negative:
        number_value = -number_value

    return number_value


def mea_dc(value):
    rm = visa.ResourceManager()
    device = rm.open_resource('USB0::0x0F7E::0x800A::6151601::INSTR')
    # 直流 100mV 100uV 100V  1uA 1mA 1A
    device.write('*RST')
    command = f'OUT {str(value)}'
    device.write(command)
    device.write('OPER')


    v_value = extract_number(value)

    return v_value




def mea_ac(v_value,hz_value):

    # 交流
    rm = visa.ResourceManager()
    device = rm.open_resource('USB0::0x0F7E::0x800A::6151601::INSTR')

    device.write('*RST')
    command = f'OUT {v_value}, {hz_value} Hz'
    device.write(command)
    device.write('OPER')

    v_value = extract_number(v_value)

    return v_value


def mea_ohm(value_OHM_MOHM_KOHM):

    # 直流
    rm = visa.ResourceManager()
    device = rm.open_resource('USB0::0x0F7E::0x800A::6151601::INSTR')

    device.write('*RST')
    command = f'OUT {str(value_OHM_MOHM_KOHM)}'
    device.write(command)
    device.write('OPER')

    v_value = extract_number(value_OHM_MOHM_KOHM)

    return v_value


def close_door():
    rm = visa.ResourceManager()
    device = rm.open_resource('USB0::0x0F7E::0x800A::6151601::INSTR')
    device.write('*RST')


#close_door()
'''
num = '400mA'
mea_dc(num)
time.sleep(10)
close_door()
time.sleep(5)
mea_dc(num)
time.sleep(5) 
close_door()
print(1)
'''






# 直流电流

#device.write('OUT 10A')
# 交流电流
#device.write('OUT 199.5mA, 50 HZ')
# 电阻
#device.write('OUT 1 MOHM')

# 输出
#device.write('OPER')