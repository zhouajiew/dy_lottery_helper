import json
import os
import re
from datetime import datetime

from colorama import Fore, init

from global_v import *

live_info = []
# 发过福袋的直播间
live_info2 = []
# 发过优质福袋(参与过的福袋)的直播间
live_info3 = []

# 收益列表
income_detail = []

# 获取当前文件所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 构建相对路径
relative_path = os.path.join(current_dir)

gift_value_dic = {'小心心':'1钻', '大啤酒':'2钻', '棒棒糖':'9钻', '小皇冠':'10钻', '撩一下':'19钻'}
gift_value_dic2 = {'小心心':1, '大啤酒':2, '棒棒糖':9, '小皇冠':10, '撩一下':19}

def get_pushplus_token():
    p = f'{relative_path}/pushplus.json'

    try:
        if not os.path.exists(p):
            data = [{'token':''}]

            # 打开文件，以写入模式创建文件对象
            with open(f'{relative_path}/pushplus.json', 'w', encoding='utf-8') as file:
                # indent=1 每个层级缩进1个空格
                file.write(json.dumps(data, indent=1, ensure_ascii=False))
        else:
            original_data = read_json_file(p)

            pushplus_token[0] = original_data[0].get('token')
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(Fore.RED + f'{timestamp} 读取pushplus.json文件失败！' + Fore.RESET)

def get_lottery_info():
    global income_detail

    global gift_value_dic
    global gift_value_dic2

    p = f'{relative_path}/lottery_info'

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp2 = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(p):
        os.makedirs(f"{relative_path}/lottery_info", exist_ok=True)
    else:
        p2 = f'{relative_path}/lottery_info/{timestamp2}.json'
        if os.path.exists(p2):
            try:
                income_detail = read_json_file(p2)

                for i in income_detail:
                    if i.get('实物奖品'):
                        today_real_object_num[0] += 1

                    if not i.get('type'):
                        if i.get('reward'):
                            reward = i['reward']
                            pattern = r'([\s\S]+)钻'
                            if re.search(pattern, reward):
                                int_reward = int(re.search(pattern, reward).group(1))
                                if int_reward > 0:
                                    today_bag_num3[0] += 1
                                    total_bag_num3_value[0] += int_reward

                                today_income[0] += int_reward

                    if i.get('type'):
                        if i.get('special_type'):
                            if i.get('reward'):
                                reward = i['reward']
                                pattern = r'([\s\S]+)钻'
                                if re.search(pattern, reward):
                                    int_reward = int(re.search(pattern, reward).group(1))
                                    today_income[0] += int_reward

                        if i['type'] == '钻石红包':
                            if i.get('reward'):
                                reward = i['reward']
                                pattern = r'([\s\S]+)钻'
                                if re.search(pattern, reward):
                                    int_reward = int(re.search(pattern, reward).group(1))
                                    total_red_packet_num3_value[0] += int_reward

                                    today_income[0] += int_reward

                        if i['type'] == '礼物红包':
                            if i.get('gift_type'):
                                temp_gift_type = i['gift_type']
                                if i.get('gift_value') == 'unknown':
                                    if temp_gift_type in gift_value_dic:
                                        i['gift_value'] = gift_value_dic[temp_gift_type]
                                        total_red_packet_gift_num3_value[0] += gift_value_dic2[temp_gift_type]
                                else:
                                    if temp_gift_type in gift_value_dic:
                                        total_red_packet_gift_num3_value[0] += gift_value_dic2[temp_gift_type]

                        if i.get('special_type') and i.get('reward'):
                            if i['special_type'] == '人气红包':
                                today_popularity_ticket_red_packet_num[0] += 1

                if income_detail[0].get('今日参与的福袋数'):
                    today_bag_num1[0] = income_detail[0].get('今日参与的福袋数')
                    income_detail[0]['今日中奖率'] = today_bag_num3[0] / today_bag_num1[0]

                if income_detail[0].get('今日总收益'):
                    if today_income[0] >= 0:
                        income_detail[0]['今日总收益'] = f'+{today_income[0]}'
                    else:
                        income_detail[0]['今日总收益'] = f'{today_income[0]}'

                income_detail[0]['今日中福袋的数量'] = today_bag_num3[0]
                income_detail[0]['今日中实物福袋的数量'] = today_real_object_num[0]
                income_detail[0]['今日中过的福袋的总收益'] = f'+{total_bag_num3_value[0]}'
                income_detail[0]['今日中过的钻石红包的总收益'] = f'+{total_red_packet_num3_value[0]}'
                income_detail[0]['今日参与的人气红包数'] = today_popularity_ticket_red_packet_num[0]
                income_detail[0]['今日中过的礼物红包的总收益'] = f'+{total_red_packet_gift_num3_value[0]}'

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if today_income[0] >= 0:
                    print(Fore.YELLOW + f'{timestamp} 本次钻石收益:0，今日钻石收益:+{today_income[0]}，今日中过的福袋的总收益:+{total_bag_num3_value[0]}' + Fore.RESET)
                else:
                    print(Fore.YELLOW + f'{timestamp} 本次钻石收益:0，' + Fore.LIGHTBLUE_EX + f'今日钻石收益:{today_income[0]}，' + Fore.YELLOW + f'今日中过的福袋的总收益:+{total_bag_num3_value[0]}' + Fore.RESET)

                # 打开文件，以写入模式创建文件对象
                with open(f'{relative_path}/lottery_info/{timestamp2}.json', 'w',
                          encoding='utf-8') as temp_f:
                    # indent=1 每个层级缩进1个空格
                    temp_f.write(json.dumps(income_detail, indent=1, ensure_ascii=False))

            except Exception as e:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.RED + f'{timestamp} 读取lottery_info/{timestamp2}.json失败！' + Fore.RESET)
        else:
            try:
                # 打开文件，以写入模式创建文件对象
                with open(f'{relative_path}/lottery_info/{timestamp2}.json', 'w',
                          encoding='utf-8') as temp_f:
                    # indent=1 每个层级缩进1个空格
                    temp_f.write(json.dumps([{'今日总收益':'+0', '今日参与的福袋数': 0, '今日中奖率': 0, '今日中福袋的数量': 0, '今日中过的福袋的总收益' : '+0', '今日中过的钻石红包的总收益' : '+0'}], indent=1, ensure_ascii=False))

            except Exception as e:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(Fore.RED + f'{timestamp} 创建lottery/{timestamp2}.json文件失败！' + Fore.RESET)

def get_records():
    path = f'{relative_path}/record.json'

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    current_time = datetime.timestamp(datetime.now())
    date_format = "%Y-%m-%d %H:%M:%S"

    if os.path.exists(path):
        try:
            original_data = read_json_file(path)

            for o in original_data:
                if o.get('record_time'):
                    temp_time = o.get('record_time')
                    temp_time = datetime.strptime(temp_time, date_format)
                    temp_time = temp_time.timestamp()

                    time_difference = current_time - temp_time

                    # 清除time_difference大于8小时的记录，因为room_id会发生变化
                    if time_difference <= 28800:
                        live_info.append(o)

        except Exception as e:
            print(Fore.RED + f'{timestamp} 读取record.json文件失败！' + Fore.RESET)
    else:
        data = []

        # 打开文件，以写入模式创建文件对象
        with open(f'{relative_path}/record.json', 'w', encoding='utf-8') as file:
            # indent=1 每个层级缩进1个空格
            file.write(json.dumps(data, indent=1, ensure_ascii=False))

    path = f'{relative_path}/record2.json'

    if os.path.exists(path):
        try:
            original_data = read_json_file(path)
            for o in original_data:
                if o.get('record_time'):
                    temp_time = o.get('record_time')
                    temp_time = datetime.strptime(temp_time, date_format)
                    temp_time = temp_time.timestamp()

                    time_difference = current_time - temp_time

                    # 清除time_difference大于8小时的记录，因为room_id会发生变化
                    if time_difference <= 28800:
                        live_info2.append(o)

        except Exception as e:
            print(Fore.RED + f'{timestamp} 读取record2.json文件失败！' + Fore.RESET)
    else:
        data = []

        # 打开文件，以写入模式创建文件对象
        with open(f'{relative_path}/record2.json', 'w', encoding='utf-8') as file:
            # indent=1 每个层级缩进1个空格
            file.write(json.dumps(data, indent=1, ensure_ascii=False))

    path = f'{relative_path}/record3.json'

    if os.path.exists(path):
        try:
            original_data = read_json_file(path)
            for o in original_data:
                if o.get('record_time'):
                    temp_time = o.get('record_time')
                    temp_time = datetime.strptime(temp_time, date_format)
                    temp_time = temp_time.timestamp()

                    time_difference = current_time - temp_time

                    # 清除time_difference大于3天(259200秒)的记录，因为room_id会发生变化
                    if time_difference <= 259200:
                        '''
                        if o.get('update_time'):
                            del o['update_time']
                        '''

                        live_info3.append(o)

        except Exception as e:
            print(Fore.RED + f'{timestamp} 读取record3.json文件失败！' + Fore.RESET)
    else:
        data = []

        # 打开文件，以写入模式创建文件对象
        with open(f'{relative_path}/record3.json', 'w', encoding='utf-8') as file:
            # indent=1 每个层级缩进1个空格
            file.write(json.dumps(data, indent=1, ensure_ascii=False))

# 读取json文件
def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as temp_f:
        d = json.load(temp_f)
        return d
