# !/usr/bin/env python3
# -*-coding:utf-8 -*-

"""
# File       : AdDiscern.py
# Time       ：2020/6/11 14:51
# Author     ：Yooha
"""

#************************************************************************
#    功能：通过对批量样本中的相关文件进行对比，输出相似度，作为马甲包判定的依据

#    文件：hash.txt----------记录需要判定的样本的hash,每行一条
#    环境：windows
#    工具：Robocopy.exe(windows系统自带) , 7z.exe , apktool.jar 
#

#        多维度比较点： 关键词：权重、重复率

#        一、AM文件：                       权重---30%  //反编译提取

#        二、Assets文件夹：                 权重---10%  //解压提取

#        三、lib\armeabi-v7a 文件夹：       权重---10%  //解压提取

#        四、res\xml：                     权重---10%  //反编译提取

#        五、res\drawable：                权重---10%  //反编译提取

#        六、res\layout：                  权重---20%  //反编译提取

#        七、res\values\strings.xml：      权重---10%  //反编译提取

# > python MJ.py  //hash.txt中写入要分析的hash
#************************************************************************
import requests
import shutil
import openpyxl
import datetime
import subprocess
import time
import getopt
import random
import sys
import os
import colorama
from colorama import init,Fore,Back,Style
init(autoreset=True)

try:
    import click
except:
    class click:
        @staticmethod
        def secho(message=None, **kwargs):
            print(message)

        @staticmethod
        def style(**kwargs):
            raise Exception("unsupported style")

#---------------------------------------------------------------
_WEIGHT_AM_       = 0.30
_WEIGHT_ASSETS_   = 0.10
_WEIGHT_LIB_      = 0.10
_WEIGHT_XML_      = 0.10
_WEIGHT_DRAWABLE_ = 0.10
_WEIGHT_LAYOUT_   = 0.20
_WEIGHT_STRINGS_  = 0.10


#---------------------------------------------------------------
banner = """
----------------------------------------------------------------------------------------
         ________    ________                              _______                      
         /       \  /        \                             |      |                     
        /         \/          \                            |      |                     
       /     /\        /\      \                           |      |                     
      /     /  \      /  \      \                          /      /                     
     /     /    \    /    \      \            ____        /      /                      
    /     /      \  /      \      \          |    |______/      /                       
   /     /        \/        \      \         \                 /                        
  /_____/                    \______\         \_______________/                         
                                                                                        
                                  YooHa                                                 
----------------------------------------------------------------------------------------\n
"""


#---------------------------------------------------------------
class Stdout(object):
    _label_info_start:str = "\033[32m"
    _label_end:str = "\033[0m"
    _label_error_start:str = "\033[31m"
    _label_warn_start:str = "\033[33m"
    _label_hint_start:str = "\033[34m"
    # click.secho

    @classmethod
    def info(cls, info:str):
        print(cls._label_info_start + "[+++++++++] -->> " + info + cls._label_end)
        pass
        
    @classmethod 
    def error(cls, func:str, err:str):
        print(cls._label_error_start + "[---------] -->> " +  "[ " + func + " ]" + err + cls._label_end)
        pass

    @classmethod
    def warning(cls, warn:str):
        print(cls._label_warn_start + "[*********] -->> " + warn + cls._label_end)
        pass

    @classmethod
    def hint(cls, hint:str):
        print(cls._label_hint_start + "     " + hint + cls._label_end)
        pass
#---------------------------------------------------------------

#---------------------------------------------------------------
class Cls_list(object):
    # list去重
    @classmethod
    def _del_repeat(cls, lists):
        new_list = []
        for item in lists:
            if item not in new_list:
                new_list.append(item)
        return new_list


    # 处理列表中的 \n 和 空行
    @classmethod
    def _update_data(cls, lists):
        new_list = []
        for item in lists:
            strs = item.strip()
            if strs != "":
                new_list.append(strs)
        return new_list
#---------------------------------------------------------------


# 下载apk文件
def download_apk(hash):
    url = "http://sample.antiy/download/"
    res = requests.get(url + hash)

    if(res.status_code == 404):
        Stdout.error("download_apk", hash + " 下载出错 ")
        return False

    with open(hash + ".apk", "wb") as apk:
        apk.write(res.content)
    Stdout.info(hash + " 下载完成 ")
    return True


# 从一行字符串中筛选出 android:name 字段
def get_android_name(lines):
    try:
        names = lines.split("android:name=\"")[1]
        names = names.split("\"")[0]
    except Exception as err:
        Stdout.error("get_android_name", str(err))
        names = ""
    return names


# 获取AM文件的信息列表
def get_AM_list(path):
    list_AM = []
    with open(path,'r',encoding='utf-8') as files:
        lists = files.readlines()
        for lines in lists:
            if lines.find("<activity") != -1:
                list_AM.append(get_android_name(lines))
            elif lines.find("<provider") != -1:
                list_AM.append(get_android_name(lines))
            elif lines.find("<service") != -1:
                list_AM.append(get_android_name(lines))
            elif lines.find("<receiver") != -1:
                list_AM.append(get_android_name(lines))
    return list_AM


# 获取文件夹中的文件信息列表
def get_filename_list(path):
    list_filename = []
    if os.path.exists(path) == False:
        return list_filename
    list_file = os.listdir(path)
    if len(list_file) == 0:
        return list_filename
    else:
        for file_name in list_file:
            if (os.path.isfile(path + "/" + file_name)):
                list_filename.append(file_name)
            else:
                list_tmp = get_filename_list(path + "/" + file_name)
                for lists in list_tmp:
                    list_filename.append(lists)
    return list_filename


# 获取strings文件的信息列表
def get_strings_list(path):
    list_strings = []
    with open(path,'r',encoding='utf-8') as files:
        lists = files.readlines()
        for lines in lists:
            if lines.find("<string name") != -1:
                list_strings.append(lines)
    return list_strings


# 模糊匹配文件名
def fuzzy_find_filename(path, fuzzyField):
    list_filename = []
    list_file = os.listdir(path)
    for file_name in list_file:
        if fuzzyField in file_name:
            list_filename.append(file_name)
    return list_filename



# 获取各个文件的信息,并汇总
def get_file_info(dict_hash_data, hash_list):
    for hash in hash_list:
        # {"AM":[], "Assets":[], ...}
        dict_data = {"AM":[], "Assets":[], "lib":[], "xml":[], "drawable":[], "layout":[], "strings":[]}
        
        dict_data["AM"] = Cls_list._del_repeat(get_AM_list(hash + "/AndroidManifest.xml"))

        dict_data["Assets"] = Cls_list._del_repeat(get_filename_list(hash + "7z/assets"))

        list_lib_filename = fuzzy_find_filename(hash + "7z/lib", "armeabi")
        list_lib_all_file = []
        for filename in list_lib_filename:
            list_lib_all_file += get_filename_list(hash + "7z/lib/" + filename)
        dict_data["lib"] = Cls_list._del_repeat(list_lib_all_file)

        dict_data["xml"] = Cls_list._del_repeat(get_filename_list(hash + "/res/xml"))

        list_drawable_filename = fuzzy_find_filename(hash + "/res/", "drawable")
        list_drawable_all_file = []
        for filename in list_drawable_filename:
            list_drawable_all_file += get_filename_list(hash + "/res/" + filename)
        dict_data["drawable"] = Cls_list._del_repeat(list_drawable_all_file)

        list_layout_filename = fuzzy_find_filename(hash + "/res/", "layout")
        list_layout_all_file = []
        for filename in list_layout_filename:
            list_layout_all_file += get_filename_list(hash + "/res/" + filename)
        dict_data["layout"] = Cls_list._del_repeat(list_layout_all_file)

        dict_data["strings"] = Cls_list._del_repeat(get_strings_list(hash + "/res/values/strings.xml"))
        dict_hash_data[hash] = dict_data
    return


# 对2个列表中的数据进行相似度判定,并返回结果
def field_compare(list_dst, list_src):
    total = 0
    repeat = 0
    list_sum = []
    for lists in list_src:
        list_sum.append(lists)
        total = total + 1
    for lists in list_dst:
        if lists not in list_sum:
            list_sum.append(lists)
            total = total + 1
        else:
            repeat = repeat + 1
    if total == 0:
        return round(0, 3)
    else:
        return round(float(repeat)/float(total), 3) # 结果保留3位有效数----0.33


# 对传入的2个hash进行数据对比
def get_hash_compare_info(dict_compare_table, dict_hash_data):
    hash_dst = dict_compare_table["hash_dst"]
    hash_src = dict_compare_table["hash_src"]

    dict_data_dst = dict_hash_data[hash_dst]
    dict_data_src = dict_hash_data[hash_src]

    ret = field_compare(dict_data_dst["AM"], dict_data_src["AM"])
    dict_compare_table["AM"] = ret
    total = ret * _WEIGHT_AM_

    ret = field_compare(dict_data_dst["Assets"], dict_data_src["Assets"])
    dict_compare_table["Assets"] = ret
    total = total + ret * _WEIGHT_ASSETS_

    ret = field_compare(dict_data_dst["lib"], dict_data_src["lib"])
    dict_compare_table["lib"] = ret
    total = total + ret * _WEIGHT_LIB_

    ret = field_compare(dict_data_dst["xml"], dict_data_src["xml"])
    dict_compare_table["xml"] = ret
    total = total + ret * _WEIGHT_XML_

    ret = field_compare(dict_data_dst["drawable"], dict_data_src["drawable"])
    dict_compare_table["drawable"] = ret
    total = total + ret * _WEIGHT_DRAWABLE_

    ret = field_compare(dict_data_dst["layout"], dict_data_src["layout"])
    dict_compare_table["layout"] = ret
    total = total + ret * _WEIGHT_LAYOUT_

    ret = field_compare(dict_data_dst["strings"], dict_data_src["strings"])
    dict_compare_table["strings"] = ret
    total = total + ret * _WEIGHT_STRINGS_

    dict_compare_table["total"] = round(total, 3)
    return


# 循环遍历并对比各hash的信息列表
def get_compare_info(list_compare_table_total, hash_list, dict_hash_data):
    dict_num = {}
    num = 1
    for hash in hash_list: # 建立hash编号表
        dict_num[num] = hash
        num = num + 1
    for i in range(1, num - 1):
        for j in range(i + 1, num):
            dict_compare_table = {}
            dict_compare_table["hash_dst"] = dict_num[i]
            dict_compare_table["hash_src"] = dict_num[j]
            get_hash_compare_info(dict_compare_table, dict_hash_data)
            list_compare_table_total.append(dict_compare_table)
    return

# 将马甲包分类----配对数据的网状链接问题
def select_waistcoat(list_result):
    list_classify = []
    for list_hash in list_result: # 取出hash对
        hash0 = list_hash[0]
        hash0_list = []
        hash1 = list_hash[1]
        hash1_list = []

        for classify in list_classify:
            if hash0 in classify:
                hash0_list = classify
            if hash1 in classify:
                hash1_list = classify
        
        if hash0_list and hash1_list:
            if hash0_list != hash1_list:
                list_classify.remove(hash0_list)
                list_classify.remove(hash1_list)
                tmp = hash0_list + hash1_list
                list_classify.append(tmp)
        if hash0_list and len(hash1_list) == 0:
            list_classify.remove(hash0_list)
            hash0_list.append(hash1)
            list_classify.append(hash0_list)
        if hash1_list and len(hash0_list) == 0:
            list_classify.remove(hash1_list)
            hash1_list.append(hash0)
            list_classify.append(hash1_list)
        if len(hash0_list) == 0 and len(hash1_list) == 0:
            tmp = [hash0, hash1]
            list_classify.append(tmp)
    Stdout.info("以下样本有明显马甲包特征：")
    for lists in list_classify:
        Stdout.info("--------------------------------------------------------------------------------")
        for hash in lists:
            Stdout.info(hash)
        Stdout.info("--------------------------------------------------------------------------------")

def select_match(list_hash_pairs_value):
    try:
        Stdout.info("以下样本有明显马甲包特征：")
        for list_hash_pairs in list_hash_pairs_value:
            Stdout.info(list_hash_pairs["hash"][0] + " <======> " + list_hash_pairs["hash"][1] + " ==>>  {:%} ".format(list_hash_pairs["total"]))
        Stdout.info("--------------------------------------------------------------------------------")
    except Exception as err:
        Stdout.error("select_match", str(err))
        
        

# 提取总表的数据并打印
def print_compare_result(list_compare_table_total, range):
    list_hash_pairs = []
    list_hash_pairs_value = []
    for dict_compare_table in list_compare_table_total:
        try:
            Stdout.info("--------------------------------------------------------------------------------")
            Stdout.info(dict_compare_table["hash_dst"] + " <======> " + dict_compare_table["hash_src"] )
            Stdout.info("AM >>  {:%}".format(dict_compare_table["AM"]))
            Stdout.info("Assets >>  {:%}".format(dict_compare_table["Assets"]))
            Stdout.info("lib >>  {:%}".format(dict_compare_table["lib"]))
            Stdout.info("xml >>  {:%}".format(dict_compare_table["xml"]))
            Stdout.info("drawable >>  {:%}".format(dict_compare_table["drawable"]))
            Stdout.info("layout >>  {:%}".format(dict_compare_table["layout"]))
            Stdout.info("strings >>  {:%}".format(dict_compare_table["strings"]))
            Stdout.info("total >>  {:%}".format(dict_compare_table["total"]))
            Stdout.info("--------------------------------------------------------------------------------")
            # 将结果分类
            if (dict_compare_table["total"] > range):
                list_tmp = [dict_compare_table["hash_dst"], dict_compare_table["hash_src"]]
                list_hash_pairs.append(list_tmp)
                dict_tmp = {"total":dict_compare_table["total"], "hash":list_tmp}
                list_hash_pairs_value.append(dict_tmp)
        except Exception as err:
            Stdout.error("delete_file", str(err))
    # select_waistcoat(list_hash_pairs) //会出现传递递减现象
    select_match(list_hash_pairs_value)
    return


# 执行命令行工具
def execute_cmd(command, timeout=0):
    time_start = datetime.datetime.now()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
    while process.poll() is None:  #poll函数返回None 表示在运行
        time.sleep(1) 
        if timeout != 0:  #timeout==0 则默认认为程序不会卡死，必须要等待程序自然结束
            time_now = datetime.datetime.now() #此时间单位为秒
            if (time_now - time_start).seconds > timeout: #执行时间超过timeout，认为进程卡死
                process.terminate()   #关掉进程
                time.sleep(1)       #给 1 秒的缓冲时间
                return  False 
    return True


# 调用shell执行字符串
def execute_shell(command, timeout):  
    time_start = datetime.datetime.now()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) 
    while process.poll() is None:  #poll函数返回None 表示在运行
        time.sleep(0.5) 
        time_now = datetime.datetime.now() #此时间单位为秒
        if (time_now - time_start).seconds > timeout: #执行时间超过timeout，shell已经执行完字符串指令，需要手动关闭shell，因为他并不会自己关闭自己
            process.terminate()   #关掉进程
            time.sleep(0.5)       #给0.5秒的缓冲时间
    return


# 删除文件夹
def my_rmtree(path):
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception as err:
        Stdout.error("my_rmtree", path + " 删除失败")
        Stdout.error("my_rmtree", str(err))
    return


# 整体、彻底、删除文件夹及其子文件
def delete_folder(path, temp):
    if os.path.exists(path):  
        my_rmtree(path)
        if os.path.exists(path):  # 如果文件夹还存在，说明存在部分文件无法删除，使用Robocopy来删
            command = "Robocopy /MIR " + temp + " " + path
            if execute_cmd(command, 30):   
                my_rmtree(path)
            else:
                Stdout.error("delete_folder", path + " 删除失败")
    return


# 删除apk文件
def delete_apk(path):
    if os.path.exists(path):
        try:
            os.remove(path)     # 删除apk文件
        except Exception as err:
            Stdout.error("delete_file", path + " 删除失败")
            Stdout.error("delete_file", str(err))
    return


# 删除多余文件
def delete_file(lists):
    dir_temp = "delete_temp"
    if os.path.exists(dir_temp) == False:
        os.mkdir(dir_temp)
    for hash in lists:
        delete_folder(hash, dir_temp)        # 删除反编译文件夹
        delete_folder(hash + "7z", dir_temp) # 删除解压文件夹
        delete_apk(hash + ".apk")
        Stdout.info(hash + "文件信息清理完成")
    my_rmtree(dir_temp)
    return

#............................................................................................................................................................................
    # 编号总表----------------dict_num = {1:hash1, 2:hash2, 3:hash3, 4:hash4, 5:hash5, ....}  2层循环比较的时候使用
    # 数据信息表--------------dict_data = {"AM":[], "Assets":[], "lib":[], "xml":[], "drawable":[], "layout":[], "strings":[]}
    # hash/数据信息对应表-----dict_hash_data = {hash1:dict_data, ...}
    # 对比结果存储表----------dict_compare_table = {"hash_dst":hash1, "hash_src":src, "AM":num, "Assets":num, "lib":num, "xml":num, "drawable":num, "layout":num, "strings":num, "total":num}
    # 对比结果存储总表--------list_compare_table_total = [dict_compare_table, dict_compare_table, ...]
    # 依次获取每个hash的数据信息，写进数据信息表，然后将该表添加进 hash/数据信息对应表 
    # 用两层循环让各个hash的数据信息进行比较，并将结果写进对比结果存储表，然后将该表添加进对比结果存储总表
#............................................................................................................................................................................

#---------------------------------------------------------------
class Argv(object):
    def __init__(self, argv:list):
        self._show_banner()
        self.init_opt(argv)
        #self.execute_argv()
        pass

    def init_opt(self, argv:list):
        """
        function:  初始化命令行参数
        param:     argv -> 参数列表
        """
        self.hash_file = ""              # hash文件路径
        self.range = 0.6                 # 阈值

        try:
            self.opts, self.argv = getopt.getopt(argv,"vr:ho:",["read=", "version", "help", ])
        except getopt.GetoptError as err:
            Stdout.error("Argv -> init_opt", str(err))
            sys.exit(2)

        for opt, arg in self.opts:
            if opt in ("-h", "--help"):
                self._show_help()
                sys.exit()
            elif opt in ("-r", "--read"):
                self.hash_file = arg
            elif opt in ("-v", "--version"):
                self._show_version()
                sys.exit()
            elif opt == "-o":
                try:
                    if (float(arg) < 1 and float(arg) > 0.5):
                        self.range = float(arg)
                    else:
                        Stdout.error("Argv -> init_opt", "请设置正确的阈值 [0.5 ~ 1.0]")
                        sys.exit(2)
                except Exception as err:
                    Stdout.error("Argv -> init_opt", str(err))
                    Stdout.error("Argv -> init_opt", "请设置正确的阈值 [0.5 ~ 1.0]")
                    sys.exit(2)
        pass 

    @classmethod
    def _show_help(cls):
        """
        function:  显示帮助文档
        """
        Stdout.info("-v          --version         :查看版本信息")
        Stdout.info("-r[XX.txt]  --read[XX.txt]    :从文件获取hash")
        Stdout.info("-o[0.5~1.0]                   :判定为马甲的阈值")
        Stdout.info("-h          --help            :查看帮助文档")
        pass

    @classmethod
    def _show_banner(cls):
        """
        function:  显示横幅
        """
        colors = ['bright_red', 'bright_green', 'bright_blue', 'cyan', 'magenta']
        try:
            click.style('color test', fg='bright_red')
        except:
            colors = ['red', 'green', 'blue', 'cyan', 'magenta']
        try:
            columns = os.get_terminal_size().columns
            if columns >= len(banner.splitlines()[1]):
                for line in banner.splitlines():
                    if line:
                        fill = int((columns - len(line)) / 2)
                        line = line[0] * fill + line
                        line += line[-1] * fill
                    click.secho(line, fg=random.choice(colors))
        except:
            pass
        time.sleep(2)
        pass

    @classmethod
    def _show_version(cls):
        """
        function:  显示版本信息
        """
        Stdout.info("当前版本为： 1.0.0")
        pass
#---------------------------------------------------------------


def main(argv):
    hash_list = []  
    total_list = []
    download_fail_list = []  
    deCompression_fail_list = []

    args = Argv(argv)

    with open(args.hash_file) as files:
        hash_list = Cls_list._update_data(files.readlines())
    hash_list = Cls_list._del_repeat(hash_list)

    if len(hash_list) == 1 or len(hash_list) == 0:
        Stdout.error("main", "请输入2条及以上hash值")
        return 
    else:
        for hash in hash_list:
            total_list.append(hash)

    delete_temp = []
    for hash in hash_list: 
        if download_apk(hash) == False:  #下载样本
            download_fail_list.append(hash)
            delete_temp.append(hash)
        else:
            Stdout.info("开始解压......")
            if execute_cmd('7z x "' + hash + '.apk"  -y -aos -o"./' + hash + '7z/"', 200) == False: # 解压apk 给3min时间，超时则认为解压失败
                deCompression_fail_list.append(hash)
                delete_temp.append(hash)
                Stdout.error(hash + ".apk", " 文件解压失败")
            else:
                Stdout.info(hash + ".apk 解压完成")

            Stdout.info("开始反编译......")
            execute_cmd("java -jar apktool.jar d " + hash + ".apk", 30)   #反编译样本 给30秒进行反编译 因为只需要比较res文件夹和AM文件，所以无需将整个apk都反编译
            Stdout.info(hash + ".apk 反编译完成")
    if delete_temp:
        for temp in delete_temp:
            hash_list.remove(temp)

    # 收集每个hash的文件信息,并汇总
    dict_hash_data = {}
    get_file_info(dict_hash_data, hash_list)

    # 用两层循环让各个hash的数据信息进行比较，并将结果写进对比结果存储表，然后将该表添加进对比结果存储总表
    list_compare_table_total = []
    get_compare_info(list_compare_table_total, hash_list, dict_hash_data)

    # 提取总表的数据并打印
    print_compare_result(list_compare_table_total, args.range)

    # 打印出错信息表
    if len(download_fail_list):
        for hash in download_fail_list:
            Stdout.error("下载失败的hash:", hash)
    if len(deCompression_fail_list):
        for hash in deCompression_fail_list:
            Stdout.error("解压失败的hash:", hash)

    #删除文件
    delete_file(total_list)
    return

if __name__ == "__main__":
   main(sys.argv[1:])
    

