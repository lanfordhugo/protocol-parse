# 添加模块文档字符串
"""
这是一个日志记录模块。

该模块提供了两个主要的日志记录类：ComLogger 和 MyLogger。
ComLogger 用于记录通信相关的日志，而 MyLogger 用于记录一般的应用程序日志。
模块还包含了日志模式的枚举类 LogMode，以及一个用于显示进度条的辅助函数。

主要功能：
1. 支持多种日志记录模式（仅保存、仅打印、保存并打印）
2. 自动日志文件轮换
3. 线程安全的日志记录
4. 支持彩色日志输出
5. 提供详细的调用者信息

版本：1.0
"""

import atexit
import datetime
import glob
import inspect
import os
import sys
import threading
import time
from enum import Enum


class LogMode(Enum):
    """
    日志模式枚举类。
    """

    SAVE_ONLY = 1  # 仅保存，不打印
    PRINT_ONLY = 2  # 仅打印，不保存
    PRINT_AND_SAVE = 3  # 打印并保存


class ComLogger:
    """
    通信日志记录器类。
    """

    _file_paths = set()
    _exit_handler_registered = False
    _lock = threading.Lock()

    def __new__(
        cls, log_file=0, log_mode=LogMode.SAVE_ONLY, log_dir=None, max_size=1024 * 1024, max_files=3
    ):
        """
        创建或返回现有的 ComLogger 实例。
        :param log_file: 日志文件名，生成的文件名为log_{log_file}_com.txt
        :param log_mode: 日志模式
        :param log_dir: 可选的日志文件保存目录
        :param max_size: 日志文件最大大小，默认1MB
        :param max_files: 最大保留的日志文件数量
        :return: ComLogger 实例
        """
        log_dir = log_dir or "log"
        file_name = f"log_{log_file}_com.txt"
        file_path = os.path.join(log_dir, file_name)

        # 检查是否已经存在相同路径的实例
        if file_path in cls._file_paths:
            raise ValueError(f"日志文件路径 '{file_path}' 已存在。")

        # 创建新实例并存储路径
        instance = super(ComLogger, cls).__new__(cls)
        cls._file_paths.add(file_path)
        return instance

    def __init__(
        self,
        log_file=0,
        log_mode=LogMode.SAVE_ONLY,
        log_dir=None,
        max_size=1024 * 1024,
        max_files=3,
    ):
        """
        初始化通信日志记录器
        :param log_file: 日志文件名，生成的文件名为log_{log_file}_com.txt
        :param log_mode: 日志模式
        :param log_dir: 可选的日志文件保存目录
        :param max_size: 日志文件最大大小，默认1MB
        :param max_files: 最大保留的日志文件数量
        """
        # 确保初始化只执行一次
        if hasattr(self, "initialized") and self.initialized:
            return

        self.config = {
            "max_files": max_files,
            "base_file_name": f"log_{log_file}_com",
            "log_dir": log_dir or "log",
            "log_mode": log_mode,
            "max_size": max_size,
        }
        self.file_name = f"{self.config['base_file_name']}.txt"
        os.makedirs(self.config["log_dir"], exist_ok=True)
        self.com_file_path = os.path.join(self.config["log_dir"], self.file_name)
        self.com_file = None
        self.open_com_file()
        if not ComLogger._exit_handler_registered:
            atexit.register(self._exit_handler)
            ComLogger._exit_handler_registered = True

        # 标记初始化完成
        self.initialized = True

    @classmethod
    def _exit_handler(cls):
        """
        程序退出时的处理方法，关闭所有未关闭的文件。
        """
        for file_path in list(cls._file_paths):  # 使用列表复制以避免在迭代时修改集合
            if os.path.exists(file_path):
                try:
                    # 尝试打开文件并关闭它
                    with open(file_path, "a", encoding="utf-8") as f:
                        f.close()
                    cls._file_paths.remove(file_path)
                except Exception as e:
                    print(f"关闭文件 {file_path} 时发生错误: {e}")
            else:
                print(f"文件 {file_path} 不存在，已从列表中移除")
                cls._file_paths.remove(file_path)

    def open_com_file(self):
        """
        打开通信日志文件。
        """
        if self.com_file is None or self.com_file.closed:
            try:
                # pylint: disable=R1732
                self.com_file = open(self.com_file_path, "a", encoding="utf-8")
                # pylint: enable=R1732
            except IOError as e:
                raise IOError(f"无法打开日志文件 {self.com_file_path}: {str(e)}") from e

    def close_file(self):
        """
        关闭通信日志文件。
        """
        if self.com_file and not self.com_file.closed:
            self.com_file.flush()
            self.com_file.close()

    def __enter__(self):
        """
        上下文管理器的进入方法。
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器的退出方法。关闭文件。
        """
        self.close_file()

    def __del__(self):
        """
        析构方法。确保对象被销毁时关闭文件。
        """
        self.close_file()

    def rotate_log_file(self):
        """
        滚动日志文件。
        """
        self.close_file()
        # 获取所有相关的日志文件
        file_pattern = os.path.join(self.config["log_dir"], f"{self.config['base_file_name']}*.txt")
        existing_files = glob.glob(file_pattern)
        existing_files.sort(key=os.path.getmtime, reverse=True)
        # 如果文件数量超过限制，删除最旧的文件
        while len(existing_files) >= self.config["max_files"]:
            os.remove(existing_files.pop())
        # 重命名当前文件
        # 使用毫秒级时间戳避免同一秒内的文件名冲突
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 保留毫秒前3位
        new_file_name = f"{self.config['base_file_name']}_{timestamp}.txt"
        new_file_path = os.path.join(self.config["log_dir"], new_file_name)
        os.rename(self.com_file_path, new_file_path)
        # 创建新的日志文件
        self.open_com_file()

    def com_print(self, tx_data: bytes, cmd: int, addr: int) -> None:
        """
        打印通信日志。
        :param tx_data: 发送的数据
        :param cmd: 命令
        :param addr: 地址
        """
        try:
            log_message = self._create_log_message(tx_data, cmd, addr)
            hex_data = " ".join([f"{b:02X}" for b in tx_data])
            hex_lines = [hex_data[i : i + 75] for i in range(0, len(hex_data), 75)]
            log_message += "\n".join(hex_lines) + "\n"

            with self._lock:
                if self.config["log_mode"] in [LogMode.SAVE_ONLY, LogMode.PRINT_AND_SAVE]:
                    self.open_com_file()
                    if self.com_file:
                        self.com_file.write(log_message)
                        self.com_file.flush()
                        if self.com_file.tell() >= self.config["max_size"]:
                            self.rotate_log_file()
                if self.config["log_mode"] in [LogMode.PRINT_ONLY, LogMode.PRINT_AND_SAVE]:
                    print(log_message)

        except Exception as e:  # pylint: disable=W0718
            self._handle_exception(e, cmd, tx_data)

    def _create_log_message(self, tx_data: bytes, cmd: int, addr: int) -> str:
        """
        创建日志消息。
        :param tx_data: 发送的数据
        :param cmd: 命令
        :param addr: 地址
        :return: 格式化的日志消息
        """
        cmd_hex = f"0x{cmd:02X}" if isinstance(cmd, int) else str(cmd)
        caller_frame = inspect.currentframe()
        if caller_frame:
            caller_frame = caller_frame.f_back
        if caller_frame:
            caller_file = os.path.basename(caller_frame.f_code.co_filename)
            caller_line = caller_frame.f_lineno
        else:
            caller_file = "UnknownFile"
            caller_line = 0
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return (
            f"[{timestamp}] "
            f"[{addr}] yy com: Send {len(tx_data)} Bytes "
            f"(cmd={cmd}[{cmd_hex}]) "
            f"[{caller_file}:{caller_line} pid:{os.getpid()} tid:{threading.get_ident()}]:\n"
        )

    def _handle_exception(self, e: Exception, cmd: int, tx_data: bytes) -> None:
        """
        处理异常。
        :param e: 异常
        :param cmd: 命令
        :param tx_data: 发送的数据
        """
        print(f"com_print 发生异常: {e}")
        error_message = f"打印通信日志时发生异常: {e}\n"
        error_detail = f"异常详情: cmd={cmd}, tx_data长度={len(tx_data)}\n"
        if self.config["log_mode"] in [LogMode.SAVE_ONLY, LogMode.PRINT_AND_SAVE]:
            self.open_com_file()
            if self.com_file:
                self.com_file.write(error_message)
                self.com_file.write(error_detail)
                self.com_file.flush()
        if self.config["log_mode"] in [LogMode.PRINT_ONLY, LogMode.PRINT_AND_SAVE]:
            print(error_message)
            print(error_detail)


class MyLogger:
    """
    日志记录器类。
    """

    _file_paths = set()
    _exit_handler_registered = False
    _lock = threading.Lock()

    def __new__(
        cls,
        log_file=0,
        log_mode=LogMode.PRINT_ONLY,
        log_dir=None,
        max_size=1024 * 1024,
        max_files=3,
    ):
        """
        创建或返回现有的 MyLogger 实例。
        :param log_file: 日志文件名，生成的文件名为log_{log_file}.txt
        :param log_mode: 日志模式
        :param log_dir: 可选的日志文件保存目录
        :param max_size: 日志文件最大大小，默认1MB
        :param max_files: 最大保留的日志文件数量
        :return: MyLogger 实例
        """
        # PRINT_ONLY模式下不需要检查文件路径冲突
        if log_mode == LogMode.PRINT_ONLY:
            return super(MyLogger, cls).__new__(cls)

        log_dir = log_dir or "log"
        file_name = f"log_{log_file}.txt"
        file_path = os.path.join(log_dir, file_name)

        # 检查是否已经存在相同路径的实例
        if file_path in cls._file_paths:
            raise ValueError(f"日志文件路径 '{file_path}' 已存在。")

        # 创建新实例并存储路径
        instance = super(MyLogger, cls).__new__(cls)
        cls._file_paths.add(file_path)
        return instance

    def __init__(
        self,
        log_file=0,
        log_mode=LogMode.PRINT_ONLY,
        log_dir=None,
        max_size=1024 * 1024,
        max_files=3,
    ):
        """
        初始化日志记录器
        :param log_file: 日志文件名，生成的文件名为log_{log_file}.txt
        :param log_mode: 日志模式
        :param log_dir: 可选的日志文件保存目录
        :param max_size: 日志文件最大大小，默认1MB
        :param max_files: 最大保留的日志文件数量
        """
        # 确保初始化只执行一次
        if hasattr(self, "initialized") and self.initialized:
            return

        self.config = {
            "max_files": max_files,
            "base_file_name": f"log_{log_file}",
            "log_dir": log_dir or "log",
            "log_mode": log_mode,
            "max_size": max_size,
        }

        # 只有在需要保存文件的模式下才创建文件相关资源
        if log_mode in [LogMode.SAVE_ONLY, LogMode.PRINT_AND_SAVE]:
            self.file_name = f"{self.config['base_file_name']}.txt"
            os.makedirs(self.config["log_dir"], exist_ok=True)
            self.file_path = os.path.join(self.config["log_dir"], self.file_name)
            self.file = None
            self.last_flush_time = time.time()
            self.flush_interval = 60
            self.open_file()
            if not MyLogger._exit_handler_registered:
                atexit.register(self._exit_handler)
                MyLogger._exit_handler_registered = True
        else:
            # PRINT_ONLY模式下不创建文件相关资源
            self.file_name = None
            self.file_path = None
            self.file = None
            self.last_flush_time = None
            self.flush_interval = None

        # 标记初始化完成
        self.initialized = True

    @classmethod
    def _exit_handler(cls):
        """
        程序退出时的处理方法，关闭所有未关闭的文件。
        """
        for file_path in list(cls._file_paths):  # 使用列表复制以避免在迭代时修改集合
            if os.path.exists(file_path):
                try:
                    # 尝试打开文件并关闭它
                    with open(file_path, "a", encoding="utf-8") as f:
                        f.close()
                    cls._file_paths.remove(file_path)
                except Exception as e:
                    print(f"关闭文件 {file_path} 时发生错误: {e}")
            else:
                print(f"文件 {file_path} 不存在，已从列表中移除")
                cls._file_paths.remove(file_path)

    def open_file(self):
        """
        打开日志文件。如果文件未打开或已关闭，则重新打开。
        只有在需要保存文件的模式下才执行。
        """
        if self.config["log_mode"] == LogMode.PRINT_ONLY:
            return  # PRINT_ONLY模式下不操作文件

        print("打开日志文件:", self.file_path)
        if self.file is None or self.file.closed:
            try:
                # pylint: disable=R1732
                self.file = open(self.file_path, "a", encoding="utf-8")
                # pylint: enable=R1732
            except Exception as e:
                print(f"无法打开日志文件 {self.file_path}: {e}")
                raise

    def close_file(self):
        """
        关闭所有日志文件。
        """
        if self.file and not self.file.closed:
            self.file.flush()
            self.file.close()

    def __enter__(self):
        """
        上下文管理器的进入方法。
        :return: 返回 MyLogger 实例自身
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器的退出方法。关闭文件。
        :param exc_type: 异常类型
        :param exc_val: 异常值
        :param exc_tb: 异常追踪信息
        """
        self.close_file()

    def __del__(self):
        """
        析构方法。确保对象被销毁时关闭文件。
        """
        self.close_file()

    def check_and_flush(self):
        """
        检查是否需要刷新文件，如果距离上次刷新时间超过设定间隔，则刷新文件。
        """
        if self.config["log_mode"] == LogMode.PRINT_ONLY:
            return  # PRINT_ONLY模式下不操作文件

        current_time = time.time()
        if current_time - self.last_flush_time > self.flush_interval:
            if self.file:
                self.file.flush()
            self.last_flush_time = current_time

    def rotate_log_file(self):
        """
        滚动日志文件。
        """
        if self.config["log_mode"] == LogMode.PRINT_ONLY:
            return  # PRINT_ONLY模式下不操作文件

        self.close_file()
        print(f"关闭文件: {self.file_path}")

        # 获取所有相关的日志文件
        file_pattern = os.path.join(self.config["log_dir"], f"{self.config['base_file_name']}*.txt")
        existing_files = glob.glob(file_pattern)
        existing_files.sort(key=os.path.getmtime, reverse=True)
        print(f"现有日志文件: {existing_files}")

        # 如果文件数量超过限制，删除最旧的文件
        while len(existing_files) >= self.config["max_files"]:
            oldest_file = existing_files.pop()
            try:
                os.remove(oldest_file)
                print(f"删除旧文件: {oldest_file}")
            except Exception as e:
                print(f"无法删除文件 {oldest_file}: {e}")

        # 重命名当前文件
        # 使用毫秒级时间戳避免同一秒内的文件名冲突
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 保留毫秒前3位
        new_file_name = f"{self.config['base_file_name']}_{timestamp}.txt"
        new_file_path = os.path.join(self.config["log_dir"], new_file_name)
        try:
            os.rename(self.file_path, new_file_path)
            print(f"重命名文件: {self.file_path} -> {new_file_path}")
        except PermissionError as e:
            print(f"无法重命名文件: {e}")
        except Exception as e:
            print(f"重命名文件时发生其他错误: {e}")

        # 创建新的日志文件
        self.open_file()
        print(f"创建新文件: {self.file_path}")

    def _log(self, color, message, caller_info):
        """
        根据日志模式处理日志。
        :param color: 日志颜色
        :param message: 日志消息
        :param caller_info: 调用者信息
        """
        now = datetime.datetime.now()
        milliseconds = now.microsecond // 1000
        current_time = now.strftime(f"%Y-%m-%d %H:%M:%S.{milliseconds:03d}")
        output = (
            f"{color}[{current_time}] {message} [{caller_info}]\033[0m\n"  # 在每行结束时添加重置颜色的 ANSI 转义序列
        )
        with self._lock:
            if self.config["log_mode"] in [LogMode.PRINT_ONLY, LogMode.PRINT_AND_SAVE]:
                print(output, end="")
            if self.config["log_mode"] in [LogMode.SAVE_ONLY, LogMode.PRINT_AND_SAVE]:
                if self.file:
                    self.file.write(output)
                    self.file.flush()
                    if self.file.tell() >= self.config["max_size"]:
                        self.rotate_log_file()

    def e_print(self, *args: object) -> None:
        """
        打印错误日志。
        :param args: 要打印的参数
        """
        color = "\033[31m"  # 红色
        caller_frame = inspect.stack()[1]
        caller_module = inspect.getmodule(caller_frame[0])
        func_name = caller_frame[3]
        line = caller_frame[2]
        message = " ".join(map(str, args))
        caller_module_name = caller_module.__name__ if caller_module else "UnknownModule"
        caller_info = f"{caller_module_name}.{func_name}():{line}"
        self._log(color, message, caller_info)

    def d_print(self, *args: object) -> None:
        """
        打印调试日志。
        :param args: 要打印的参数
        """
        color = "\033[0m"  # 白色
        caller_frame = inspect.stack()[1]
        caller_module = inspect.getmodule(caller_frame[0])
        func_name = caller_frame[3]
        line = caller_frame[2]
        message = " ".join(map(str, args))
        caller_module_name = caller_module.__name__ if caller_module else "UnknownModule"
        caller_info = f"{caller_module_name}.{func_name}():{line}"
        self._log(color, message, caller_info)

    def i_print(self, *args: object) -> None:
        """
        打印信息日志。
        :param args: 要打印的参数
        """
        color = "\033[32m"  # 绿色
        caller_frame = inspect.stack()[1]
        caller_module = inspect.getmodule(caller_frame[0])
        func_name = caller_frame[3]
        line = caller_frame[2]
        message = " ".join(map(str, args))
        caller_module_name = caller_module.__name__ if caller_module else "UnknownModule"
        caller_info = f"{caller_module_name}.{func_name}():{line}"
        self._log(color, message, caller_info)

    def printf(self, *args: object) -> None:
        """
        打印信息日志。
        :param args: 要打印的参数
        """
        message = " ".join(map(str, args))
        with self._lock:
            if self.config["log_mode"] in [LogMode.PRINT_ONLY, LogMode.PRINT_AND_SAVE]:
                print(message)
            if self.config["log_mode"] in [LogMode.SAVE_ONLY, LogMode.PRINT_AND_SAVE]:
                if self.file:
                    self.file.write(message + "\n")
                    self.file.flush()
                    if self.file.tell() >= self.config["max_size"]:
                        self.rotate_log_file()


# 进度条显示
def progress_bar(progress, rate=0):
    """
    进度条显示
    :param rate: 速率
    :param progress: 进度比例
    """
    color = "\033[0m"
    now = datetime.datetime.now()
    milliseconds = now.microsecond // 1000  # 截断为三位微秒（毫秒）
    current_time = now.strftime(f"%Y-%m-%d %H:%M:%S.{milliseconds:03d}")
    sys.stdout.write("\r")
    sys.stdout.write(f"{color}[{current_time}] Progress: [{progress:.2f}%][{rate:.2f}k/s]\033[0m")
    sys.stdout.flush()
