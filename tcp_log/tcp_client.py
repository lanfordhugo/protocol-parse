"""
文件名称: tcp_client.py
内容摘要: TCP日志发送客户端，模拟spdlog tcpsink行为
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-02
"""

import socket
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

from tcp_log.log_entry_parser import LogEntryParser, LogEntry


class ClientState(Enum):
    """客户端状态"""
    DISCONNECTED = "未连接"
    CONNECTING = "连接中"
    CONNECTED = "已连接"
    SENDING = "发送中"
    PAUSED = "已暂停"
    ERROR = "错误"


@dataclass
class SendProgress:
    """发送进度信息"""
    current: int        # 当前发送条数
    total: int          # 总条数
    bytes_sent: int     # 已发送字节数
    elapsed_time: float # 已用时间(秒)
    current_entry: Optional[LogEntry] = None  # 当前发送的条目


class TcpLogClient:
    """
    TCP日志发送客户端
    
    模拟spdlog tcpsink的行为，从本地日志文件读取内容并通过TCP发送
    """
    
    def __init__(self):
        self._socket: Optional[socket.socket] = None
        self._state = ClientState.DISCONNECTED
        self._host = "127.0.0.1"
        self._port = 9999
        
        # 发送控制
        self._send_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 默认不暂停
        
        # 回调函数
        self._on_state_changed: Optional[Callable[[ClientState], None]] = None
        self._on_progress: Optional[Callable[[SendProgress], None]] = None
        self._on_log: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        
        # 发送设置
        self._send_interval_ms = 100
        self._loop_send = False
        self._disconnect_after_send = False
    
    @property
    def state(self) -> ClientState:
        return self._state
    
    @property
    def is_connected(self) -> bool:
        return self._state in (ClientState.CONNECTED, ClientState.SENDING, ClientState.PAUSED)
    
    def set_callbacks(
        self,
        on_state_changed: Optional[Callable[[ClientState], None]] = None,
        on_progress: Optional[Callable[[SendProgress], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """设置回调函数"""
        self._on_state_changed = on_state_changed
        self._on_progress = on_progress
        self._on_log = on_log
        self._on_error = on_error
    
    def _set_state(self, state: ClientState):
        """设置状态并触发回调"""
        self._state = state
        if self._on_state_changed:
            self._on_state_changed(state)
    
    def _log(self, message: str):
        """记录日志"""
        if self._on_log:
            self._on_log(message)
    
    def _error(self, message: str):
        """记录错误"""
        if self._on_error:
            self._on_error(message)
    
    def connect(self, host: str = "127.0.0.1", port: int = 9999) -> bool:
        """
        连接到服务器
        
        :param host: 服务器地址
        :param port: 服务器端口
        :return: 是否连接成功
        """
        if self.is_connected:
            self._log("已经连接，请先断开")
            return False
        
        self._host = host
        self._port = port
        self._set_state(ClientState.CONNECTING)
        
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((host, port))
            self._socket.settimeout(None)
            
            self._set_state(ClientState.CONNECTED)
            self._log(f"连接成功 {host}:{port}")
            return True
            
        except socket.timeout:
            self._error(f"连接超时 {host}:{port}")
            self._set_state(ClientState.DISCONNECTED)
            return False
            
        except Exception as e:
            self._error(f"连接失败: {e}")
            self._set_state(ClientState.ERROR)
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_send()
        
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        
        self._set_state(ClientState.DISCONNECTED)
        self._log("已断开连接")
    
    def start_send(
        self,
        log_file: str,
        interval_ms: int = 100,
        loop_send: bool = False,
        disconnect_after: bool = False
    ):
        """
        开始发送日志文件
        
        :param log_file: 日志文件路径
        :param interval_ms: 发送间隔(毫秒)
        :param loop_send: 是否循环发送
        :param disconnect_after: 发送完成后是否断开
        """
        if not self.is_connected:
            self._error("未连接到服务器")
            return
        
        if self._state == ClientState.SENDING:
            self._error("正在发送中")
            return
        
        if not Path(log_file).exists():
            self._error(f"文件不存在: {log_file}")
            return
        
        self._send_interval_ms = interval_ms
        self._loop_send = loop_send
        self._disconnect_after_send = disconnect_after
        
        self._stop_event.clear()
        self._pause_event.set()
        
        self._send_thread = threading.Thread(
            target=self._send_worker,
            args=(log_file,),
            daemon=True
        )
        self._send_thread.start()
    
    def _send_worker(self, log_file: str):
        """发送工作线程"""
        self._set_state(ClientState.SENDING)
        
        try:
            # 解析日志文件
            entries = LogEntryParser.parse_file(log_file)
            total = len(entries)
            
            if total == 0:
                self._log("日志文件为空")
                self._set_state(ClientState.CONNECTED)
                return
            
            self._log(f"开始发送 {Path(log_file).name} ({total}条)")
            
            start_time = time.time()
            bytes_sent = 0
            current = 0
            
            while not self._stop_event.is_set():
                for i, entry in enumerate(entries):
                    # 检查停止
                    if self._stop_event.is_set():
                        break
                    
                    # 检查暂停
                    self._pause_event.wait()
                    if self._stop_event.is_set():
                        break
                    
                    # 发送数据
                    try:
                        data = entry.raw_text.encode('utf-8')
                        self._socket.sendall(data)
                        bytes_sent += len(data)
                        current = i + 1
                        
                        # 更新进度
                        progress = SendProgress(
                            current=current,
                            total=total,
                            bytes_sent=bytes_sent,
                            elapsed_time=time.time() - start_time,
                            current_entry=entry
                        )
                        if self._on_progress:
                            self._on_progress(progress)
                        
                    except Exception as e:
                        self._error(f"发送失败: {e}")
                        self._set_state(ClientState.ERROR)
                        return
                    
                    # 发送间隔
                    time.sleep(self._send_interval_ms / 1000.0)
                
                # 是否循环发送
                if not self._loop_send:
                    break
                
                self._log("循环发送...")
            
            self._log(f"发送完成: {current}条, {bytes_sent}字节")
            
            if self._disconnect_after_send:
                self.disconnect()
            else:
                self._set_state(ClientState.CONNECTED)
                
        except Exception as e:
            self._error(f"发送异常: {e}")
            self._set_state(ClientState.ERROR)
    
    def pause_send(self):
        """暂停发送"""
        if self._state == ClientState.SENDING:
            self._pause_event.clear()
            self._set_state(ClientState.PAUSED)
            self._log("已暂停")
    
    def resume_send(self):
        """恢复发送"""
        if self._state == ClientState.PAUSED:
            self._pause_event.set()
            self._set_state(ClientState.SENDING)
            self._log("已恢复")
    
    def stop_send(self):
        """停止发送"""
        self._stop_event.set()
        self._pause_event.set()  # 确保线程不会卡在暂停状态
        
        if self._send_thread and self._send_thread.is_alive():
            self._send_thread.join(timeout=2.0)
        
        self._send_thread = None
        
        if self.is_connected:
            self._set_state(ClientState.CONNECTED)
            self._log("已停止发送")
