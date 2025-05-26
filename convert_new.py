import cv2
import numpy as np


pic_blue_path = 'E:\photo_test\VICTOR&VC890C+_ori.jpg'
pic_equip_path ='E:\photo_test\VICTORVC890C+002.jpg'

'''
pic_blue_path = 'G:\study\Python\python310_work\photo\VICTOR_2.jpg'
pic_equip_path = 'G:\study\Python\python310_work\photo\VICTOR_1.jpg'
'''


def find_blue_circle_loc(adress, scale = 1):

    # 读取图片
    image = cv2.imread(adress)

    img_copy = image.copy()
    img_copy = cv2.resize(img_copy, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    #cv2.imshow('img_copy', img_copy)
    #cv2.waitKey(0)
    """
    提取图中的蓝色部分 hsv范围可以自行优化
    cv2.inRange()
    参数介绍：
    第一个参数：hsv指的是原图
    第二个参数：在图像中低于这个数值的全部变为0
    第二个参数：在图像中高于这个数值的全部变为0
    在之间的变为255
    图像中0-255。是变得越来越亮的
    """
    hsv = cv2.cvtColor(img_copy, cv2.COLOR_BGR2HSV)
    # cv2.imshow('hsv', hsv)
    # cv2.waitKey(0)
    low_hsv = np.array([100, 80, 80])  # 这里的阈值是自己进行设置的
    high_hsv = np.array([115, 255, 255])
    # 设置HSV的阈值
    mask = cv2.inRange(hsv, lowerb=low_hsv, upperb=high_hsv)
    # cv2.imshow('mask', mask)
    # cv2.waitKey(0)
    # show_pic('hsv_color_find', mask)#这里是得到黑白颜色的图片
    # 将掩膜与图像层逐像素相加
    # cv2.bitwise_and()是对二进制数据进行“与”操作，即对图像（灰度图像或彩色图像均可）每个像素值进行二进制“与”操作，1&1=1，1&0=0，0&1=0，0&0=0
    res = cv2.bitwise_and(img_copy, img_copy, mask=mask)
    # cv2.imshow('res', res)
    # cv2.waitKey(0)

    # show_pic('hsv_color_find2',res)#在这里得到蓝底黑字的照片
    # print('hsv提取蓝色部分完毕')

    # 定义膨胀和腐蚀的核
    kernel = np.ones((5, 5), np.uint8)
    # 腐蚀操作
    eroded_image = cv2.erode(res, kernel, iterations=2)

    # 膨胀操作
    dilated_image = cv2.dilate(eroded_image, kernel, iterations=2)
    # cv2.imshow('dilated_image', dilated_image)
    # cv2.waitKey(0)
    imagegray = cv2.cvtColor(dilated_image, cv2.COLOR_BGR2GRAY)
    # cv2.imshow('image', imagegray)
    # cv2.waitKey(0)

    # edge = cv2.Canny(imagegray,50,100)
    # cv2.imshow('image', edge)
    # cv2.waitKey(0)

    # 0.9以上对有缺陷的小圆检测不明显，只能在调小该参数同时调整最小距离以免重复
    circles = cv2.HoughCircles(imagegray, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=30, param1=100, param2=0.8)
    if circles is not None:
        count = 0
        circles = np.uint16(np.around(circles))
        for i in circles[0, :]:  # 对每个检测到的圆形,格式为(x,y,r)
            if (1):  # 与固定轴线的x距离不超过十个像素点，则确定为目标，这里先设置为永真
                count += 1
                # 绘制圆形的边缘
                cv2.circle(img_copy, (i[0], i[1]), i[2], (0, 255, 0), 1)
                # 绘制圆形的中心
                cv2.circle(img_copy, (i[0], i[1]), 1, (0, 0, 255), 3)

        #cv2.imshow('ss', img_copy)
        #cv2.waitKey(0)

    else:
        print("未检测成功")



    # 红点排序！！！！！！！！！！！！！！！！！


    '''
    param : circles是霍夫检测返回的包含各个圆的[x,y,r]列表
    return : 返回从左上到右下排好序的列表
    '''

    c = circles[0]
    #先按y分组排序
    sorted_c = c[c[:,1].argsort()]
    len_sc = len(sorted_c)
    # print(sorted_c)
    # print('---')
    ssorted_c  =[]
    counts=[]
    count=0
    #第一个的y坐标
    flag =sorted_c[0][1]


    for i,item in enumerate(sorted_c,1):#主要做组别分类
        if abs(item[1]-flag)<=5 and i<=len_sc:
            #说明是一行的
            count+=1
            if(i==len_sc):
                counts.append(count)
                break
        else:
            counts.append(count)
            flag=item[1]

   
    listNum = len(counts)
    for i in range(listNum-1):
        counts[listNum - 1 - i] = counts[listNum - 1 - i] - counts[listNum - 2 - i] + 1
    #需要一个计数的，和放不同组别园的列表
    flag1 =0
    list_temp = []
    #按counts中分好的组去分别排序x,counts有多长就有几组先截出来
    for i in range(listNum):
        if i==0:
            list_temp.append(sorted_c[flag1:counts[i]])
            flag1 = counts[i]
        else:
            list_temp.append(sorted_c[flag1:flag1+counts[i]])
            flag1 = flag1+counts[i]


    # 分好组后对每一组排序:按从左到右，从上到下

    for i in range(listNum):
        ssorted_c.extend(list_temp[i][list_temp[i][:,0].argsort()])

    # 将多个元素数组，转成二维数组，并以【x，y】的格式 存入 new_array 中
    new_array = [ssorted_c[i][:2].tolist() for i in range(len(ssorted_c))]

    # 打印 new_array 来查看结果
    #print(new_array)


    # 下面则找出 所有点中 的 拨盘中心点 位置
    first_min = min(el[0] for el in new_array)
    first_max = max(el[0] for el in new_array)
    second_min = min(el[1] for el in new_array)
    second_max = max(el[1] for el in new_array)

    # 计算平均值
    first_avg = (first_min + first_max) / 2
    second_avg = (second_min + second_max) / 2

    # 初始化最接近的元素和最小距离
    closest_element = None
    min_distance = float('inf')

    # 遍历数组，找到最接近平均值的元素
    for element1 in new_array:
        # 计算当前元素与平均值的差的平方和
        distance = (element1[0] - first_avg) ** 2 + (element1[1] - second_avg) ** 2
        # 如果当前元素的距离小于已知的最小距离，则更新最接近的元素和最小距离
        if distance < min_distance:
            min_distance = distance
            closest_element = element1


    # 打印结果
    #print("转盘中心（最接近平均值）点:", closest_element)

    circle_loaction = [[
        (element[0] - closest_element[0]) * scale,  # 第一个元素的差值
        (closest_element[1] - element[1]) * scale  # 第二个元素的差值
    ] for element in new_array]

    circle_loaction = [item for item in circle_loaction if item != [0, 0]]


    return circle_loaction,closest_element



def find_zp_delta_loc(address,gray=True,enhance=True,binary=True,blur=True,fliter=True,fx=0.25,fy=0.25,clipLimit=255.0,bi_threshold=99,
               minDist=100,param1=80,param2=0.9,minRadius=50, maxRadius=120,threhsold=60,scale = 1):


    '''
    Param address:目标图片地址
    return (检测圆心到图片中心x像素距离,检测圆心到图片中心y像素距离)
    未成功检测会返回(None,None)

    负数表示要向右或者向下移动
    '''

    # 读取输入地址的图片
    image = cv2.imread(address)
    # 固定输入2048*2448然后resize
    image = cv2.resize(image, None, fx=fx, fy=fy, interpolation=cv2.INTER_AREA)
    res = image
    # 确定中线,预先设定，这里先假设为下例(x,y)，用于后续判断合理圆心位置
    mid_line = int(res.shape[1] * 0.536)
    # 图片中心(x,y)
    center = [res.shape[1] // 2, res.shape[0] // 2]

    # 预处理
    # 灰度
    if gray:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # cv2.imshow('bw',image)
        # cv2.waitKey(0)

    # 增强对比度cliplimit越大越黑白
    if enhance:
        clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=(8, 8))
        image = clahe.apply(image)
        # cv2.imshow('eg',image)
        # cv2.waitKey(0)

    if blur:
        # 对图像进行模糊处理，以减少噪声
        image = cv2.GaussianBlur(image, (5, 5), 2)
        # cv2.imshow('bw',image)
        # cv2.waitKey(0)
    if fliter:
        # 应用拉普拉斯滤波器
        # image = cv2.Laplacian(image, cv2.CV_8U)
        # cv2.imshow('bw',image)
        # cv2.waitKey(0)
        # 定义锐化卷积核
        kernel = np.array([[-1, -1, -1],
                           [-1, 9, -1],
                           [-1, -1, -1]], dtype=np.float32)
        kernel2 = np.array([[0, -1, 0],
                            [-1, 5, -1],
                            [0, -1, 0]], dtype=np.float32)

        # 应用卷积核进行图像滤波
        image = cv2.filter2D(image, -1, kernel2)
        # cv2.imshow('eg',image)
        # cv2.waitKey(0)
    # 二值化
    if binary:
        _, image = cv2.threshold(image, bi_threshold, 255, cv2.THRESH_BINARY)
        # cv2.imshow('bg',image)
        # cv2.waitKey(0)

    # 检测
    # 霍夫圆变换检测圆形，返回列表
    circles = cv2.HoughCircles(
        image,
        cv2.HOUGH_GRADIENT_ALT,
        dp=1,
        minDist=minDist,  # 圆之间的最小距离，只用检测一个圆所以尽量调大点，后期设为resize图的一半大小
        param1=param1,
        param2=param2,
        minRadius=minRadius,
        maxRadius=maxRadius  # (614, 734, 3)大小的图片对应80-100的半径,旋钮半径大约图短边0.14~0.16
    )

    if circles is not None:
        count = 0
        circles = np.uint16(np.around(circles))
        for i in circles[0, :]:  # 对每个检测到的圆形,格式为(x,y,r)
            if (abs(i[0] - mid_line) <= threhsold):  # 与固定轴线的x距离不超过十个像素点，则确定为目标
                count += 1
                # cv2.imshow('prototype',image)
                # cv2.waitKey(0)
                # 绘制圆形的边缘
                cv2.line(res, (mid_line, 0), (mid_line, res.shape[0]), (255, 0, 0), 2)
                cv2.circle(res, (i[0], i[1]), i[2], (0, 255, 0), 1)
                # 绘制圆形的中心
                cv2.circle(res, (i[0], i[1]), 1, (0, 0, 255), 3)
                cv2.circle(res, (center[0], center[1]), 2, (0, 0, 255), 3)
                #cv2.imshow('ss', res)
                #cv2.waitKey(0)

                # 算距离，开头缩小四倍，这里放大四倍
                pixel_x = (int(circles[0][0][0]) - center[0]) * scale

                pixel_y = (-(int(circles[0][0][1]) - center[1])) * scale

                if (int(i[2]) >= 88) and (int(i[2]) <= 96):

                    return pixel_x, pixel_y , res

                else:

                    print('圆心半径不对!')
                    return None, None, None

        if (count == 0):
            print("没有符合要求的圆形")
            return None, None, None
        #cv2.imshow('ss', res)
        #cv2.waitKey(0)

    else:
        print("未检测成功")
        return None, None, None



def get_now_wyb_loc(kong_num,scale = 1):

    delta_x, delta_y, res = find_zp_delta_loc(pic_equip_path,binary=False,param2=0.8,scale = scale)

    #print(delta_x, delta_y)

    if (delta_x is not None) and (delta_y is not None) and (res is not None):

        circle_loaction,zp_location = find_blue_circle_loc(pic_blue_path,scale)

        #print(circle_loaction)

        wyb_all_loc = [[(element[0] + delta_x), (element[1] + delta_y)] for element in circle_loaction]

        kong_all_loc = wyb_all_loc[len(wyb_all_loc) - kong_num : len(wyb_all_loc)]

        zp_delta_pos = [delta_x,delta_y]

        return wyb_all_loc,kong_all_loc,res,zp_delta_pos

    else:

        return None, None, None, None



'''
all_loc,kong_loc,res,zp_delta_pos = get_now_wyb_loc(4,0.241935)

print(kong_loc)
print(zp_delta_pos)
cv2.imshow('ss', res)
cv2.waitKey(0)
'''