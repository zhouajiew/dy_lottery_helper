import asyncio
import json
import os
import re
import time

import pymysql
import socketio

from datetime import datetime
from colorama import Fore,init

from global_v import *

sio = socketio.AsyncClient()

username = ''
password = ''
vip_time = -1
balance = 0

# 获取当前文件所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 构建相对路径
relative_path = os.path.join(current_dir)

# 读取json文件
def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as temp_f:
        d = json.load(temp_f)
        return d

# 还原成默认配置
def reset_temporary_vip():
    is_temporary_VIP[0] = False

    set_normal_p[0] = 0.1
    set_fan_club_p[0] = 0.2
    set_real_object_p[0] = 0.01
    min_normal_p[0] = 0.1
    min_fan_club_p[0] = 0.3
    min_real_object_p[0] = 0.01
    max_normal_p[0] = 0.1
    max_fan_club_p[0] = 0.5
    max_real_object_p[0] = 0.01

    want_bag_type1[0] = 1
    want_bag_type2[0] = 1
    want_bag_type3[0] = 0

    set_risk_income[0] = -5
    set_risk_today_income[0] = -5
    set_get_reward_p[0] = 0.1
    set_raise_fan_club_bag_p[0] = 0.1

    open_account2_browser[0] = 0
    need_change_account[0] = 0
    set_change_account_running_time[0] = 999999
    set_change_account_today_income[0] = -10
    set_change_account_today_income2[0] = 100
    set_change_account_bag_num1[0] = 200
    set_change_account_bag_num3[0] = 15

    want_red_packet[0] = 0
    want_popularity_ticket_red_packet[0] = 0
    set_max_count_popularity_ticket_red_packet[0] = 0

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(Fore.RED + f'{timestamp} 当前时间不处于免费VIP时间段，无法临时使用VIP功能:(' + Fore.RESET)

async def main():
    # 隐藏的连接到服务器的代码
    await sio.wait()

# 查看当前版本
@sio.on('get_program_version')
async def get_program_version(data):
    global username

    current_program_version = '4.0.3'

    if data != current_program_version:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            Fore.RED + f'\n{timestamp} 当前程序不是最新版本的程序，你可以前往Github获取最新版本的程序:D\n' + Fore.RESET)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            Fore.GREEN + f'\n{timestamp} 当前程序已经是最新版本的程序:D\n' + Fore.RESET)

    await asyncio.sleep(2)
    await sio.emit('select', username)

@sio.event
async def connect():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(Fore.YELLOW + f'{timestamp} 已建立和服务器的连接' + Fore.RESET)

    await sio.emit('get_program_version', '1')


@sio.event
async def disconnect():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(Fore.YELLOW + f'{timestamp} 已关闭和服务器的连接' + Fore.RESET)

@sio.on('no_result')
async def create_account(data):
    global username
    global password
    global vip_time
    global balance

    username = ''
    password = ''

    if username != 'default':
        if len(username) < 3:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(Fore.RED + f'{timestamp} 账号长度太短，长度至少要大于等于3位！' + Fore.RESET)
        else:
            if len(password) < 6:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.RED + f'{timestamp} 密码长度太短，长度至少要大于等于6位！' + Fore.RESET)
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.RED + f'{timestamp} 用户不存在，创建用户' + Fore.RESET)

                await sio.emit('insert', [{'username':username, 'password':password, 'vip_time':time.time()}])

    await asyncio.sleep(2)
    await sio.disconnect()

@sio.on('get_user_info')
async def get_user_info(data):
    global username
    global password
    global vip_time
    global balance

    temp_set_normal_p = 0.1
    temp_set_fan_club_p = 0.2
    temp_set_real_object_p = 0.01
    temp_min_normal_p = 0.1
    temp_min_fan_club_p = 0.3
    temp_min_real_object_p = 0.01
    temp_max_normal_p = 0.1
    temp_max_fan_club_p = 0.5
    temp_max_real_object_p = 0.01

    temp_want_bag_type1 = 1
    temp_want_bag_type2 = 1
    temp_want_bag_type3 = 0

    temp_set_risk_income = -5
    temp_set_risk_today_income = -5
    temp_set_get_reward_p = 0.1
    temp_set_raise_fan_club_bag_p = 0.1

    temp_open_account2_browser = 0
    temp_need_change_account = 0
    temp_set_change_account_running_time = 999999
    temp_set_change_account_income = -10
    temp_set_change_account_today_income = 100
    temp_set_change_account_bag_num1 = 200
    temp_set_change_account_bag_num3 = 15

    temp_want_red_packet = 0
    temp_want_popularity_ticket_red_packet = 0
    temp_set_max_count_popularity_ticket_red_packet = 0

    p = f'{relative_path}/user.json'

    # 在免费VIP时段，设置临时VIP
    pattern = r'([0-9]+):([0-9]+):([0-9]+)'

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S")
    t_h = -1
    t_m = -1
    t_s = -1
    if re.search(pattern, timestamp):
        t_h = int(re.search(pattern, timestamp).group(1))
        t_m = int(re.search(pattern, timestamp).group(2))
        t_s = int(re.search(pattern, timestamp).group(3))

    # 免费VIP时段 20:00:00-22:00:00
    if 72000 <= t_h * 3600 + t_m * 60 + t_s <= 79200:
        is_temporary_VIP[0] = 1

    # 默认设置
    try:
        temp_idx = -1
        for idx, o in enumerate(original_data):
            if o.get('功能') == '符合条件时自动暂停程序':
                temp_idx = idx

        pause_automatically[0] = original_data[temp_idx].get('是否启用该功能')
        set_pause_running_time[0] = original_data[temp_idx].get('程序运行时间≥')
        set_pause_today_income[0] = original_data[temp_idx].get('今日单账号钻石收益≤')
        set_pause_today_income2[0] = original_data[temp_idx].get('今日单账号钻石收益≥')
        set_pause_bag_num1[0] = original_data[temp_idx].get('今日单账号参与福袋数≥')
        set_pause_bag_num3[0] = original_data[temp_idx].get('今日单账号已中福袋数≥')
    except Exception as e:
        pass

    if pause_automatically[0] is None:
        pause_automatically[0] = 0
    if set_pause_running_time[0] is None:
        set_pause_running_time[0] = 999999
    if set_pause_today_income[0] is None:
        set_pause_today_income[0] = -10
    if set_pause_today_income2[0] is None:
        set_pause_today_income2[0] = 100
    if set_pause_bag_num1[0] is None:
        set_pause_bag_num1[0] = 200
    if set_pause_bag_num3[0] is None:
        set_pause_bag_num3[0] = 15

    pass

    temp_password = data[0].get('password')
    vip_time = data[0].get('vip_time')

    if password != temp_password:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.RED + f'{timestamp} 密码错误！' + Fore.RESET)
    else:
        login_status[0] = 1

        remaining_time = vip_time - time.time()
        d = int(remaining_time / 60 / 60 / 24)
        h = int((remaining_time - d * 60 * 60 * 24) / 60 / 60)
        m = int((remaining_time - d * 60 * 60 * 24 - h * 60 * 60) / 60)
        s = int(remaining_time - d * 60 * 60 * 24 - h * 60 * 60 - m * 60)

        if remaining_time > 0:
            is_VIP[0] = 1
            # 是VIP的话要取消临时VIP！
            is_temporary_VIP[0] = 0

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                Fore.GREEN + f'{timestamp} 当前用户的VIP剩余时间:{d}天{h}小时{m}分钟{s}秒' + Fore.RESET)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                Fore.GREEN + f'{timestamp} VIP功能已启用' + Fore.RESET)
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(Fore.RED + f'{timestamp} 当前用户的VIP已过期！' + Fore.RESET)

    if is_VIP[0] == 0 and is_temporary_VIP[0] == 0:
        try:
            temp_idx = -1
            for idx, o in enumerate(original_data):
                if o.get('功能') == '设置福袋筛选概率':
                    temp_idx = idx

            temp_set_normal_p = original_data[temp_idx].get('普通福袋的基础筛选概率')
            temp_set_fan_club_p = original_data[temp_idx].get('粉丝团福袋的基础筛选概率')
            temp_set_real_object_p = original_data[temp_idx].get('实物福袋的基础筛选概率')
            temp_min_normal_p = original_data[temp_idx].get('普通福袋的最低筛选概率')
            temp_min_fan_club_p = original_data[temp_idx].get('粉丝团福袋的最低筛选概率')
            temp_min_real_object_p = original_data[temp_idx].get('实物福袋的最低筛选概率')
            temp_max_normal_p = original_data[temp_idx].get('普通福袋的最高筛选概率')
            temp_max_fan_club_p = original_data[temp_idx].get('粉丝团福袋的最高筛选概率')
            temp_max_real_object_p = original_data[temp_idx].get('实物福袋的最高筛选概率')
        except Exception as e:
            pass

        if temp_set_normal_p is None:
            temp_set_normal_p = 0.1
        if temp_set_fan_club_p is None:
            temp_set_fan_club_p = 0.2
        if temp_set_real_object_p is None:
            temp_set_real_object_p = 0.01
        if temp_min_normal_p is None:
            temp_min_normal_p = 0.1
        if temp_min_fan_club_p is None:
            temp_min_fan_club_p = 0.3
        if temp_min_real_object_p is None:
            temp_min_real_object_p = 0.01
        if temp_max_normal_p is None:
            temp_max_normal_p = 0.1
        if temp_max_fan_club_p is None:
            temp_max_fan_club_p = 0.5
        if temp_max_real_object_p is None:
            temp_max_real_object_p[0] = 0.01

        try:
            temp_idx = -1
            for idx, o in enumerate(original_data):
                if o.get('功能') == '筛选福袋类型':
                    temp_idx = idx

            temp_want_bag_type1 = original_data[temp_idx].get('普通福袋')
            temp_want_bag_type2 = original_data[temp_idx].get('粉丝团福袋')
            temp_want_bag_type3 = original_data[temp_idx].get('实物福袋')
        except Exception as e:
            pass

        if temp_want_bag_type1 is None:
            temp_want_bag_type1 = 1
        if temp_want_bag_type2 is None:
            temp_want_bag_type2 = 1
        if temp_want_bag_type3 is None:
            temp_want_bag_type3 = 0

        try:
            temp_idx = -1
            for idx, o in enumerate(original_data):
                if o.get('功能') == '自定义被风控判断规则':
                    temp_idx = idx

            temp_set_risk_income = original_data[temp_idx].get('本次钻石收益≤')
            temp_set_risk_today_income = original_data[temp_idx].get('今日单账号钻石收益≤')
            temp_set_get_reward_p = original_data[temp_idx].get('预期的抽中福袋的概率')
            temp_set_raise_fan_club_bag_p = original_data[temp_idx].get('提高的粉丝团福袋的筛选概率')
        except Exception as e:
            pass

        if temp_set_risk_income is None:
            temp_set_risk_income = -5
        if temp_set_risk_today_income is None:
            temp_set_risk_today_income = -5
        if temp_set_get_reward_p is None:
            temp_set_get_reward_p = 0.1
        if temp_set_raise_fan_club_bag_p is None:
            temp_set_raise_fan_club_bag_p[0] = 0.1

        try:
            temp_idx = -1
            for idx, o in enumerate(original_data):
                if o.get('功能') == '符合条件时切换账号':
                    temp_idx = idx

            temp_open_account2_browser = original_data[temp_idx].get('启动程序时打开要切换的账号所在的浏览器')
            temp_need_change_account = original_data[temp_idx].get('本次需要切换账号')
            temp_set_change_account_running_time = original_data[temp_idx].get('程序运行时间≥')
            temp_set_change_account_income = original_data[temp_idx].get('今日单账号钻石收益≤')
            temp_set_change_account_today_income = original_data[temp_idx].get('今日单账号钻石收益≥')
            temp_set_change_account_bag_num1 = original_data[temp_idx].get('今日单账号参与福袋数≥')
            temp_set_change_account_bag_num3 = original_data[temp_idx].get('今日单账号已中福袋数≥')
        except Exception as e:
            pass

        if temp_open_account2_browser is None:
            temp_open_account2_browser = 0
        if temp_need_change_account is None:
            temp_need_change_account = 0
        if temp_set_change_account_running_time is None:
            temp_set_change_account_running_time = 999999
        if temp_set_change_account_income is None:
            temp_set_change_account_income = -10
        if temp_set_change_account_today_income is None:
            temp_set_change_account_today_income = 100
        if temp_set_change_account_bag_num1 is None:
            temp_set_change_account_bag_num1 = 200
        if temp_set_change_account_bag_num3 is None:
            temp_set_change_account_bag_num3 = 15

        try:
            temp_idx = -1
            for idx, o in enumerate(original_data):
                if o.get('功能') == '自动抢红包':
                    temp_idx = idx

            temp_want_red_packet = original_data[temp_idx].get('是否启用该功能')
            temp_want_popularity_ticket_red_packet = original_data[temp_idx].get('是否参与人气红包')
            temp_set_max_count_popularity_ticket_red_packet = original_data[temp_idx].get(
                '参与人气红包的次数上限')
        except Exception as e:
            pass

        if temp_want_red_packet is None:
            temp_want_red_packet = 0
        if temp_want_popularity_ticket_red_packet is None:
            temp_want_popularity_ticket_red_packet = 0
        if temp_set_max_count_popularity_ticket_red_packet is None:
            temp_set_max_count_popularity_ticket_red_packet = 0

    if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
        if is_temporary_VIP[0] == 1 and is_VIP[0] == 0:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                Fore.GREEN + f'{timestamp} 当前在免费VIP时段，VIP功能已临时启用:)' + Fore.RESET)

        try:
            try:
                temp_idx = -1
                for idx, o in enumerate(original_data):
                    if o.get('功能') == '设置福袋筛选概率':
                        temp_idx = idx

                set_normal_p[0] = original_data[temp_idx].get('普通福袋的基础筛选概率')
                set_fan_club_p[0] = original_data[temp_idx].get('粉丝团福袋的基础筛选概率')
                set_real_object_p[0] = original_data[temp_idx].get('实物福袋的基础筛选概率')
                min_normal_p[0] = original_data[temp_idx].get('普通福袋的最低筛选概率')
                min_fan_club_p[0] = original_data[temp_idx].get('粉丝团福袋的最低筛选概率')
                min_real_object_p[0] = original_data[temp_idx].get('实物福袋的最低筛选概率')
                max_normal_p[0] = original_data[temp_idx].get('普通福袋的最高筛选概率')
                max_fan_club_p[0] = original_data[temp_idx].get('粉丝团福袋的最高筛选概率')
                max_real_object_p[0] = original_data[temp_idx].get('实物福袋的最高筛选概率')
            except Exception as e:
                pass

            if set_normal_p[0] is None:
                set_normal_p[0] = 0.1
            if set_fan_club_p[0] is None:
                set_fan_club_p[0] = 0.2
            if set_real_object_p[0] is None:
                set_real_object_p[0] = 0.01
            if min_normal_p[0] is None:
                min_normal_p[0] = 0.1
            if min_fan_club_p[0] is None:
                min_fan_club_p[0] = 0.3
            if min_real_object_p[0] is None:
                min_real_object_p[0] = 0.01
            if max_normal_p[0] is None:
                max_normal_p[0] = 0.1
            if max_fan_club_p[0] is None:
                max_fan_club_p[0] = 0.5
            if max_real_object_p[0] is None:
                max_real_object_p[0] = 0.01

            try:
                temp_idx = -1
                for idx, o in enumerate(original_data):
                    if o.get('功能') == '筛选福袋类型':
                        temp_idx = idx

                want_bag_type1[0] = original_data[temp_idx].get('普通福袋')
                want_bag_type2[0] = original_data[temp_idx].get('粉丝团福袋')
                want_bag_type3[0] = original_data[temp_idx].get('实物福袋')
            except Exception as e:
                pass

            if want_bag_type1[0] is None:
                want_bag_type1[0] = 1
            if want_bag_type2[0] is None:
                want_bag_type2[0] = 1
            if want_bag_type3[0] is None:
                want_bag_type3[0] = 0

            try:
                temp_idx = -1
                for idx, o in enumerate(original_data):
                    if o.get('功能') == '自定义被风控判断规则':
                        temp_idx = idx

                set_risk_income[0] = original_data[temp_idx].get('本次钻石收益≤')
                set_risk_today_income[0] = original_data[temp_idx].get('今日单账号钻石收益≤')
                set_get_reward_p[0] = original_data[temp_idx].get('预期的抽中福袋的概率')
                set_raise_fan_club_bag_p[0] = original_data[temp_idx].get('提高的粉丝团福袋的筛选概率')
            except Exception as e:
                pass

            if set_risk_income[0] is None:
                set_risk_income[0] = -5
            if set_risk_today_income[0] is None:
                set_risk_today_income[0] = -5
            if set_get_reward_p[0] is None:
                set_get_reward_p[0] = 0.1
            if set_raise_fan_club_bag_p[0] is None:
                set_raise_fan_club_bag_p[0] = 0.1

            try:
                temp_idx = -1
                for idx, o in enumerate(original_data):
                    if o.get('功能') == '符合条件时切换账号':
                        temp_idx = idx

                open_account2_browser[0] = original_data[temp_idx].get('启动程序时打开要切换的账号所在的浏览器')
                need_change_account[0] = original_data[temp_idx].get('本次需要切换账号')
                set_change_account_running_time[0] = original_data[temp_idx].get('程序运行时间≥')
                set_change_account_today_income[0] = original_data[temp_idx].get('今日单账号钻石收益≤')
                set_change_account_today_income2[0] = original_data[temp_idx].get('今日单账号钻石收益≥')
                set_change_account_bag_num1[0] = original_data[temp_idx].get('今日单账号参与福袋数≥')
                set_change_account_bag_num3[0] = original_data[temp_idx].get('今日单账号已中福袋数≥')
            except Exception as e:
                pass

            if open_account2_browser[0] is None:
                open_account2_browser[0] = 0
            if need_change_account[0] is None:
                need_change_account[0] = 0
            if set_change_account_running_time[0] is None:
                set_change_account_running_time[0] = 999999
            if set_change_account_today_income[0] is None:
                set_change_account_today_income[0] = -10
            if set_change_account_today_income2[0] is None:
                set_change_account_today_income2[0] = 100
            if set_change_account_bag_num1[0] is None:
                set_change_account_bag_num1[0] = 200
            if set_change_account_bag_num3[0] is None:
                set_change_account_bag_num3[0] = 15

            try:
                temp_idx = -1
                for idx, o in enumerate(original_data):
                    if o.get('功能') == '自动抢红包':
                        temp_idx = idx

                want_red_packet[0] = original_data[temp_idx].get('是否启用该功能')
                want_popularity_ticket_red_packet[0] = original_data[temp_idx].get('是否参与人气红包')
                set_max_count_popularity_ticket_red_packet[0] = original_data[temp_idx].get(
                    '参与人气红包的次数上限')
            except Exception as e:
                pass

            if want_red_packet[0] is None:
                want_red_packet[0] = 0
            if want_popularity_ticket_red_packet[0] is None:
                want_popularity_ticket_red_packet[0] = 0
            if set_max_count_popularity_ticket_red_packet[0] is None:
                set_max_count_popularity_ticket_red_packet[0] = 0

        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(Fore.RED + f'{timestamp} 读取user.json文件失败，尝试自动更新user.json文件' + Fore.RESET)

    if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
        data = [{
            'username': username,
            'password': password
        },
            {
                '功能': '符合条件时自动暂停程序',
                '限制': '无限制',
                '是否启用该功能': pause_automatically[0],
                '程序运行时间≥': set_pause_running_time[0],
                '今日单账号钻石收益≤': set_pause_today_income[0],
                '今日单账号钻石收益≥': set_pause_today_income2[0],
                '今日单账号参与福袋数≥': set_pause_bag_num1[0],
                '今日单账号已中福袋数≥': set_pause_bag_num3[0]
            },
            {
                '功能': '设置福袋筛选概率',
                '限制': '仅VIP用户可用',
                '普通福袋的基础筛选概率': set_normal_p[0],
                '粉丝团福袋的基础筛选概率': set_fan_club_p[0],
                '实物福袋的基础筛选概率': set_real_object_p[0],
                '普通福袋的最低筛选概率': min_normal_p[0],
                '粉丝团福袋的最低筛选概率': min_fan_club_p[0],
                '实物福袋的最低筛选概率': min_real_object_p[0],
                '普通福袋的最高筛选概率': max_normal_p[0],
                '粉丝团福袋的最高筛选概率': max_fan_club_p[0],
                '实物福袋的最高筛选概率': max_real_object_p[0]
            },
            {
                '功能': '筛选福袋类型',
                '限制': '仅VIP用户可用',
                '普通福袋': want_bag_type1[0],
                '粉丝团福袋': want_bag_type2[0],
                '实物福袋': want_bag_type3[0]
            },
            {
                '功能': '自定义被风控判断规则',
                '限制': '仅VIP用户可用',
                '本次钻石收益≤': set_risk_income[0],
                '今日单账号钻石收益≤': set_risk_today_income[0],
                '预期的抽中福袋的概率': set_get_reward_p[0],
                '提高的粉丝团福袋的筛选概率': set_raise_fan_club_bag_p[0]
            },
            {
                '功能': '符合条件时切换账号',
                '限制': '仅VIP用户可用',
                '启动程序时打开要切换的账号所在的浏览器': open_account2_browser[0],
                '本次需要切换账号': need_change_account[0],
                '程序运行时间≥': set_change_account_running_time[0],
                '今日单账号钻石收益≤': set_change_account_today_income[0],
                '今日单账号钻石收益≥': set_change_account_today_income2[0],
                '今日单账号参与福袋数≥': set_change_account_bag_num1[0],
                '今日单账号已中福袋数≥': set_change_account_bag_num3[0]
            },
            {
                '功能': '自动抢红包',
                '限制': '仅VIP用户可用',
                '是否启用该功能': want_red_packet[0],
                '是否参与人气红包': want_popularity_ticket_red_packet[0],
                '参与人气红包的次数上限': set_max_count_popularity_ticket_red_packet[0]
            }]

        # 打开文件，以写入模式创建文件对象
        with open(f'{relative_path}/user.json', 'w', encoding='utf-8') as file:
            # indent=1 每个层级缩进1个空格
            file.write(json.dumps(data, indent=1, ensure_ascii=False))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.GREEN + f'{timestamp} user.json文件格式已更新到最新版:D' + Fore.RESET)

        await asyncio.sleep(2)
        await sio.disconnect()

        return original_data
    if is_VIP[0] == 0 and is_temporary_VIP[0] == 0:
        data = [{
            'username': username,
            'password': password
        },
            {
                '功能': '符合条件时自动暂停程序',
                '限制': '无限制',
                '是否启用该功能': pause_automatically[0],
                '程序运行时间≥': set_pause_running_time[0],
                '今日单账号钻石收益≤': set_pause_today_income[0],
                '今日单账号钻石收益≥': set_pause_today_income2[0],
                '今日单账号参与福袋数≥': set_pause_bag_num1[0],
                '今日单账号已中福袋数≥': set_pause_bag_num3[0]
            },
            {
                '功能': '设置福袋筛选概率',
                '限制': '仅VIP用户可用',
                '普通福袋的基础筛选概率': temp_set_normal_p,
                '粉丝团福袋的基础筛选概率': temp_set_fan_club_p,
                '实物福袋的基础筛选概率': temp_set_real_object_p,
                '普通福袋的最低筛选概率': temp_min_normal_p,
                '粉丝团福袋的最低筛选概率': temp_min_fan_club_p,
                '实物福袋的最低筛选概率': temp_min_real_object_p,
                '普通福袋的最高筛选概率': temp_max_normal_p,
                '粉丝团福袋的最高筛选概率': temp_max_fan_club_p,
                '实物福袋的最高筛选概率': temp_max_real_object_p
            },
            {
                '功能': '筛选福袋类型',
                '限制': '仅VIP用户可用',
                '普通福袋': temp_want_bag_type1,
                '粉丝团福袋': temp_want_bag_type2,
                '实物福袋': temp_want_bag_type3
            },
            {
                '功能': '自定义被风控判断规则',
                '限制': '仅VIP用户可用',
                '本次钻石收益≤': temp_set_risk_income,
                '今日单账号钻石收益≤': temp_set_risk_today_income,
                '预期的抽中福袋的概率': temp_set_get_reward_p,
                '提高的粉丝团福袋的筛选概率': temp_set_raise_fan_club_bag_p
            },
            {
                '功能': '符合条件时切换账号',
                '限制': '仅VIP用户可用',
                '启动程序时打开要切换的账号所在的浏览器': temp_open_account2_browser,
                '本次需要切换账号': temp_need_change_account,
                '程序运行时间≥': temp_set_change_account_running_time,
                '今日单账号钻石收益≤': temp_set_change_account_income,
                '今日单账号钻石收益≥': temp_set_change_account_today_income,
                '今日单账号参与福袋数≥': temp_set_change_account_bag_num1,
                '今日单账号已中福袋数≥': temp_set_change_account_bag_num3
            },
            {
                '功能': '自动抢红包',
                '限制': '仅VIP用户可用',
                '是否启用该功能': temp_want_red_packet,
                '是否参与人气红包': temp_want_popularity_ticket_red_packet,
                '参与人气红包的次数上限': temp_set_max_count_popularity_ticket_red_packet
            }]

        # 打开文件，以写入模式创建文件对象
        with open(f'{relative_path}/user.json', 'w', encoding='utf-8') as file:
            # indent=1 每个层级缩进1个空格
            file.write(json.dumps(data, indent=1, ensure_ascii=False))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.GREEN + f'{timestamp} user.json文件格式已更新到最新版:D' + Fore.RESET)

        await asyncio.sleep(2)
        await sio.disconnect()

        return original_data

# 初始化colorama
init()

p = f'{relative_path}/user.json'
if os.path.exists(p):
    original_data = read_json_file(p)

    username = ''
    password = ''

    try:
        username = original_data[0].get('username')
        password = original_data[0].get('password')
    except Exception as e:
        pass

    if username is None:
        username = 'default'
    if password is None:
        password = '123456'
else:
    login_status[0] = 1

    temp_data = [{
        'username': 'default',
        'password': '123456'
    },
        {
            '功能': '符合条件时自动暂停程序',
            '限制': '无限制',
            '是否启用该功能': 0,
            '程序运行时间≥': 999999,
            '今日单账号钻石收益≤': -10,
            '今日单账号钻石收益≥': 100,
            '今日单账号参与福袋数≥': 200,
            '今日单账号已中福袋数≥': 15
        },
        {
            '功能': '设置福袋筛选概率',
            '限制': '仅VIP用户可用',
            '普通福袋的基础筛选概率': 0.1,
            '粉丝团福袋的基础筛选概率': 0.2,
            '实物福袋的基础筛选概率': 0.01,
            '普通福袋的最低筛选概率': 0.1,
            '粉丝团福袋的最低筛选概率': 0.3,
            '实物福袋的最低筛选概率': 0.01,
            '普通福袋的最高筛选概率': 0.1,
            '粉丝团福袋的最高筛选概率': 0.5,
            '实物福袋的最高筛选概率': 0.01
        },
        {
            '功能': '筛选福袋类型',
            '限制': '仅VIP用户可用',
            '普通福袋': 1,
            '粉丝团福袋': 1,
            '实物福袋': 0
        },
        {
            '功能': '自定义被风控判断规则',
            '限制': '仅VIP用户可用',
            '本次钻石收益≤': -5,
            '今日单账号钻石收益≤': -5,
            '预期的抽中福袋的概率': 0.1,
            '提高的粉丝团福袋的筛选概率': 0.1
        },
        {
            '功能': '符合条件时切换账号',
            '限制': '仅VIP用户可用',
            '启动程序时打开要切换的账号所在的浏览器': 0,
            '本次需要切换账号': 0,
            '程序运行时间≥': 999999,
            '今日单账号钻石收益≤': -10,
            '今日单账号钻石收益≥': 100,
            '今日单账号参与福袋数≥': 200,
            '今日单账号已中福袋数≥': 15
        },
        {
            '功能': '自动抢红包',
            '限制': '仅VIP用户可用',
            '是否启用该功能': 0,
            '是否参与人气红包': 0,
            '参与人气红包的次数上限': 0
        }]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(Fore.YELLOW + f'{timestamp} 当前为默认免费账号' + Fore.RESET)

    # 打开文件，以写入模式创建文件对象
    with open(f'{relative_path}/user.json', 'w', encoding='utf-8') as file:
        # indent=1 每个层级缩进1个空格
        file.write(json.dumps(temp_data, indent=1, ensure_ascii=False))

try:
    asyncio.run(main())
except Exception as e:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(Fore.RED + f'{timestamp} 连接服务器失败！{e}' + Fore.RESET)
