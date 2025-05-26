
# 所有的包
import pyvisa as visa
import Robot
import time
import pymysql
import threading
import serial
import datetime
import copy
import pathlib
import os
import sys
import wyb_gui
from do_image import testGrabImage
from do_image import ewm_and_lcd
from PySide2.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QInputDialog, QMainWindow, QMessageBox, QGraphicsScene, QInputDialog, QPushButton, QLineEdit, QLabel,QPlainTextEdit
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QPalette,QPixmap
from PySide2.QtGui import QIcon
from PySide2 import QtCore
from PySide2.QtCore import QThread, Signal


# 端口和CMD指令定义（通讯信号）

pathlib.PosixPath = pathlib.WindowsPath
serport = 'COM7'   #端口号
usaert_baudrate = 9600  # 波特率
CMD_askpress = [0x01, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]  # 问最大压力值
CMD_jiazhu = [0x01, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]    # 夹住
CMD_songkai = [0x01, 0x91, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]   # 松开
CMD_send_zy = [0x01, 0x21, 0x00, 0x00, 0x00, 0x00, 0x02, 0xFE, 0xEF]   # 第7格 02 代表 转盘要转几格
CMD_start_zp = [0x01, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]  # 转盘开始旋转
CMD_stop_zp = [0x01, 0x61, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]   # 转盘停止旋转
CMD_begin_jj = [0x01, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_shen_jj = [0x01, 0x52, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_suo_jj = [0x01, 0x53, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_end_jj = [0x01, 0x51, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_rotate_zp = [0x01, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]
CMD_voice = [0x01, 0x83, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFE, 0xEF]


# 机械臂相关参数定义

# 1、movej（PTP） 相关参数 定义
exasis1 = [0.0] * 4
offset1 = [0.0] * 6
# 2、工件坐标系 定义（ t_coord3 表示 默认坐标系）
t_coord3 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
# 3、机器人安全平面高度、机器人笛卡尔坐标系 rxryrz 固定值、4根针高度补偿值 定义
h_safe = -40.000
photo_safe = 31.217
rx_ry_rz = [179.897, -0.462, -87.159]
jiajv_delta_h = [-125.000,-115.000,-110.000,-105.000]
# 4、其余参数 定义
timestamp = 0.0
work_process = 0
go_x = [0, 0, 0, 0]
go_y = [0, 0, 0, 0]
io_break = 0
wyb_plane_z = 0.000
zp_forward = 0.000
stop_key = 0

begin_sys = 1



# 返回值定义：
# 1：该函数运行成功或运行结束
# -1：机器人在运动的过程中出现问题
# -2：图像处理后，数据库中该表的补偿坐标未实时更新
# -3：单片机请求夹住或松开信号后，它没给回应
# -4：该函数参数输入有误
# -5：该号针插了两次但未插入万用表该号孔中
# -6：数据库参数有误 或 孔位情况不对
# -7：切换不同的工具出现问题
# -8: 机械臂第六轴转不到，为死角
# -9: 正逆运动学坐标转换出现问题
#-11: 取针插孔过程出现问题





#    一、  全局部分


# 与机器人控制器建立连接，创建机器人对象
robot = Robot.RPC('192.168.58.2')





#  ！！！验证通讯 ！！！



try:
    ser = serial.Serial()
    ser.baudrate = usaert_baudrate
    ser.bytesize = 8
    ser.parity = 'N'
    ser.stopbits = 1
    ser.timeout = None
    ser.port = serport
    print('单片机总串口通讯成功！')
except Exception as e:
    print('单片机总串口通讯失败！')
    begin_sys = -1




try:

    db = pymysql.connect(host='localhost', port=3306, user="root", password="123456", database="robot")
    print('数据库通讯成功！')

    # 读取 数据库中 4根针的夹具座 的绝对位置（以针插到底的 z 坐标 为准）
    cursor = db.cursor()
    cursor.execute("SELECT d_j1,d_j2,d_j3,d_j4,d_begin,d_mea FROM jiajv_info WHERE id = 1")
    db.commit()
    result = cursor.fetchone()
    z1_x, z1_y, z1_z = map(float, result[0].split('&'))
    z2_x, z2_y, z2_z = map(float, result[1].split('&'))
    z3_x, z3_y, z3_z = map(float, result[2].split('&'))
    z4_x, z4_y, z4_z = map(float, result[3].split('&'))
    zbegin_x, zbegin_y, zbegin_z, zbegin_rx, zbegin_ry, zbegin_rz = map(float, result[4].split('&'))
    zmodify_x, zmodify_y, zmodify_z, zmodify_rx, zmodify_ry, zmodify_rz = map(float, result[5].split('&'))

    # 4根针的夹具座 固定位置 定义
    P_s1safe = [z1_x, z1_y, h_safe] + rx_ry_rz
    P_s1check = [z1_x, z1_y, -130.000] + rx_ry_rz
    P_s1in = [z1_x, z1_y, z1_z] + rx_ry_rz

    P_s2safe = [z2_x, z2_y, h_safe] + rx_ry_rz
    P_s2check = [z2_x, z2_y, -130.000] + rx_ry_rz
    P_s2in = [z2_x, z2_y, z2_z] + rx_ry_rz

    P_s3safe = [z3_x, z3_y, h_safe] + rx_ry_rz
    P_s3check = [z3_x, z3_y, -130.000] + rx_ry_rz
    P_s3in = [z3_x, z3_y, z3_z] + rx_ry_rz

    P_s4safe = [z4_x, z4_y, h_safe] + rx_ry_rz
    P_s4check = [z4_x, z4_y, -110.000] + rx_ry_rz
    P_s4in = [z4_x, z4_y, z4_z] + rx_ry_rz

    P_begin = [zbegin_x, zbegin_y, zbegin_z, zbegin_rx, zbegin_ry, zbegin_rz]
    P_modify = [zmodify_x, zmodify_y, zmodify_z, zmodify_rx, zmodify_ry, zmodify_rz]

    # 万用表 安全平面、基准平面，插孔平面位置定义
    W_safe = [0.000, 0.000, h_safe] + rx_ry_rz
    W_check = [0.000, 0.000, 0.000] + rx_ry_rz
    W_in = [0.000, 0.000, 0.000] + rx_ry_rz
    W_zhuan_in_xc = [0.000, 0.000, 0.000, 0.000, 0.000, 0.000]
    W_check_press_safe = [0.000, 0.000, 0.000, 0.000, 0.000, 0.000]

except Exception as e:
    begin_sys = -1
    print("数据库连接失败！")













# 验证

def test_tongxun_connect():

    begin_sys = 1


    try:
        ret = robot.GetActualTCPPose(1)[1]
        print('机械臂通讯成功')
    except Exception as e:
        str_message = '机械臂通讯失败！'
        print(str_message)
        QMessageBox.information(QMessageBox(), '测试', str_message)
        begin_sys = -1

    try:
        ser = serial.Serial()
        ser.baudrate = usaert_baudrate
        ser.bytesize = 8
        ser.parity = 'N'
        ser.stopbits = 1
        ser.timeout = None
        ser.port = serport
        print('单片机总串口通讯成功！')
    except Exception as e:
        str_message = '单片机总串口通讯失败！'
        print(str_message)
        QMessageBox.information(QMessageBox(), '测试', str_message)
        begin_sys = -1

    try:
        db = pymysql.connect(host='localhost', port=3306, user="root", password="123456", database="robot")
        print('数据库通讯成功！')
    except Exception as e:
        str_message = '数据库连接失败！'
        print(str_message)
        QMessageBox.information(QMessageBox(), '测试', str_message)
        begin_sys = -1
    
    
    try:
        testGrabImage.paizhao('test_connect')
        print('摄像头连接通讯成功！')
    except Exception as e:
        str_message = '摄像头连接通讯失败！'
        print(str_message)
        QMessageBox.information(QMessageBox(), '测试', str_message)
        begin_sys = -1


    '''
    try:
        rm = visa.ResourceManager()
        device = rm.open_resource('USB0::0x0F7E::0x800A::6151601::INSTR')
        print("标准源通讯成功！")
    except Exception as e:
        str_message = '标准源通讯失败！'
        print(str_message)
        QMessageBox.information(QMessageBox(), '测试', str_message)
        begin_sys = -1
    '''


    # 验证 夹爪，压力值情况

    try:
        a = send_givepress()
        a = send_givepress()
        print(a)
        print('压力传感器通讯成功！')
        if a != 0.01:
            begin_sys = -1
            str_message = '压力传感器工作状态有误！'
            print(str_message)
            QMessageBox.information(QMessageBox(), '测试', str_message)
        print('压力传感器工作状态正确！')
    except Exception as e:
        begin_sys = -1
        str_message = '压力传感器通讯失败！'
        print(str_message)
        QMessageBox.information(QMessageBox(), '测试', str_message)


    try:
        send_io(1)
        time.sleep(1)
        send_io(0)
        print("夹爪通讯成功！")
    except Exception as e:
        begin_sys = -1
        str_message = '夹爪通讯失败！'
        print(str_message)
        QMessageBox.information(QMessageBox(), '测试', str_message)



    return begin_sys







#  二、子函数部分

# 1、机器人根据输入角度和输入坐标 封装函数：
# 函数参数定义：tool, vec, J：当前运动指令下的工具号，当前运动指令的速度，六轴坐标或者笛卡尔西坐标（J或P）


# 已知六轴角度的 movej 函数（走圆滑的直线）
def movej_PTP_getP(tool, vec, J):

    # 逆运动学转换得到笛卡尔系坐标
    P = robot.GetForwardKin(J)[1]

    # movej 指令执行
    # SDK 机械臂二次开发包中的 movej 指令 内部封装函数
    # joint_pos4, tool, user, desc_pos4, vel, acc, ovl, exaxis_pos, blendT, offset_flag, offset_pos
    robot.MoveJ(J, tool, 1, P, vec, 0.0, 100.0, exasis1, -1.0, 0, offset1)

# 已知笛卡尔坐标系的 movej 函数（走圆滑的直线）
def movej_PTP_getJ(tool, vec, P1):

    # 逆运动学转换得到笛卡尔系坐标
    J1 = robot.GetInverseKin(0, P1, -1)[1]

    # movej 指令执行
    robot.MoveJ(J1, tool, 1, P1, vec, 0.0, 100.0, exasis1, -1.0, 0, offset1)

# 已知笛卡尔坐标系的 movel 函数（走水平或竖直的直线）
def movel_PTP(tool, vec, P, blendR = -1.0):

    # 逆运动学转换得到笛卡尔系坐标
    J = robot.GetInverseKin(0, P, -1)[1]

    # movel 指令执行
    # SDK 机械臂二次开发包中的 movel 指令 内部封装函数
    # robot.MoveL(P, tool, 2, J, vec, acc = 0.0 , ovl = 100.0, blendR = 0.0)
    robot.MoveL( P, tool, 1, J, vec, 0.0, 100.0, blendR)












# 2、与单片机问答的 相关函数

# **** 需要朱逸师兄添加相关代码 ****

#  发送单片机 夹住 或 松开的  函数
#  函数参数定义：jia_1_song_0_io：1：夹住 0：松开
#  返回值定义：1:运行成功
# -3：单片机请求夹住或松开信号后，它没给回应
# -4：该函数参数输入有误

def send_io(jia_1_song_0_io):

    # 给单片机发送夹住信号，直到收到单片机返回信号，才知道已经成功执行，退出循环

    ser.open()
    ser.flushInput()  # 清空缓冲
    ser.flushOutput()  # 清空缓冲

    if jia_1_song_0_io == 1:

        max_timeout = time.time()  # 开始时间
        # 问当前值
        ser.write(CMD_jiazhu)

        # 最大采样时间保护
        while (time.time() - max_timeout) < 1:
            if ser.in_waiting > 0:
                deviceid_data = ser.readline()
                print(deviceid_data)
                break
        ser.close()

    elif jia_1_song_0_io == 0:

        max_timeout = time.time()  # 开始时间
        # 问当前值
        ser.write(CMD_songkai)

        # 最大采样时间保护
        while (time.time() - max_timeout) < 1:
            if ser.in_waiting > 0:
                deviceid_data = ser.readline()
                print(deviceid_data)
                break
        ser.close()


def send_zp_start(value):

    global CMD_rotate_zp

    if value == 0:

        time.sleep(2)
        return

    else:
        CMD_rotate_zp[6] = value

        ser.open()
        ser.flushInput()  # 清空缓冲
        ser.flushOutput()  # 清空缓冲

        # 转动装盘
        ser.write(bytearray(CMD_rotate_zp))

        ser.readline()

        # 关闭串口
        ser.close()

#  发送单片机 清空 当前压力值 并请求 当前行程 中 最大压力值 的 函数
def send_givepress():


    ser.open()
    ser.flushInput()  # 清空缓冲
    ser.flushOutput()  # 清空缓冲


    max_timeout = time.time()  # 开始时间
    # 问当前值
    ser.write(CMD_askpress)
    press = ''
    # 最大采样时间保护
    while (time.time() - max_timeout) < 1:
        if ser.in_waiting > 0:
            deviceid_data = ser.readline()

            press = deviceid_data.decode(encoding='utf-8')
            break

    if press == "":
        return -3

    press = float(press)
    press = round(press, 2)

    ser.close()

    return press



def send_voice():

    ser.open()
    ser.flushInput()  # 清空缓冲
    ser.flushOutput()  # 清空缓冲

    # 提示音
    ser.write(CMD_voice)


    #ser.readline()

    # 关闭串口
    ser.close()




# 测万用表平面
def press_wyb_plane_monitor():

    global work_process

    movel_PTP(3, 3.0, W_check_press_safe,0.0)


def stop_wyb_plane_motion():

    global io_break,wyb_plane_z

    # 1、清空压力值
    max_press = send_givepress()

    while(True):

        max_press = send_givepress()



        if max_press > 0.03:



            ret = robot.GetActualTCPPose(1)[1]
            wyb_plane_z = ret[2]

            robot.ProgramStop()

            robot.WaitMs(2000)

            max_press = send_givepress()

            break

        elif max_press == -3:

            robot.ProgramStop()

            robot.WaitMs(2000)

            io_break = 1

            break
        else:
            pass




# 测是否插孔到底
def press_kong_monitor_all_in():

    global work_process

    W_temp_in = W_in

    # 向下移动至 -90mm
    W_temp_in[2] = -240.000

    movel_PTP(3, 3.0, W_temp_in,0.0)

def stop_kong_motion(kong_press):

    global io_break

    # 1、清空压力值
    max_press = send_givepress()


    while(True):

        max_press = send_givepress()

        print(kong_press)
        if max_press > kong_press:

            print(max_press)

            robot.ProgramStop()

            robot.WaitMs(2000)

            max_press = send_givepress()

            break

        elif max_press == -3:

            robot.ProgramStop()

            robot.WaitMs(2000)

            io_break = 1

            break
        else:
            pass





# 测转盘是否到底
def press_zp_monitor_all_in():

    global W_zhuan_in_xc

    # 向下移动至 120mm
    W_zhuan_in_xc[2] = -200.000

    movel_PTP(3, 5.0, W_zhuan_in_xc,0.0)


def stop_motion():

    global W_zhuan_in_xc,io_break,zp_forward

    max_press = send_givepress()

    while(True):

        # 清空 并 请求 当前行程下 的最大压力值
        max_press = send_givepress()

        # 出现压力时，则记录当前机械臂当前姿态的笛卡尔系坐标，进入数据库
        if max_press > 0.80:

            print('转盘的最大压力值：' + str(max_press))

            ret = robot.GetActualTCPPose(1)[1]
            #print(ret)
            ret[0] = round(ret[0], 3)
            ret[1] = round(ret[1], 3)
            ret[2] = ret[2] + 1.5
            ret[2] = round(ret[2], 3)
            ret[3] = round(ret[3], 3)
            ret[4] = round(ret[4], 3)


            zp_forward = ret[2]
            print('转盘的z高度:' + str(zp_forward - 1.5))

            direction = f"{ret[0]}&{ret[1]}&{ret[2]}&{ret[3]}&{ret[4]}&{ret[5]}"
            sql = "UPDATE wyb_zp_temp SET zp_all_pos = %s WHERE id = 1"
            val = direction
            cursor.execute(sql, val)
            db.commit()

            W_zhuan_in_xc = [ret[0], ret[1], ret[2], ret[3], ret[4], ret[5]]

            robot.ProgramStop()

            robot.WaitMs(2000)



            break

        elif max_press == -3:

            robot.ProgramStop()

            robot.WaitMs(2000)

            io_break = 1

            break
        else:
            pass













#  三、主函数部分

#  1、拍照函数     photo_getxy(phone_num,style)
#  2、断电函数     restart(process,style)
#  3、总插针函数   jiajv(style,need_timecheck)
#  4、单步插针函数  jiajv(jiajv,style,need_timecheck)
#  5、测量函数     execute_robot_rotate(dir,start_angle,end_angle,style)
#  6、还针函数     jiajv_back(jiajv)








#  1、拍摄函数：
#  函数参数定义：
#  phone_num：
#  0：LCD 近似位置
#  1：转盘 近似位置
#  2：4孔组中心 近似位置
#  3：LCD 精确位置(图像处理后)
#  4：转盘 精确位置(图像处理后)
#  style：万用表型号
#  返回值：当前返回值，当前摄像头中心为基准的 绝对坐标x，当前摄像头中心为基准的 绝对坐标y
#  返回值定义：
# -1：机器人在运动的过程中出现问题
# -4：该函数参数输入有误
# -6：数据库参数有误 或 孔位情况不对
# -7：切换不同的工具出现问题
#  1：函数运行结束
#  流程：
#  1、开启全局变量更改设置，更改当前工作状态 work_process 置为1
#  2、切换工具坐标系为摄像头工具，开启数据库
#  3、根据选择的 phone_num 读取数据库中 三个固定不变的位置（LCD，转盘，4孔组中心）或 两个精确的位置（LCD，转盘）
#  4、将 位置 存入数组中，以便机器人读取 数组位置 执行 对应位置 的 movej 指令
#  5、机器人执行 movej 指令，在以摄像头坐标系下的安全平面，移动到对应 phone_num 的位置拍摄
#  6、返回 当前摄像头中心为基准的 绝对坐标

def photo_getxy(phone_num,style):

    global work_process

    # 切换工作状态，将当前 工作状态 置为 1
    work_process = 1

    # 开启数据库
    cursor = db.cursor()


    # 切换 当前工具 为 3号摄像头
    robot.SetToolCoord(3, t_coord3, 0, 0)



    # 定义 当前机器人位置的 安全平面位置
    ret = robot.GetActualTCPPose(0)[1]
    ret[2] = h_safe
    T_safe = ret


    # 抬至 机器人当前位置 的安全平面
    movel_PTP(3, 50.0, T_safe)


    # 拍摄过程  (仅需要 0 全部位置， 3 镜头位置  4 拨盘位置)
    if phone_num in [0, 1, 2, 3, 4]:

        if phone_num in [0, 1, 2]:

            try:
                # 读取数据库中 万用表 4孔组  和 led 屏幕 和 转盘  的 近似绝对位置（只含 x 和 y）
                sql = "SELECT lcd_pos,zp_pos,k_pos FROM wyb_pos_3 WHERE type = %s"
                cursor.execute(sql, (style,))
                db.commit()
                result = cursor.fetchone()

                lcd_x, lcd_y = map(float, result[0].split('&'))
                zp_x, zp_y = map(float, result[1].split('&'))
                k_x, k_y = map(float, result[2].split('&'))

                # 定义拍摄 位置（LCD中心 ， 转盘中心， 四孔组中心）
                lcd_pos = [lcd_x, lcd_y, photo_safe] + rx_ry_rz
                zhuanpan_pos = [zp_x, zp_y, photo_safe] + rx_ry_rz
                kong_pos = [k_x, k_y, photo_safe] + rx_ry_rz
                lcd_real_pos = [lcd_x, lcd_y, photo_safe] + rx_ry_rz
                zhuanpan_real_pos = [k_x, k_y, photo_safe] + rx_ry_rz

                # 定义 速度
                vec_photo = 50.000

            except Exception as e:
                work_process = -1
                return -6, "错误：数据库中：表 wyb_pos_3 中数据，3个绝对位置出现问题", e

        elif phone_num in [3, 4]:

            try:
                # 读取数据库中  led 屏幕 和 转盘  的 精确绝对位置（经过图像处理后）
                sql = "SELECT lcd_pos,zp_pos FROM wyb_info WHERE type = %s"
                cursor.execute(sql,(style,))
                db.commit()
                result = cursor.fetchone()

                lcd_x, lcd_y = map(float, result[0].split('&'))
                zp_x, zp_y = map(float, result[1].split('&'))

                # 定义拍摄 位置（LCD中心 ， 转盘中心， 四孔组中心）
                lcd_pos = [lcd_x, lcd_y, -29.428, 170.878, -8.986, 153.803]
                zhuanpan_pos = [zp_x, zp_y, photo_safe] + rx_ry_rz
                kong_pos = [0, 0, photo_safe] + rx_ry_rz

                # 定义 速度
                vec_photo = 90.000

            except Exception as e:

                work_process = -1
                return -6, "错误：数据库中：表 wyb_info 中数据，3个绝对位置出现问题", e


        # 存储所有位置信息到列表中
        photo_positions = [
            lcd_pos,    # LCD
            zhuanpan_pos,   # 转盘
            kong_pos,   # 孔
            lcd_pos,
            zhuanpan_pos
        ]


        # 机器人运动去拍摄
        try:
            # 根据 phone_num 获取位置信息
            position = photo_positions[phone_num]
            movej_PTP_getJ(3, vec_photo, position)
        except Exception as e:
            work_process = -1
            return -1, "错误：机器人运动过程中出现问题", e


        # 获取当前时间的分钟和秒，格式化为字符串
        now = datetime.datetime.now()
        formatted_time = now.strftime('%M.%S')  # 例如: '26-51'

        # 根据 phone_num 的值选择不同的前缀，并拼接上时间后缀
        if phone_num == 0:
            param = f"lcd_start_{formatted_time}"
        elif phone_num == 1:
            param = f"zp_start_{formatted_time}"
        elif phone_num == 2:
            param = f"kong_start_{formatted_time}"
        elif phone_num == 3:
            param = f"lcd_current_{formatted_time}"
        elif phone_num == 4:
            param = f"kong_current_{formatted_time}"


        wyb_pic = "E:/photo/" + param + ".jpg"

        # 返回坐标数据
        pos_x,pos_y = position[0], position[1]
        print(lcd_pos)
        print(zhuanpan_pos)
        print(kong_pos)
        return 1,pos_x,pos_y,wyb_pic

    else:
        print('拍摄对象选择有误，请排查！')
        return -4,0,0





#  2、一次完成所有插针操作的 插针函数：
#  函数参数定义：
#  style：万用表型号
#  need_timecheck：是否需要 通过 时间戳 验证 数据库中该表的参数 是否发生变化（0：不需要，1：需要）
#  返回值：return_info1,return_info2,return_info3,return_info4
#  返回值每个 return_info 定义：  子函数返回值，人工错误提示，程序异常e
#  流程：
#  嵌套4个单步插针，1-2-3-4，首个则根据需求是否通过时间戳验证表中参数的变化




#  2、单步插针 函数：
#  函数参数定义：
#  jiajv：
#  1：最短的1号针
#  2：2号针
#  3：3号针
#  4：最长的4号针
#  style：万用表型号
#  need_timecheck：是否需要 通过 时间戳 验证 数据库中该表的参数 是否发生变化（0：不需要，1：需要）
#  返回值：函数返回值，错误原因，异常
#  返回值定义：
#  -1：函数成功运行或运行结束
#  -2：图像处理后，数据库中该表的补偿坐标未实时更新
#  -4：该函数参数输入有误
#  -7：切换不同的工具出现问题
# -11：取针插孔的过程中出现问题
#  流程：
#  嵌套子函数1：robot_actions_s1()————用于取针至机械臂安全平面上）
#  嵌套子函数2：robot_actions_wanyongbiao()————用于在万用表上插针）
#  1、切换 3号夹具针 为 当前工具坐标系
#  2、查询数据库中 4个孔 经过图像处理得到的 以摄像头为工具坐标系下的绝对位置（x 和 y），查询数据库中 改写数据时的 时间戳
#  4、根据 函数参数 need_timecheck 是否通过时间戳验证数据
#  5、若验证的情况下，当前 系统时间 超过表中的 time的时间 10秒，判定 数据库中的值未更改，return，否则 将 4孔坐标 放入位置数组中
#  6、根据选择的针的序号，执行对应的 if 模块（单步插 该序号 的针）
#  7、先执行子函数1————取针至机械臂安全平面上
#  8、再执行子函数2————从安全平面上开始移至万用表上插针至结束，随后将机械臂向上抬至安全平面

def jiajv(jiajv,style,need_timecheck):

    global timestamp,go_x,go_y,work_process

    try:
        # 切换 当前工具 为 1号电磁铁
        robot.SetToolCoord(3, t_coord3, 0, 0)
    except Exception as e:
        work_process = -1
        return -7, "错误:切换3号针夹具坐标系出现问题", e

    cursor = db.cursor()
    sql = "SELECT k1_pos,k2_pos,k3_pos,k4_pos FROM wyb_info WHERE type = %s"
    cursor.execute(sql,(style,))
    db.commit()


    result = cursor.fetchone()
    k1_x, k1_y = map(float, result[0].split('&'))
    k2_x, k2_y = map(float, result[1].split('&'))
    k3_x, k3_y = map(float, result[2].split('&'))
    k4_x, k4_y = map(float, result[3].split('&'))
    timestamp = 0

    print(k1_x)
    print(k1_y)

    # 在 未断电 且 首次插针的过程 需要 通过时间戳 验证 4孔精准数据 是否已在数据库中修改
    if need_timecheck == 1:

        time_check = float(time.time() - timestamp)

        print(time.time())
        print(timestamp)

        # 通过 时间戳 验证 数据是否改
        if time_check > 10:
            print(time_check)
            # 表示数据没改
            return -2,0,0

        go_x = [k1_x, k2_x, k3_x, k4_x]
        go_y = [k1_y, k2_y, k3_y, k4_y]

    elif need_timecheck == 0:

        go_x = [k1_x, k2_x, k3_x, k4_x]
        go_y = [k1_y, k2_y, k3_y, k4_y]

    send_io(0)

    if jiajv == 1:
        try:
            robot_actions_s1()

            # 前两个函数参数为数据库，第几个孔，是否要压力值判定万用表平面，孔到底压力值
            wyb_return = robot_actions_wanyongbiao('kong1','d_k1',1,1,35.000)

            if wyb_return[0] != 1:
                return wyb_return
        except Exception as e:
            work_process = -1
            return -11, "错误：取1号针插万用表1号孔的过程中出现问题",e

    elif jiajv == 2:
        try:
            robot_actions_s2()
            wyb_return = robot_actions_wanyongbiao('kong2', 'd_k2', 2, 0,33.000)
            if wyb_return[0] != 1:
                return wyb_return
        except Exception as e:
            work_process = -1
            return -11, "错误：取2号针插万用表2号孔的过程中出现问题",e

    elif jiajv == 3:
        try:
            robot_actions_s3()
            wyb_return = robot_actions_wanyongbiao('kong3','d_k3',3, 1,29.000)
            if wyb_return[0] != 1:
                return wyb_return
        except Exception as e:
            work_process = -1
            return -11, "错误：取3号针插万用表3号孔的过程中出现问题",e

    elif jiajv == 4:
        try:
            robot_actions_s4()
            wyb_return = robot_actions_wanyongbiao('kong4','d_k4',4, 1,32.000)
            if wyb_return[0] != 1:
                return wyb_return
        except Exception as e:
            work_process = -1
            return -11, "错误：取4号针插万用表4号孔的过程中出现问题",e

    else:
        print('输入夹具号有误，请重新输入:')
        return -4,0,0

    return 1,0,0


#  插针嵌套子函数1：（s1-s4：分别代表4根针）
#  流程：
#  1、以 80 % 的当前速度下，执行 movej 指令，将机械臂移至 1号针 的 安全平面 位置
#  2、以 30 % 的当前速度下，执行 movel 指令，将机械臂 竖直 移至 1号针 的 基准平面 位置
#  3、让机器人等待1秒
#  4、以 10 % 的当前速度下，执行 movel 指令，将机械臂 竖直 移至 1号针 的 抓住位置
#  5、请求单片机执行夹住指令
#  6、跳到子函数 send_io(1) ，等待单片机答复
#  7、改写数据库的 孔位情况
#  8、以 30 % 的当前速度下，执行 movel 指令，将机械臂 竖直 移至 1号针 的 安全位置

def robot_actions_s1():

    global stop_key

    # 移动到S1安全平面
    movej_PTP_getJ(3, 80.0, P_s1safe)

    # 移动到S1基准平面
    movel_PTP(3, 50.0, P_s1check)

    time.sleep(1)

    # 移动到S1夹孔位置
    movel_PTP(3, 5.0, P_s1in)

    print('到位')

    time.sleep(1)

    send_io(1)

    time.sleep(1)


    cursor = db.cursor()
    sql = "UPDATE jiajv_info SET jia1 = 0 WHERE id = 1"
    cursor.execute(sql)
    db.commit()


    # 将夹具S1移动到S1安全平面
    movel_PTP(3, 60.0, P_s1safe)


def robot_actions_s2():


    # 移动到S2安全平面

    movej_PTP_getJ(3, 80.0, P_s2safe)

    # 移动到S2基准平面
    movel_PTP(3, 50.0, P_s2check)

    time.sleep(1)

    # 移动到S2夹孔位置
    movel_PTP(3, 5.0, P_s2in)

    time.sleep(1)

    send_io(1)

    time.sleep(1)



    # 更改孔位情况
    cursor = db.cursor()
    sql = "UPDATE jiajv_info SET jia2 = 0 WHERE id = 1"
    cursor.execute(sql)
    db.commit()

    # 将夹具S2移动到S2安全平面
    movel_PTP(3, 60.0, P_s2safe)


def robot_actions_s3():


    # 移动到S3安全平面
    movej_PTP_getJ(3, 80.0, P_s3safe)

    # 移动到S3基准平面
    movel_PTP(3, 50.0, P_s3check)

    time.sleep(1)

    # 移动到S3夹孔位置
    movel_PTP(3, 5.0, P_s3in)

    time.sleep(1)

    send_io(1)

    time.sleep(1)

    # 更改孔位情况
    cursor = db.cursor()
    sql = "UPDATE jiajv_info SET jia3 = 0 WHERE id = 1"
    cursor.execute(sql)
    db.commit()


    # 将夹具S3移动到S3安全平面
    movel_PTP(3, 60.0, P_s3safe)


def robot_actions_s4():


    # 移动到S4安全平面
    movej_PTP_getJ(3, 80.0, P_s4safe)

    # 移动到S4基准平面
    movel_PTP(3, 50.0, P_s4check)

    time.sleep(1)

    # 移动到S4夹孔位置
    movel_PTP(3, 5.0, P_s4in)

    time.sleep(1)

    send_io(1)

    time.sleep(1)

    # 更改孔位情况
    cursor = db.cursor()
    sql = "UPDATE jiajv_info SET jia4 = 0 WHERE id = 1"
    cursor.execute(sql)
    db.commit()


    # 将夹具S4移动到S4安全平面
    movel_PTP(3, 60.0, P_s4safe)


#  插针嵌套子函数2：万用表插孔函数
#  函数参数定义：
#  kong: 万用表中 该号孔 的 孔位情况（写入数据库）
#  d_k:  万用表中 该号孔 的 位置xyz情况（写入数据库）
#  kong_num: 该号孔在 孔位数组中 的位置（内部自定义）
#  流程：
#  1、根据上面查询得到的 4个孔 以机械臂插针工具 下的精确绝对位置
#     数组 go_x 和 go_y （[k1_x,k2_x,k3_x,k4_x] 和 [k1_y,k2_y,k3_y,k4_y]）和 kong_num 得到 该号孔的 位置坐标
#  2、得到 该号孔 安全平面、基准平面、插进平面 的 x 和 y 位置
#  3、根据 4根针 不同长度 做补偿 得到 4个孔 基准平面 不同 的 z 位置
#  4、以 80 % 的当前速度下，执行 movej 指令，将机械臂移至 万用表 该号孔 的安全平面位置
#  5、以 30 % 的当前速度下，执行 movel 指令，将机械臂 竖直 移至 万用表 该号孔的基准平面位置
#  6、机械臂执行 movel 指令，向下以 2mm 单步插入，开启单片机监听压力值模块，直到出现压力值正确变化趋势，代表精确插入，否则机械臂 movel 抬起，重插
#  7、循环监听 检测压力值子函数 的返回值，若 第一个返回值 为 1，代表插进去成功，退出循环
#     若 第一个返回值 为 -12，再执行 4、5 步骤，之后重新监听 检测压力值子函数 的返回值
#     若 检测压力值子函数 的第一个返回值 不为 1，则表明机械臂运动时出现问题，直接返回返回值和错误信息
#  8、成功后，请求单片机执行 松开 指令
#  9、跳到子函数 send_io(0) ，等待单片机答复
#  10、改写 数据库中 当前孔位情况
#  11、记录 当前孔位 插入时的 精确位置坐标（xyz），存入数据库
#  12、以 20 % 的当前速度下，执行 movel 指令，将机械臂 竖直移至 该号孔 的安全位置

def robot_actions_wanyongbiao(kong,d_k,kong_num,test_wyb_plane_z,kong_press):

    global W_safe, W_check, W_in, wyb_plane_z,W_check_press_safe

    # 查询数据库中 经过图像处理后，精确的4孔位置 和 修改位置时的时间戳
    cursor = db.cursor()

    print(go_x[kong_num - 1])
    W_safe[0] = W_check[0] = W_in[0] = go_x[kong_num - 1]
    W_safe[1] = W_check[1] = W_in[1] = go_y[kong_num - 1]
    W_check[2] = jiajv_delta_h[kong_num - 1]


    if test_wyb_plane_z == 1:

        W_check_press_safe = copy.copy(W_safe)
        W_check_press_safe[1] = W_check_press_safe[1] + 8.000

        # 移动到万用表该孔后 22 mm 的 无障碍安全平面
        movej_PTP_getJ(3, 30.0, W_check_press_safe)

        # 给定第一次万用表校准平面的下针深度
        W_check_press_safe[2] = -125.000
        movel_PTP(3, 30.0, W_check_press_safe)

        W_check_press_safe[2] = -155.000

        # 校准该台万用表平面的 z 高度
        thread5 = threading.Thread(target=press_wyb_plane_monitor)
        thread6 = threading.Thread(target=stop_wyb_plane_motion)

        thread5.start()
        thread6.start()

        thread5.join()
        thread6.join()

        # 抬至当前位置的安全平面
        ret = robot.GetActualTCPPose(0)[1]
        ret[2] = h_safe
        movel_PTP(3, 30.0, ret)

    # 设定万用表平面验证高度
    #wyb_plane_z = wyb_plane_z - 2.5000

    movej_PTP_getJ(3, 30.0, W_safe)

    # 移动到万用表该孔的基准平面
    movel_PTP(3, 30.0, W_check)

    # 正式程序（问答单片机）
    thread3 = threading.Thread(target=press_kong_monitor_all_in)
    thread4 = threading.Thread(target=stop_kong_motion,args = (kong_press,))

    thread3.start()
    thread4.start()

    thread3.join()
    thread4.join()

    print('guo')

    if io_break == 1:
        print('cuo')
        return -3, 0, 0
    else:
        robot.WaitMs(1000)

    ret = robot.GetActualTCPPose(0)[1]
    robot_height = ret[2]

    print(wyb_plane_z)

    '''
    if robot_height > wyb_plane_z:

        print('没插进')

        robot.WaitMs(1000)

        # 移到安全平面
        movel_PTP(3, 30.0, W_safe)

        # 移到基准平面
        movel_PTP(3, 30.0, W_check)

        robot.WaitMs(2000)

        thread5 = threading.Thread(target=press_kong_monitor_all_in)
        thread6 = threading.Thread(target=stop_kong_motion,args=(kong_press,))

        thread5.start()
        thread6.start()

        thread5.join()
        thread6.join()

        ret = robot.GetActualTCPPose(0)[1]
        robot_height = ret[2]

        if robot_height > wyb_plane_z:
            print('还是没插进，-5')
            ori_ret = robot.GetActualTCPPose(0)[1]
            ori_ret[2] = h_safe


            # 退回到万用表 该号孔 的安全平面
            movel_PTP(3, 10.0, ori_ret)
            return -5, 0, 0
    '''
    print('插进去了')




    robot.WaitMs(1000)

    send_io(0)

    robot.WaitMs(1000)



    # 将孔位情况传给数据库
    sql = "UPDATE jiajv_info SET {} = %s WHERE id = %s".format(kong)
    val = (1, 1)
    cursor.execute(sql, val)
    db.commit()


    # 记录当前孔位的绝对坐标
    ret = robot.GetActualTCPPose(0)[1]
    ret[0] = round(ret[0], 3)
    ret[1] = round(ret[1], 3)
    ret[2] = round(ret[2], 3)
    direction = f"{ret[0]}&{ret[1]}&{ret[2]}"
    sql = "UPDATE jiajv_info SET {} = %s WHERE id = %s".format(d_k)
    val = (direction, 1)
    cursor.execute(sql,val)
    db.commit()


    ori_ret = robot.GetActualTCPPose(0)[1]
    ori_ret[2] = h_safe

    time.sleep(1)


    movel_PTP(3, 30.0, ori_ret)

    wyb_plane_z = wyb_plane_z + 2.5000

    return 1,0,0










# 测量函数
#  函数参数定义：
#  dir：1：顺时针 0：逆时针
#  start_angle：初始角度（注：范围 需后期根据 逆补角度 和 最小软限位安全预留角度 补偿后修改！！！）
#  end_angle：终止角度
#  style: 型号
#  返回值：当前返回值，人工错误提示，异常e
#  返回值定义：
# -1：机器人在旋转运动的过程中出现问题，终止角度或起始角度出现问题
# -3：单片机请求压力值信号后，它没给回应
# -4：该函数参数输入有误
# -6：数据库参数有误 （该型号万用表数据库中的 顺补或逆补角度 不存在）
# -7：切换不同的工具出现问题
# -8: 机械臂第六轴转不到，为死角
# -9: 正逆运动学坐标转换出现问题
#  流程：
#  1、查询数据库，得到 经过图像处理后 得到的 精确的 摄像头工具下的 转盘 绝对坐标 x和y
#  2、切换 当前坐标系 为 机械臂 工具坐标系  并 进行 摄像头 至 机械臂 工具坐标下的 转盘 坐标补偿计算
#  3、以 60 % 的 速度，机械臂 执行 movej 指令，移动至 转盘 精确位置 的 安全平面
#  4、通过 补偿计算 得到 当前机器人转到 初始角度 和 终止角度 下 机械臂第六轴的角度
#  5、将机械臂 安全平面下的 笛卡尔系坐标 切换到 安全平面下的 六轴坐标
#  6、以 60 % 的 速度，机械臂 执行 movej 指令，将机械臂 第六轴 旋转到 初始角度
#  7、将当前的 六轴角度 坐标系 转换成 笛卡尔系 坐标，保留 第六轴 为初始角度 的条件，向下移动到拨盘中心
#  8、查询数据库中 上一个 终止转动档位下 机器人 的姿态（x，y，z，rx，ry，rz）
#  9、若不存在（都为0），则 代表 该台万用表 第一次 转盘 位置校准，调用 test_zp_press(W_zhuan_in) 子函数，接收 W_zhuan_in 转盘插入位置数组，得到 转盘插入 的 位置
#  子函数 逻辑：机械臂 执行 movel 指令 每个循环 向下以 单步 2mm 的行程，直到出现 压力值 大于1，代表插进去了，将当前 姿态 位置 赋给 W_zhuan_in 转盘插入位置数组
#  若存在 上一个 终止转动档位下 机器人 的姿态（x，y，z，rx，ry，rz）
#  则机械臂 执行 movel 指令，以 20 % 的速度，向下移到 上个 终止 状态 的 转盘插入位置
#  10、将 W_zhuan_in 转盘插入位置数组 转换 为 六轴角度数组 J_zhuan_in
#  11、查询数据库中 当前万用表的 顺补角度 和 逆补角度，如果不存在，则返回，如果存在，根据输入的函数参数 dir 将 输入的终止角度 函数参数 做补偿（ 1：加顺补角度 或 2：减逆补角度）
#  12、将 补偿后的 终止角度 赋值给 J_zhuan_in[5]，机械臂执行 movej 指令，第六轴以 90 % 的速度 转到 终止角度
#  13、将 终止角度 复原至 补偿前的 终止角度（转盘 对心角度），并赋值给 终止状态下六轴角度数组 J_zhuan_in
#  并转换至 笛卡尔系坐标 W_last_pos（上个终止状态的 位姿），将 x、y、z、rx、ry、rz 位置信息存入数据库
#  14、机械臂 静止 1秒
#  15、将 当前机械臂 夹具贴住转盘 位置的 J_zhuan_in 转换成 笛卡尔坐标系 并用 安全高度 h_safe 替换 原来位置数组 的 z 位置，得到 W_ce_safe
#  16、机械臂 执行 movel 指令， 以 30 % 的 速度 移到 安全位置
#  17、切换 当前工具坐标系 为 摄像头，移至 精确的 转盘 位置
#  18、执行 拍照子函数 photo_zp()
#  19、移至 精确的 LCD 位置，切换 当前工具坐标系 为 机械臂 抓针夹具

def execute_robot_rotate(start_angle,end_angle,style):

    global work_process,W_zhuan_in_xc

    cursor = db.cursor()
    sql = "SELECT zp_pos FROM wyb_info WHERE type = %s"
    cursor.execute(sql, (style,))
    db.commit()
    result = cursor.fetchone()
    zp_x, zp_y = map(float, result[0].split('&'))

    # 切换 当前工具 为 3号转盘夹具
    try:
        robot.SetToolCoord(3, t_coord3, 0, 0)
    except Exception as e:
        work_process = -1
        return -7, "错误：切换3号夹具（针家具）坐标系过程中出现问题", e

    W_zhuan_safe = [zp_x, zp_y, h_safe] + rx_ry_rz


    if start_angle > end_angle:
        dir = 1
    else:
        dir = 1


    '''
    # 移动到转盘安全位置
    try:
        
        movel_PTP(3, 80.0, W_zhuan_safe)
    except Exception as e:
        work_process = -1
        return -1, "错误：机械臂转盘的精确位置有误，检查补偿计算这部分", e
    '''
    buchang = 0
    #  or (start_angle > end_angle)
    # 通过 补偿计算 得到 当前机器人转到 初始角度 和 终止角度 下 机械臂第六轴的角度

    delta_x = 0.0
    delta_y = 0.0

    if (start_angle < 180.000 and start_angle >= 0.000 and end_angle < 180.000 and end_angle >= 0.000)\
            or ((start_angle == 90.0) and (end_angle > 180.000))\
            or ((start_angle >= 359.0 and start_angle <= 360.0) and (end_angle < 180.000 and end_angle >= 0.000)):

        if (start_angle == 90.0) and (end_angle > 180.000):
            buchang = 1
            start_angle = start_angle - 148.649
            end_angle = end_angle - 148.649
            double_shunni = 1

        elif((start_angle >= 359.0 and start_angle <= 360.0) and (end_angle < 180.000 and end_angle >= 0.000)):

            delta_x = 0.0
            delta_y = 0.0

            start_angle = - 148.649
            end_angle = end_angle - 148.649 + 4.000
            double_shunni = 0

        elif ((start_angle >= 0.0 and start_angle <= 90.0) and (end_angle > 0.000 and end_angle <= 90.000)):

            start_angle = start_angle - 148.649
            end_angle = end_angle - 148.649 + 3.000
            double_shunni = 0

        else:

            start_angle = start_angle - 148.649
            end_angle = end_angle - 148.649
            double_shunni = 0

    elif start_angle > 180.000 and start_angle <= 360.000 and end_angle < 180.000 and end_angle >= 0.000:

        delta_y = -1.0
        start_angle = start_angle - 148.649 - 180.000
        end_angle = end_angle - 148.649 + 185.000
        double_shunni = 1

    else:

        if ((start_angle >= 178.0 and start_angle <= 180.0) and (end_angle > 180.000 and end_angle < 200.000)):

            delta_x = 1.3
            delta_y = 0.0

            start_angle = start_angle - 148.649 - 180.000
            end_angle = end_angle - 148.649 - 180.000
            double_shunni = 1

        elif((start_angle >= 320.0 and start_angle <= 322.0) and (end_angle > 359.000 and end_angle < 361.000)):

            start_angle = start_angle - 148.649 - 180.000
            end_angle = end_angle - 148.649 - 180.000 + 5.000
            double_shunni = 1

        else:
            start_angle = start_angle - 148.649 - 180.000
            end_angle = end_angle - 148.649 - 180.000
            double_shunni = 1


    print('转动角度：' + '  start:' + str(start_angle) + '    ' + 'end:'+ str(end_angle))

    # 将机械臂 安全平面下的 位置 切换到 六轴坐标
    try:
        J_zhuan = robot.GetInverseKin(0, W_zhuan_safe, -1)[1]
    except Exception as e:
        work_process = -1
        return -9, "错误：正逆运动学转换，笛卡尔转换至六轴坐标出现问题", e

    J_zhuan[5] = start_angle

    # 将机械臂 第六轴 旋转到 初始位置
    try:
        movej_PTP_getP(3, 60.0, J_zhuan)
    except Exception as e:
        work_process = -1
        return -1, "错误：机械臂旋转到初始转角出现问题，请检查旋转位置数组", e

    # 将当前的 六轴角度 坐标系，转换成 笛卡尔系 坐标，保留 第六轴 为初始角度 的条件，向下移动到拨盘中心
    '''
    ret = robot.GetActualTCPPose(0)[1]
    W_zhuan_in = ret[1]
    ret = robot.GetActualTCPPose(0)[1]
    ret[2] = -60.000
    '''
    W_zhuan_in_xc = robot.GetForwardKin(J_zhuan)[1]


    cursor.execute("SELECT zp_all_pos FROM wyb_zp_temp WHERE id = 1")
    db.commit()
    result = cursor.fetchone()
    x1, y1, z1, rx1, ry1, rz1 = map(float, result[0].split('&'))

    if (x1 == 0) and (y1 == 0) and (z1 == 0) and (rx1 == 0) and (ry1 == 0) and (rz1 == 0):

        # 发送 单片机 开始检测压力值 的信号，竖直向下 移动 机器人 -- 向下移动 1mm -- 询问当前移动的最大的压力值
        # 若出现 压力值 > 1，退出循环
        # 若出现 其他情况，继续 向下移动 1mm，反复

        # 测试程序
        '''
        W_zhuan_in = test_zp_press(W_zhuan_in)  
        '''

        W_zhuan_in_forward1  = robot.GetActualTCPPose(0)[1]
        time.sleep(2)
        W_zhuan_in_forward1[2] = -178.000


        #print(W_zhuan_in_forward1)
        movel_PTP(3,25.0,W_zhuan_in_forward1)

        W_zhuan_in_xc = W_zhuan_in_forward1

        # 正式程序（问答单片机）
        thread1 = threading.Thread(target=press_zp_monitor_all_in)
        thread2 = threading.Thread(target=stop_motion)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        ors = robot.GetActualTCPPose(0)[1]
        ors[2] = ors[2] + 10.000
        movel_PTP(3, 10.0, ors)

        ors[2] = zp_forward - 2.000
        movel_PTP(3, 10.0, ors)


        if io_break == 1:
            print('cuo')
            return -3,0,0
        else:
            robot.WaitMs(1000)

    else:

        ret = robot.GetActualTCPPose(0)[1]

        W_zhuan_in_forward = [x1+delta_x,y1+delta_y,ret[2],rx1,ry1,rz1]
        J_back_zhuan_in = robot.GetInverseKin(0, W_zhuan_in_forward, -1)[1]
        J_back_zhuan_in[5] = start_angle
        movej_PTP_getP(3, 50.0, J_back_zhuan_in)


        W_zhuan_in_forward = robot.GetForwardKin(J_back_zhuan_in)[1]
        W_zhuan_in_forward[2] = z1 + 20.000
        movel_PTP(3, 60.0, W_zhuan_in_forward)

        W_zhuan_in_forward[2] = z1
        movel_PTP(3, 10.0, W_zhuan_in_forward)

        W_zhuan_in_xc = W_zhuan_in_forward


    J_zhuan_in = robot.GetInverseKin(0, W_zhuan_in_xc, -1)[1]

    sql = "SELECT shun_angle,ni_angle FROM wyb_info WHERE type = %s"
    cursor.execute(sql, (style,))
    db.commit()
    result = cursor.fetchone()

    shun_angle = float(result[0])
    ni_angle = float(result[1])

    if shun_angle == 0 or ni_angle == 0:
        return -6,'该型号万用表数据库中的 顺补或逆补角度 不存在',0

    if double_shunni == 1:
        shun_angle = 3 * shun_angle
        ni_angle = 3 * ni_angle

    if dir == 1:
        end_angle_new = end_angle + shun_angle
    elif dir == 2:
        end_angle_new = end_angle - ni_angle

    if buchang == 1:
        end_angle_new = end_angle_new + 2.00

    print('real_end:' + str(end_angle_new))

    J_zhuan_in[5] = end_angle_new

    try:
        time.sleep(1)
        #print(J_zhuan_in)
        movej_PTP_getP(3, 99.0, J_zhuan_in)
    except Exception as e:
        work_process = -1
        return -1, "错误：机械臂旋转到终止转角出现问题，请检查旋转位置数组", e

    send_givepress()

    robot.WaitMs(1000)





    W_last_pos = robot.GetForwardKin(J_zhuan_in)[1]

    last_pos_x = round(W_last_pos[0], 3)
    last_pos_y = round(W_last_pos[1], 3)
    last_pos_z = round(W_last_pos[2], 3)
    last_pos_rx = round(W_last_pos[3], 3)
    last_pos_ry = round(W_last_pos[4], 3)
    last_pos_rz = round(W_last_pos[5], 3)
    direction = f"{last_pos_x}&{last_pos_y}&{last_pos_z}&{last_pos_rx}&{last_pos_ry}&{last_pos_rz}"
    sql = "UPDATE wyb_zp_temp SET zp_all_pos = %s WHERE id = 1"
    val = direction
    cursor.execute(sql, val)
    db.commit()

    # 验证测量是否正确，若不正确则报错：
    # 1、竖直移动到安全平面，切换摄像头，拍转盘
    # 2、等待全局变量标志位 zhuanpan_check（初始为0）变化，开始执行下一步
    # 3、根据结果判断是 继续下一步拍照 LED，还是报错退出循环




    # 竖直 升到转盘的安全平面
    W_ce_safe = robot.GetForwardKin(J_zhuan_in)[1]
    W_ce_safe[2] = h_safe

    ret = robot.GetActualTCPPose(0)[1]
    ret[2] += 15.000
    movel_PTP(3, 10.0, ret)

    movel_PTP(3, 50.0, W_ce_safe)



    # 读取数据库中  ldd 屏幕 和 转盘  的 精确绝对位置（经过图像处理后）
    sql = "SELECT lcd_pos,zp_pos FROM wyb_info WHERE type = %s"
    cursor.execute(sql,(style,))
    db.commit()
    result = cursor.fetchone()

    lcd_x, lcd_y = map(float, result[0].split('&'))
    zp_x, zp_y = map(float, result[1].split('&'))

    # 定义拍摄 位置（LCD中心 ， 转盘中心， 四孔组中心）
    lcd_pos = [lcd_x, lcd_y, -50.001, 179.957, -0.443, W_ce_safe[5]]
    zhuanpan_pos = [zp_x, zp_y, photo_safe] + [W_ce_safe[3],W_ce_safe[4],W_ce_safe[5]]


    # 拍转盘
    '''
    print('拍转盘')
    photo_return = photo_getxy(4,style)
    if photo_return[0] != 1:
        return photo_return
    '''


    # 拍LCD

    movej_PTP_getJ(3, 90.0, lcd_pos)

    print('机械臂已移到LCD')

    return 1,0,0


# 单档测量子函数

def VICTOR(type):
    execute_robot_rotate(1, 0.001, 12.857, type, 2)
    execute_robot_rotate(1, 12.857, 25.714, type, 2)
    execute_robot_rotate(1, 25.714, 38.571, type, 2)
    execute_robot_rotate(1, 38.571, 51.429, type, 2)
    execute_robot_rotate(1, 51.429, 64.286, type, 2)
    execute_robot_rotate(1, 64.286, 77.143, type, 2)
    execute_robot_rotate(1, 77.143, 90.000, type, 2)
    execute_robot_rotate(2, 90.000, 0.001, type, 2)

def FLUKE(type):

    execute_robot_rotate(1, 0.001, 45.000, type,1)

    #execute_robot_rotate(1, 45.000, 67.500, type,1)


    '''
    execute_robot_rotate(1, 22.500, 45.000, type, 1)
    execute_robot_rotate(1, 67.500, 90.000, type,1)
    execute_robot_rotate(1, 90.000, 112.500, type, 1)
    execute_robot_rotate(1, 112.500, 135.000, type, 1)
    execute_robot_rotate(1, 135.000, 157.500, type, 1)
    execute_robot_rotate(1, 157.500, 180.000, type, 1)
    execute_robot_rotate(1, 180.000, 202.500, type, 1)
    execute_robot_rotate(2, 202.500, 0.001, type,1)
    '''







# 还针函数

def jiajv_back(jiajv):

    global work_process

    cursor = db.cursor()

    try:
        cursor.execute("SELECT d_k1,d_k2,d_k3,d_k4 FROM jiajv_info WHERE id = 1")
        db.commit()

        result = cursor.fetchone()
        x11, y11, z11 = map(float, result[0].split('&'))
        x12, y12, z12 = map(float, result[1].split('&'))
        x13, y13, z13 = map(float, result[2].split('&'))
        x14, y14, z14 = map(float, result[3].split('&'))

    except Exception as e:
        work_process = -1
        return -6, "错误:该数据库中 4孔 精确位置 数据存在问题，请核对", e

    try:
        # 换成 夹具
        robot.SetToolCoord(3, t_coord3, 0, 0)
    except Exception as e:
        work_process = -1
        return -7, "错误:切换3号针夹具坐标系出现问题", e

    send_io(0)

    if jiajv == 1:
        if x11 == 0 and y11 == 0 and z11 == 0:
            return -6,'该机器人 还回 1号针 时，未检测到 针的位置，请判断是否数据库有误 或者 该针未插入过该号孔',0
        else:
            robot_back_s1(x11, y11, z11)
            work_process = 1

    elif jiajv == 2:
        if x12 == 0 and y12 == 0 and z12 == 0:
            return -6,'该机器人 还回 1号针 时，未检测到 针的位置，请判断是否数据库有误 或者 该针未插入过该号孔',0
        else:
            robot_back_s2(x12, y12, z12)
    elif jiajv == 3:
        if x13 == 0 and y13 == 0 and z13 == 0:
            return -6,'该机器人 还回 1号针 时，未检测到 针的位置，请判断是否数据库有误 或者 该针未插入过该号孔',0
        else:
            robot_back_s3(x13, y13, z13)
    elif jiajv == 4:
        if x14 == 0 and y14 == 0 and z14 == 0:
            return -6,'该机器人 还回 1号针 时，未检测到 针的位置，请判断是否数据库有误 或者 该针未插入过该号孔',0
        else:
            robot_back_s4(x14, y14, z14)

    else:
        print('输入夹具有误，请重新输入！')
        return -4,'输入夹具有误，请重新输入！',0


    return 1,0,0


def robot_back_s4(x4_w, y4_w, z4_w):


    global W_safe, W_in
    W_safe[0] = W_in[0] = x4_w
    W_safe[1] = W_in[1] = y4_w
    W_in[2] = z4_w

    # 移动到万用表该孔的安全平面
    movej_PTP_getJ(3, 80.0, W_safe)

    # 移动到万用表1孔的插进平面
    movel_PTP(3, 8.0, W_in)

    thread7 = threading.Thread(target=press_kong_monitor_all_in)
    thread8 = threading.Thread(target=stop_kong_motion,args=(1.0,))

    thread7.start()
    thread8.start()

    thread7.join()
    thread8.join()

    robot.WaitMs(2000)

    send_io(1)

    robot.WaitMs(2000)

    # 更改孔位情况
    cursor = db.cursor()
    sql = "UPDATE jiajv_info SET kong4 = 0 WHERE id = 1"
    cursor.execute(sql)
    db.commit()


    # 回到到万用表4孔的安全平面
    movel_PTP(3, 30.0, W_safe)


    # 移动到S4安全平面
    movej_PTP_getJ(3, 80.0, P_s4safe)

    P_s4in_forward = P_s4in

    P_s4in_forward[2] = P_s4in_forward[2] + 2.000

    # 移动到S4夹孔位置
    movel_PTP(3, 13.0, P_s4in_forward)



    send_io(0)

    '''
    sjk_io(0)
    '''

    sql = "UPDATE jiajv_info SET jia4 = %s WHERE id = %s"
    val = (1, 1)
    cursor.execute(sql, val)
    db.commit()


    # 移动到S4安全平面
    movel_PTP(3, 30.0, P_s4safe)


def robot_back_s3(x3_w, y3_w, z3_w):

    global W_safe, W_in
    W_safe[0] = W_in[0] = x3_w
    W_safe[1] = W_in[1] = y3_w
    W_in[2] = z3_w

    # 移动到万用表该孔的安全平面
    movej_PTP_getJ(3, 80.0, W_safe)


    # 移动到万用表1孔的插进平面
    movel_PTP(3, 8.0, W_in)


    thread9 = threading.Thread(target=press_kong_monitor_all_in)
    thread10 = threading.Thread(target=stop_kong_motion,args=(1.0,))

    thread9.start()
    thread10.start()

    thread9.join()
    thread10.join()

    robot.WaitMs(2000)

    send_io(1)

    robot.WaitMs(2000)

    '''
    sjk_io(1)
    '''

    # 更改孔位情况
    cursor = db.cursor()
    sql = "UPDATE jiajv_info SET kong3 = 0 WHERE id = 1"
    cursor.execute(sql)
    db.commit()


    # 回到到万用表3孔的安全平面
    movel_PTP(3, 30.0, W_safe)


    # 移动到S3安全平面
    movej_PTP_getJ(3, 80.0, P_s3safe)

    P_s3in_forward = P_s3in

    P_s3in_forward[2] = P_s3in_forward[2] + 4.000

    # 移动到S3夹孔位置
    movel_PTP(3, 13.0, P_s3in_forward)



    send_io(0)

    '''
    sjk_io(0)
    '''

    sql = "UPDATE jiajv_info SET jia3 = %s WHERE id = %s"
    val = (1, 1)
    cursor.execute(sql, val)
    db.commit()


    # 将夹具S3移动到S3安全平面
    movel_PTP(3, 30.0, P_s3safe)


def robot_back_s2(x2_w, y2_w, z2_w):

    global W_safe, W_in
    W_safe[0] = W_in[0] = x2_w
    W_safe[1] = W_in[1] = y2_w
    W_in[2] = z2_w

    # 移动到万用表2孔的安全平面
    movej_PTP_getJ(3, 80.0, W_safe)

    # 移动到万用表2孔的插进平面
    movel_PTP(3, 8.0, W_in)

    thread11 = threading.Thread(target=press_kong_monitor_all_in)
    thread12 = threading.Thread(target=stop_kong_motion,args=(1.0,))

    thread11.start()
    thread12.start()

    thread11.join()
    thread12.join()

    send_io(1)

    # 更改孔位情况
    cursor = db.cursor()
    sql = "UPDATE jiajv_info SET kong2 = 0 WHERE id = 1"
    cursor.execute(sql)
    db.commit()

    # 回到到万用表2孔的安全平面
    movel_PTP(3, 30.0, W_safe)


    # 移动到S2安全平面
    movej_PTP_getJ(3, 80.0, P_s2safe)

    P_s2in_forward = P_s2in

    P_s2in_forward[2] = P_s2in_forward[2] + 2.000

    # 移动到S2夹孔位置
    movel_PTP(3, 13.0, P_s2in_forward)

    robot.WaitMs(2000)

    send_io(0)

    robot.WaitMs(2000)

    '''
    sjk_io(0)
    '''

    sql = "UPDATE jiajv_info SET jia2 = %s WHERE id = %s"
    val = (1, 1)
    cursor.execute(sql, val)
    db.commit()


    # 将夹具S2移动到S2安全平面
    movel_PTP(3, 30.0, P_s2safe)


def robot_back_s1(x1_w, y1_w, z1_w):

    global W_safe,W_in
    W_safe[0] = W_in[0] = x1_w
    W_safe[1] = W_in[1] = y1_w
    W_in[2] = z1_w

    # 移动到万用表该孔的安全平面
    movej_PTP_getJ(3, 80.0, W_safe)


    # 移动到万用表1孔的插进平面
    movel_PTP(3, 8.0, W_in)

    thread13 = threading.Thread(target=press_kong_monitor_all_in)
    thread14 = threading.Thread(target=stop_kong_motion,args=(1.0,))

    thread13.start()
    thread14.start()

    thread13.join()
    thread14.join()

    send_io(1)


    '''
    sjk_io(1)
    '''

    # 更改孔位情况
    cursor = db.cursor()
    sql = "UPDATE jiajv_info SET kong1 = 0 WHERE id = 1"
    cursor.execute(sql)
    db.commit()

    # 回到到万用表1孔的安全平面
    movel_PTP(3, 30.0, W_safe)

    # 移动到S1安全平面
    movej_PTP_getJ(3, 80.0, P_s1safe)

    P_s1in_forward = P_s1in

    P_s1in_forward[2] = P_s1in_forward[2] + 7.000

    # 移动到S1夹孔位置
    movel_PTP(3, 13.0, P_s1in_forward)

    robot.WaitMs(2000)

    send_io(0)

    robot.WaitMs(2000)


    sql = "UPDATE jiajv_info SET jia1 = %s WHERE id = %s"
    val = (1, 1)
    cursor.execute(sql, val)
    db.commit()


    # 将机器人移动到S1安全平面
    movel_PTP(3, 30.0, P_s1safe)







# 回位安全高度函数

def back_to_safe_plane():

    robot.SetToolCoord(3, t_coord3, 0, 0)
    ret = robot.GetActualTCPPose(0)[1]
    ret[2] = -60.000
    movel_PTP(3, 30.0, ret)


# 断电复原函数

def restart(process,style,sjk_id):

    global go_x,go_y

    # 查询数据库得到 当前孔位 情况
    cursor.execute("SELECT jia1,jia2,jia3,jia4,kong1,kong2,kong3,kong4 FROM jiajv_info WHERE id = 1")
    db.commit()
    result = cursor.fetchone()
    locate = list(map(int, result))

    print(locate)

    # 定义 当前机器人位置的 安全平面位置
    robot.SetToolCoord(3, t_coord3, 0, 0)
    ret = robot.GetActualTCPPose(0)[1]
    ret[2] = h_safe
    T_safe = ret

    # 抬至 机器人当前位置 的安全平面
    movel_PTP(3, 20.0, T_safe)

    if process == 1:

        # 还针
        if locate == [1, 1, 1, 1, 0, 0, 0, 0]:
            print('所有针都在初始位置')

        elif locate == [0, 1, 1, 1, 0, 0, 0, 0]:
            print('当前 1 针 在 中间')

            # 移动到S1安全平面
            movej_PTP_getJ(3, 80.0, P_s1safe)
            # 移动到S1夹孔位置
            movel_PTP(3, 20.0, P_s1in)
            '''
            send_io(0)
            '''
            send_io(0)
            sql = "UPDATE jiajv_info SET jia1 = %s WHERE id = %s"
            val = (1, 1)
            cursor.execute(sql, val)
            db.commit()

            # 将机器人移动到S1安全平面
            movel_PTP(3, 30.0, P_s1safe)

        elif locate == [0, 1, 1, 1, 1, 0, 0, 0]:
            print('当前 1 针 在 万用表上')

            cursor.execute("SELECT d_k1 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x11, y11, z11 = map(float, result[0].split('&'))
            robot_back_s1(x11,y11,z11)

        elif locate == [0, 0, 1, 1, 1, 0, 0, 0]:
            print('当前 2 针 在 中间')

            # 移动到S2安全平面
            movej_PTP_getJ(3, 80.0, P_s2safe)
            # 移动到S2夹孔位置
            movel_PTP(3, 20.0, P_s2in)

            '''
            send_io(0)
            '''
            send_io(0)

            sql = "UPDATE jiajv_info SET jia2 = %s WHERE id = %s"
            val = (1, 1)
            cursor.execute(sql, val)
            db.commit()

            # 将机器人移动到S2安全平面
            movel_PTP(3, 30.0, P_s2safe)

            cursor.execute("SELECT d_k1 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x11, y11, z11 = map(float, result[0].split('&'))
            robot_back_s1(x11, y11, z11)

        elif locate == [0, 0, 1, 1, 1, 1, 0, 0]:
            print('当前 2 针 在 万用表上')

            # 逆时针还针，先还 2 号针
            cursor.execute("SELECT d_k2 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x12, y12, z12 = map(float, result[0].split('&'))
            robot_back_s2(x12, y12, z12)

            # 还 1 号 针
            cursor.execute("SELECT d_k1 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x11, y11, z11 = map(float, result[0].split('&'))
            robot_back_s1(x11, y11, z11)

        elif locate == [0, 0, 0, 1, 1, 1, 0, 0]:
            print('当前 3 针 在 中间')

            # 移动到S3安全平面
            movej_PTP_getJ(3, 80.0, P_s3safe)

            # 移动到S3夹孔位置
            movel_PTP(3, 20.0, P_s3in)

            '''
            send_io(0)
            '''
            send_io(0)

            sql = "UPDATE jiajv_info SET jia3 = 1 WHERE id = 1"
            cursor.execute(sql)
            db.commit()

            # 将机器人移动到S3安全平面
            movel_PTP(3, 30.0, P_s3safe)

            # 逆时针还针，先还 2 号针
            cursor.execute("SELECT d_k2 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x12, y12, z12 = map(float, result[0].split('&'))
            robot_back_s2(x12, y12, z12)

            # 还 1 号 针
            cursor.execute("SELECT d_k1 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x11, y11, z11 = map(float, result[0].split('&'))
            robot_back_s1(x11, y11, z11)

        elif locate == [0, 0, 0, 1, 1, 1, 1, 0]:
            print('当前 3 针 在 万用表上')

            # 逆时针还针，先还 3 号针
            cursor.execute("SELECT d_k3 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x13, y13, z13 = map(float, result[0].split('&'))
            robot_back_s3(x13, y13, z13)

            # 还 2 号针
            cursor.execute("SELECT d_k2 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x12, y12, z12 = map(float, result[0].split('&'))
            robot_back_s2(x12, y12, z12)

            # 还 1 号 针
            cursor.execute("SELECT d_k1 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x11, y11, z11 = map(float, result[0].split('&'))
            robot_back_s1(x11, y11, z11)

        elif locate == [0, 0, 0, 0, 1, 1, 1, 0]:
            print('当前 4 针 在 中间')

            # 移动到S4安全平面
            movej_PTP_getJ(3, 80.0, P_s4safe)

            # 移动到S4夹孔位置
            movel_PTP(3, 20.0, P_s4in)

            '''
            send_io(0)
            '''
            send_io(0)

            sql = "UPDATE jiajv_info SET jia4 = 1 WHERE id = 1"
            cursor.execute(sql)
            db.commit()

            # 将机器人移动到S4安全平面
            movel_PTP(3, 30.0, P_s4safe)

            # 逆时针还针，先还 3 号针
            cursor.execute("SELECT d_k3 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x13, y13, z13 = map(float, result[0].split('&'))
            robot_back_s3(x13, y13, z13)

            # 还 2 号针
            cursor.execute("SELECT d_k2 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x12, y12, z12 = map(float, result[0].split('&'))
            robot_back_s2(x12, y12, z12)

            # 还 1 号 针
            cursor.execute("SELECT d_k1 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x11, y11, z11 = map(float, result[0].split('&'))
            robot_back_s1(x11, y11, z11)

        elif locate == [0, 0, 0, 0, 1, 1, 1, 1]:
            print('当前 4 针 在 万用表上')

            # 逆时针还针，先还 4 号针
            cursor.execute("SELECT d_k4 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x14, y14, z14 = map(float, result[0].split('&'))
            robot_back_s4(x14, y14, z14)

            # 还 3 号针
            cursor.execute("SELECT d_k3 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x13, y13, z13 = map(float, result[0].split('&'))
            robot_back_s3(x13, y13, z13)

            # 还 2 号针
            cursor.execute("SELECT d_k2 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x12, y12, z12 = map(float, result[0].split('&'))
            robot_back_s2(x12, y12, z12)

            # 还 1 号 针
            cursor.execute("SELECT d_k1 FROM jiajv_info WHERE id = 1")
            db.commit()
            result = cursor.fetchone()
            x11, y11, z11 = map(float, result[0].split('&'))
            robot_back_s1(x11, y11, z11)

        else:
            print('当前数据库出错，请检查数据库孔位情况')
            return -1

        print('所有针已插完')

    elif process == 2:
        print('测量过程中断电')

    elif process == 3:
        print('继续插针')

        sql = "SELECT k1_pos,k2_pos,k3_pos,k4_pos FROM wyb_info WHERE type = %s"
        cursor.execute(sql, (type,))
        db.commit()

        result = cursor.fetchone()
        k1_x, k1_y = map(float, result[0].split('&'))
        k2_x, k2_y = map(float, result[1].split('&'))
        k3_x, k3_y = map(float, result[2].split('&'))
        k4_x, k4_y = map(float, result[3].split('&'))

        go_x = [k1_x, k2_x, k3_x, k4_x]
        go_y = [k1_y, k2_y, k3_y, k4_y]

        if locate == [1, 1, 1, 1, 0, 0, 0, 0]:
            print('所有针都在初始位置')

            jiajv(1, style, 0)
            jiajv(2, style, 0)
            jiajv(3, style, 0)
            jiajv(4, style, 0)

        elif locate == [0, 1, 1, 1, 0, 0, 0, 0]:
            print('当前 1 针 在 中间')

            robot_actions_wanyongbiao('kong1', 'd_k1', 1, style)
            jiajv(2, style, 0)
            jiajv(3, style, 0)
            jiajv(4, style, 0)


        elif locate == [0, 1, 1, 1, 1, 0, 0, 0]:
            print('当前 1 针 在 万用表上')

            jiajv(2, style, 0)
            jiajv(3, style, 0)
            jiajv(4, style, 0)

        elif locate == [0, 0, 1, 1, 1, 0, 0, 0]:
            print('当前 2 针 在 中间')

            robot_actions_wanyongbiao('kong2', 'd_k2', 2, style)
            jiajv(3, style, 0)
            jiajv(4, style, 0)

        elif locate == [0, 0, 1, 1, 1, 1, 0, 0]:
            print('当前 2 针 在 万用表上')

            jiajv(3, style, 0)
            jiajv(4, style, 0)

        elif locate == [0, 0, 0, 1, 1, 1, 0, 0]:
            print('当前 3 针 在 中间')

            robot_actions_wanyongbiao('kong3', 'd_k3', 3, style)
            jiajv(3, style, 0)

        elif locate == [0, 0, 0, 1, 1, 1, 1, 0]:
            print('当前 3 针 在 万用表上')

            jiajv(4, style, 0)

        elif locate == [0, 0, 0, 0, 1, 1, 1, 0]:
            print('当前 4 针 在 中间')

            robot_actions_wanyongbiao('kong4', 'd_k4', 4, style)

        elif locate == [0, 0, 0, 0, 1, 1, 1, 1]:
            print('当前 4 针 在 万用表上')

        else:
            print('当前数据库出错，请检查数据库孔位情况')
            return -1

        print('所有针都已插完')

    else:
        print('函数参数有问题')
        return -4

    return 1


















# 测量总函数
def measure(measure_type,fluke_type,victor_type,sjk_id):

    print('通讯测试开始')
    ret, version = robot.GetSDKVersion()  # 查询SDK版本号
    if ret == 0:
        print('通讯成功！')
        print("当前fr3的SDK版本号为", version)
    else:
        print('通讯失败！请检查急停按钮和ip地址')
        exit(0)

    print('断电复原测试开始!')
    while (True):

        scan = input("1：还针，2：回位，3：继续插针,0：退出：")
        scan = int(scan)

        if scan == 0:
            k1 = scan
            break
        elif scan == 1:
            k1 = restart(1, measure_type,sjk_id)
        elif scan == 2:
            k1 = restart(2, measure_type,sjk_id)
        elif scan == 3:
            k1 = restart(3, measure_type,sjk_id)
        else:
            print('输入有误，请重新输入！')

    print('断电复原测试成功!')

    print(k1)

    # 测试拍摄功能

    # 0：万用表整体
    # x（1-4）：万用表x号孔
    # 5：万用表转盘
    # 6：万用表lcd

    while (True):

        scan1 = input("摄像头：请输入(0-2),3：退出：")
        scan1 = int(scan1)
        print(work_process)
        if scan1 == 3:
            break
        elif scan1 == 1 or scan1 == 0 or scan1 == 2:
            pos = photo_getxy(scan1, measure_type)
            if pos[0] == 1:
                print(pos[1])
                print(pos[2])
            elif pos[0] != 1:
                print(pos)
                print(work_process)
        else:
            print('输入错误，请重新输入！')

    print('拍摄测试成功!')

    # 测试 抓取功能:
    # 默认 1-4 针从短到长
    # 抓取 顺序 1-2-3-4

    print('单步抓取测试开始!')
    while (True):

        scan = input("抓取：请输入(1-4),0：退出：")
        scan = int(scan)

        if scan == 0:
            break
        elif scan == 1:
            j = jiajv(1, measure_type, 0)
        elif scan == 2:
            j = jiajv(2, measure_type, 0)
        elif scan == 3:
            j = jiajv(3, measure_type, 0)
        elif scan == 4:
            j = jiajv(4, measure_type, 0)
        else:
            print('输入有误，请重新输入！')

        print(j)

    print('单步抓取测试成功!')

    print('所有插针抓取测试开始!')
    while (True):

        scan = input("请输入1：开始,0：退出：")
        scan = int(scan)

        if scan == 0:
            break
        elif scan == 1:

            jiajv(1, measure_type, 0)
            jiajv(2, measure_type, 0)
            jiajv(3, measure_type, 0)
            jiajv(4, measure_type, 0)

            print('所有插针抓取测试成功!')
        else:
            print('输入有误，请重新输入！')



    while (True):

        print('测量测试开始!')

        while (True):

            scan = input("输入是否单档连转测试：请输入(1：是 0：否): ")
            scan = int(scan)

            while (True):
                if scan == 1:
                    while (True):
                        scan = input("输入型号：请输入(1：FLUKE 2：VICTOR 0：退出): ")
                        scan = int(scan)
                        if scan == 1:
                            FLUKE(fluke_type)
                        elif scan == 2:
                            VICTOR(victor_type)
                        elif scan == 0:
                            break
                        else:
                            print('输入有误，请重新输入')
                            pass
                        print('单档测试完毕!')
                elif scan == 0:
                    print('单档测试完毕!')
                    break
                else:
                    print('输入有误，请重新输入')
                    pass
            break
        scan = input("输入顺时针还是逆时针：请输入(1：顺 2：逆),0：退出：")
        scan = int(scan)
        while (True):
            if scan == 1 or scan == 2:
                dir_1shun_2ni = int(scan)
                break
            elif scan == 0:
                dir_1shun_2ni = scan
                break
            else:
                print('输入有误，请重新输入')
                pass

        if dir_1shun_2ni == 0:
            break

        scan1 = input("输入起始角度：,（0：退出）：")
        scan1 = float(scan1)
        while (True):
            if scan1 == 0:
                start_ang = scan1
                break
            else:
                start_ang = float(scan1)
                break

        if start_ang == 0:
            break

        scan = input("输入终止角度：,（0：退出）：")
        scan = float(scan)
        while (True):
            if scan == 0:
                end_ang = scan
                break
            else:
                end_ang = float(scan)
                break

        if end_ang == 0:
            break

        execute_robot_rotate(dir_1shun_2ni, start_ang, end_ang, measure_type, sjk_id)

    print('测量测试成功!')

    # 测试 还针功能:
    # 默认 1-4 针从短到长
    # 还针顺序：4-3-2-1

    print('单步还针测试开始!')
    while (True):

        scan = input("还针：请输入(1-4),0：退出：")
        scan = int(scan)

        if scan == 0:
            break
        else:
            jj_back = jiajv_back(scan)
            if jj_back[0] == 1:
                print('归还成功')
            else:
                print(jj_back)

    print('还针测试成功!')

    print('所有还抓取测试开始!')
    while (True):

        scan = input("请输入1：开始,0：退出：")
        scan = int(scan)

        if scan == 0:
            break
        elif scan == 1:
            jv_back_return = jiajv_back(4)
            jv_back_return = jiajv_back(3)
            jv_back_return = jiajv_back(2)
            jv_back_return = jiajv_back(1)
            print(jv_back_return)
        else:
            print('输入有误，请重新输入！')

    print('所有插针抓取测试成功!')



def fluke_17b_test():

    jiajv(1, '17B+', 0)
    jiajv(2, '17B+', 0)
    jiajv(3, '17B+', 0)
    jiajv(4, '17B+', 0)


def main():

    #measure('17B+', '17B+', 'VC890C+', 1)



    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

    app = QApplication([])

    login_home = wyb_gui.system_wyb()
    login_home.ui.show()
    app.exec_()




if __name__ == '__main__':
    main()






