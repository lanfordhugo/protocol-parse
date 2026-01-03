"""
文件名称: tcp_server.py
内容摘要: TCP日志接收服务器，支持实时解析
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-02
"""

import socket
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from tcp_log.log_entry_parser import LogEntryParser, LogEntry


class ServerState(Enum):
    """服务器状态"""
    STOPPED = "已停止"
    STARTING = "启动中"
    LISTENING = "监听中"
    CONNECTED = "已连接"
    ERROR = "错误"


@dataclass
class ClientInfo:
    """客户端信息"""
    address: str
    port: int
    connected_time: float


class TcpLogServer:
    """
    TCP日志接收服务器
    
    接收spdlog tcpsink发送的日志数据，实时解析并回调
    """
    
    def __init__(self):
        self._socket: Optional[socket.socket] = None
        self._client_socket: Optional[socket.socket] = None
        self._state = ServerState.STOPPED
        self._host = "0.0.0.0"
        self._port = 9999
        
        # 线程控制
        self._accept_thread: Optional[threading.Thread] = None
        self._recv_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 解析器
        self._parser = LogEntryParser()
        
        # 客户端信息
        self._client_info: Optional[ClientInfo] = None
        
        # 回调函数
        self._on_state_changed: Optional[Callable[[ServerState], None]] = None
        self._on_client_connected: Optional[Callable[[ClientInfo], None]] = None
        self._on_client_disconnected: Optional[Callable[[], None]] = None
        self._on_entry_received: Optional[Callable[[LogEntry], None]] = None
        self._on_log: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        
        # 统计信息
        self._total_entries = 0
        self._total_bytes = 0
    
    @property
    def state(self) -> ServerState:
        return self._state
    
    @property
    def is_running(self) -> bool:
        return self._state in (ServerState.LISTENING, ServerState.CONNECTED)
    
    @property
    def client_info(self) -> Optional[ClientInfo]:
        return self._client_info
    
    @property
    def total_entries(self) -> int:
        return self._total_entries
    
    @property
    def total_bytes(self) -> int:
        return self._total_bytes
    
    def set_callbacks(
        self,
        on_state_changed: Optional[Callable[[ServerState], None]] = None,
        on_client_connected: Optional[Callable[[ClientInfo], None]] = None,
        on_client_disconnected: Optional[Callable[[], None]] = None,
        on_entry_received: Optional[Callable[[LogEntry], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """设置回调函数"""
        self._on_state_changed = on_state_changed
        self._on_client_connected = on_client_connected
        self._on_client_disconnected = on_client_disconnected
        self._on_entry_received = on_entry_received
        self._on_log = on_log
        self._on_error = on_error
    
    def _set_state(self, state: ServerState):
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
    
    def start(self, host: str = "0.0.0.0", port: int = 9999) -> bool:
        """
        启动服务器
        
        :param host: 监听地址
        :param port: 监听端口
        :return: 是否启动成功
        """
        if self.is_running:
            self._log("服务器已在运行")
            return False
        
        self._host = host
        self._port = port
        self._set_state(ServerState.STARTING)
        
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((host, port))
            self._socket.listen(1)
            self._socket.settimeout(1.0)  # 设置超时以便检查停止事件
            
            self._stop_event.clear()
            self._total_entries = 0
            self._total_bytes = 0
            
            self._accept_thread = threading.Thread(
                target=self._accept_worker,
                daemon=True
            )
            self._accept_thread.start()
            
            self._set_state(ServerState.LISTENING)
            self._log(f"服务器启动 {host}:{port}")
            return True
            
        except Exception as e:
            self._error(f"启动失败: {e}")
            self._set_state(ServerState.ERROR)
            return False
    
    def stop(self):
        """停止服务器"""
        self._stop_event.set()
        
        # 关闭客户端连接
        if self._client_socket:
            try:
                self._client_socket.close()
            except Exception:
                pass
            self._client_socket = None
        
        # 关闭服务器socket
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        
        # 等待线程结束
        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=2.0)
        if self._recv_thread and self._recv_thread.is_alive():
            self._recv_thread.join(timeout=2.0)
        
        self._accept_thread = None
        self._recv_thread = None
        self._client_info = None
        
        self._parser.reset()
        self._set_state(ServerState.STOPPED)
        self._log("服务器已停止")
    
    def _accept_worker(self):
        """接受连接的工作线程"""
        while not self._stop_event.is_set():
            try:
                client_socket, address = self._socket.accept()
                
                # 如果已有客户端连接，拒绝新连接
                if self._client_socket:
                    self._log(f"拒绝连接 {address[0]}:{address[1]} (已有客户端)")
                    client_socket.close()
                    continue
                
                self._client_socket = client_socket
                self._client_info = ClientInfo(
                    address=address[0],
                    port=address[1],
                    connected_time=0
                )
                
                self._set_state(ServerState.CONNECTED)
                self._log(f"客户端连接 {address[0]}:{address[1]}")
                
                if self._on_client_connected:
                    self._on_client_connected(self._client_info)
                
                # 启动接收线程
                self._recv_thread = threading.Thread(
                    target=self._recv_worker,
                    daemon=True
                )
                self._recv_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    self._error(f"接受连接异常: {e}")
    
    def _recv_worker(self):
        """接收数据的工作线程"""
        self._parser.reset()
        
        try:
            while not self._stop_event.is_set():
                try:
                    self._client_socket.settimeout(1.0)
                    data = self._client_socket.recv(4096)
                    
                    if not data:
                        # 客户端断开连接
                        break
                    
                    self._total_bytes += len(data)
                    
                    # 解析日志条目
                    try:
                        text = data.decode('utf-8')
                        entries = self._parser.feed(text)
                        
                        for entry in entries:
                            self._total_entries += 1
                            if self._on_entry_received:
                                self._on_entry_received(entry)
                                
                    except UnicodeDecodeError:
                        self._error("解码错误，非UTF-8数据")
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if not self._stop_event.is_set():
                        self._error(f"接收数据异常: {e}")
                    break
        
        finally:
            # 处理剩余数据
            remaining = self._parser.flush()
            for entry in remaining:
                self._total_entries += 1
                if self._on_entry_received:
                    self._on_entry_received(entry)
            
            # 清理客户端连接
            if self._client_socket:
                try:
                    self._client_socket.close()
                except Exception:
                    pass
                self._client_socket = None
            
            self._client_info = None
            
            if not self._stop_event.is_set():
                self._set_state(ServerState.LISTENING)
                self._log("客户端断开连接")
                
                if self._on_client_disconnected:
                    self._on_client_disconnected()
    
    def reset_stats(self):
        """重置统计信息"""
        self._total_entries = 0
        self._total_bytes = 0
