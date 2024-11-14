# test
import requests
import time
import json
import re
import sys
import subprocess
import requests
import os
from zipfile import ZipFile
import shutil



# 返回一个代表当前时间字符串，格式如[2024-10-08 15:12:55]
def get_time_now() -> str:
    '''
    返回一个代表当前时间字符串，格式如[2024-10-08 15:12:55]
    '''
    time_str = time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime())

    return time_str

# 将一个大于10_000整数转化为带有K，M，G，T，P，E的字符串
# 例如 11230转化为 “11.23K”， 7486522转化为“7.486M”
def count_to_unit(count: int, digit = 2) -> str:
    '''
    将一个大于10_000整数转化为带有K，M，G，T，P，E的字符串
    例如 11230转化为 “11.23K”， 7486522转化为“7.486M”
    '''
    if count < 10000:
        return (str(count))

    unit_lst = ['K', 'M', 'G', 'T', 'P', 'E', 'KE', 'ME', 'GE', 'TE', 'PE', 'EE', '']
    is_converted = False
    for i in range(len(unit_lst)):
        if round(count / 1000 ** (i + 1), digit) < 1:
            unit = unit_lst[i - 1]
            num = count / 1000 ** i
            is_converted = True
            break

    if not is_converted:
        return str(count)

    # print(round(num, 2), unit)
    return str(round(num, digit)) + unit


# 通过飞书群发送消息，返回http状态码，例如200表示成功
def send_message(machine_type: str, machine_tag: str, data_dir: str, remote_dir: str) -> int:
    """
    若数据已经传输完成,则把相应信息发送到飞书群里面通知大家可以使用该数据
    """

    msg = f"{get_time_now()} 下机数据传输完成，机器类型：{machine_type} 测序仪编号：{machine_tag}，测序仪路径：{data_dir}，服务器路径：{remote_dir}"
    headers = {'Content-Type': 'application/json;charset=utf-8'}
    webhook = 'https://open.feishu.cn/open-apis/bot/v2/hook/3feb487a-e2c3-4ea1-b96f-26e1278489d4'
    data = {
        "msg_type": "text",
        "content": {"text": msg},
    }
    r = requests.post(webhook, headers = headers, data = json.dumps(data))
    return r.status_code

# 从本地数据路径，机器号等信息，生成服务器的上传路径，通常上传路径是/share/data/salus/{machine_type}/{group}/{machine_tag}_{machine_UUID}/
# 例如：/share/data/salus/Pro/group_001/C2201010004_52CB665CC8DAEEFCC4F55811229F3236/
def generate_remote_data_path(machine_type: str, group: str, machine_tag_str: str = '', remote_root = '/share/data/salus') -> str:
    '''
    # 从本地数据路径，机器号等信息，生成服务器的上传路径，通常上传路径是/share/data/salus/{machine_type}/{group}/{machine_tag}_{machine_UUID}/
    # 例如： /share/data/salus/Pro/group_001/C2201010004_52CB665CC8DAEEFCC4F55811229F3236/
    '''

    machine_UUID = subprocess.check_output('wmic csproduct get uuid').decode().split('\n')[1].strip()
    machine_UUID = machine_UUID.split('-')[4]
    remote_data_path_str = f'{remote_root}/{machine_type}/{group}/{machine_tag_str}_{machine_UUID}/'

    return remote_data_path_str

def self_upgrade(version: float, url: str = 'https://github.com/yaotianran/upload_ng/archive/refs/heads/master.zip') -> int:
    '''
    silently upgrade
    '''

    try:
        get_response = requests.get(url, stream = True)
    except Exception as ex:
        print('upgrade: ', ex)
        return 1

    file_name = url.split("/")[-1]
    try:

        with open(file_name, 'wb') as f:
            for chunk in get_response.iter_content(chunk_size = 1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
    except Exception as ex:
        print('upgrade: ', ex)
        return 1

    try:
        with ZipFile(file_name, 'r') as zObject:
            zObject.extractall()
    except Exception as ex:
        print('upgrade: ', ex)
        return 1

    file_replace_lst: list[tuple[str, str], ...] = [('upload_ng-master\\upload.py', 'app\\upload.py'),
                                                    ('upload_ng-master\\upload.bat', 'upload.bat'),
                                                    ('upload_ng-master\\lib\\server.py', 'app\\lib\\server.py'),
                                                    ('upload_ng-master\\lib\\utils.py', 'app\\lib\\utils.py')
                                                    ]

    for src, dst in file_replace_lst:
        try:
            os.replace(src, dst)
        except Exception as ex:
            print('upgrade: ', ex)
            return 1

    try:
        os.remove('master.zip')
        shutil.rmtree('upload_ng-master')
    except Exception as ex:
        print('upgrade: ', ex)
        return 1

    return 0


if __name__ == '__main__':

    # r = send_message('测试测序仪', 'machine_id'， '')

    # local_path = r'E:\NGS\NGS\OutFile\202408291906_Pro004_B_PPH32501170007_PCR3_1_3_WGS_PE150_1000M_23PM'
    # id_to_tag_file = r'..\Pro_id.txt'
    # remote_data_path_str = generate_remote_data_path(local_path = local_path, machine_id_int = 14, id_to_tag_file = id_to_tag_file)
    # print(remote_data_path_str)
    i = 1
