# -*- coding:utf-8 -*-  
# teenyda
# 使用tesseract-ocr识别验证码

import requests
import time
from http import cookiejar
import pytesseract
from PIL import Image
import os
import json
import time
import re
import web
import schedule
import threading
import datetime
# web.py disallows some types of python legal statements to be executed within the template. 
# web/template.py contains a list ALLOWED_AST_NODES which are constructs (used by the abstract syntax tree parser) which are permitted in within templates.
# fix “execution of 'Constant' statements is denied” error
from web.template import ALLOWED_AST_NODES
ALLOWED_AST_NODES.append('Constant')

#官网
# url = 'https://m.client.10010.com/sma-lottery/qpactivity/qingpiindex'

# 抽奖接口 post
# 参数:mobile,image(验证码),userid
# luckUrl = 'https://m.client.10010.com/sma-lottery/qpactivity/qpLuckdraw.htm'

# 验证码地址
# https://m.client.10010.com/sma-lottery/qpactivity/getSysManageLoginCode.htm?userid=" + "8F62A3D5E3ED9AF1472CDB071B2BDD63"+"&code=" + new Date().getTime()

# 验证图片地址
# type: "POST",
# https://m.client.10010.com/sma-lottery/validation/qpImgValidation.htm

# 步骤：获取验证码，验证验证码获取加密手机号， 抽奖

# 手机号保存文件（没有则自动创建）
fileName = 'phone.txt'
# 备份文件（没有则自动创建）
backFileName = 'phone.back'
# 抽奖任务执行时间，跟你服务器所在时区有关。例如默认的16：05UTC就是北京时间24：05UTC+8
taskTime = '16:05'
# 抽奖时间间隔
intervalTime = 0
# 连续多少次不中奖停止抽奖（针对流量被抽完停止抽奖）
stopCount = 500


# 不中奖累加器(不用管)
stopcounter = 0
# 这个不用管
stopFlag = False

# 请求路径
# 分别是首页,添加手机号,移除手机号
urls = (
    '/qingdao', 'qingdao',
    '/addphone', 'addphone',
    '/removephone', 'removephone'
)
# web应用
app = web.application(urls, globals())
# templates模版文件夹
render = web.template.render('templates/')

# -------------------------------------http-------------------------------
def httpGet(url):
    response = {}
    try:
        response = requests.get(url)
    except requests.ConnectTimeout:
        print('连接超时')
        httpGet(url)
    except requests.HTTPError:
        print('http状态码非200')
        httpGet(url)
    except Exception as e:
        print('未知错误:', e)
        httpGet(url)
    return response

def httpPost(url, data, headers):
    response = {}
    try:
        response = requests.post(url, data=data, headers=headers)
    except requests.ConnectTimeout:
        print('连接超时')
        httpPost(url, data, headers)
    except requests.HTTPError:
        print('http状态码非200')
        httpPost(url, data, headers)
    except Exception as e:
        print('未知错误:', e)
        httpPost(url, data, headers)
    return response
# ------------------------------------------------------------------------


# --------------------------------------web--------------------------------
# 首页：http://localhost:8080/qingdao
class qingdao:
    def GET(self):
        return render.index()

class addphone:
    def POST(self):
        data = web.input('phone')
        phone = data.phone
        result = writeToFile(phone)
        if result:
            return '添加成功'
        return '手机号已存在'

class removephone:
    def POST(self):
        data = web.input('phone')
        phone = data.phone
        removePhoneByFile(phone)
        return '删除成功'

# --------------------------------------class req--------------------------------
class Req():
    def __init__(self):
        self.userid = ''
        self.mobile = ''
        self.sourceMobile = ''
        self.code = ''
        # 官方地址
        self.officialUrl = 'https://m.client.10010.com/sma-lottery/qpactivity/qingpiindex'
        # 验证码获取地址
        self.loginCodeUrl = 'https://m.client.10010.com/sma-lottery/qpactivity/getSysManageLoginCode.htm?userid='
        # 验证码验证
        self.validationUrl = 'https://m.client.10010.com/sma-lottery/validation/qpImgValidation.htm'
        #抽奖地址
        self.luckUrl = 'https://m.client.10010.com/sma-lottery/qpactivity/qpLuckdraw.htm'
        self.headers = {}
        self.headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
        self.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36'
        self.headers['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8'
        self.headers['Referer'] = 'https://m.client.10010.com/sma-lottery/qpactivity/qingpiindex'
        self.headers['Host'] = 'm.client.10010.com'
        self.headers['Origin'] = 'https://m.client.10010.com'
        self.headers['Sec-Fetch-Mode'] = 'cors'
        self.headers['Sec-Fetch-Site'] = 'same-origin'
        self.headers['X-Requested-With'] = 'XMLHttpRequest'
        self.formData = {}
        self.count = 0

    # 获取验证码链接
    def getCodeUrl(self):
        url = self.loginCodeUrl + self.userid + '&'
        t = time.time()
        timestamp = int(round(t * 1000))
        url = url + 'code=' + str(timestamp)
        return url
    
    # 获取官方网
    def getOfficialUrl(self):
        return self.officialUrl
    
    # 验证码验证地址
    def getVaildationUrl(self):
        return self.validationUrl
    
    # 抽奖地址
    def getLuckUrl(self):
        return self.luckUrl

    # 获取cookies
    def setCookiesAndUserId(self,resp):
        cookies = requests.utils.dict_from_cookiejar(resp.cookies)
        cookiesValue = ''
        for key in cookies.keys():
            cookiesValue += key + '=' + cookies.get(key) + ';'
            if key == 'JSESSIONID':
                self.userid = cookies.get(key)
                
        self.headers['Cookie'] = cookiesValue

    # 验证码验证
    def vailSubmit(self):
        resp = httpPost(self.validationUrl, data=self.formData, headers=self.headers)
        # resp.encoding = 'utf-8'
        jsonObj = json.loads(resp.text)
        return jsonObj

    # return 返回
    # -3 已抽完
    # -2 不是联通号码
    # -1 没中奖
    # 0 50MB
    # 1 100MB
    # 2 1000MB
    # 3 20砖石
    def goodLuck (self):
        resp = httpPost(self.luckUrl, data=self.formData, headers=self.headers)
        resp.encoding = 'utf-8'
        jsonObj = json.loads(resp.text)
        if jsonObj['status'] == 500:
            isunicom = jsonObj['isunicom']
            if not(isunicom):
                print(self.formData['mobile'] + '不是联通手机')
                self.count = 3
                return -1
            else:
                print('没抽奖次数了哦，改日再战吧!')
                self.count = 3
                return 0

        elif jsonObj['status'] == 0 or jsonObj['status'] == 200:
            self.count += 1
            data = jsonObj['data']
            level = data['level']
            prize = self.switch_id(level)
            print(prize)
            return int(level)
        elif jsonObj['status'] == 700:
            print('当前抽奖人数过多，请稍后重试！')

    def setFormData(self):
        self.formData = {
            'mobile': self.mobile,
            'image': self.code,
            'userid': self.userid
        }

    def printReqParam(self):
        print('--------------------------')
        print('userid', self.userid)
        print('code', self.code)
        print('mobile', self.mobile)
        print('sourceMobile', self.sourceMobile)
        print('headers', self.headers)
        print('formData', self.formData)
        print('--------------------------')


    def switch_id(self,id):
        switcher = {
            '1': '50MB',
            '2': '100MB',
            '3': '幸运奖',
            '4': '1000MB',
            '5': '20钻石',
            '6': '15yuan',
            '7': '50yuan'
        }
        return switcher.get(id)

# --------------------------------------class user--------------------------------
class Record():
    phone = ''
    prizeList = []
    prize = 0
    prize_50 = 0
    prize_100 = 0
    prize_1000 = 0     
    isunicom = True

    def setAttribute(self,line):
        # line既一行，存放手机号和奖品记录
        # 手机号 50MB累计流量,100MB累计流量,1000MB累计流量,20钻石
        record = line.split(' ')
        self.phone = record[0].strip()
        strArr = record[1].strip().split(',')
        # 将字符串转成数组
        prizeList = list(map(int, strArr))
        self.prizeList = prizeList
        self.prize_1000 = int(prizeList[2])
        self.prize_50 = int(prizeList[0])
        self.prize_100 = int(prizeList[1])

    def getLine(self):
        # 将数据写入文件(join函数就是字符串的函数,参数和插入的都要是字符串)
        line = self.phone + ' ' + ','.join('%s' %id for id in self.prizeList) + '\n'
        return line

# --------------------------------------class image--------------------------------
class MyImage():
    imgName = ''
    imgPath = ''
    def __init__(self, imgName):
        self.imgName = imgName
    
    def saveImage(self, res):
        with open(self.imgName, 'wb') as file:
            for data in res.iter_content(128):
                file.write(data)
        img = Image.open(self.imgName)
        return img
    # 使用pytesseract识别图片
    # 先去除干扰线，再把背景变透明
    def imgToString(self,img):
        img = img.convert('RGBA')
        pixdata = img.load()
        for y in range(img.size[1]):
            for x in range(img.size[0]):
                if pixdata[x,y][0] == pixdata[x,y][1] and pixdata[x,y][0] == pixdata[x,y][3]:
                    pixdata[x, y] = (255, 255, 255,0)
                if pixdata[x,y][0] > 80 and pixdata[x,y][0] <= 220  and pixdata[x,y][1] > 80 and pixdata[x,y][1] <= 220 and pixdata[x,y][2] > 80 and pixdata[x,y][2]< 220:
                    pixdata[x, y] = (255, 255, 255,0)
        return pytesseract.image_to_string(img)
    # 删除图片
    def removeThisImg(self):
        path = os.path.abspath('.') + '\\' + self.imgName
        path = path.replace('\\','/')
        print(path)
        os.remove(path)

# --------------------------------------文件读写---------------------------
def removePhoneByFile(phone):
    removePhone(fileName,phone)
    removePhone(backFileName,phone)

def removePhone(fileName,removePhone):
    with open(fileName,"r",encoding="utf-8") as f:
        lines = f.readlines()
        #print(lines)
    with open(fileName,"w",encoding="utf-8") as f_w:
        for line in lines:
            record = line.split(' ')
            phoneRecord = record[0].strip()
            if removePhone in phoneRecord:
                continue
            f_w.write(line)

# 月底恢复记录
def recoverRecord():
    with open(fileName, 'w') as mfile, open(backFileName, 'r') as backFile:
        lines = backFile.readlines()
        for line in lines:
            mfile.write(line)

def writeToFile(phone):
    phoneList = getPhoneList()
    for pho in phoneList:
        if pho == phone:
            return False
    
    #a 不覆盖，追加写 
    with open(fileName, 'a') as mfile, open(backFileName, 'a') as backFile:
        mfile.write(phone + ' 0,0,0,0' + '\n')
        backFile.write(phone + ' 0,0,0,0' + '\n')
        return True

def getPhoneList():
    phoneList = []
    file = {}
    try:
        file = open(fileName, 'r')
        lines = file.readlines()

        for line in lines:
            record = line.split(' ')
            phone = record[0].strip()
            phoneList.append(phone)
        return phoneList
    except FileNotFoundError:
        file = open(fileName, mode='w', encoding='utf-8')
        print("文件创建成功！")
        return phoneList
    finally:
        if not(file is None):
            file.close()
# ------------------------------------------------------------------------------



# 匹配手机号
def checkMobile(mobile):
    # ret = re.match(r"1[35678]\d{9}", tel)
    # 由于手机号位数大于11位也能匹配成功，所以修改如下：
    result = re.match(r"^1[35678]\d{9}$", mobile)
    if result:
        return True
    else:
        print("手机号码错误")
        return False

    
# 获取验证码，验证验证码获取加密手机号， 抽奖

# 获取验证码
def getVerificationCode(reqObj):
    # 请求获取验证码
    codeUrl = reqObj.getCodeUrl()
    imgResp = httpGet(codeUrl)
    myImage = MyImage('test.png')
    # 转为图片
    imgObj = myImage.saveImage(imgResp)
    # 转为字符串
    code = myImage.imgToString(imgObj)
    if len(code) != 4:
        print('验证码识别失败！重新获取验证码')
        getVerificationCode(reqObj)
    return code

# 验证验证码获取加密手机号
def getEncryptionMobile(reqObj):
    jsonObj = reqObj.vailSubmit()
    if jsonObj['code'] == 'YES':
        return jsonObj['mobile']
    elif jsonObj['code'] == 'IMGNULL':
        #刷新验证码
        print('刷新验证码')
        # time.sleep(3)
        return False
    elif jsonObj['code'] == 'IMGERROR':
        # 验证码错误
        return False


def outwitTheMilk(reqObj,f_w,recordObj):
    global stopFlag
    global stopcounter

    if(reqObj.count > 2):
        # 手机不是联通号
        if not(recordObj.isunicom):
            removePhoneByFile(recordObj.phone)
            return
        else:
            # 写入文件# 写入文件# 写入文件# 写入文件
            line = recordObj.getLine()
            f_w.write(line)
            # 返回不在抽奖
            return
    code = getVerificationCode(reqObj)
    reqObj.code = code
    print('验证码:'+code)

    reqObj.setFormData()

    # 验证码验证并获取加密手机号
    encryptionMobile = getEncryptionMobile(reqObj)
    # time.sleep(1)
    if isinstance(encryptionMobile, str):
        reqObj.mobile = encryptionMobile
        reqObj.setFormData()
        # 抽奖
        prize = reqObj.goodLuck()
        recordObj.prize = prize
        # 记录
        setRecord(recordObj)

        reqObj.mobile = reqObj.sourceMobile

        time.sleep(intervalTime)

    outwitTheMilk(reqObj, f_w, recordObj)    

def job():
    global stopcounter
    global stopCount
    with open(fileName,"r",encoding="utf-8") as f:
        lines = f.readlines()
        #print(lines)
    with open(fileName,"w",encoding="utf-8") as f_w:
        # line -> 手机号码 50MB累计流量,100MB累计流量,1000MB累计流量,20钻石
        for line in lines:
            # 连续stopCount次不中奖则停止抽奖
            if stopcounter >= stopCount:
                f_w.write(line)
                continue
            record = Record()
            record.setAttribute(line)

            print('手机号', record.phone)

            if not(checkMobile(record.phone)):
                # 手机号码错误将移除
                continue
            
            reqObj = Req()
            reqObj.mobile = record.phone
            reqObj.sourceMobile = record.phone
            resp = httpGet(reqObj.officialUrl)
            reqObj.setCookiesAndUserId(resp)
            
            # 流量>=1000这个月不再抽奖
            if record.prize_1000 >= 1000 or record.prize_50 + record.prize_100 >= 1000:
                print('流量>=1000')
                f_w.write(line)
                continue
            
            # 进行抽奖
            outwitTheMilk(reqObj,f_w, record)

            # 没中奖 +1 连续stopCount次不中则退出
            if stopFlag:
                stopcounter += 1
            

    print('抽奖完成')
    stopcounter = 0
    # 如果是最后一天，将恢复记录
    if isLastDay():
        print('lastday')
        recoverRecord()



# 记录一下
def setRecord(record):
    global stopFlag
    # -1 不是联通号码,移除
    # 0 无抽奖次数
    # 1 50MB
    # 2 100MB
    # 3 幸运奖
    # 4 1000MB
    # 5 20钻石
    # 6 15yuan

    if record.prize == -1:
        record.isunicom = False
        return

    if record.prize == 1:
        record.prizeList[0] += 50
    if record.prize == 2:
        record.prizeList[1] += 100
    if record.prize == 4:
        record.prizeList[2] = 1000
    if record.prize == 5:
        record.prizeList[3] += 20
    
    # 中奖
    if record.prize == 1 or record.prize == 2 \
    or record.prize == 4 or record.prize == 5:
        stopFlag = False
    else:
        # 没中
        stopFlag = True
# --------------------------------------是否是月末(copy)----------------------------
def last_day_of_month(any_day):
    """
    获取获得一个月中的最后一天
    :param any_day: 任意日期
    :return: string
    """
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
    return next_month - datetime.timedelta(days=next_month.day)

def isLastDay():
    # 当前日期
    now = datetime.datetime.now().date()
    year,month,day = str(now).split("-")  # 切割
    # 年月日，转换为数字
    year = int(year)
    month = int(month)
    day = int(day)

    # 获取这个月最后一天
    last_day = last_day_of_month(datetime.date(year, month, day))
    # 2020-02-29
    # 判断当前日期是否为月末
    if str(now) == last_day:
        return True
    else:
        return False


# --------------------------------------定时任务--------------------------------

# 定时任务
def scheduleTask():
    schedule.every().day.at(taskTime).do(job)
    while True:
        # 启动服务
        schedule.run_pending()
        time.sleep(5)
# web
def webAppTask():
    app.run()


if __name__ == "__main__":
    threading.Thread(target=scheduleTask).start()
    threading.Thread(target=webAppTask).start()
