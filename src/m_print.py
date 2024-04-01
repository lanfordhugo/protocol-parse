import datetime
import inspect
import sys

# 日志保存位置
file_opend = False


class MyLogger:
    def __init__(self, log_file=None):
        if log_file != None:
            self.file_path = f"log_{log_file}.txt"
        else:
            self.file_path = "log.txt"
        # print(f"Log file: {self.file_path}")
        self.file = open(self.file_path, 'a', encoding='utf-8')

    def __del__(self):
        self.file.close()

    def e_print(self, *args: object, **kwargs: object) -> None:
        color = '\033[31m'
        now = datetime.datetime.now()
        milliseconds = now.microsecond // 1000
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.{:03d}".format(milliseconds))
        caller_frame = inspect.stack()[1]
        caller_module = inspect.getmodule(caller_frame[0])
        func_name = caller_frame[3]
        line = caller_frame[2]
        message = ' '.join(map(str, args))
        output = f'{color}[{current_time}] {message} [{caller_module.__name__}.{func_name}():{line}]'
        
        print(output, **kwargs)
        self.file.write(output + '\n')
        self.file.flush()

    def d_print(self, *args: object, **kwargs: object) -> None:
        color = '\033[0m'
        now = datetime.datetime.now()
        milliseconds = now.microsecond // 1000
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.{:03d}".format(milliseconds))
        caller_frame = inspect.stack()[1]
        caller_module = inspect.getmodule(caller_frame[0])
        func_name = caller_frame[3]
        line = caller_frame[2]
        message = ' '.join(map(str, args))
        output = f'{color}[{current_time}] {message} [{caller_module.__name__}.{func_name}():{line}]'

        print(output, **kwargs)
        self.file.write(output + '\n')
        self.file.flush()
        
    def i_print(self, *args: object, **kwargs: object) -> None:
        color = '\033[34m'
        now = datetime.datetime.now()
        milliseconds = now.microsecond // 1000
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.{:03d}".format(milliseconds))
        caller_frame = inspect.stack()[1]
        caller_module = inspect.getmodule(caller_frame[0])
        func_name = caller_frame[3]
        line = caller_frame[2]
        message = ' '.join(map(str, args))
        output = f'{color}[{current_time}] {message} [{caller_module.__name__}.{func_name}():{line}]'

        print(output, **kwargs)
        self.file.write(output + '\n')
        self.file.flush()



def progress_bar(progress, rate=0):
    """
    进度条显示
    :param rate: 速率
    :param progress: 进度比例
    """
    color = '\033[0m'
    now = datetime.datetime.now()
    milliseconds = now.microsecond // 1000  # 截断为三位微秒（毫秒）
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.{:03d}".format(milliseconds))

    sys.stdout.write('\r')
    sys.stdout.write(f'{color}[{current_time}] Progress: [{progress:.2f}%][{rate:.2f}k/s]')
    sys.stdout.flush()
