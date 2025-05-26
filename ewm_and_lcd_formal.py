# coding:utf-8
import os
import threading
import imutils
import serial.tools.list_ports
import serial.tools.list_ports
import cv2  # 模块称作cv2。python需要用到opencv-python模块。可在命令行模式输入：
from PIL import Image
from PySide2.QtWidgets import QApplication, QMessageBox, QGraphicsScene, QInputDialog, QPushButton, QLineEdit, QLabel,QPlainTextEdit
from PySide2.QtUiTools import QUiLoader
import numpy as np
import serial
import matplotlib.pyplot as plt
import serial.tools.list_ports
from PySide2.QtGui import QIcon
import cv2 as cv
from pyzbar import pyzbar as pyzbar
import openpyxl  #excel
# 识别矩形
import imutils
import numpy as np
import torch
from PIL import Image
import pathlib
pathlib.PosixPath = pathlib.WindowsPath
from models.common import DetectMultiBackend
from utils.general import ( cv2,non_max_suppression, scale_boxes)
from utils.torch_utils import select_device
import time
from PIL import Image
from pylab import *


#黑底路径
addr_heidi="C:/banshouGUI/pic_linshi/black_image.png"
#识别后的结果
addr_shibie="C:/banshouGUI/pic_linshi/shibie.png"

pingmu=1


last = []  # 用于存储原始jieguo6
new = []  # 用于存储修改后的jieguo6

# 屏幕定位函数
def LCD_dingwei(yuantu):
    kernel2 = np.ones((3, 3), np.uint8)
    # 加载图像
    img_gray = cv2.cvtColor(yuantu.copy(), cv2.COLOR_BGR2GRAY)  # 灰度图

    # 使用高斯滤波去除噪声
    blurred = cv2.GaussianBlur(img_gray, (3, 3), 0)
    zhongzhi = cv2.medianBlur(blurred, 3)  # 中值滤波
    #cv2.imshow("zhongzhi", zhongzhi)

    # 边界检测
    edge = cv2.Canny(zhongzhi, 20, 100)
    #cv2.imshow("edge1", edge)
    #cv2.waitKey(0)  # 放宽点条件检测边缘

    # 膨胀，让边缘粘在一起
    pengzhang = cv2.dilate(edge, kernel2, iterations=1)  # 膨胀2次
    #cv2.imshow("pic", pengzhang)
    #cv2.waitKey(0)

    # 边界检测  第二次 把膨胀后的图，再做边缘检测
    edge2 = cv2.Canny(pengzhang, 10, 240)  # 只检测边缘
    #("edge2", edge2)
    #cv2.waitKey(0)

    # -------------------------------找LCD外边框，把内部全画黑
    # 找最大的闭合边界
    # 寻找轮廓
    contours, hierarchy = cv2.findContours(edge2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 寻找面积最大的轮廓
    max_contour = max(contours, key=cv2.contourArea)
    #('边界长---------------')
    #print(cv2.arcLength(max_contour, False))


    # 建立一个全黑的图。
    heidi = np.zeros((yuantu.shape[0], yuantu.shape[1]), dtype=np.uint8)

    # 绘制最大的闭合边界,画实心轮廓   白色的实心轮廓，用原图，把要截取的部分提出来。
    qvyuhei = cv2.drawContours(heidi.copy(), [max_contour], -1, (255, 255, 255), -1)
    # 显示结果图像
    #cv2.imshow("qvyuhei", qvyuhei)
    #cv2.waitKey(0)

    # 旋转黑的 还有原图
    # 找最小外接框，并旋转
    waijie = cv2.minAreaRect(max_contour)  # 获取最小外接框，以及旋转的角度
    rotate = waijie[2]  # 旋转的角度
    if rotate > 45:
        rotate = rotate - 90
    if rotate < -45:
        rotate = rotate + 90
    #print('角度', rotate)
    qvyuhei_xz = imutils.rotate(qvyuhei.copy(), angle=rotate)  # 水平矫正后的图，使用原图矫正
    # 显示结果图像
    # cv2.imshow("qvyuhei_xz", qvyuhei_xz)
    # cv2.waitKey(0)
    yuantu_xz = imutils.rotate(yuantu.copy(), angle=rotate)  # 水平矫正后的图，使用原图矫正
    # 显示结果图像
    # cv2.imshow("yuantu_xz", yuantu_xz)
    # cv2.waitKey(0)

    # -------------根据黑边旋转找边界，然后把原图的切出来。
    # 边界检测  第二次 把膨胀后的图，再做边缘检测
    edge3 = cv2.Canny(qvyuhei_xz.copy(), 250, 255)  # 只检测边缘
    #cv2.imshow("edge3", edge3)
    #cv2.waitKey(0)

    # 边界检测,找边框,把所有边框都找出来，根据长度筛选
    contours3, hierarchy = cv2.findContours(edge3, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    # 找最小的边框
    max_contour3 = max(contours3, key=cv2.contourArea)  # 根据最大的边进行边缘检测，获取最大边框
    # 由于返回的r还带角度，所以利用boxPoints把最小外接矩形的四个顶点坐标提取出来
    r = cv2.minAreaRect(max_contour3)  # 获取最小外接框，以及旋转的角度
    box = cv2.boxPoints(r)  # 由于返回的box是浮点型，所以需要对box进行一次强制转换
    box = np.intp(box)
    xxiao = min(box[:, 0])  # X最小
    xda = max(box[:, 0])  # X最大
    yxiao = min(box[:, 1])  # Y最小
    yda = max(box[:, 1])  # Y最大
    #print(xxiao, xda, yxiao, yda)
    # 图像切片开始---根据上下左右切
    xxiao = int(xxiao)
    xda = int(xda)
    yxiao = int(yxiao)
    yda = int(yda)
    #print(xxiao, xda, yxiao, yda)
    yuantu_xz_jieqv = yuantu_xz[yxiao:yda, xxiao:xda]

    # 保存缩放后的图片
    return yuantu_xz_jieqv

# 单字识别，识别截取出来的部分(shuzishibie里子函数)
def danzishibie(pic,cankao):
    # 先计算图片的大小
    #print('宽', pic.shape[1])
    #print('高', pic.shape[0])
    # 解析像素点--穿线法
    x_quan = pic.shape[0]
    y_quan = pic.shape[1]
    y_zhong = int(pic.shape[1] * 0.5)
    x_shang = int(pic.shape[0] * 0.3333)
    x_xia = int(pic.shape[0] * 0.6666)
    #print(y_zhong, x_shang, x_xia)

    #图片轮廓检测
    # 滤波，核=3
    zhongzhi2 = cv2.medianBlur(pic, 3)
    zhongzhi2 = cv2.medianBlur(zhongzhi2, 3)
    # 灰度图
    zhongzhi2_huidu = cv2.cvtColor(zhongzhi2, cv2.COLOR_BGR2GRAY)
    #cv2.imshow("zhongzhi2_huidu", zhongzhi2_huidu)
    #cv2.waitKey(0)

    # 计算灰度图里最黑的点
    gray_min = 255
    for i in range(zhongzhi2_huidu.shape[0]):
        for j in range(zhongzhi2_huidu.shape[1]):
            if zhongzhi2_huidu[i][j] < gray_min:
                gray_min = zhongzhi2_huidu[i][j]
    #print('最小亮度', gray_min)
    # 先直接减去最小亮度
    zhongzhi2_huidu = zhongzhi2_huidu - gray_min

    # 计算直方图的灰度值的均值
    sum = 0
    for i in range(zhongzhi2_huidu.shape[0]):
        for j in range(zhongzhi2_huidu.shape[1]):
            sum = sum + zhongzhi2_huidu[i, j]
    junzhi = sum / (zhongzhi2_huidu.shape[0] * zhongzhi2_huidu.shape[1])  ###灰度图的均值
    #print('平均亮度', junzhi)

    # 边界检测
    # 边界检测
    pic3 = cv2.Canny(zhongzhi2_huidu, 10, 50)  # 只检测边缘,细节要多点
    #cv2.imshow("pic3", pic3)
    #cv2.waitKey(0)

    # 删除小边界，为从右向左检测做准备
    contours, hierarchy = cv2.findContours(pic3, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    # 对找到的轮廓进行面积小的删除处理。
    cv_contours = []
    for cnt in contours:
        len2 = cv2.arcLength(cnt, False)
        if len2 >= (pic.shape[1])*0.4:
            cv_contours.append(cnt)

    # 把删除后的轮廓画出来
    # 建立一个黑底，
    heidi = np.zeros((pic3.shape[0], pic3.shape[1]), dtype=np.uint8)
    # 画出来
    pic = cv2.drawContours(heidi, cv_contours, -1, (255, 255, 255), 1)
    #cv2.imshow("pic", pic)
    #cv2.waitKey(0)


    # 顺时针循环，和换电站一样
    shuzi_1 = 0
    shuzi_2 = 0
    shuzi_3 = 0
    shuzi_4 = 0
    shuzi_5 = 0
    shuzi_6 = 0
    shuzi_7 = 0

    # 区域1：自上而下，找2次从白变黑的  Y固定1/2，X从0到1/2------------1
    num = 0  # 需要2次触发
    for i in range(x_shang):
        #print(pic[i, y_zhong])
        if i >= 1 and pic[i - 1, y_zhong] == 255 and pic[i, y_zhong] == 0:  # 从白到黑
            num = num + 1
            if num >= 2:
                shuzi_1 = 1
                break

    # 区域2：自上而下，找2次从白变黑的-------------------------------2
    num = 0  # 需要2次触发
    for i in range(y_zhong, y_quan):
        #print('2----')
        #print(pic[x_shang, i])
        if i >= 1 and pic[x_shang, i - 1] == 255 and pic[x_shang, i] == 0:  # 从白到黑
            num = num + 1
            if num >= 2:
                shuzi_2 = 1
                break

    # 区域3：自上而下，找2次从白变黑的------------------------------3
    num = 0  # 需要2次触发
    for i in range(y_zhong, y_quan):
        #print('3----')
       # print(pic[x_xia, i])
        if i >= 1 and pic[x_xia, i - 1] == 255 and pic[x_xia, i] == 0:  # 从白到黑
            num = num + 1
            if num >= 2:
                shuzi_3 = 1
                break
    # 区域4：自上而下，找2次从白变黑的--------4
    num = 0  # 需要2次触发
    for i in range(x_xia, x_quan):
        #print('4----')
        #print([i, y_zhong])
        if i >= 1 and pic[i - 1, y_zhong] == 255 and pic[i, y_zhong] == 0:  # 从白到黑
            num = num + 1
            if num >= 2:
                shuzi_4 = 1
                break


    # 区域5：自上而下，找2次从白变黑的------------------------------5
    num = 0  # 需要2次触发
    for i in range(0, y_zhong):
        #print('5----')
        #print(pic[x_xia, i])
        if i >= 1 and pic[x_xia, i - 1] == 255 and pic[x_xia, i] == 0:  # 从白到黑
            num = num + 1
            if num >= 2:
                shuzi_5 = 1
                break


    # 区域6：自上而下，找2次从白变黑的-------------------------------6
    num = 0  # 需要2次触发
    for i in range(0, y_zhong):
        #print('6----')
        #print(pic[x_shang, i])
        if i >= 1 and pic[x_shang, i - 1] == 255 and pic[x_shang, i] == 0:  # 从白到黑
            num = num + 1
            if num >= 2:
                shuzi_6 = 1
                break


    # 区域7：自上而下，找2次从白变黑的  -----------7
    num = 0  # 需要2次触发
    for i in range(x_shang, x_xia):
       # print(pic[i, y_zhong])
        if i >= 1 and pic[i - 1, y_zhong] == 255 and pic[i, y_zhong] == 0:  # 从白到黑
            num = num + 1
            if num >= 2:
                shuzi_7 = 1
                break


    # 根据数字的位置确定是哪个数
    shibie0 = [1, 1, 1, 1, 1, 1, 0]
    shibie1 = [0, 1, 1, 0, 0, 0, 0]
    shibie2 = [1, 1, 0, 1, 1, 0, 1]
    shibie3 = [1, 1, 1, 1, 0, 0, 1]
    shibie4 = [0, 1, 1, 0, 0, 1, 1]
    shibie5 = [1, 0, 1, 1, 0, 1, 1]
    shibie6 = [1, 0, 1, 1, 1, 1, 1]
    shibie7 = [1, 1, 1, 0, 0, 0, 0]
    shibie7_2 = [1, 1, 1, 0, 0, 1, 0]  #有一台比较特殊

    shibie8 = [1, 1, 1, 1, 1, 1, 1]
    shibie9 = [1, 1, 1, 1, 0, 1, 1]

    shibie_jieguo = []
    shibie_jieguo.append(shuzi_1)
    shibie_jieguo.append(shuzi_2)
    shibie_jieguo.append(shuzi_3)
    shibie_jieguo.append(shuzi_4)
    shibie_jieguo.append(shuzi_5)
    shibie_jieguo.append(shuzi_6)
    shibie_jieguo.append(shuzi_7)
    #print(shibie_jieguo)
    shuzi = ''
    '''0不判 容易和8错
    if shibie_jieguo == shibie0 :
        shuzi = '0'
    '''
    if shibie_jieguo == shibie1 :
        shuzi = '1'
    if shibie_jieguo == shibie2 :
        shuzi ='2'
    if shibie_jieguo == shibie3 :
        shuzi = '3'
    if shibie_jieguo == shibie4:
        shuzi = '4'
    if shibie_jieguo == shibie5 :
        shuzi = '5'
    if shibie_jieguo == shibie6 :
        shuzi = '6'
    if shibie_jieguo == shibie7 :
        shuzi = '7'
    if shibie_jieguo == shibie8 :
        shuzi = '8'
    '''
    if shibie_jieguo == shibie9 :
        shuzi = '9'
    '''
    #print(shuzi)
    if shuzi=='':
        jieguo=str(cankao)
    else:
        jieguo=str(shuzi)
    return jieguo

# 数字识别
def shuzishibie(tupiandizhi,angle1 = -9,key1 = 1):

    # 模型权重
    #weights = 'num_last.pt'
    weights = 'D:/new_wyb_sys/do_image/num_best_L.pt'
    # GPU加速，但好像没加成，不知道为啥
    device = select_device()
    # 加载模型
    model = DetectMultiBackend(weights, device=device, dnn=False, fp16=False)
    # 模型输入格式要求
    height, width = 640, 640

    #---加载图片
    img_ori = cv2.imread(tupiandizhi)

    #先缩放--------------------标准化1024-1224
    # 计算缩放后的新尺寸
    new_height = int(1024 * img_ori.shape[0] / img_ori.shape[1])
    img = cv2.resize(img_ori.copy(), (1024, new_height))  # 尺寸变换
    #cv2.imshow("img", img)
    #cv2.waitKey(0)

    # 图像切片开始---根据上下左右切---------------------------------------------参数自己调
    xxiao = 100
    xda = 800
    yxiao = 200
    yda = 800
    #print(xxiao, xda, yxiao, yda)
    jieqv = img[yxiao:yda, xxiao:xda]
    #cv2.imshow("jieqv", jieqv)
    #cv2.waitKey(0)

    # 旋转------------------------------旋转角度自己调
    # ----旋转
    # 设置旋转中心，旋转角度，和缩放因子
    center = (jieqv.shape[1] // 2, jieqv.shape[0] // 2)  # 图像中心点
    angle = angle1  # 旋转角度
    scale = 1.0  # 缩放比例
    # 获取旋转矩阵
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)

    # 执行仿射变换，旋转图像
    rotated_image = cv2.warpAffine(jieqv, rotation_matrix, (jieqv.shape[1], jieqv.shape[0]))
    #cv2.imshow("rotated_image", rotated_image)
    #cv2.waitKey(0)


    if key1 == 0:

        # LCD定位------------

        dingwei = LCD_dingwei(rotated_image)

        if dingwei.shape[0]==rotated_image.shape[0]:
            return 'lack_of_form'


        #cv2.imshow("dingwei", dingwei)
        #cv2.waitKey(0)

        if dingwei.shape[0] < 200:
            return 'locate_incorrect'

    else:

        dingwei = rotated_image

    # ----------------------数字识别前处理 标准化+拼接补全
    # 获得长和宽
    gao = dingwei.shape[0]
    kuan = dingwei.shape[1]
    #print(kuan, gao)
    new_height = 10
    if kuan >= gao:
        # 尺寸标准化
        new_height = int(640 * dingwei.shape[0] / dingwei.shape[1])
        img1 = cv2.resize(dingwei.copy(), (640, new_height))  # 尺寸变换
        # cv2.imshow("img1", img1)
        # cv2.waitKey(0)
        # 建立一个黑色底板，进行等比例扩容
        # 建立一个全黑的图。
        bianjie_da = max(img1.shape[0], img1.shape[1])
        bianjie_xiao = min(img1.shape[0], img1.shape[1])
        bianjie_jian = bianjie_da - bianjie_xiao
        #print(bianjie_da, bianjie_xiao, bianjie_jian)
        # 创建一个全黑的图像数组，数组类型为uint8，并初始化为0
        black_image = np.zeros((bianjie_jian, bianjie_da, 3), np.uint8)
        # 保存图片
        cv2.imwrite(addr_heidi, black_image)
        # 把补好的图读出来
        heidi2 = cv2.imread(addr_heidi)
        # 水平拼接图片
        img_pinjie = cv2.vconcat([img1, heidi2])
    else:
        # 尺寸标准化
        new_width = int(640 * dingwei.shape[1] / dingwei.shape[0])
        img1 = cv2.resize(dingwei.copy(), (new_width, 640))  # 尺寸变换
        # cv2.imshow("img1", img1)
        # cv2.waitKey(0)
        # 建立一个黑色底板，进行等比例扩容
        # 建立一个全黑的图。
        bianjie_da = max(img1.shape[0], img1.shape[1])
        bianjie_xiao = min(img1.shape[0], img1.shape[1])
        bianjie_jian = bianjie_da - bianjie_xiao
        #print(bianjie_da, bianjie_xiao, bianjie_jian)
        # 创建一个全黑的图像数组，数组类型为uint8，并初始化为0
        black_image = np.zeros((bianjie_da, bianjie_jian, 3), np.uint8)
        # 保存图片
        cv2.imwrite(addr_heidi, black_image)
        # 把补好的图读出来
        heidi2 = cv2.imread(addr_heidi)
        # 水平拼接图片
        img_pinjie = cv2.hconcat([img1, heidi2])
    #print('----------------------')
    #cv2.imshow("img_pinjie", img_pinjie)
    #cv2.waitKey(0)

    # 显示拼接后的图片
    img = cv2.resize(img_pinjie, (height, width))  # 尺寸变换
    #print('-----------------aaaaaaaaaa-----')
    #print(img.shape[0],img.shape[1])

    img_copy = img.copy()
    img_show = img.copy()  # 另存出来的原图
    img = img / 255.
    img = img[:, :, ::-1].transpose((2, 0, 1))  # HWC转CHW
    img = np.expand_dims(img, axis=0)  # 扩展维度至[1,3,640,640]，也是模型输入要求
    img = torch.from_numpy(img.copy())  # numpy转tensor
    img = img.to(torch.float32)  # float64转换float32(模型输入要求)
    pred = model(img, augment=False, visualize=False)
    # pred.clone().detach()
    pred = non_max_suppression(pred, 0.25, 0.45, None, False, max_det=5)  # 非极大值抑制

    num_cunfang = []  # 放排序的
    for i, det in enumerate(pred):
        if len(det):
            det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], img_pinjie.shape).round()
            for *xyxy, conf, cls in reversed(det):
                # 输出结果：xyxy检测框左上角和右下角坐标，conf置信度，cls分类结果的索引，数字=索引-2
                #print('{},{},{}'.format(xyxy, conf.numpy(), cls.numpy() - 2))
                if conf.numpy() < 0.3 or (cls.numpy() - 2) < 0:
                    continue
                #print('-----')
                #print(int(xyxy[0].numpy()), int(xyxy[1].numpy()))  # 左边的X值 以此排序
                #print(int(xyxy[2].numpy()), int(xyxy[3].numpy()))  # 左边的X值 以此排序

                num_cunfang.append((int(xyxy[0].numpy()), int(xyxy[1].numpy()), int(xyxy[2].numpy()),
                                    int(xyxy[3].numpy()), cls.numpy() - 2))
                img_show = cv2.rectangle(img_show, (int(xyxy[0].numpy()),
                                                    int(xyxy[1].numpy())),
                                         (int(xyxy[2].numpy()),
                                          int(xyxy[3].numpy())),
                                         (255, 0, 0), 1)
                #cv2.imshow("img_show", img_show)
                #cv2.waitKey(0)
    # pred输出的三维数组为乱序，可以按x大小从左到右排序
    #print(num_cunfang)
    #print(len(num_cunfang))
    num_paixu = sorted(num_cunfang)

    #print(num_paixu)

    jieguo = ''
    for aa in range(len(num_paixu)):

        # 极大值抑制 手写
        if aa > 0 and (num_paixu[aa][0] - num_paixu[aa - 1][0]) < 20:
            #print('tiaoguo')
            continue
        '''
        print(num_paixu[aa][0],num_paixu[aa][1],num_paixu[aa][2],num_paixu[aa][3])

        if (num_paixu[aa][2] - num_paixu[aa][0]) > 125:
            num_paixu[aa][0] += 10
        '''

        if num_paixu[aa][4] == 10 :
            jieguo = jieguo + str('L')
            return '0L'

        #img_jieqv = img_copy[int(num_paixu[aa][1]):int(num_paixu[aa][3]), int(num_paixu[aa][0]): int(num_paixu[aa][2])]

        # 把截出来的图片单独识别
        #shuzi = str(danzishibie(img_jieqv, int(num_paixu[aa][4])))
        jieguo = jieguo + str(int(num_paixu[aa][4]))


    if jieguo[0] == '0' and len(jieguo) == 4:
        jieguo = jieguo[1:]

    try:
        if int(jieguo)==0 and len(jieguo) == 4:
           return '0000'
    except:
        k=0
    # 判定数据 是否合规正负5%内
    bili = 0
    # 判定是几位小数
    '''
    jieguo_int = int(jieguo)
    jieguo_out = 'shibai'
    if abs((jieguo_int - float(shijizhi)) / shijizhi) < 0.2:
        jieguo_out = str(round(jieguo_int, 3))
    if abs((jieguo_int * 0.1 - float(shijizhi)) / shijizhi) < 0.2:
        jieguo_out = str(round(jieguo_int * 0.1, 3))
    if abs((jieguo_int * 0.01 - float(shijizhi)) / shijizhi) < 0.2:
        jieguo_out = str(round(jieguo_int * 0.01, 3))
    if abs((jieguo_int * 0.001 - float(shijizhi)) / shijizhi) < 0.2:
        jieguo_out = str(round(jieguo_int * 0.001, 3))
    print('结果：' + str(shijizhi))
    print('结果：' + jieguo)
    print('读取：' + jieguo_out)
    '''

    return jieguo

def shibie(path):



    for pathvalue in path:

        jieguo6=shuzishibie("C:/Users/16667/Desktop/photo_problem/" + pathvalue + ".jpg")
        #print('原来：' + jieguo6)

        last.append(jieguo6)

        if len(jieguo6) == 3:
            jieguo6 = '1' + jieguo6
        elif len(jieguo6) == 2:
            jieguo6 = '11' + jieguo6
        elif len(jieguo6) == 1:
            jieguo6 = '111' + jieguo6

        #print('之后：' + jieguo6)

        new.append(jieguo6)


'''
path = [
    '7',
    '8',
]


shibie(path)

print(last)
print(new)
'''