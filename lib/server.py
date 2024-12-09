# v0.1k4 (master)
import sys
import os.path as path
import pathlib
import os
import glob


# -----------import customed packages here-------------
import paramiko
import utils

# ---------------------------------------------------


class Server:
    '''
    properties:

    methods:

    '''

    def __init__(self, ip: str, port: int = 22):
        self.ip = ip
        self.port = port

        self.sftp_client: paramiko.SFTPClient = None

        self.total_count_int: int = 0
        self.total_bytes_int: int = 0

        self.transfered_count_int: int = 0
        self.transfered_bytes_int: int = 0

        return None

    def __print_progress(self, bytes_transferred: int, bytes_total: int) -> None:
        '''
        用于SFTPClient.put方法的call_back属性
        '''

        total_transfered_bytes_int = self.transfered_bytes_int + bytes_transferred

        percent_perfile_str = str(round(bytes_transferred / bytes_total * 100)) + '%'
        percent_total_str = str(round(total_transfered_bytes_int / self.total_bytes_int * 100)) + '%'


        bytes_transferred = utils.count_to_unit(bytes_transferred)
        bytes_total = utils.count_to_unit(bytes_total)
        print(f'{bytes_transferred}/{bytes_total}  当前文件：{percent_perfile_str}  全部：{percent_total_str}             ', end = '\r')

        return None

    def generate_sftp_client(self, username: str, password: str = '', private_key_file = '') -> int:
        '''
        建立使用SSHClient().open_sftp一个sftp连接。

        Parameters:
           **username**，**password**: string
              如果使用username和password验证，填写这两个选项

           **private_key_file**: string
              如果使用私钥文件验证，填写这个选项，key文件为PEM格式。显然private_key_file和username不能都为‘’
              公私钥文件对可用命令“ssh-keygen -m PEM -t rsa -f SLG001_rsa”生成

        Returns:
           **sftp_client**: paramiko.SFTPClient
              paramiko.SFTPClient对象，可使用put方法上传文件
        '''

        if password == '' and private_key_file == '':
            message = 'generate_sftp_client: username和private_key_file不能同时为空'
            raise ValueError(message)

        if password != '' and private_key_file != '':
            message = 'generate_sftp_client: password和private_key_file同时存在，优先使用password'
            raise UserWarning(message)

        my_transport = paramiko.transport.Transport((self.ip, self.port))
        if password != '':
            my_transport.connect(username = username, password = password)
        else:
            try:
                private_key_file = pathlib.WindowsPath(private_key_file)
                private_key = paramiko.RSAKey.from_private_key_file(str(private_key_file.absolute()))
            except NotImplementedError:
                private_key_file = path.realpath(path.expanduser(private_key_file))
                private_key = paramiko.RSAKey.from_private_key_file(private_key_file)

            my_transport.connect(username = username, pkey = private_key)

        # my_transport = paramiko.transport.Transport(('192.168.0.185', 22), default_window_size = 2147483647, default_max_packet_size = 32768 * 4)
        # sftp_client = paramiko.SFTPClient.from_transport(my_transport, window_size = 2147483647, max_packet_size = 32768 * 4)
        sftp_client = paramiko.SFTPClient.from_transport(my_transport)
        self.sftp_client = sftp_client

        return 0

    def create_remote_folder(self, parent_folder: str, child_folder: str, dummy_mode = False) -> str:
        '''
        在server端建立文件夹
        建立'{parent_folder}/{child_folder}'
        '''
        remote_folder_str = parent_folder + '/' + child_folder
        if dummy_mode:
            print(remote_folder_str)
            return remote_folder_str

        try:
            _ = self.sftp_client.normalize(remote_folder_str)
        except FileNotFoundError:
            try:
                _ = self.sftp_client.mkdir(remote_folder_str)
            except FileNotFoundError:
                message = f'server::create_remote_folder，无法创建远程目录{remote_folder_str}，联系管理员'
                sys.exit(message)

        return remote_folder_str

    def upload_a_file(self, local_file, remote_file) -> int:
        '''
        上传一个文件, 返回上传的字节数
        '''

        # local_file = r'D:\Program Files\Common Files\System\Ole DB\msdaosp.dll'
        # remote_file = r'/share/data/salus/Pro/Program Files/Common Files/System/Ole DB/msdaosp.dll'

        if not os.access(path.realpath(local_file), os.R_OK):
            message = f'无法读取本地文件 {local_file}'
            raise FileNotFoundError(message)

        remote_folder_str = path.split(remote_file)[0]
        try:
            _ = self.sftp_client.normalize(remote_folder_str)
        except FileNotFoundError:
            message = f'上传目录不存在： {remote_folder_str}'
            raise FileNotFoundError(message)

        time_str = utils.get_time_now()
        print()
        print(f'\n{time_str}\n本地端：{local_file}\n--->\n服务器：{remote_file}')

        try:
            local_file_stat = os.stat(local_file)
        except FileNotFoundError:
            message = ''
            raise

        try:
            remote_file_stat = self.sftp_client.stat(remote_file)
            if remote_file_stat.st_size != local_file_stat.st_size or local_file_stat.st_mtime - remote_file_stat.st_mtime > 0:  # 文件大小不一致或者local文件较新
                raise FileNotFoundError
            else:    # 跳过文件
                print('已经上传，跳过')
                self.transfered_bytes_int += remote_file_stat.st_size
                return 0
        except FileNotFoundError:  # 上传文件

            try:
                remote_file_stat = self.sftp_client.put(local_file, remote_file, callback = self.__print_progress)
            except PermissionError as ex:
                print(ex)
                message = f'上传 {local_file} 失败（PermissionError），确认文件权限'

        return remote_file_stat.st_size

    def upload_a_folder(self, local_folder: str, remote_folder: str, pattern: list[str, ...]) -> int:
        '''
        将local folder上传到服务器的remote folder下，成为remote folder下的一个子目录 ，保持每个子目录下保持原始目录结构，可选择只上传某些类型的文件
        '''


        print(f'计算目录大小 {path.basename(local_folder)}')
        for root_dir_str, child_folder_lst, files_lst in os.walk(local_folder):
            for s in pattern:
                for file_str in glob.glob(f'{root_dir_str}\\*{s}'):
                    try:
                        self.total_bytes_int += os.stat(file_str).st_size
                        self.total_count_int += 1

                        total_str = utils.count_to_unit(self.total_bytes_int)
                        print(f"共 {self.total_count_int} 个文件，合计 {total_str}                        ", end = '\r')
                    except Exception as ex:
                        print(ex)
                        continue

        print()
        parent_folder_of_local = path.dirname(local_folder)  # if local_folder = "D:\Program Files\Common Files", parent_folder_of_local would be "D:\Program Files"
        for root_dir_str, child_folder_lst, files_lst in os.walk(local_folder):
            relative_remote_folder_str = root_dir_str[len(parent_folder_of_local):]
            relative_remote_folder_str = relative_remote_folder_str.replace('\\', '/')
            # print(root_dir_str, '||', parent_folder_of_local, '||', relative_remote_folder_str)

            # 建立folder
            r = self.create_remote_folder(remote_folder, relative_remote_folder_str, dummy_mode = False)
            # print(f'create {r}')

            # copy files
            for s in pattern:
                search_pattern_str = f'{root_dir_str}\\*{s}'
                local_files_lst = glob.glob(search_pattern_str)
                for file_name_str in local_files_lst:
                    file_base_name_str = path.basename(file_name_str)
                    remote_file_name = f'{remote_folder}/{relative_remote_folder_str}/{file_base_name_str}'
                    _ = self.upload_a_file(file_name_str, remote_file_name)
                    local_file_stat = os.stat(file_name_str)

                    self.transfered_bytes_int += local_file_stat.st_size
                    self.transfered_count_int += 1



        return

    def download_a_file(self, remote_file, local_file) -> int:
        '''
        download a file, 成功返回0
        '''

        # 获取远端文件属性
        try:
            remote_file_stat = self.sftp_client.stat(remote_file)
        except FileNotFoundError:
            message = f'远端文件不存在 {remote_file}'
            print(message)
            return 1

        # 获取本地文件属性
        if not os.access(local_file, os.R_OK):
            self.sftp_client.get(remote_file, local_file)
            return 0

        local_file_stat = os.stat(local_file)
        if local_file_stat.st_size != remote_file_stat.st_size or remote_file_stat.st_mtime - local_file_stat.st_mtime > 0:  # 文件大小不一致或者remote文件较新
            self.sftp_client.get(remote_file, local_file)

        return 0

    def close(self) -> int:
        '''
        关闭server链接
        '''
        try:
            self.sftp_client.close()
        except:
            pass

        return 0


if __name__ == '__main__':

    print('testing')

    server = Server(ip = '192.168.0.185')
    server.generate_sftp_client(username = 'slg010', private_key_file = '../SLG010_rsa')
    # output_f = server.sftp_client.open('/tmp/test.txt', 'a')
    # output_f.writelines('test')
    # output_f.close()
    # server.download_a_file(remote_file = '/tmp/tmp_read_resource_1681727341233295410.config', local_file = 'temp.txt')
    # server.create_remote_folder('/share/data/salus/Pro/', 'group_001')
    # print(server.sftp_client.mkdir('/share/data/salus/Pro/test'))
    # print(server.sftp_client.normalize('/share/data/salus/Pro/test/'))
    # server.upload_a_file(local_file = 'd:\\Program Files.rar', remote_file = '/share/data/salus/Pro/test/Program Files.rar')
    # server.upload_a_folder('d:\\Program Files', '/share/data/salus/Pro/test', pattern = ['.exe', 'dll'])
    # print(server.sftp_client.rmdir('/share/data/salus/Pro/test'))
    # print(os.path.getsize('d:\\Program Files\\WinRAR\\WinRAR.exe'))
    # s = server.sftp_client.stat('/share/data/salus/Pro/test/Program Files/WinRAR/WinRAR.exe')
    # s1 = server.sftp_client.stat('/share/data/salus/Pro/test/Program Files/WinRAR/WinRAR2.exe')

    # private_key_file = '../test_id_rsa'
    # private_key_file = path.realpath(path.expanduser(private_key_file))
    # private_key = paramiko.RSAKey.from_private_key_file(private_key_file)

    # client = paramiko.SSHClient()
    # client.load_system_host_keys()
    # client.connect('192.168.0.185', username = 'dtrans', pkey = private_key)
    # stdin, stdout, stderr = client.exec_command('ls -l /share/data/')

    # print(list(stdout))

    server.close()
    print('Done')
    # server.print_progress(bytes_transferred = 14346673, bytes_total = 100000000)
