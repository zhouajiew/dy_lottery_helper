import asyncio
import random
import re
import time
import math
import threading
from asyncio import timeout

import requests

from datetime import datetime

from patchright.sync_api import sync_playwright
from patchright.async_api import async_playwright

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.by import By

from selenium.webdriver.edge.service import Service

from selenium.webdriver.support import expected_conditions as EC  #跟WebDriverWait连在一起用
from selenium.webdriver.support.wait import WebDriverWait      #跟EC连在一起用  等页面加载

from colorama import Fore, init

# from pynput.mouse import Listener

from record import *
from api import *
from global_v import *
from user import *
from windows_api import *
# from window import *

# from fake_useragent import UserAgent

# pip install fake-useragent --upgrade

lock = threading.Lock()

browser = None
page = None

# 当前账号index
current_account_index = 0

# 所有符合条件的网页
eligible_websites = []

# 遇到意外异常的网页
error_websites = {}

website_titles = {}

record_time_count = 0

# 获取到的最大的直播间数量
max_live_num = 0
# 重复获取到同一直播间数量的次数
max_live_num_count = 0

# 当前要处理的直播间序号
live_index = 0

# 初始钻石数量
initial_diamond = 0
# 后续记录的钻石数量
final_diamond = 0

# 参与的福袋数
bag_num1 = 0
bag_num1_dic = {}

# 未中奖的福袋数
bag_num2 = 0
# 中奖的福袋数
bag_num3 = 0
bag_num3_dic = {}
# 实物福袋的中奖数
real_object_num_dic = {}

# 风控判断
bad_luck = False
extremely_bad_luck = False

# 普通福袋筛选概率
normal_p = 0.1
base_normal_p = normal_p
# 粉丝团福袋筛选概率
fan_club_p = 0.2
base_fan_club_p = fan_club_p
# 实物福袋筛选概率
real_object_p = 0.01
base_real_object_p = real_object_p

# 是否正在等待福袋开奖
# is_waiting = False

# 参与了，等待开奖结束
wait_until_draw_end = False

# 是否正在关闭标签页
is_closing = False

close_sign = False

# 寻找的次数
total_search_count = 0

# 无法关闭的窗口句柄
error_windows = {}

# 临时保存的room_id
dic_room_id = {}

# 防止重复开启'tasks_while_staying_in_live'线程
working_threads = {}

# 防止重复开启'delay_check'线程
working_threads2 = {}

# 需要更新room_id的record3中的直播间
need_update_lives = []

# 查看的福袋的序号
bag_index = 0

# 是否参与了红包
have_participated_red_packet = False

# 两次进入有发红包的直播间的间隔>5分钟
enter_red_packet_live_time = 0
last_enter_red_packet_live_time = 0

# task_while_staying_in_live_with_playwright
staying_in_live_task = None
live_room_changed = False
staying_in_live_task_record_url = ''

# check_control_driver2_thread检测到了异常
check_control_driver2_error = False

start_time2 = time.time()
end_time2 = start_time2
# 要重启的浏览器保存文件目录
save_edge_dir = ''
save_google_chrome_dir = ''

gift_value_dic = {'小心心':'1钻', '大啤酒':'2钻', '棒棒糖':'9钻', '小皇冠':'10钻', '撩一下':'19钻'}
gift_value_dic2 = {'小心心':1, '大啤酒':2, '棒棒糖':9, '小皇冠':10, '撩一下':19}

count_from_search_thread = 0

count_from_control_driver2_thread = 0

# 本小时已参与过该直播间的人气红包的后续不用再消耗1钻石来参与该直播间的人气红包
already_buy_popularity_ticket = []

# 中奖了需要进行消息推送
need_to_receive_notification = False
# 通知内容
notification_title = ''

def send_wechat(title, content):
    token = pushplus_token[0]  # 后台提供的token
    template = 'html'  # template模板类型有'html'、'txt'，'json'等

    url = f'https://www.pushplus.plus/send?token={token}&title={title}&content={content}&template={template}'

    try:
        r = requests.get(url=url)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.RED + f'{timestamp} 消息推送失败！' + Fore.RESET)
    # print(r.text)

async def main(temp_dir):
    global count_from_control_driver2_thread
    global browser

    global wait_until_draw_end
    global have_participated_red_packet
    global working_threads2

    global check_control_driver2_error

    global save_google_chrome_dir

    async with async_playwright() as p:
        # run many at the same time

        control_driver2_task = asyncio.create_task(control_driver2_with_playwright(p, temp_dir))

        last_count = 0
        t1 = time.time()
        t2 = t1

        # 检测control_driver2_with_playwright是否出现了异常
        while True:
            if pause[0] == 0:
                # 如果经过了60s后control_driver2的count值未发生变化，说明control_driver2_with_playwright线程出现了异常
                if t2 - t1 > 60:
                    timestamp = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.RED + f'{timestamp} control_driver2线程出现异常，重启浏览器中' + Fore.RESET)

                    # check_control_driver2_error = True

                    # 重启浏览器时重置这些变量
                    wait_until_draw_end = False
                    have_participated_red_packet = False
                    working_threads2 = {}

                    await browser.close()

                    break

                if last_count != count_from_control_driver2_thread:
                    t1 = t2
                    last_count = count_from_control_driver2_thread
                else:
                    t2 = time.time()

            # time.sleep(1)
            await asyncio.sleep(1)

        control_driver2_task.cancel()

    await main(save_google_chrome_dir)

# 通过键盘事件以隐藏/恢复浏览器的线程
def check_keyboard_event():
    record_press1_count = 0
    while True:
        try:
            time.sleep(0.1)

            temp_press1_count = return_press1_count()

            if record_press1_count != temp_press1_count :
                record_press1_count = temp_press1_count

                if check_website_status[0] == 1:
                    driver.set_window_position(driver_px, driver_py)
                    if want_red_packet[0] == 0 or (is_VIP[0] == 0 and is_temporary_VIP[0] == 0):
                        driver2.set_window_position(driver2_px, driver2_py)

                    tp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(Fore.YELLOW + f'{tp} 已显示浏览器' + Fore.RESET)
                else:
                    driver.set_window_position(-9999, -9999)
                    if want_red_packet[0] == 0 or (is_VIP[0] == 0 and is_temporary_VIP[0] == 0):
                        driver2.set_window_position(-9999, -9999)

                    tp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(Fore.YELLOW + f'{tp} 已隐藏浏览器' + Fore.RESET)
        except Exception as e:
            pass

# Edge浏览器目前不需要这个判断
def check_control_driver2_thread_status1():
    global count_from_control_driver2_thread
    global browser
    global driver2

    last_count = 0
    t1 = time.time()
    t2 = t1

    while True:
        if pause[0] == 0:
            # 如果经过了60s后control_driver2的count值未发生变化，说明search线程出现了异常
            if t2 - t1 > 60:
                timestamp = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S")
                print(
                    Fore.RED + f'{timestamp} control_driver2线程出现异常，重启浏览器中' + Fore.RESET)

                driver2.quit()
                change_account(save_edge_dir)

            if last_count != count_from_control_driver2_thread:
                t1 = t2
                last_count = count_from_control_driver2_thread
            else:
                t2 = time.time()

        time.sleep(1)

# 检查search线程运行情况
def check_search_thread_status():
    global count_from_search_thread

    last_count = 0
    t1 = time.time()
    t2 = t1

    while True:
        if pause[0] == 0:
            # 如果经过了60s后search的count值未发生变化，说明search线程出现了异常
            if t2 - t1 > 60:
                timestamp = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S")
                print(
                    Fore.RED + f'{timestamp} search线程出现异常，请重启程序！' + Fore.RESET)

            if last_count != count_from_search_thread:
                t1 = t2
                last_count = count_from_search_thread
            else:
                t2 = time.time()

        time.sleep(1)


# 获取msToken和a_bogus
def get_important_data():
  # 隐藏的代码块

# 模拟滚动页面
def scroll_website():
    target_rd_y = random.randint(500, 800)

    move_s = 0
    move_t = 0.02

    temp_e = driver.find_element(By.ID, "_douyin_live_scroll_container_")

    while move_s < target_rd_y:
        time.sleep(move_t)

        move_v = random.randint(40, 60)

        move_s += move_v

        try:
            scroll_origin = ScrollOrigin.from_element(temp_e)
            ActionChains(driver) \
                .scroll_from_origin(scroll_origin, 0, move_v) \
                .perform()
        except Exception as e:
            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            print(
                Fore.RED + f'{timestamp} 滚动页面失败！' + Fore.RESET)

            break

# 用api的形式寻找有福袋的直播间
def get_live_by_api():
  # 隐藏的代码块

# 从record2、3中寻找
def search_from_records():
    global need_update_lives

    while True:
        time.sleep(1)

        if pause[0] == 0:
            temp_lives = []

            temp_live_info2 = []

            temp_live_info3 = []

            # 记录的时间差越小，分数越高(>2小时的分数为0)
            time_score = 0
            # 记录的中奖概率越大，分数越高
            record_p_score = 0

            total_score = 0

            for l in live_info3:
                pattern = r'([0-9]+):([0-9]+):[0-9]+'
                if re.search(pattern, l['record_time']):
                    h = re.search(pattern, l['record_time']).group(1)
                    m = re.search(pattern, l['record_time']).group(2)

                    i_h = int(h)
                    i_m = int(m)

                    # 只查询最近8小时(28800秒)内有直播过的直播间
                    current_time = datetime.timestamp(datetime.now())
                    date_format = "%Y-%m-%d %H:%M:%S"

                    pattern = r'([0-9]+):([0-9]+):([0-9]+)'

                    timestamp = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S")
                    t_h = -1
                    t_m = -1
                    # t_s = -1
                    if re.search(pattern, timestamp):
                        t_h = int(re.search(pattern, timestamp).group(1))
                        t_m = int(re.search(pattern, timestamp).group(2))
                        # t_s = int(re.search(pattern, timestamp).group(3))

                    temp_time = l['record_time']
                    temp_time = datetime.strptime(temp_time, date_format)
                    temp_time = temp_time.timestamp()

                    time_difference = current_time - temp_time

                    if time_difference <= 28800:
                        if time_difference > 7200:
                            time_score = 0
                        else:
                            time_score = 0.25 * ((7200 - time_difference) / 7200)

                        record_p_score = 0.75 * l['record_p']
                        l['record_p_score'] = record_p_score
                        l['time_score'] = time_score
                        l['total_score'] = record_p_score + time_score

                        # 比较当前时间和某直播间发福袋的时间，记录合理时间差之间的直播间(默认视为固定时间段开播)
                        if -90 <= (t_h * 60 + t_m) - (i_h * 60 + i_m) <= 180:
                            # 如果是VIP，要对live_info3进行筛选
                            if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
                                temp_live_info3.append(l)
                            else:
                                l['from'] = 3
                                temp_lives.append(l)
                    # total_score>=0.5且距离记录时间>1小时的直播间才需要更新room_id
                    else:
                        if l.get('total_score'):
                            temp_total_score = l['total_score']

                            if temp_total_score >= 0.5:
                                # 只在相应直播间的可能开播时间段内更新room_id
                                if -90 <= (t_h * 60 + t_m) - (i_h * 60 + i_m) <= 180:
                                    # 去除anchor_id后面的字符
                                    if 'anchor_id' in l['url']:
                                        pattern = r'live.douyin.com/([0-9]+)'
                                        if re.search(pattern, l['url']):
                                            short_id = re.search(pattern, l['url']).group(1)
                                            l['url'] = f'https://live.douyin.com/{short_id}'

                                    if not l.get('update_time'):
                                        need_update_lives.append(l)
                                    else:
                                        current_time = datetime.timestamp(datetime.now())

                                        temp_time = l['update_time']
                                        temp_time = datetime.strptime(temp_time, date_format)
                                        temp_time = temp_time.timestamp()

                                        time_difference = current_time - temp_time
                                        if time_difference <= 3600:
                                            l['time_score'] = 0
                                            l['total_score'] = 0.75 * l['record_p']

                                            pattern = r'([0-9]+):([0-9]+):[0-9]+'
                                            if re.search(pattern, l['update_time']):
                                                h = re.search(pattern, l['record_time']).group(1)
                                                m = re.search(pattern, l['record_time']).group(2)

                                                i_h = int(h)
                                                i_m = int(m)

                                                pattern = r'([0-9]+):([0-9]+):([0-9]+)'
                                                timestamp = datetime.now().strftime(
                                                    "%Y-%m-%d %H:%M:%S")
                                                t_h = -1
                                                t_m = -1
                                                # t_s = -1
                                                if re.search(pattern, timestamp):
                                                    t_h = int(re.search(pattern, timestamp).group(1))
                                                    t_m = int(re.search(pattern, timestamp).group(2))
                                                    # t_s = int(re.search(pattern, timestamp).group(3))

                                                # 比较当前时间和某直播间发福袋的时间，记录合理时间差之间的直播间(默认视为固定时间段开播)
                                                if -90 <= (t_h * 60 + t_m) - (i_h * 60 + i_m) <= 180:
                                                    # 处在直播状态才放入temp_lives中
                                                    live_status = -1
                                                    if l.get('live_status'):
                                                        if l.get('live_status') == 1:
                                                            live_status = 1

                                                    if live_status:
                                                        # 如果是VIP，要对live_info3进行筛选
                                                        if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
                                                            temp_live_info3.append(l)
                                                        else:
                                                            l['from'] = 3
                                                            temp_lives.append(l)

                                        # 距离更新时间>8小时的直播间需要更新room_id
                                        else:
                                            need_update_lives.append(l)

            # print(f'need_update_lives:{need_update_lives}')

            temp_live_info3.sort(key=lambda x: x["total_score"], reverse=True)

            if len(temp_live_info3) > 75:
                fliter_temp_live_info3 = temp_live_info3[:75]

                for ft in fliter_temp_live_info3:
                    ft['from'] = 3
                    temp_lives.append(ft)
            else:
                for tl in temp_live_info3:
                    tl['from'] = 3
                    temp_lives.append(tl)

            for l in live_info2:
                pattern = r'([0-9]+):([0-9]+):[0-9]+'
                if re.search(pattern, l['record_time']):
                    h = re.search(pattern, l['record_time']).group(1)
                    m = re.search(pattern, l['record_time']).group(2)

                    i_h = int(h)
                    i_m = int(m)

                    # 只查询最近8小时(28800秒)内有直播过的直播间
                    current_time = datetime.timestamp(datetime.now())
                    date_format = "%Y-%m-%d %H:%M:%S"

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

                    temp_time = l['record_time']
                    temp_time = datetime.strptime(temp_time, date_format)
                    temp_time = temp_time.timestamp()

                    time_difference = current_time - temp_time

                    if time_difference <= 28800:
                        # 当前时间在00:00:00-01:00:00 or 19:00:00-23:59:59
                        right_time = False
                        if 0 <= t_h * 60 * 60 + t_m * 60 + t_s <= 3600:
                            right_time = True
                        if 68400 <= t_h * 60 * 60 + t_m * 60 + t_s <= 86399:
                            right_time = True

                        if right_time:
                            # 在20:15~23:45点之间发过福袋的直播间
                            if 1215 <= i_h * 60 + i_m <= 1425:
                                # 如果是VIP，要对live_info2进行筛选
                                if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
                                    temp_live_info2.append(l)
                                else:
                                    temp_lives.append(l)

                        # 顺便比较当前时间和某直播间发福袋的时间，记录合理时间差之间的直播间(默认视为固定时间段开播)
                        if -30 <= (t_h * 60 + t_m) - (i_h * 60 + i_m) <= 60:
                            if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
                                temp_live_info2.append(l)
                            else:
                                l['from'] = 2
                                temp_lives.append(l)

            if len(temp_live_info2) > 25:
                random_temp_live_info2 = random.choices(temp_live_info2, k=25)

                for r in random_temp_live_info2:
                    r['from'] = 2
                    temp_lives.append(r)
            else:
                for tl in temp_live_info2:
                    tl['from'] = 2
                    temp_lives.append(tl)

            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")

            if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
                print(
                    Fore.YELLOW + f'{timestamp} 当前为VIP用户，用高级算法进行筛选后，共找到了{len(temp_lives)}个优质的直播间' + Fore.RESET)
            else:
                print(
                    Fore.YELLOW + f'{timestamp} 当前非VIP用户，用简单算法进行筛选后，共找到了{len(temp_lives)}个比较合适的直播间' + Fore.RESET)

            for idx, tl in enumerate(temp_lives):
                if pause[0] == 1:
                    break

                rd_time = random.uniform(3, 5)
                time.sleep(rd_time)

                temp_url = tl['url']
                temp_title = tl['title']
                temp_room_id = str(tl['room_id'])

                pattern = r'([\s\S]*抖音直播间) - 抖音直播'
                if re.search(pattern, temp_title):
                    temp_title = re.search(pattern, temp_title).group(1)

                timestamp = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S")
                print(
                    f'{timestamp} 正在从record*(total:{len(temp_lives)})中搜索直播间(from record{tl['from']})，序号:{idx}，title:{temp_title}，bag_index:{bag_index}')

                temp_bag_info = get_bag_info_by_api(temp_room_id, bag_index)

                if temp_bag_info:
                    if temp_bag_info.get('p'):
                        p = temp_bag_info.get('p')
                        prize_count = temp_bag_info.get('prize_count')
                        lucky_count = temp_bag_info.get('lucky_count')
                        count_down = temp_bag_info.get('count_down')
                        r_time = temp_bag_info.get('r_time')

                        bag_type = temp_bag_info.get('type')
                        prize_name = temp_bag_info.get('name')

                        if '粉丝团' in bag_type and want_bag_type2[0] == 1:
                            if float(p) > fan_club_p + math.log(float(r_time), 3) / 100:
                                already_exist = False

                                for ew in eligible_websites:
                                    if temp_url in ew['url']:
                                        already_exist = True
                                        ew['time'] = r_time
                                        ew['record_time'] = time.time()
                                        ew['p'] = p

                                        break

                                if not already_exist:
                                    eligible_websites.append(
                                        {'url': temp_url,
                                         'room_id': temp_room_id,
                                         'title': temp_title,
                                         'time': r_time,
                                         'record_time': time.time(),
                                         'stay': 0,
                                         'p': p,
                                         'type': bag_type,
                                         'lucky_count':lucky_count,
                                         'prize_count': prize_count,
                                         'count_down': count_down})

                                    timestamp = datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S")
                                    print(
                                        f'{timestamp} 该福袋(粉丝团)中奖概率为{p * 100}%，符合条件，加入等待池中，等待池现有{len(eligible_websites)}个符合条件的网页')

                        if '普通' in bag_type and want_bag_type1[0] == 1:
                            if float(p) > normal_p + math.log(float(r_time), 3) / 100:
                                already_exist = False

                                for ew in eligible_websites:
                                    if temp_url in ew['url']:
                                        already_exist = True
                                        ew['time'] = r_time
                                        ew['record_time'] = time.time()
                                        ew['p'] = p

                                        break

                                if not already_exist:
                                    eligible_websites.append(
                                        {'url': temp_url,
                                         'room_id': temp_room_id,
                                         'title': temp_title,
                                         'time': r_time,
                                         'record_time': time.time(),
                                         'stay': 0,
                                         'p': p,
                                         'type': bag_type,
                                         'lucky_count':lucky_count,
                                         'prize_count': prize_count,
                                         'count_down': count_down})

                                    timestamp = datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S")
                                    print(
                                        f'{timestamp} 该福袋(发送评论)中奖概率为{p * 100}%，符合条件，加入等待池中，等待池现有{len(eligible_websites)}个符合条件的网页')

                        if '实物' in bag_type and want_bag_type3[0] == 1:
                            if float(p) > real_object_p:
                                already_exist = False

                                for ew in eligible_websites:
                                    if temp_url in ew['url']:
                                        already_exist = True
                                        ew['time'] = r_time
                                        ew['record_time'] = time.time()
                                        ew['p'] = p

                                        break

                                if not already_exist:
                                    eligible_websites.append(
                                        {'url': temp_url,
                                         'room_id': temp_room_id,
                                         'title': temp_title,
                                         'time': r_time,
                                         'record_time': time.time(),
                                         'stay': 0,
                                         'p': p,
                                         'type': bag_type,
                                         'name': prize_name,
                                         'lucky_count': lucky_count,
                                         'prize_count': prize_count,
                                         'count_down': count_down})

                                    timestamp = datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S")
                                    print(
                                        f'{timestamp} 该福袋(实物)中奖概率为{p * 100}%，符合条件，加入等待池中，等待池现有{len(eligible_websites)}个符合条件的网页')

# 获取临时的room_id，注意:room_id会在主播下次开播后变更！
def get_room_id():
  # 隐藏的代码块

def get_bag_info_by_api(room_id, index):
  # 隐藏的代码块

def close_windows():
    global is_closing
    global error_windows

    time.sleep(1)

    for i in range(len(driver.window_handles)):
        j = 1
        while j < len(driver.window_handles):
            driver.switch_to.window(driver.window_handles[j])
            try:
                if driver.window_handles[j] not in error_windows:
                    if driver.current_url != 'https://live.douyin.com/categorynew/4_103':
                        time.sleep(1)
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f'{timestamp} 正在关闭标签页{driver.title}')

                        driver.close()
                        time.sleep(1)

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f'{timestamp} 已关闭当前标签页，当前标签页数:{len(driver.window_handles)}')
                        break
            except Exception as e:
                error_windows[driver.window_handles[j]] = 1

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.RED + f'{timestamp} 该标签页无法被关闭，已被记录！' + Fore.RESET)

            j += 1

    is_closing = False

    driver.switch_to.window(driver.window_handles[0])

async def task_while_staying_in_live_with_playwright(record_url, key_element_type):
  # 隐藏的代码块

def tasks_while_staying_in_live(record_url, key_element_type):
  # 隐藏的代码块

# 参与红包
async def participate_red_packet(first_time):
  # 隐藏的代码块
  
async def delay_check_with_playwright(key_element_type):
  # 隐藏的代码块

def delay_check(key_element_type):
  # 隐藏的代码块

# 切换账号
def change_account(temp_dir):
    global js
    global driver2
    global edge_options2

    global wait_until_draw_end
    global working_threads2

    # 切换账号时重置这些变量
    wait_until_draw_end = False
    working_threads2 = {}

    edge_options2 = webdriver.EdgeOptions()
    edge_options2.add_argument(f'--user-data-dir={temp_dir}')

    # 屏蔽inforbar
    edge_options2.add_experimental_option('useAutomationExtension', False)
    edge_options2.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])

    temp_rd_w = random.randint(-10, 10)
    temp_rd_h = random.randint(-10, 10)

    driver2 = webdriver.Edge(options=edge_options2)
    driver2.set_window_size(900 + temp_rd_w, 700 + temp_rd_h)
    driver2.set_window_position(950, 200)
    driver2.set_page_load_timeout(60)

    driver2.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": js
    })

    time.sleep(1)

    for i in range(len(driver2.window_handles)):
        j = 1
        while j < len(driver2.window_handles):
            driver2.switch_to.window(driver2.window_handles[j])
            try:
                if driver2.window_handles[j] not in error_windows:
                    time.sleep(1)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f'{timestamp} 正在关闭标签页{driver2.title}')

                    driver2.close()
                    time.sleep(1)

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f'{timestamp} 已关闭当前标签页，当前标签页数:{len(driver2.window_handles)}')
                    break
            except Exception as e:
                error_windows[driver2.window_handles[j]] = 1

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.RED + f'{timestamp} 该标签页无法被关闭，已被记录！' + Fore.RESET)

            j += 1

    driver2.switch_to.window(driver2.window_handles[0])

    try:
        driver2.get('https://www.douyin.com/jingxuan')
    except Exception as e:
        driver2.refresh()

async def control_driver2_with_playwright(p, temp_dir):
    global browser
    global page

    global start_time
    global current_account_index
    global record_time_count
    global max_live_num
    global max_live_num_count
    global live_index
    global eligible_websites
    global website_titles
    global initial_diamond
    global final_diamond
    global is_closing
    global close_sign
    global wait_until_draw_end
    global bad_luck
    global extremely_bad_luck
    global normal_p
    global fan_club_p
    global real_object_p
    global base_normal_p
    global base_fan_club_p
    global base_real_object_p
    global working_threads2

    global have_participated_red_packet
    global enter_red_packet_live_time
    global last_enter_red_packet_live_time

    global start_time2
    global end_time2
    global save_google_chrome_dir

    global count_from_control_driver2_thread
    global check_control_driver2_error

    global already_buy_popularity_ticket

    global need_to_receive_notification
    global notification_title
    global notification_detailed_content

    global staying_in_live_task
    global live_room_changed

    control_driver2_restart_browser = False
    control_driver2_change_account = False

    browser = await p.chromium.launch_persistent_context(
        user_data_dir=temp_dir,
        channel="chrome",
        headless=False,
        no_viewport=True,
        # do NOT add custom browser headers or user_agent
    )

    page = await browser.new_page()

    # page.goto("https://bot.sannysoft.com/")
    # page.goto("https://www.browserscan.net/bot-detection")

    try:
        await page.goto("https://www.douyin.com/jingxuan", timeout=20000)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.RED + f'{timestamp} 打开网页超时！' + Fore.RESET)

    # await page.pause()

    while True:
        # 消息推送
        if pushplus_token[0] != '':
            if need_to_receive_notification:
                need_to_receive_notification = False

                send_wechat(notification_title, notification_detailed_content)

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.GREEN + f'{timestamp} 已推送中奖通知至微信:D' + Fore.RESET)

        # 去除符合条件的已参与人气红包的直播间
        temp_index_list = []
        current_time = datetime.now().strftime("%H:%M:%S")
        for idx, a in enumerate(already_buy_popularity_ticket):
            # 比较小时位的差异，小时位不一样就是需要再次花1钻参与人气红包了
            if a.get('record_time'):
                temp_record_time = a['record_time']
                pattern = r'([0-9])+:([0-9]+):([0-9]+)'
                temp_h = -1
                temp_h2 = -1
                if re.search(pattern, current_time):
                    temp_h = re.search(pattern, current_time).group(1)

                if re.search(pattern, temp_record_time):
                    temp_h2 = re.search(pattern, temp_record_time).group(1)

                if temp_h != -1 and temp_h2 != -1:
                    if temp_h2 != temp_h:
                        temp_index_list.append(idx)

        if len(temp_index_list) > 0:
            temp_already_buy_popularity_ticket = []
            for idx, a in enumerate(already_buy_popularity_ticket):
                if idx not in temp_index_list:
                    temp_already_buy_popularity_ticket.append(a)

            already_buy_popularity_ticket = temp_already_buy_popularity_ticket[:]

            # 打开文件，以写入模式创建文件对象
            with open(f'{relative_path}/already_buy_popularity_ticket.json', 'w',
                      encoding='utf-8') as file:
                # indent=1 每个层级缩进1个空格
                file.write(json.dumps(already_buy_popularity_ticket, indent=1, ensure_ascii=False))

        if is_temporary_VIP[0] == 1:
            # 在免费VIP时段，设置临时VIP
            pattern = r'([0-9]+):([0-9]+):([0-9]+)'

            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            temp_h = -1
            temp_m = -1
            temp_s = -1
            if re.search(pattern, timestamp):
                temp_h = int(re.search(pattern, timestamp).group(1))
                temp_m = int(re.search(pattern, timestamp).group(2))
                temp_s = int(re.search(pattern, timestamp).group(3))

            # 非免费VIP时段，还原至初始功能
            if temp_h * 3600 + temp_m * 60 < 72000 or temp_h * 3600 + temp_m * 60 + temp_s > 79200:
                reset_temporary_vip()

                normal_p = set_normal_p[0]
                base_normal_p = normal_p
                fan_club_p = set_fan_club_p[0]
                base_fan_club_p = fan_club_p
                real_object_p = set_real_object_p[0]
                base_real_object_p = real_object_p

                # 动态调整粉丝团福袋的筛选概率
                timestamp2 = datetime.now().strftime("%Y-%m-%d")
                temp_today_bag_num2 = bag_num1_dic[timestamp2] - bag_num3_dic[timestamp2]

                if temp_today_bag_num2 > 0:
                    fan_club_p = base_fan_club_p + math.log(temp_today_bag_num2, 2) / 100 + bag_num3_dic[
                        timestamp2] / 100

                if normal_p < min_normal_p[0]:
                    normal_p = min_normal_p[0]
                if normal_p > max_normal_p[0]:
                    normal_p = max_normal_p[0]

                if fan_club_p < min_fan_club_p[0]:
                    fan_club_p = min_fan_club_p[0]
                if fan_club_p > max_fan_club_p[0]:
                    fan_club_p = max_fan_club_p[0]

                if real_object_p < min_real_object_p[0]:
                    real_object_p = min_real_object_p[0]
                if real_object_p > max_real_object_p[0]:
                    real_object_p = max_real_object_p[0]

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.YELLOW + f'{timestamp} 普通福袋筛选概率已变更为:{normal_p}' + Fore.RESET)

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.YELLOW + f'{timestamp} 粉丝团福袋筛选概率已变更为:{fan_club_p}' + Fore.RESET)

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.YELLOW + f'{timestamp} 实物福袋筛选概率已变更为:{real_object_p}' + Fore.RESET)

        if pause[0] == 0:
            '''
            if check_control_driver2_error:
                break
            '''

            end_time = time.time()
            temp_time = end_time - start_time
            temp_time = round(temp_time, 2)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(Fore.YELLOW + f'{timestamp} 当前程序运行时间:{temp_time}s' + Fore.RESET)
            '''
            if end_time - start_time > record_time_count * 10:
                record_time_count += 1
                '''

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                Fore.GREEN + f'{timestamp} 本次已参与福袋数:' + Fore.LIGHTBLUE_EX + f'{bag_num1}' + Fore.GREEN + '，未中奖福袋数:' + Fore.RED + f'{bag_num2}' + Fore.GREEN + '，中奖福袋数:' + Fore.YELLOW + f'{bag_num3}' + Fore.RESET)

            income = final_diamond - initial_diamond

            if income >= 0:
                if today_income[0] >= 0:
                    print(
                        Fore.YELLOW + f'{timestamp} 本次钻石收益:+{income}，今日钻石收益:+{today_income[0]}，今日中过的福袋的总收益:+{total_bag_num3_value[0]}，今日中过的钻石红包的总收益:+{total_red_packet_num3_value[0]}, 今日中过的礼物红包的总收益:+{total_red_packet_gift_num3_value[0]}' + Fore.RESET)
                else:
                    print(
                        Fore.YELLOW + f'{timestamp} 本次钻石收益:+{income}，' + Fore.LIGHTBLUE_EX + f'今日钻石收益:{today_income[0]}，' + Fore.YELLOW + f'今日中过的福袋的总收益:+{total_bag_num3_value[0]}，今日中过的红包的总收益:+{total_red_packet_num3_value[0]}, 今日中过的礼物红包的总收益:+{total_red_packet_gift_num3_value[0]}' + Fore.RESET)
            else:
                if today_income[0] >= 0:
                    print(
                        Fore.LIGHTBLUE_EX + f'{timestamp} 本次钻石收益:{income}，' + Fore.YELLOW + f'今日钻石收益:+{today_income[0]}，今日中过的福袋的总收益:+{total_bag_num3_value[0]}，今日中过的钻石红包的总收益:+{total_red_packet_num3_value[0]}, 今日中过的礼物红包的总收益:+{total_red_packet_gift_num3_value[0]}' + Fore.RESET)
                else:
                    print(
                        Fore.LIGHTBLUE_EX + f'{timestamp} 本次钻石收益:{income}，今日钻石收益:{today_income[0]}，' + Fore.YELLOW + f'今日中过的福袋的总收益:+{total_bag_num3_value[0]}，今日中过的钻石红包的总收益:+{total_red_packet_num3_value[0]}, 今日中过的礼物红包的总收益:+{total_red_packet_gift_num3_value[0]}' + Fore.RESET)

            if bad_luck:
                # 可能被风控的几种情况
                at_risk = False
                # 本次钻石收益 <= set_risk_income[0] or 今日钻石收益 <= set_risk_today_income[0]
                if income <= income <= set_risk_income[0] or today_income[0] <= set_risk_today_income[0]:
                    at_risk = True
                # 中奖福袋数为0的情况下，未中奖福袋数 > 1 / set_get_reward_p[0]
                if bag_num3 == 0 and bag_num2 > 1 / set_get_reward_p[0]:
                    at_risk = True
                # 中奖福袋数不为0的情况下，中奖福袋数 / 本次已参与福袋数 < set_get_reward_p[0]
                if bag_num3 != 0 and bag_num3 / bag_num1 < set_get_reward_p[0]:
                    at_risk = True

                if not at_risk:
                    bad_luck = False

                    base_fan_club_p -= set_raise_fan_club_bag_p[0]
                    fan_club_p -= set_raise_fan_club_bag_p[0]

                    normal_p = base_normal_p

                    # time.sleep(0.25)
                    await asyncio.sleep(0.25)

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.GREEN + f'{timestamp} 当前暂时回归正常状态，将降低抢粉丝团福袋的筛选概率，同时提高普通福袋的筛选概率' + Fore.RESET)
                    print(Fore.YELLOW + f'{timestamp} 粉丝团福袋的筛选概率已调整至{fan_club_p}' + Fore.RESET)
                    print(Fore.YELLOW + f'{timestamp} 普通福袋的筛选概率已调整至{normal_p}' + Fore.RESET)

            if not bad_luck:
                # 可能被风控的几种情况
                at_risk = False
                # 本次钻石收益 <= set_risk_income[0] or 今日钻石收益 <= set_risk_today_income[0]
                if income <= income <= set_risk_income[0] or today_income[0] <= set_risk_today_income[0]:
                    at_risk = True
                # 中奖福袋数为0的情况下，未中奖福袋数 > 1 / set_get_reward_p[0]
                if bag_num3 == 0 and bag_num2 > 1 / set_get_reward_p[0]:
                    at_risk = True
                # 中奖福袋数不为0的情况下，中奖福袋数 / 本次已参与福袋数 < set_get_reward_p[0]
                if bag_num3 != 0 and bag_num3 / bag_num1 < set_get_reward_p[0]:
                    at_risk = True

                if at_risk:
                    bad_luck = True

                    base_fan_club_p += set_raise_fan_club_bag_p[0]
                    fan_club_p += set_raise_fan_club_bag_p[0]

                    normal_p = base_normal_p * 0.8

                    # time.sleep(0.25)
                    await asyncio.sleep(0.25)

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.RED + f'{timestamp} 当前可能处于被风控状态，将提高抢粉丝团福袋的筛选概率，同时降低普通福袋的筛选概率' + Fore.RESET)
                    print(Fore.YELLOW + f'{timestamp} 粉丝团福袋的筛选概率已调整至{fan_club_p}' + Fore.RESET)
                    print(Fore.YELLOW + f'{timestamp} 普通福袋的筛选概率已调整至{normal_p}' + Fore.RESET)

            timestamp2 = datetime.now().strftime("%Y-%m-%d")

            # 处于非常严重的被风控状态，警告
            if bag_num1_dic.get(timestamp2):
                temp_p = bag_num3_dic[timestamp2] / bag_num1_dic[timestamp2]
                if temp_p > 0:
                    if temp_p < 0.03:
                        extremely_bad_luck = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.RED + f'{timestamp} 当前可能处于非常严重的被风控状态，不建议继续进行抢福袋任务！' + Fore.RESET)
                    else:
                        extremely_bad_luck = False

            # 满足条件时暂停程序
            if pause_automatically[0] == 1:
                right_condition = False
                if temp_time >= set_pause_running_time[0]:
                    right_condition = True

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 程序运行时间{temp_time}s≥指定值{set_pause_running_time[0]}s，自动暂停程序' + Fore.RESET)

                if income <= set_pause_income[0]:
                    right_condition = True

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 本次钻石收益{income}≤指定值{set_pause_income[0]}，自动暂停程序' + Fore.RESET)

                if today_income[0] >= set_pause_today_income[0]:
                    right_condition = True

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 今日钻石收益{today_income[0]}≥指定值{set_pause_today_income[0]}，自动暂停程序' + Fore.RESET)

                timestamp2 = datetime.now().strftime("%Y-%m-%d")
                if bag_num1_dic.get(timestamp2):
                    if bag_num1_dic[timestamp2] >= set_pause_bag_num1[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 今日参与福袋数{bag_num1_dic[timestamp2]}≥指定值{set_pause_bag_num1[0]}，自动暂停程序' + Fore.RESET)

                if bag_num3_dic.get(timestamp2):
                    if bag_num3_dic[timestamp2] >= set_pause_bag_num3[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 今日已中福袋数{bag_num3_dic[timestamp2]}≥指定值{set_pause_bag_num3[0]}，自动暂停程序' + Fore.RESET)

                if right_condition:
                    pause[0] = 1

                    # 自动暂停时重置今日数据
                    start_time = time.time()
                    initial_diamond = 0
                    final_diamond = 0
                    today_income[0] = 0
                    bag_num1_dic[timestamp2] = 0
                    bag_num3_dic[timestamp2] = 0
                    real_object_num_dic[timestamp2] = 0
                    popularity_ticket_num_dic[timestamp2] = 0

            end_time2 = time.time()
            if end_time2 - start_time2 > 7200:
                # 确保当前没有参与福袋or红包的情况下再关闭浏览器
                if len(working_threads2) == 0 and not have_participated_red_packet:
                    start_time2 = time.time()

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 程序运行时间太长，自动重启浏览器' + Fore.RESET)

                    control_driver2_restart_browser = True

                    break

            # 满足条件时切换账号
            if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
                if need_change_account[0] == 1:
                    right_condition = False
                    if temp_time >= set_change_account_running_time[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 程序运行时间{temp_time}s≥指定值{set_change_account_running_time[0]}s，切换账号' + Fore.RESET)

                    if income <= set_change_account_income[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 本次钻石收益{income}≤指定值{set_change_account_income[0]}，切换账号' + Fore.RESET)

                    if today_income[0] >= set_change_account_today_income[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 今日钻石收益{today_income[0]}≥指定值{set_change_account_today_income[0]}，切换账号' + Fore.RESET)

                    timestamp2 = datetime.now().strftime("%Y-%m-%d")
                    if bag_num1_dic.get(timestamp2):
                        if bag_num1_dic[timestamp2] >= set_change_account_bag_num1[0]:
                            right_condition = True

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.YELLOW + f'{timestamp} 今日参与福袋数{bag_num1_dic[timestamp2]}≥指定值{set_change_account_bag_num1[0]}，切换账号' + Fore.RESET)

                    if bag_num3_dic.get(timestamp2):
                        if bag_num3_dic[timestamp2] >= set_change_account_bag_num3[0]:
                            right_condition = True

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.YELLOW + f'{timestamp} 今日已中福袋数{bag_num3_dic[timestamp2]}≥指定值{set_change_account_bag_num3[0]}，切换账号' + Fore.RESET)

                    # 启动程序时不打开要切换的账号所在的浏览器时才切换
                    if right_condition and open_account2_browser[0] == 0:
                        control_driver2_change_account = True

                        break

            error_occur = False

            with lock:
                # 清除所有剩余时间小于0/p_time >= 300的网页
                temp_websites = []
                for e in eligible_websites:
                    temp_right_condition = False
                    if not e.get('red_packet'):
                        if e['time'] > 0:
                            temp_right_condition = True

                    if e.get('red_packet'):
                        if e['time'] > 0:
                            if e.get('p_time'):
                                p_time = e['p_time']
                                if p_time < 300:
                                    temp_right_condition = True
                            else:
                                e['p_time'] = time.time() - e['record_time']
                                temp_right_condition = True

                    if temp_right_condition:
                        temp_websites.append(e)

                eligible_websites = temp_websites[:]

                # 有重复的room_id的只保留一个
                delete_index = {}
                temp_eligible_websites = eligible_websites[:]
                for idx1, e1 in enumerate(temp_eligible_websites):
                    if e1.get('room_id'):
                        temp_room_id1 = e1['room_id']
                        index_list = []
                        for idx2, e2 in enumerate(temp_eligible_websites):
                            if e2.get('room_id'):
                                temp_room_id2 = e2['room_id']
                                if temp_room_id2 == temp_room_id1:
                                    index_list.append(idx2)

                        if len(index_list) > 1:
                            temp_index_list = index_list[1:]
                            for t in temp_index_list:
                                delete_index[t] = 1

                temp_websites = []
                temp_eligible_websites = eligible_websites[:]
                for idx, te in enumerate(temp_eligible_websites):
                    if idx not in delete_index:
                        temp_websites.append(te)

                eligible_websites = temp_websites[:]

                # 更新所有符合条件网页福袋的剩余时间
                for idx, e in enumerate(eligible_websites):
                    if not e.get('red_packet'):
                        temp_type = e.get('type')
                        if temp_type:
                            if '实物' in temp_type:
                                e_time = e.get('record_time')
                                p_time = time.time() - e_time
                                r_time = e.get('time') - p_time
                                e['time'] = r_time
                                e['record_time'] = time.time()

                                # 剩余时间长的实物福袋排最前面，因为是最新检测到有发实物福袋的
                                # 如果设置了实物福袋，优先参与实物福袋
                                e['estimate_p'] = 1 - p_time / 1000000
                            else:
                                e_time = e.get('record_time')
                                p_time = time.time() - e_time
                                r_time = e.get('time') - p_time
                                e['time'] = r_time
                                e['record_time'] = time.time()

                                bn = e.get('lucky_count')

                                count_down = 600
                                if e.get('count_down'):
                                    count_down = e.get('count_down')

                                if not e.get('p2'):
                                    e['p2'] = -1

                                # 概率发生变化，重新计算最终概率
                                if e['p'] != e['p2']:
                                    # 预估的最终概率
                                    base = math.pow(e['p'] / bn, 1 / (count_down - r_time + 1))
                                    e['estimate_p'] = bn / base * math.pow(base, count_down)

                                e['p2'] = e['p']
                        # 此为非使用api找到的直播间
                        else:
                            e_time = e.get('record_time')
                            p_time = time.time() - e_time
                            r_time = e.get('time') - p_time
                            e['time'] = r_time
                            e['record_time'] = time.time()

                            bn = e.get('lucky_count')

                            count_down = 600
                            if e.get('count_down'):
                                count_down = e.get('count_down')

                            if not e.get('p2'):
                                e['p2'] = -1

                            # 概率发生变化，重新计算最终概率
                            if e['p'] != e['p2']:
                                # 预估的最终概率
                                base = math.pow(e['p'] / bn, 1 / (count_down - r_time + 1))
                                e['estimate_p'] = bn / base * math.pow(base, count_down)

                            e['p2'] = e['p']
                    else:
                        e_time = e.get('record_time')
                        p_time = time.time() - e_time
                        e['p_time'] = p_time

                        # 剩余时间长的红包排最前面，因为是最新检测到有红包的
                        e['estimate_p'] = 0.01 - p_time / 1000000

            original_stay_in_live_index = -1

            if len(eligible_websites) > 0:
                # 预测中奖概率最大的排前面
                with lock:
                    eligible_websites.sort(key=lambda x: x["estimate_p"], reverse=True)

                for idx, ew in enumerate(eligible_websites):
                    if ew['stay'] == 1:
                        original_stay_in_live_index = idx

                sub_title = eligible_websites[0]['title']
                pattern = r'([\s\S]*抖音直播间) - 抖音直播'
                if re.search(pattern, sub_title):
                    sub_title = re.search(pattern, sub_title).group(1)

                if not eligible_websites[0].get('red_packet'):
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 中奖概率最大({sub_title})的福袋的中奖预测概率为{round(eligible_websites[0]['estimate_p'] * 100, 5)}%，剩余时间为{round(eligible_websites[0]['time'], 2)}s' + Fore.RESET)
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 直播间({sub_title})正在发放红包' + Fore.RESET)

                allowed_to_change_live = False

                # 只有当新的预测概率-原先的预测概率>0.15时才跳转，避免频繁跳转
                if len(eligible_websites) >= 2:
                    if original_stay_in_live_index != -1:
                        if original_stay_in_live_index != 0:
                            if eligible_websites[0]["estimate_p"] - eligible_websites[original_stay_in_live_index][
                                "estimate_p"] > 0.15:
                                allowed_to_change_live = True

                if allowed_to_change_live:
                    # 在非等待开奖以及等待红包结束的情况下，如果中奖概率最大的直播间发生了变更，直接跳转到新的中奖概率最大的直播间
                    if original_stay_in_live_index != -1 and not wait_until_draw_end and not have_participated_red_packet:
                        if original_stay_in_live_index != 0:
                            eligible_websites[original_stay_in_live_index]['stay'] = 0

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.YELLOW + f'{timestamp} 预测福袋中奖概率最大的直播间已变更，将跳转至该直播间' + Fore.RESET)

            if not is_closing:
                try:
                    current_url = page.url
                except Exception as e:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(Fore.RED + f'{timestamp} driver2获取当前url失败！' + Fore.RESET)

                    error_occur = True

            c1 = False

            if not is_closing:
                if not error_occur and len(eligible_websites) > 0:
                    pattern = r'live.douyin.com/([0-9]+)'

                    temp_short_id = ''
                    # temp_url = driver2.current_url
                    temp_url = page.url

                    if re.search(pattern, temp_url):
                        temp_short_id = re.search(pattern, temp_url).group(1)

                    # 有要stay的直播间但是因为某些原因没进入(在别的直播间or不在直播间)，重新尝试进入
                    if eligible_websites[0]['stay'] == 1 and (
                            temp_short_id not in eligible_websites[0]['url'] or temp_short_id == ''):
                        c1 = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            f'{timestamp} 意外退出指定直播间，尝试重新进入该直播间')

                        try:
                            await page.goto(eligible_websites[0]['url'], timeout=20000)
                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(Fore.RED + f'{timestamp} 打开网页超时！' + Fore.RESET)

                    # 这里不再等待红包结束，保证至少参与一个红包就行
                    if 30 <= eligible_websites[0]['time'] < 300 and eligible_websites[0][
                        'stay'] == 0 and len(working_threads2) == 0:
                        try:
                            in_live = False
                            pattern = r'live.douyin.com/[0-9]+'
                            # if re.search(pattern, driver2.current_url)
                            temp_page_url = page.url
                            if re.search(pattern, temp_page_url):
                                in_live = True

                            # 如果不位于直播间，直接前往指定直播间
                            if not in_live:
                                if not eligible_websites[0].get('red_packet'):
                                    c1 = True

                                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    print(
                                        f'{timestamp} 当前不位于直播间，检测到有福袋剩余时间<5分钟的直播间，切换至指定直播间')

                                    # 剩余时间到5分钟以内时停留在该直播间，等待开奖结束
                                    eligible_websites[0]['stay'] = 1

                                    live_room_changed = True
                                    try:
                                        staying_in_live_task.cancel()

                                        if staying_in_live_task_record_url in working_threads:
                                            del working_threads[staying_in_live_task_record_url]

                                        have_participated_red_packet = False

                                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        print(Fore.YELLOW + f'{timestamp} 已切换直播间，取消task_while_staying_in_live_with_playwright任务' + Fore.RESET)
                                    except Exception as e:
                                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        print(Fore.RED + f'{timestamp} 取消task_while_staying_in_live_with_playwright失败！' + Fore.RESET)

                                    try:
                                        # driver2.get(eligible_websites[0]['url'])
                                        await page.goto(eligible_websites[0]['url'], timeout=20000)
                                    except Exception as e:
                                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        print(Fore.RED + f'{timestamp} 打开网页超时！' + Fore.RESET)

                                        # time.sleep(2)
                                    await asyncio.sleep(2)
                                if eligible_websites[0].get('red_packet'):
                                    enter_red_packet_live_time = time.time()
                                    if enter_red_packet_live_time - last_enter_red_packet_live_time > 300:
                                        c1 = True

                                        last_enter_red_packet_live_time = enter_red_packet_live_time

                                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        print(
                                            f'{timestamp} 当前不位于直播间，检测到有发放红包的直播间，切换至指定直播间')

                                        # 剩余时间到5分钟以内时停留在该直播间，等待开奖结束
                                        eligible_websites[0]['stay'] = 1

                                        live_room_changed = True
                                        try:
                                            staying_in_live_task.cancel()

                                            if staying_in_live_task_record_url in working_threads:
                                                del working_threads[staying_in_live_task_record_url]

                                            have_participated_red_packet = False

                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            print(
                                                Fore.YELLOW + f'{timestamp} 已切换直播间，取消task_while_staying_in_live_with_playwright任务' + Fore.RESET)
                                        except Exception as e:
                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            print(
                                                Fore.RED + f'{timestamp} 取消task_while_staying_in_live_with_playwright失败！' + Fore.RESET)

                                        try:
                                            # driver2.get(eligible_websites[0]['url'])
                                            await page.goto(eligible_websites[0]['url'], timeout=20000)
                                        except Exception as e:
                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            print(Fore.RED + f'{timestamp} 打开网页超时！' + Fore.RESET)

                                            # time.sleep(2)
                                        await asyncio.sleep(2)

                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(Fore.RED + f'{timestamp} 前往指定直播间时出错！' + Fore.RESET)

                        try:
                            in_live = False
                            pattern = r'live.douyin.com/[0-9]+'
                            # if re.search(pattern, driver2.current_url):
                            temp_page_url = page.url
                            if re.search(pattern, temp_page_url):
                                in_live = True

                            if in_live:
                                if not eligible_websites[0].get('red_packet'):
                                    c1 = True

                                    # 当前正处于别的直播间，切换
                                    # if eligible_websites[0]['url'] != driver2.current_url:
                                    temp_page_url = page.url
                                    if eligible_websites[0]['url'] != temp_page_url:
                                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        print(
                                            f'{timestamp} 当前正处于别的直播间，检测到有福袋剩余时间<5分钟的直播间，切换至指定直播间')

                                        # 剩余时间到5分钟以内时停留在该直播间，等待开奖结束
                                        eligible_websites[0]['stay'] = 1

                                        live_room_changed = True
                                        try:
                                            staying_in_live_task.cancel()

                                            if staying_in_live_task_record_url in working_threads:
                                                del working_threads[staying_in_live_task_record_url]

                                            have_participated_red_packet = False

                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            print(
                                                Fore.YELLOW + f'{timestamp} 已切换直播间，取消task_while_staying_in_live_with_playwright任务' + Fore.RESET)
                                        except Exception as e:
                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            print(
                                                Fore.RED + f'{timestamp} 取消task_while_staying_in_live_with_playwright失败！' + Fore.RESET)

                                        try:
                                            # driver2.get(eligible_websites[0]['url'])
                                            await page.goto(eligible_websites[0]['url'], timeout=20000)
                                        except Exception as e:
                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            print(Fore.RED + f'{timestamp} 打开网页超时！' + Fore.RESET)
                                    # 如果正处于当前直播间，不关闭
                                    else:
                                        # 剩余时间到5分钟以内时停留在该直播间，等待开奖结束
                                        eligible_websites[0]['stay'] = 1

                                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        print(
                                            f'{timestamp} 已位于指定直播间，不执行自动关闭')
                                if eligible_websites[0].get('red_packet'):
                                    enter_red_packet_live_time = time.time()
                                    if enter_red_packet_live_time - last_enter_red_packet_live_time > 300:
                                        c1 = True

                                        last_enter_red_packet_live_time = enter_red_packet_live_time

                                        # 当前正处于别的直播间，切换
                                        # if eligible_websites[0]['url'] != driver2.current_url:
                                        temp_page_url = page.url
                                        if eligible_websites[0]['url'] != temp_page_url:
                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            print(
                                                f'{timestamp} 当前正处于别的直播间，检测到有发放红包的直播间，切换至指定直播间')

                                            # 剩余时间到5分钟以内时停留在该直播间，等待开奖结束
                                            eligible_websites[0]['stay'] = 1

                                            live_room_changed = True
                                            try:
                                                staying_in_live_task.cancel()

                                                if staying_in_live_task_record_url in working_threads:
                                                    del working_threads[staying_in_live_task_record_url]

                                                have_participated_red_packet = False

                                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                print(
                                                    Fore.YELLOW + f'{timestamp} 已切换直播间，取消task_while_staying_in_live_with_playwright任务' + Fore.RESET)
                                            except Exception as e:
                                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                print(
                                                    Fore.RED + f'{timestamp} 取消task_while_staying_in_live_with_playwright失败！' + Fore.RESET)

                                            try:
                                                # driver2.get(eligible_websites[0]['url'])
                                                await page.goto(eligible_websites[0]['url'], timeout=20000)
                                            except Exception as e:
                                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                print(Fore.RED + f'{timestamp} 打开网页超时！' + Fore.RESET)
                                        # 如果正处于当前直播间，不关闭
                                        else:
                                            # 剩余时间到5分钟以内时停留在该直播间，等待开奖结束
                                            eligible_websites[0]['stay'] = 1

                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            print(
                                                f'{timestamp} 已位于指定直播间，不执行自动关闭')
                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.RED + f'{timestamp} 切换直播间时出错！' + Fore.RESET)

            p = f"{relative_path}/eligible_websites.json"

            with open(p, 'w',
                      encoding='utf-8') as temp_f:
                # indent=1 每个层级缩进1个空格
                temp_f.write(json.dumps(eligible_websites, indent=1,
                                        ensure_ascii=False))

            if not is_closing:
                if c1 and len(working_threads2) == 0:
                    k1 = False
                    k2 = False
                    k3 = False
                    k4 = False
                    no_k = False

                    for i in range(5):
                        try:
                            if k1 or k2 or k3 or k4:
                                break

                            # time.sleep(2)
                            await asyncio.sleep(2)

                            '''
                            e1 = driver2.find_elements(By.CLASS_NAME,
                                                       'UxWMHF9c')
                            '''

                            e1 = await page.locator("[class='UxWMHF9c']").all()

                            if e1:
                                k1 = True

                            '''
                            # 在线观众数量
                            e2 = driver2.find_elements(By.CLASS_NAME,
                                                       'ClV317pr')
                            '''
                            e2 = await page.locator("[class='ClV317pr']").all()

                            if e2:
                                k2 = True

                            '''
                            e3 = driver2.find_elements(By.CLASS_NAME,
                                                       'pnW5bGAA')
                            '''

                            e3 = await page.locator("[class='pnW5bGAA']").all()
                            if e3:
                                k3 = True

                            '''
                            e4 = driver2.find_elements(By.CLASS_NAME,
                                                       'dfUO7idl')
                            '''

                            e4 = await page.locator("[class='dfUO7idl']").all()
                            if e4:
                                k4 = True

                            if not e1 and not e2 and not e3 and not e4:
                                no_k = True
                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.RED + f'{timestamp} 查找关键元素失败！' + Fore.RESET)

                            # driver2.refresh()

                    key_element_type = -1

                    if k1:
                        key_element_type = 1
                    if k2:
                        key_element_type = 2
                    if k3:
                        key_element_type = 3
                    if k4:
                        key_element_type = 4
                    if no_k:
                        key_element_type = 404

                    if 'red_packet' in eligible_websites[0]:
                        key_element_type = 888

                    unsupported_live_type = False

                    if key_element_type == 404:
                        try:
                            # 检查一下是不是不支持的直播类型
                            '''
                            if driver2.find_elements(By.CLASS_NAME,
                                                     'mjogM52Q'):
                            '''
                            if await page.locator("[class='mjogM52Q']").all():
                                unsupported_live_type = True

                        except Exception as e:
                            pass

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 获取到的key_element_type:{key_element_type}' + Fore.RESET)

                    if unsupported_live_type:
                        eligible_websites[0]['time'] = -100

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.RED + f'{timestamp} 不支持的直播间类型，直接跳过！' + Fore.RESET)
                    else:
                        try:
                            if len(working_threads2) == 0:
                                # temp_url = driver2.current_url
                                temp_url = page.url

                                '''
                                dc = threading.Thread(target=delay_check, args=(key_element_type,))
                                dc.start()
                                '''

                                asyncio.create_task(delay_check_with_playwright(key_element_type))

                                working_threads2[temp_url] = 1
                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.RED + f'{timestamp} 开启delay_check线程失败！' + Fore.RESET)

        # time.sleep(random.uniform(5, 10))
        await asyncio.sleep(random.uniform(5, 10))

        count_from_control_driver2_thread += 1

    if control_driver2_change_account:
        timestamp2 = datetime.now().strftime("%Y-%m-%d")

        # 切换账号时重置今日数据
        start_time = time.time()
        initial_diamond = 0
        final_diamond = 0
        today_income[0] = 0
        bag_num1_dic[timestamp2] = 0
        bag_num3_dic[timestamp2] = 0
        real_object_num_dic[timestamp2] = 0
        popularity_ticket_num_dic[timestamp2] = 0

        # driver2.quit()
        await browser.close()

        current_account_index += 1
        if current_account_index > 1:
            current_account_index = 0

        '''
        if current_account_index == 0:
            change_account(f'{relative_path}/user/data/dir2')
        if current_account_index == 1:
            change_account(f'{relative_path}/user/data/account2')
        '''

        # 切换账号时重置这些变量
        wait_until_draw_end = False
        have_participated_red_packet = False
        working_threads2 = {}

        if current_account_index == 0:
            save_google_chrome_dir = f'{relative_path}/user/playwright_data/dir2'
            await main(f'{relative_path}/user/playwright_data/dir2')
        if current_account_index == 1:
            save_google_chrome_dir = f'{relative_path}/user/playwright_data/account2'
            await main(f'{relative_path}/user/playwright_data/account2')

    if control_driver2_restart_browser:
        # 重启浏览器时重置这些变量
        wait_until_draw_end = False
        # have_participated_red_packet = False
        # working_threads2 = {}

        await browser.close()

        await main(save_google_chrome_dir)

def control_driver2():
    global start_time
    global current_account_index
    global record_time_count
    global max_live_num
    global max_live_num_count
    global live_index
    global eligible_websites
    global website_titles
    global initial_diamond
    global final_diamond
    global is_closing
    global close_sign
    global wait_until_draw_end
    global bad_luck
    global extremely_bad_luck
    global normal_p
    global fan_club_p
    global real_object_p
    global base_normal_p
    global base_fan_club_p
    global base_real_object_p
    global working_threads2

    global save_edge_dir

    global need_to_receive_notification
    global notification_title
    global notification_detailed_content
    
    while True:
        # 消息推送
        if pushplus_token[0] != '':
            if need_to_receive_notification:
                need_to_receive_notification = False

                send_wechat(notification_title, notification_detailed_content)

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.GREEN + f'{timestamp} 已推送中奖通知至微信:D' + Fore.RESET)
        
        if is_temporary_VIP[0] == 1:
            # 在免费VIP时段，设置临时VIP
            pattern = r'([0-9]+):([0-9]+):([0-9]+)'

            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            temp_h = -1
            temp_m = -1
            temp_s = -1
            if re.search(pattern, timestamp):
                temp_h = int(re.search(pattern, timestamp).group(1))
                temp_m = int(re.search(pattern, timestamp).group(2))
                temp_s = int(re.search(pattern, timestamp).group(3))

            # 非免费VIP时段，还原至初始功能
            if temp_h * 3600 + temp_m * 60 < 72000 or temp_h * 3600 + temp_m * 60 + temp_s > 79200:
                reset_temporary_vip()

                normal_p = set_normal_p[0]
                base_normal_p = normal_p
                fan_club_p = set_fan_club_p[0]
                base_fan_club_p = fan_club_p
                real_object_p = set_real_object_p[0]
                base_real_object_p = real_object_p

                # 动态调整粉丝团福袋的筛选概率
                timestamp2 = datetime.now().strftime("%Y-%m-%d")
                temp_today_bag_num2 = bag_num1_dic[timestamp2] - bag_num3_dic[timestamp2]

                if temp_today_bag_num2 > 0:
                    fan_club_p = base_fan_club_p + math.log(temp_today_bag_num2, 2) / 100 + bag_num3_dic[
                        timestamp2] / 100

                if normal_p < min_normal_p[0]:
                    normal_p = min_normal_p[0]
                if normal_p > max_normal_p[0]:
                    normal_p = max_normal_p[0]

                if fan_club_p < min_fan_club_p[0]:
                    fan_club_p = min_fan_club_p[0]
                if fan_club_p > max_fan_club_p[0]:
                    fan_club_p = max_fan_club_p[0]

                if real_object_p < min_real_object_p[0]:
                    real_object_p = min_real_object_p[0]
                if real_object_p > max_real_object_p[0]:
                    real_object_p = max_real_object_p[0]

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.YELLOW + f'{timestamp} 普通福袋筛选概率已变更为:{normal_p}' + Fore.RESET)

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.YELLOW + f'{timestamp} 粉丝团福袋筛选概率已变更为:{fan_club_p}' + Fore.RESET)

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.YELLOW + f'{timestamp} 实物福袋筛选概率已变更为:{real_object_p}' + Fore.RESET)

        if pause[0] == 0:
            end_time = time.time()
            temp_time = end_time - start_time
            temp_time = round(temp_time, 2)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(Fore.YELLOW + f'{timestamp} 当前程序运行时间:{temp_time}s' + Fore.RESET)
            '''
            if end_time - start_time > record_time_count * 10:
                record_time_count += 1
                '''

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                Fore.GREEN + f'{timestamp} 本次已参与福袋数:' + Fore.LIGHTBLUE_EX + f'{bag_num1}' + Fore.GREEN + '，未中奖福袋数:' + Fore.RED + f'{bag_num2}' + Fore.GREEN + '，中奖福袋数:' + Fore.YELLOW + f'{bag_num3}' + Fore.RESET)

            income = final_diamond - initial_diamond

            if income >= 0:
                if today_income[0] >= 0:
                    print(
                        Fore.YELLOW + f'{timestamp} 本次钻石收益:+{income}，今日钻石收益:+{today_income[0]}，今日中过的福袋的总收益:+{total_bag_num3_value[0]}，今日中过的红包的总收益:+{total_red_packet_num3_value[0]}' + Fore.RESET)
                else:
                    print(
                        Fore.YELLOW + f'{timestamp} 本次钻石收益:+{income}，' + Fore.LIGHTBLUE_EX + f'今日钻石收益:{today_income[0]}，' + Fore.YELLOW + f'今日中过的福袋的总收益:+{total_bag_num3_value[0]}，今日中过的红包的总收益:+{total_red_packet_num3_value[0]}' + Fore.RESET)
            else:
                if today_income[0] >= 0:
                    print(
                        Fore.LIGHTBLUE_EX + f'{timestamp} 本次钻石收益:{income}，' + Fore.YELLOW + f'今日钻石收益:+{today_income[0]}，今日中过的福袋的总收益:+{total_bag_num3_value[0]}，今日中过的红包的总收益:+{total_red_packet_num3_value[0]}' + Fore.RESET)
                else:
                    print(
                        Fore.LIGHTBLUE_EX + f'{timestamp} 本次钻石收益:{income}，今日钻石收益:{today_income[0]}，' + Fore.YELLOW + f'今日中过的福袋的总收益:+{total_bag_num3_value[0]}，今日中过的红包的总收益:+{total_red_packet_num3_value[0]}' + Fore.RESET)

            if bad_luck:
                # 可能被风控的几种情况
                at_risk = False
                # 本次钻石收益 <= set_risk_income[0] or 今日钻石收益 <= set_risk_today_income[0]
                if income <= income <= set_risk_income[0] or today_income[0] <= set_risk_today_income[0]:
                    at_risk = True
                # 中奖福袋数为0的情况下，未中奖福袋数 > 1 / set_get_reward_p[0]
                if bag_num3 == 0 and bag_num2 > 1 / set_get_reward_p[0]:
                    at_risk = True
                # 中奖福袋数不为0的情况下，中奖福袋数 / 本次已参与福袋数 < set_get_reward_p[0]
                if bag_num3 != 0 and bag_num3 / bag_num1 < set_get_reward_p[0]:
                    at_risk = True

                if not at_risk:
                    bad_luck = False

                    base_fan_club_p -= set_raise_fan_club_bag_p[0]
                    fan_club_p -= set_raise_fan_club_bag_p[0]

                    normal_p = base_normal_p

                    time.sleep(0.25)

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(Fore.GREEN + f'{timestamp} 当前暂时回归正常状态，将降低抢粉丝团福袋的筛选概率，同时提高普通福袋的筛选概率' + Fore.RESET)
                    print(Fore.YELLOW + f'{timestamp} 粉丝团福袋的筛选概率已调整至{fan_club_p}' + Fore.RESET)
                    print(Fore.YELLOW + f'{timestamp} 普通福袋的筛选概率已调整至{normal_p}' + Fore.RESET)

            if not bad_luck:
                # 可能被风控的几种情况
                at_risk = False
                # 本次钻石收益 <= set_risk_income[0] or 今日钻石收益 <= set_risk_today_income[0]
                if income <= income <= set_risk_income[0] or today_income[0] <= set_risk_today_income[0]:
                    at_risk = True
                # 中奖福袋数为0的情况下，未中奖福袋数 > 1 / set_get_reward_p[0]
                if bag_num3 == 0 and bag_num2 > 1 / set_get_reward_p[0]:
                    at_risk = True
                # 中奖福袋数不为0的情况下，中奖福袋数 / 本次已参与福袋数 < set_get_reward_p[0]
                if bag_num3 != 0 and bag_num3 / bag_num1 < set_get_reward_p[0]:
                    at_risk = True

                if at_risk:
                    bad_luck = True

                    base_fan_club_p += set_raise_fan_club_bag_p[0]
                    fan_club_p += set_raise_fan_club_bag_p[0]

                    normal_p = base_normal_p * 0.8

                    time.sleep(0.25)

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(Fore.RED + f'{timestamp} 当前可能处于被风控状态，将提高抢粉丝团福袋的筛选概率，同时降低普通福袋的筛选概率' + Fore.RESET)
                    print(Fore.YELLOW + f'{timestamp} 粉丝团福袋的筛选概率已调整至{fan_club_p}' + Fore.RESET)
                    print(Fore.YELLOW + f'{timestamp} 普通福袋的筛选概率已调整至{normal_p}' + Fore.RESET)

            timestamp2 = datetime.now().strftime("%Y-%m-%d")

            # 处于非常严重的被风控状态，警告
            if bag_num1_dic.get(timestamp2):
                temp_p = bag_num3_dic[timestamp2] / bag_num1_dic[timestamp2]
                if temp_p > 0:
                    if temp_p < 0.03:
                        extremely_bad_luck = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.RED + f'{timestamp} 当前可能处于非常严重的被风控状态，不建议继续进行抢福袋任务！' + Fore.RESET)
                    else:
                        extremely_bad_luck = False

            # 满足条件时暂停程序
            if pause_automatically[0] == 1:
                right_condition = False
                if temp_time >= set_pause_running_time[0]:
                    right_condition = True

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 程序运行时间{temp_time}s≥指定值{set_pause_running_time[0]}s，自动暂停程序' + Fore.RESET)

                if income <= set_pause_income[0]:
                    right_condition = True

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 本次钻石收益{income}≤指定值{set_pause_income[0]}，自动暂停程序' + Fore.RESET)

                if today_income[0] >= set_pause_today_income[0]:
                    right_condition = True

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 今日钻石收益{today_income[0]}≥指定值{set_pause_today_income[0]}，自动暂停程序' + Fore.RESET)

                timestamp2 = datetime.now().strftime("%Y-%m-%d")
                if bag_num1_dic.get(timestamp2):
                    if bag_num1_dic[timestamp2] >= set_pause_bag_num1[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 今日参与福袋数{bag_num1_dic[timestamp2]}≥指定值{set_pause_bag_num1[0]}，自动暂停程序' + Fore.RESET)

                if bag_num3_dic.get(timestamp2):
                    if bag_num3_dic[timestamp2] >= set_pause_bag_num3[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 今日已中福袋数{bag_num3_dic[timestamp2]}≥指定值{set_pause_bag_num3[0]}，自动暂停程序' + Fore.RESET)

                if right_condition:
                    pause[0] = 1

                    # 自动暂停时重置今日数据
                    start_time = time.time()
                    initial_diamond = 0
                    final_diamond = 0
                    today_income[0] = 0
                    bag_num1_dic[timestamp2] = 0
                    bag_num3_dic[timestamp2] = 0
                    real_object_num_dic[timestamp2] = 0

            # 满足条件时切换账号
            if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
                if need_change_account[0] == 1:
                    right_condition = False
                    if temp_time >= set_change_account_running_time[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 程序运行时间{temp_time}s≥指定值{set_change_account_running_time[0]}s，切换账号' + Fore.RESET)

                    if income <= set_change_account_income[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 本次钻石收益{income}≤指定值{set_change_account_income[0]}，切换账号' + Fore.RESET)

                    if today_income[0] >= set_change_account_today_income[0]:
                        right_condition = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.YELLOW + f'{timestamp} 今日钻石收益{today_income[0]}≥指定值{set_change_account_today_income[0]}，切换账号' + Fore.RESET)

                    timestamp2 = datetime.now().strftime("%Y-%m-%d")
                    if bag_num1_dic.get(timestamp2):
                        if bag_num1_dic[timestamp2] >= set_change_account_bag_num1[0]:
                            right_condition = True

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.YELLOW + f'{timestamp} 今日参与福袋数{bag_num1_dic[timestamp2]}≥指定值{set_change_account_bag_num1[0]}，切换账号' + Fore.RESET)

                    if bag_num3_dic.get(timestamp2):
                        if bag_num3_dic[timestamp2] >= set_change_account_bag_num3[0]:
                            right_condition = True

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.YELLOW + f'{timestamp} 今日已中福袋数{bag_num3_dic[timestamp2]}≥指定值{set_change_account_bag_num3[0]}，切换账号' + Fore.RESET)

                    # 启动程序时不打开要切换的账号所在的浏览器时才切换
                    if right_condition and open_account2_browser[0] == 0:
                        # 切换账号时重置今日数据
                        start_time = time.time()
                        initial_diamond = 0
                        final_diamond = 0
                        today_income[0] = 0
                        bag_num1_dic[timestamp2] = 0
                        bag_num3_dic[timestamp2] = 0
                        real_object_num_dic[timestamp2] = 0

                        driver2.quit()

                        current_account_index += 1
                        if current_account_index > 1:
                            current_account_index = 0

                        if current_account_index == 0:
                            save_edge_dir = f'{relative_path}/user/data/dir2'
                            change_account(f'{relative_path}/user/data/dir2')
                        if current_account_index == 1:
                            save_edge_dir = f'{relative_path}/user/data/account2'
                            change_account(f'{relative_path}/user/data/account2')

            error_occur = False

            with lock:
                # 清除所有剩余时间小于0的网页
                temp_websites = []
                for e in eligible_websites:
                    if e['time'] > 0:
                        temp_websites.append(e)

                eligible_websites = temp_websites[:]

                # 有重复的room_id的只保留一个
                delete_index = {}
                temp_eligible_websites = eligible_websites[:]
                for idx1, e1 in enumerate(temp_eligible_websites):
                    if e1.get('room_id'):
                        temp_room_id1 = e1['room_id']
                        index_list = []
                        for idx2, e2 in enumerate(temp_eligible_websites):
                            if e2.get('room_id'):
                                temp_room_id2 = e2['room_id']
                                if temp_room_id2 == temp_room_id1:
                                    index_list.append(idx2)

                        if len(index_list) > 1:
                            temp_index_list = index_list[1:]
                            for t in temp_index_list:
                                delete_index[t] = 1

                temp_websites = []
                temp_eligible_websites = eligible_websites[:]
                for idx, te in enumerate(temp_eligible_websites):
                    if idx not in delete_index:
                        temp_websites.append(te)

                # 更新所有符合条件网页福袋的剩余时间
                for idx, e in enumerate(eligible_websites):
                    temp_type = e.get('type')
                    if temp_type:
                        if '实物' in temp_type:
                            e_time = e.get('record_time')
                            p_time = time.time() - e_time
                            r_time = e.get('time') - p_time
                            e['time'] = r_time
                            e['record_time'] = time.time()

                            # 剩余时间长的实物福袋排最前面，因为是最新检测到有发实物福袋的
                            # 如果设置了实物福袋，优先参与实物福袋
                            e['estimate_p'] = 1 - p_time / 1000000
                        else:
                            e_time = e.get('record_time')
                            p_time = time.time() - e_time
                            r_time = e.get('time') - p_time
                            e['time'] = r_time
                            e['record_time'] = time.time()

                            bn = e.get('lucky_count')

                            count_down = 600
                            if e.get('count_down'):
                                count_down = e.get('count_down')

                            if not e.get('p2'):
                                e['p2'] = -1

                            # 概率发生变化，重新计算最终概率
                            if e['p'] != e['p2']:
                                # 预估的最终概率
                                base = math.pow(e['p'] / bn, 1 / (count_down - r_time + 1))
                                e['estimate_p'] = bn / base * math.pow(base, count_down)

                            e['p2'] = e['p']
                    # 此为非使用api找到的直播间
                    else:
                        e_time = e.get('record_time')
                        p_time = time.time() - e_time
                        r_time = e.get('time') - p_time
                        e['time'] = r_time
                        e['record_time'] = time.time()

                        bn = e.get('lucky_count')

                        count_down = 600
                        if e.get('count_down'):
                            count_down = e.get('count_down')

                        if not e.get('p2'):
                            e['p2'] = -1

                        # 概率发生变化，重新计算最终概率
                        if e['p'] != e['p2']:
                            # 预估的最终概率
                            base = math.pow(e['p'] / bn, 1 / (count_down - r_time + 1))
                            e['estimate_p'] = bn / base * math.pow(base, count_down)

                        e['p2'] = e['p']

            original_stay_in_live_index = -1

            if len(eligible_websites) > 0:
                # 预测中奖概率最大的排前面
                with lock:
                    eligible_websites.sort(key=lambda x: x["estimate_p"], reverse=True)

                for idx, ew in enumerate(eligible_websites):
                    if ew['stay'] == 1:
                        original_stay_in_live_index = idx

                sub_title = eligible_websites[0]['title']
                pattern = r'([\s\S]*抖音直播间) - 抖音直播'
                if re.search(pattern, sub_title):
                    sub_title = re.search(pattern, sub_title).group(1)

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(
                    Fore.YELLOW + f'{timestamp} 中奖概率最大({sub_title})的福袋的中奖预测概率为{round(eligible_websites[0]['estimate_p'] * 100, 5)}%，剩余时间为{round(eligible_websites[0]['time'], 2)}s' + Fore.RESET)

                allowed_to_change_live = False

                # 只有当新的预测概率-原先的预测概率>0.15时才跳转，避免频繁跳转
                if len(eligible_websites) >= 2:
                    if original_stay_in_live_index != -1:
                        if original_stay_in_live_index != 0:
                            if eligible_websites[0]["estimate_p"] - eligible_websites[original_stay_in_live_index]["estimate_p"] > 0.15:
                                allowed_to_change_live = True

                if allowed_to_change_live:
                    # 在非等待开奖情况下，如果中奖概率最大的直播间发生了变更，直接跳转到新的中奖概率最大的直播间
                    if original_stay_in_live_index != -1 and not wait_until_draw_end:
                        if original_stay_in_live_index != 0:
                            eligible_websites[original_stay_in_live_index]['stay'] = 0

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.YELLOW + f'{timestamp} 预测福袋中奖概率最大的直播间已变更，将跳转至该直播间' + Fore.RESET)

            '''
            if len(eligible_websites) <= 1:
                new_best_bag_sign = False

            if len(eligible_websites) == 1:
                if eligible_websites[0]['time'] >= 300 and not wait_until_draw_end:
                    is_waiting = False

            if len(eligible_websites) == 0:
                if not wait_until_draw_end:
                    is_waiting = False
            '''

            if not is_closing:
                try:
                    current_url = driver2.current_url
                except Exception as e:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(Fore.RED + f'{timestamp} driver2获取当前url失败！' + Fore.RESET)

                    error_occur = True

            c1 = False

            if not is_closing:
                if not error_occur and len(eligible_websites) > 0:
                    pattern = r'live.douyin.com/([0-9]+)'

                    temp_short_id = ''
                    temp_url = driver2.current_url

                    if re.search(pattern, temp_url):
                        temp_short_id = re.search(pattern, temp_url).group(1)

                    # 有要stay的直播间但是因为某些原因没进入(在别的直播间or不在直播间)，重新尝试进入
                    if eligible_websites[0]['stay'] == 1 and (
                            temp_short_id not in eligible_websites[0]['url'] or temp_short_id == ''):
                        c1 = True

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            f'{timestamp} 意外退出指定直播间，尝试重新进入该直播间')

                        try:
                            driver2.get(eligible_websites[0]['url'])
                            time.sleep(1)
                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(Fore.RED + f'{timestamp} 打开网页超时！' + Fore.RESET)

                    if 30 <= eligible_websites[0]['time'] < 300 and eligible_websites[0][
                        'stay'] == 0 and len(working_threads2) == 0:
                        c1 = True

                        try:
                            in_live = False
                            pattern = r'live.douyin.com/[0-9]+'
                            if re.search(pattern, driver2.current_url):
                                in_live = True

                            # 如果不位于直播间，直接前往指定直播间
                            if not in_live:
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                print(
                                    f'{timestamp} 当前不位于直播间，检测到有福袋剩余时间<5分钟的直播间，切换至指定直播间')

                                # 剩余时间到5分钟以内时停留在该直播间，等待开奖结束
                                eligible_websites[0]['stay'] = 1

                                try:
                                    driver2.get(eligible_websites[0]['url'])
                                    time.sleep(2)
                                except Exception as e:
                                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    print(Fore.RED + f'{timestamp} 打开网页超时，自动退出！' + Fore.RESET)
                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(Fore.RED + f'{timestamp} 前往指定直播间时出错！' + Fore.RESET)

                        try:
                            in_live = False
                            pattern = r'live.douyin.com/[0-9]+'
                            if re.search(pattern, driver2.current_url):
                                in_live = True

                            if in_live:
                                # 当前正处于别的直播间，切换
                                if eligible_websites[0]['url'] != driver2.current_url:
                                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    print(
                                        f'{timestamp} 当前正处于别的直播间，检测到有福袋剩余时间<5分钟的直播间，切换至指定直播间')

                                    # 剩余时间到5分钟以内时停留在该直播间，等待开奖结束
                                    eligible_websites[0]['stay'] = 1

                                    try:
                                        driver2.get(eligible_websites[0]['url'])
                                        time.sleep(1)
                                    except Exception as e:
                                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        print(Fore.RED + f'{timestamp} 打开网页超时！' + Fore.RESET)
                                # 如果正处于当前直播间，不关闭
                                else:
                                    # 剩余时间到5分钟以内时停留在该直播间，等待开奖结束
                                    eligible_websites[0]['stay'] = 1

                                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    print(
                                        f'{timestamp} 已位于指定直播间，不执行自动关闭')
                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.RED + f'{timestamp} 切换直播间时出错！' + Fore.RESET)

            p = f"{relative_path}/eligible_websites.json"

            with open(p, 'w',
                      encoding='utf-8') as temp_f:
                # indent=1 每个层级缩进1个空格
                temp_f.write(json.dumps(eligible_websites, indent=1,
                                        ensure_ascii=False))

            if not is_closing:
                if c1 and len(working_threads2) == 0:
                    k1 = False
                    k2 = False
                    k3 = False
                    k4 = False
                    no_k = False

                    for i in range(5):
                        try:
                            if k1 or k2 or k3 or k4:
                                break

                            time.sleep(2)

                            e1 = driver2.find_elements(By.CLASS_NAME,
                                                       'UxWMHF9c')
                            if e1:
                                k1 = True

                            # 在线观众数量
                            e2 = driver2.find_elements(By.CLASS_NAME,
                                                       'ClV317pr')
                            if e2:
                                k2 = True

                            e3 = driver2.find_elements(By.CLASS_NAME,
                                                       'pnW5bGAA')
                            if e3:
                                k3 = True

                            e4 = driver2.find_elements(By.CLASS_NAME,
                                                       'dfUO7idl')
                            if e4:
                                k4 = True

                            if not e1 and not e2 and not e3 and not e4:
                                no_k = True
                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.RED + f'{timestamp} 查找关键元素失败！' + Fore.RESET)

                            # driver2.refresh()

                    key_element_type = -1

                    if k1:
                        key_element_type = 1
                    if k2:
                        key_element_type = 2
                    if k3:
                        key_element_type = 3
                    if k4:
                        key_element_type = 4
                    if no_k:
                        key_element_type = 404

                    unsupported_live_type = False

                    if key_element_type == 404:
                        try:
                            # 检查一下是不是不支持的直播类型
                            if driver2.find_elements(By.CLASS_NAME,
                                                     'mjogM52Q'):
                                unsupported_live_type = True

                        except Exception as e:
                            pass

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        Fore.YELLOW + f'{timestamp} 获取到的key_element_type:{key_element_type}' + Fore.RESET)

                    if unsupported_live_type:
                        eligible_websites[0]['time'] = -100

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            Fore.RED + f'{timestamp} 不支持的直播间类型，直接跳过！' + Fore.RESET)
                    else:
                        try:
                            if len(working_threads2) == 0:
                                temp_url = driver2.current_url

                                dc = threading.Thread(target=delay_check, args=(key_element_type,))
                                dc.start()

                                working_threads2[temp_url] = 1
                        except Exception as e:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                Fore.RED + f'{timestamp} 开启delay_check线程失败！' + Fore.RESET)

        time.sleep(random.uniform(5, 10))

def search():
  # 隐藏的代码块

def restart_driver():
    global driver

    # 设置用户数据目录的路径
    user_data_dir = f'{relative_path}/user/data/dir'

    # 设置用户数据目录的路径
    user_data_dir = f'{relative_path}/user/data/dir'

    # ua = UserAgent()
    edge_options = webdriver.EdgeOptions()
    # edge_options.add_argument(f'--user-agent={ua.random}')
    # 保持登录会话信息
    edge_options.add_argument(f'--user-data-dir={user_data_dir}')
    # 无头模式
    # edge_options.add_argument('--headless')

    # 屏蔽inforbar
    edge_options.add_experimental_option('useAutomationExtension', False)
    edge_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])

    driver = webdriver.Edge(options=edge_options)

    # 设置超时时间
    driver.set_page_load_timeout(1)

    try:
        driver.set_window_size(700, 600)
        driver.set_window_position(50, 200)
    except Exception as e:
        while True:
            try:
                driver.set_window_size(700, 600)
                driver.set_window_position(50, 200)
                break
            except Exception as e:
                pass

    with open(f"{relative_path}/stealth.min.js") as f:
        js = f.read()
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": js
    })

    time.sleep(1)

    for i in range(len(driver.window_handles)):
        j = 1
        while j < len(driver.window_handles):
            driver.switch_to.window(driver.window_handles[j])
            try:
                if driver.window_handles[j] not in error_windows:
                    if driver.current_url != 'https://live.douyin.com/categorynew/4_103':
                        time.sleep(1)
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f'{timestamp} 正在关闭标签页{driver.title}')

                        driver.close()
                        time.sleep(1)

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f'{timestamp} 已关闭当前标签页，当前标签页数:{len(driver.window_handles)}')
                        break
            except Exception as e:
                error_windows[driver.window_handles[j]] = 1

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.RED + f'{timestamp} 该标签页无法被关闭，已被记录！' + Fore.RESET)

            j += 1

    driver.switch_to.window(driver.window_handles[0])

    driver.set_page_load_timeout(5)

    try:
        # 打开抖音官网
        driver.get('https://live.douyin.com/categorynew/4_103')
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.RED + f'{timestamp} 打开抖音官网超时！' + Fore.RESET)

        driver.set_page_load_timeout(20)

        while True:
            try:
                # 打开抖音官网
                driver.get('https://live.douyin.com/categorynew/4_103')
                break
            except Exception as e:
                pass

if __name__ == "__main__":
    # 初始化colorama
    init()

    tp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(Fore.YELLOW + f'{tp} 正在连接服务器中...' + Fore.RESET)

    # 设置临时的系统变量，以正常运行Microsoft Edge WebDriver
    os.environ['Path'] = os.environ.get('path') + relative_path

    # 初始化record中的方法
    get_pushplus_token()
    get_records()
    get_lottery_info()
    time.sleep(1)

    # 读取already_buy_popularity_ticket.json
    p = f'{relative_path}/already_buy_popularity_ticket.json'

    try:
        if not os.path.exists(p):
            # 打开文件，以写入模式创建文件对象
            with open(f'{relative_path}/already_buy_popularity_ticket.json', 'w',
                      encoding='utf-8') as file:
                # indent=1 每个层级缩进1个空格
                file.write(json.dumps([], indent=1, ensure_ascii=False))
        else:
            already_buy_popularity_ticket = read_json_file(p)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.RED + f'{timestamp} 操作already_buy_popularity_ticket.json时出错！' + Fore.RESET)
    
    timestamp2 = datetime.now().strftime("%Y-%m-%d")
    bag_num1_dic[timestamp2] = today_bag_num1[0]
    bag_num3_dic[timestamp2] = today_bag_num3[0]
    real_object_num_dic[timestamp2] = today_real_object_num[0]
    popularity_ticket_num_dic[timestamp2] = today_popularity_ticket_red_packet_num[0]

    # 初始化用户信息
    get_user_info()

    normal_p = set_normal_p[0]
    base_normal_p = normal_p
    fan_club_p = set_fan_club_p[0]
    base_fan_club_p = fan_club_p
    real_object_p = set_real_object_p[0]
    base_real_object_p = real_object_p

    if normal_p < min_normal_p[0]:
        normal_p = min_normal_p[0]
    if normal_p > max_normal_p[0]:
        normal_p = max_normal_p[0]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(Fore.YELLOW + f'{timestamp} 普通福袋筛选概率:{normal_p}' + Fore.RESET)

    temp_today_bag_num2 = today_bag_num1[0] - today_bag_num3[0]

    if temp_today_bag_num2 > 0:
        fan_club_p = base_fan_club_p + math.log(temp_today_bag_num2, 2) / 100 + today_bag_num3[0] / 100

    if fan_club_p < min_fan_club_p[0]:
        fan_club_p = min_fan_club_p[0]
    if fan_club_p > max_fan_club_p[0]:
        fan_club_p = max_fan_club_p[0]

    if temp_today_bag_num2 > 0:
        print(
            Fore.YELLOW + f'{timestamp} 初始粉丝团福袋筛选概率:{fan_club_p} ({base_fan_club_p} + {math.log(temp_today_bag_num2, 2) / 100} + {today_bag_num3[0] / 100})' + Fore.RESET)
    else:
        print(
            Fore.YELLOW + f'{timestamp} 初始粉丝团福袋筛选概率:{fan_club_p} ({base_fan_club_p} + 0.00 + 0.00)' + Fore.RESET)

    if real_object_p < min_real_object_p[0]:
        real_object_p = min_real_object_p[0]
    if real_object_p > max_real_object_p[0]:
        real_object_p = max_real_object_p[0]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(Fore.YELLOW + f'{timestamp} 实物福袋筛选概率:{real_object_p}' + Fore.RESET)

    print(Fore.YELLOW + f'{timestamp} 普通福袋的最低筛选概率:{min_normal_p[0]}' + Fore.RESET)
    print(Fore.YELLOW + f'{timestamp} 粉丝团福袋的最低筛选概率:{min_fan_club_p[0]}' + Fore.RESET)
    print(Fore.YELLOW + f'{timestamp} 实物福袋的最低筛选概率:{min_real_object_p[0]}' + Fore.RESET)
    print(Fore.YELLOW + f'{timestamp} 普通福袋的最高筛选概率:{max_normal_p[0]}' + Fore.RESET)
    print(Fore.YELLOW + f'{timestamp} 粉丝团福袋的最高筛选概率:{max_fan_club_p[0]}' + Fore.RESET)
    print(Fore.YELLOW + f'{timestamp} 实物福袋的最高筛选概率:{max_real_object_p[0]}' + Fore.RESET)

    '''
    # 最大筛选概率(未中福袋增加的概率最多为0.05，中福袋增加的概率最多为0.15)
    if fan_club_p > base_fan_club_p + 0.05 + today_bag_num3[0] / 100:
        if today_bag_num3[0] <= 15:
            fan_club_p = base_fan_club_p + 0.05 + today_bag_num3[0] / 100
            print(
                Fore.YELLOW + f'{timestamp} 初始粉丝团福袋筛选概率:{fan_club_p} ({base_fan_club_p} + 0.05 + {today_bag_num3[0] / 100})' + Fore.RESET)
        else:
            fan_club_p = base_fan_club_p + 0.05 + 0.15
            print(Fore.YELLOW + f'{timestamp} 初始粉丝团福袋筛选概率:{fan_club_p} ({base_fan_club_p} + 0.05 + 0.15)' + Fore.RESET)
    else:
        if temp_today_bag_num2 > 0:
            print(
                Fore.YELLOW + f'{timestamp} 初始粉丝团福袋筛选概率:{fan_club_p} ({base_fan_club_p} + {math.log(temp_today_bag_num2, 2) / 100} + {today_bag_num3[0] / 100})' + Fore.RESET)
        else:
            print(
                Fore.YELLOW + f'{timestamp} 初始粉丝团福袋筛选概率:{fan_club_p} ({base_fan_club_p} + 0.0 + {today_bag_num3[0] / 100})' + Fore.RESET)
    '''

    if want_bag_type1[0] == 1:
        print(Fore.YELLOW + f'{timestamp} 是否抢普通福袋:是' + Fore.RESET)
    else:
        print(Fore.YELLOW + f'{timestamp} 是否抢普通福袋:否' + Fore.RESET)
    if want_bag_type2[0] == 1:
        print(Fore.YELLOW + f'{timestamp} 是否抢粉丝团福袋:是' + Fore.RESET)
    else:
        print(Fore.YELLOW + f'{timestamp} 是否抢粉丝团福袋:否' + Fore.RESET)
    if want_bag_type3[0] == 1:
        print(Fore.YELLOW + f'{timestamp} 是否抢实物福袋:是' + Fore.RESET)
    else:
        print(Fore.YELLOW + f'{timestamp} 是否抢实物福袋:否' + Fore.RESET)

    print(Fore.YELLOW + f'{timestamp} 本次钻石收益的风控值:{set_risk_income[0]}' + Fore.RESET)
    print(Fore.YELLOW + f'{timestamp} 今日钻石收益的风控值:{set_risk_today_income[0]}' + Fore.RESET)
    print(Fore.YELLOW + f'{timestamp} 预期的抽中福袋的概率:{set_get_reward_p[0]}' + Fore.RESET)
    print(Fore.YELLOW + f'{timestamp} 提高的粉丝团福袋的筛选概率:{set_raise_fan_club_bag_p[0]}' + Fore.RESET)
    if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
        if open_account2_browser[0] == 1:
            print(Fore.YELLOW + f'{timestamp} 启动程序时打开要切换的账号所在的浏览器:是' + Fore.RESET)
        else:
            print(Fore.YELLOW + f'{timestamp} 启动程序时打开要切换的账号所在的浏览器:否' + Fore.RESET)
        if need_change_account[0] == 1:
            print(Fore.YELLOW + f'{timestamp} 本次需要切换账号:是' + Fore.RESET)
        else:
            print(Fore.YELLOW + f'{timestamp} 本次需要切换账号:否' + Fore.RESET)
        print(Fore.YELLOW + f'{timestamp} 设置的切换账号时满足的程序运行时间:≥{set_change_account_running_time[0]}s' + Fore.RESET)
        print(
            Fore.YELLOW + f'{timestamp} 设置的切换账号时满足的本次钻石收益:≤{set_change_account_income[0]}' + Fore.RESET)
        print(
            Fore.YELLOW + f'{timestamp} 设置的切换账号时满足的今日钻石收益:≥{set_change_account_today_income[0]}' + Fore.RESET)
        print(
            Fore.YELLOW + f'{timestamp} 设置的切换账号时满足的今日参与福袋数:≥{set_change_account_bag_num1[0]}' + Fore.RESET)
        print(
            Fore.YELLOW + f'{timestamp} 设置的切换账号时满足的今日已中福袋数:≥{set_change_account_bag_num3[0]}' + Fore.RESET)
        if want_red_packet[0]:
            print(Fore.YELLOW + f'{timestamp} 是否自动抢红包:是' + Fore.RESET)
        else:
            print(Fore.YELLOW + f'{timestamp} 是否自动抢红包:否' + Fore.RESET)
        if want_popularity_ticket_red_packet[0]:
            print(Fore.YELLOW + f'{timestamp} 是否自动抢红人气包:是' + Fore.RESET)
            print(Fore.YELLOW + f'{timestamp} 设置的参与人气红包的次数上限:{set_max_count_popularity_ticket_red_packet[0]}' + Fore.RESET)
        else:
            print(Fore.YELLOW + f'{timestamp} 是否自动抢人气红包:否' + Fore.RESET)
            print(Fore.YELLOW + f'{timestamp} 设置的参与人气红包的次数上限:{set_max_count_popularity_ticket_red_packet[0]}' + Fore.RESET)

    # 比较程序版本
    get_program_version()

    time.sleep(5)

    if login_status[0] == 1:
        start_time = time.time()

        tp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f'{tp} 正在打开抖音官网')

        # 下载/更新Edge浏览器
        # 下载Microsoft Edge WebDriver
        # Microsoft Edge 和 Microsoft Edge WebDriver 之间，由四个部分构成的版本号的前三个部分必须匹配。
        # 将msedgedriver.exe所在的文件夹添加到你的 PATH 环境变量

        # 设置用户数据目录的路径
        user_data_dir = f'{relative_path}/user/data/dir'
        user_data_dir2 = f'{relative_path}/user/data/dir2'

        # ua = UserAgent()
        edge_options = webdriver.EdgeOptions()
        # edge_options.add_argument(f'--user-agent={ua.random}')
        # 保持登录会话信息
        edge_options.add_argument(f'--user-data-dir={user_data_dir}')
        # 无头模式
        # edge_options.add_argument('--headless')

        # 屏蔽inforbar
        edge_options.add_experimental_option('useAutomationExtension', False)
        edge_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])

        # ua2 = UserAgent()
        edge_options2 = webdriver.EdgeOptions()
        # edge_options2.add_argument(f'--user-agent={ua2.random}')
        edge_options2.add_argument(f'--user-data-dir={user_data_dir2}')

        # 屏蔽inforbar
        edge_options2.add_experimental_option('useAutomationExtension', False)
        edge_options2.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])

        # 初始化 WebDriver 并打开一个Edge浏览器窗口
        service = Service(executable_path=f'{relative_path}/msedgedriver.exe')
        # 开启performance，记录日志
        edge_options.set_capability("ms:loggingPrefs", {'performance': 'ALL'})

        driver = webdriver.Edge(options=edge_options)

        # 设置超时时间
        driver.set_page_load_timeout(1)

        try:
            driver.set_window_size(700, 600)
            driver.set_window_position(50, 200)
        except Exception as e:
            while True:
                try:
                    driver.set_window_size(700, 600)
                    driver.set_window_position(50, 200)
                    break
                except Exception as e:
                    pass

        rd_w = random.randint(-10, 10)
        rd_h = random.randint(-10, 10)

        driver2 = None

        if want_red_packet[0] == 0 or (is_VIP[0] == 0 and is_temporary_VIP[0] == 0):
            driver2 = webdriver.Edge(options=edge_options2)
            driver2.set_window_size(900 + rd_w, 700 + rd_h)
            driver2.set_window_position(950, 200)
            driver2.set_page_load_timeout(5)

        with open(f"{relative_path}/stealth.min.js") as f:
            js = f.read()
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": js
        })

        time.sleep(1)

        for i in range(len(driver.window_handles)):
            j = 1
            while j < len(driver.window_handles):
                driver.switch_to.window(driver.window_handles[j])
                try:
                    if driver.window_handles[j] not in error_windows:
                        if driver.current_url != 'https://live.douyin.com/categorynew/4_103':
                            time.sleep(1)
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f'{timestamp} 正在关闭标签页{driver.title}')

                            driver.close()
                            time.sleep(1)

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f'{timestamp} 已关闭当前标签页，当前标签页数:{len(driver.window_handles)}')
                            break
                except Exception as e:
                    error_windows[driver.window_handles[j]] = 1

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(Fore.RED + f'{timestamp} 该标签页无法被关闭，已被记录！' + Fore.RESET)

                j += 1

        driver.switch_to.window(driver.window_handles[0])

        driver.set_page_load_timeout(5)

        try:
            # 打开抖音官网
            driver.get('https://live.douyin.com/categorynew/4_103')
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(Fore.RED + f'{timestamp} 打开抖音官网超时！' + Fore.RESET)

            driver.set_page_load_timeout(20)

            while True:
                try:
                    # 打开抖音官网
                    driver.get('https://live.douyin.com/categorynew/4_103')
                    break
                except Exception as e:
                    pass

        time.sleep(1)

        if want_red_packet[0] == 0 or (is_VIP[0] == 0 and is_temporary_VIP[0] == 0):
            for i in range(len(driver2.window_handles)):
                j = 1
                while j < len(driver2.window_handles):
                    driver2.switch_to.window(driver2.window_handles[j])
                    try:
                        if driver2.window_handles[j] not in error_windows:
                            time.sleep(1)
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f'{timestamp} 正在关闭标签页{driver2.title}')

                            driver2.close()
                            time.sleep(1)

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f'{timestamp} 已关闭当前标签页，当前标签页数:{len(driver2.window_handles)}')
                            break
                    except Exception as e:
                        error_windows[driver2.window_handles[j]] = 1

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(Fore.RED + f'{timestamp} 该标签页无法被关闭，已被记录！' + Fore.RESET)

                    j += 1

            driver2.switch_to.window(driver2.window_handles[0])

        if want_red_packet[0] == 0 or (is_VIP[0] == 0 and is_temporary_VIP[0] == 0):
            driver2.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": js
            })

            try:
                driver2.get('https://www.douyin.com/jingxuan')
            except Exception as e:

                driver2.set_page_load_timeout(20)

                while True:
                    try:
                        driver2.get('https://www.douyin.com/jingxuan')
                        break
                    except Exception as e:
                        pass

        driver.set_window_position(-9999, -9999)

        if want_red_packet[0] == 0 or (is_VIP[0] == 0 and is_temporary_VIP[0] == 0):
            driver2.set_window_position(-9999, -9999)

        tp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.YELLOW + f'{tp} 浏览器已被隐藏，按下\'1键\'可再次显示浏览器' + Fore.RESET)

        if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
            if open_account2_browser[0] == 1 and want_red_packet[0] == 0:
                user_data_dir3 = f'{relative_path}/user/data/account2'

                edge_options3 = webdriver.EdgeOptions()
                edge_options3.add_argument(f'--user-data-dir={user_data_dir3}')

                # 屏蔽inforbar
                edge_options3.add_experimental_option('useAutomationExtension', False)
                edge_options3.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])

                rd_w = random.randint(-10, 10)
                rd_h = random.randint(-10, 10)

                driver3 = webdriver.Edge(options=edge_options3)
                driver3.set_window_size(900 + rd_w, 600 + rd_h)
                driver3.set_window_position(950, 200)
                driver3.set_page_load_timeout(60)

                driver3.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": js
                })

                time.sleep(1)

                for i in range(len(driver3.window_handles)):
                    j = 1
                    while j < len(driver3.window_handles):
                        driver3.switch_to.window(driver3.window_handles[j])
                        try:
                            if driver3.window_handles[j] not in error_windows:
                                time.sleep(1)
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                print(f'{timestamp} 正在关闭标签页{driver3.title}')

                                driver3.close()
                                time.sleep(1)

                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                print(f'{timestamp} 已关闭当前标签页，当前标签页数:{len(driver3.window_handles)}')
                                break
                        except Exception as e:
                            error_windows[driver3.window_handles[j]] = 1

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(Fore.RED + f'{timestamp} 该标签页无法被关闭，已被记录！' + Fore.RESET)

                        j += 1

                driver3.switch_to.window(driver3.window_handles[0])

                driver3.get('https://www.douyin.com/jingxuan')

            if open_account2_browser[0] == 1 and want_red_packet[0] == 1:
                def open_temp_google_chrome():
                    with sync_playwright() as p:
                        temp_browser = p.chromium.launch_persistent_context(
                            user_data_dir=f'{relative_path}/user/playwright_data/account2',
                            channel="chrome",
                            headless=False,
                            no_viewport=True,
                            # do NOT add custom browser headers or user_agent
                        )

                        temp_page = temp_browser.new_page()

                        temp_page.goto('https://www.douyin.com/jingxuan')

                        while True:
                            try:
                                temp_page.get_by_text('钻石').all()
                            except Exception as e:
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                print(Fore.RED + f'{timestamp} 要切换的账号所在的浏览器已被关闭！' + Fore.RESET)

                                break

                            time.sleep(0.1)

                temp_task = threading.Thread(target=open_temp_google_chrome)
                temp_task.start()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.YELLOW + f'{timestamp} 正在获取关键数据...' + Fore.RESET)

        get_important_data()

        if msToken[0] != '' and a_bogus[0] != '':
            # 先推送一次
            notification_title = '今日数据'
            if bag_num1_dic[timestamp2] != 0:
                notification_detailed_content = (
                        f'{time.time()}\n'
                        + f'今日总收益: %2B{today_income[0]}\n'
                        + f'今日参与的福袋数: {bag_num1_dic[timestamp2]}\n'
                        + f'今日中奖率: {bag_num3_dic[timestamp2] / bag_num1_dic[timestamp2]}\n'
                        + f'今日中福袋的数量: {bag_num3_dic[timestamp2]}\n'
                        + f'今日中实物福袋的数量: {real_object_num_dic[timestamp2]}\n'
                        + f'今日中过的福袋的总收益: %2B{total_bag_num3_value[0]}\n'
                        + f'今日中过的钻石红包的总收益: %2B{total_red_packet_num3_value[0]}\n'
                        + f'今日参与的人气红包数: {popularity_ticket_num_dic[timestamp2]}\n'
                        + f'今日中过的礼物红包的总收益: %2B{total_red_packet_gift_num3_value[0]}')
            else:
                notification_detailed_content = (
                        f'{time.time()}\n'
                        + f'今日总收益: %2B{today_income[0]}\n'
                        + f'今日参与的福袋数: {bag_num1_dic[timestamp2]}\n'
                        + f'今日中奖率: 0.00'
                        + f'今日中福袋的数量: {bag_num3_dic[timestamp2]}\n'
                        + f'今日中实物福袋的数量: {real_object_num_dic[timestamp2]}\n'
                        + f'今日中过的福袋的总收益: %2B{total_bag_num3_value[0]}\n'
                        + f'今日中过的钻石红包的总收益: %2B{total_red_packet_num3_value[0]}\n'
                        + f'今日参与的人气红包数: {popularity_ticket_num_dic[timestamp2]}\n'
                        + f'今日中过的礼物红包的总收益: %2B{total_red_packet_gift_num3_value[0]}')

            send_wechat(notification_title, notification_detailed_content)

            # 开启无限循环线程保持浏览器处于运行状态
            t = threading.Thread(target=search)
            t.start()

            # search_from_record2 线程
            task1 = threading.Thread(target=search_from_records)
            task1.start()

            # get_live_by_api 线程
            task2 = threading.Thread(target=get_live_by_api)
            task2.start()

            # 检查search运行状况 线程
            check_thread = threading.Thread(target=check_search_thread_status)
            check_thread.start()

            # 检查键盘事件 线程
            keyboard_thread = threading.Thread(target=check_keyboard_event)
            keyboard_thread.start()

            # control_driver2 线程
            if want_red_packet[0] == 0 or (is_VIP[0] == 0 and is_temporary_VIP[0] == 0):
                save_edge_dir = f'{relative_path}/user/data/dir2'

                control_thread = threading.Thread(target=control_driver2)
                control_thread.start()
            if is_VIP[0] == 1 or is_temporary_VIP[0] == 1:
                if want_red_packet[0]:
                    save_google_chrome_dir = f'{relative_path}/user/playwright_data/dir2'
                    asyncio.run(main(f'{relative_path}/user/playwright_data/dir2'))
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(Fore.RED + f'{timestamp} 获取关键数据失败，请重启程序！' + Fore.RESET)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.RED + f'{timestamp} 当前未登录，请正确填写_internal/user.json文件！' + Fore.RESET)
