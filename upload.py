# v0.1g (master)
import sys
import os
import os.path as path
import glob

sys.path.append('app\\lib')
sys.path.append('python-3.12.7-embed-amd64\\Lib\\site-packages')
sys.path.pop(0)

import requests
import paramiko

from server import server
import utils

arguments_dict = {}

def get_arguments() -> dict:
    '''
    获取参数.
    '''

    global arguments_dict

    if os.access('machine.ini', os.R_OK):
        with open('machine.ini', 'rt') as in_f:
            for line_str in in_f:
                line_lst = line_str.split()
                arguments_dict[line_lst[0]] = line_lst[1]

    while True:

        # 上传的项目目录
        arguments_dict['local_path'] = []
        print()
        print('第一步：将所需上传的项目目录依次拖曳到此处后按回车（注意：不是Res目录，而是项目目录。例如：202410181422_C22091401_A_PRM32502260044_SEQ_A_AB_PE150）目录名不能有空格。')
        i = 0
        while True:
            if i == 0:
                local_path_str = input('>')
            else:
                local_path_str = input('你可以上传另一个目录，如果没有，直接按回车>')

            if local_path_str != '' and local_path_str not in arguments_dict['local_path']:
                arguments_dict['local_path'].append(local_path_str.replace('"', ''))
            elif arguments_dict['local_path'] != []:
                break
            else:
                pass

            i += 1

        # 上传文件类型
        print()
        print('第二步：是否上传图像文件（数据量大，上传缓慢)，输入y上传，直接按回车不上传')
        arguments_dict['pattern'] = ['.fastq.gz', '.fq.gz', '.fq', '.fastq', '.md5', '.html', '.exe', '.dll']
        is_upload_image_str = input('>')
        if is_upload_image_str.upper() in ['Y', 'YES', 'T', 'TRUE', '是']:
            arguments_dict['pattern'].extend(['.tif', '.tiff', '.png', '.TIF', '.TIFF', '.PNG'])
        else:
            is_upload_image_str = '否'

        # 测序仪类型
        while True:
            if 'machine_type' in arguments_dict.keys():
                print()
                print(f"第三步：输入测序仪类型【Pro, Nimbo, Evo】，直接按回车默认为{arguments_dict['machine_type']}")
                machine_type_str = input('>')
                if machine_type_str == '':
                    machine_type_str = arguments_dict['machine_type']
            else:
                print()
                print(f"<第三步：输入测序仪类型【Pro, Nimbo, Evo】")
                machine_type_str = input('>')

            if machine_type_str.lower() in ['pro', 'evo', 'nimbo']:
                break

        arguments_dict['machine_type'] = machine_type_str[0].upper() + machine_type_str[1:].lower()


        # 测序仪编号
        while True:
            if 'machine_tag' in arguments_dict.keys():
                print()
                print(f"第四步：输入测序仪编号。直接按回车使用 {arguments_dict['machine_tag']} 或手动输入机器号。")
                machine_tag_str = input('>')
                if machine_tag_str == '':
                    machine_tag_str = arguments_dict['machine_tag']
            else:
                print()
                print("第四步：输入测序仪编号，例如C2201010004")
                machine_tag_str = input('>')

            if machine_tag_str.strip() != '':
                break

        arguments_dict['machine_tag'] = machine_tag_str.strip()

        # 确认
        print()
        print('确认信息')
        print(f"{len(arguments_dict['local_path'])}个上传目录：")
        for local_path_str in arguments_dict['local_path']:
            print(f'{local_path_str}')
        print()
        print(f'是否上传图片：{is_upload_image_str}')
        print()
        print(f"机器类型和编号：{arguments_dict['machine_type']}，{arguments_dict['machine_tag']}")
        if input('<确认上述信息是否正确，直接按回车确认正确，输入N重新运行>') == '':
            break
        else:
            print('上述信息有误，重新运行脚本')


    # 保存machine_type和machine_id
    with open('machine.ini', 'wt') as out_f:
        for key in ['machine_type', 'machine_tag', 'username']:
            out_f.writelines(f'{key}\t{arguments_dict[key]}\n')

    return None


def main(argvList = sys.argv, argv_int = len(sys.argv)):
    local_path_lst = arguments_dict['local_path']
    machine_tag_str = arguments_dict['machine_tag']
    machine_type_str = arguments_dict['machine_type']
    username_str = arguments_dict['username']


    private_key_file = glob.glob('app\\*_rsa')[0]
    group_str = private_key_file[4:-4]
    print(group_str)


    remote_folder_str = utils.generate_remote_data_path(machine_type_str, group_str, machine_tag_str)
    print('服务器数据上传路径： ', remote_folder_str)

    data_server = server(ip = '192.168.0.185')
    print('正在连接服务器192.168.0.185 ...')
    print(f'用户名： {username_str}  私钥文件： {private_key_file}')
    data_server.generate_sftp_client(username = username_str, private_key_file = private_key_file)
    data_server.create_remote_folder(parent_folder = '/', child_folder = remote_folder_str)

    for local_path_str in local_path_lst:
        if 'Res' not in os.listdir(local_path_str) and 'Res1' not in os.listdir(local_path_str):
            message = f'{path.basename(local_path_str)}，该上传目录下无Res，确定这是一个项目文件？'
            print(message)
        data_server.upload_a_folder(local_path_str, remote_folder_str, pattern = arguments_dict['pattern'])
        try:
            utils.send_message(machine_type_str, machine_tag_str, path.basename(local_path_str), remote_folder_str)
        except Exception as ex:
            print('send message: ', ex)

    print('\n上传完毕，可以关闭本窗口。')

    return


if __name__ == '__main__':
    try:
        version = 0.1
        r = utils.self_upgrade(version)
        if r == 0:
            print('启动成功')
    except Exception as ex:
        pass

    r = get_arguments()
    print(arguments_dict)
    main()



