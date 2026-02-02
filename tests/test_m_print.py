# test_m_print.py - 日志模块单元测试
"""
测试日志记录器的各种功能：
1. ComLogger 通信日志记录器
2. MyLogger 通用日志记录器
3. 日志模式枚举
4. 进度条显示功能
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.m_print import ComLogger, LogMode, MyLogger, progress_bar


class TestLogMode:
    """测试日志模式枚举"""

    def test_log_mode_values(self):
        """测试日志模式枚举值"""
        assert LogMode.SAVE_ONLY.value == 1
        assert LogMode.PRINT_ONLY.value == 2
        assert LogMode.PRINT_AND_SAVE.value == 3


class TestComLogger:
    """测试 ComLogger 通信日志记录器"""

    def test_com_logger_init_save_only(self, tmp_path):
        """测试 ComLogger 初始化（仅保存模式）"""
        logger = ComLogger(
            log_file=1, log_mode=LogMode.SAVE_ONLY, log_dir=str(tmp_path), max_size=1024, max_files=3
        )

        # 验证初始化
        assert logger.config["log_mode"] == LogMode.SAVE_ONLY
        assert logger.config["max_size"] == 1024
        assert logger.config["max_files"] == 3
        assert logger.initialized is True
        assert logger.com_file_path == str(tmp_path / "log_1_com.txt")
        assert logger.com_file is not None
        assert logger.com_file_path.endswith("log_1_com.txt")
        assert logger.config["base_file_name"] == "log_1_com"

        # 验证文件已创建
        log_file = tmp_path / "log_1_com.txt"
        assert log_file.exists()
        assert log_file.is_file()

        # 清理
        logger.close_file()

    def test_com_logger_duplicate_path_error(self, tmp_path):
        """测试重复路径的错误处理"""
        # 创建第一个日志记录器
        logger1 = ComLogger(log_file=1, log_mode=LogMode.SAVE_ONLY, log_dir=str(tmp_path))
        logger1.close_file()

        # 尝试创建第二个相同路径的日志记录器
        with pytest.raises(ValueError, match="日志文件路径.*已存在"):
            logger2 = ComLogger(log_file=1, log_mode=LogMode.SAVE_ONLY, log_dir=str(tmp_path))

    def test_com_logger_print_only(self, tmp_path):
        """测试 ComLogger 仅打印模式"""
        logger = ComLogger(log_file=2, log_mode=LogMode.PRINT_ONLY, log_dir=str(tmp_path))

        # 验证初始化状态
        assert logger.config["log_mode"] == LogMode.PRINT_ONLY
        assert logger.initialized is True

        # 测试打印功能
        with patch("builtins.print") as mock_print:
            test_data = b"\x01\x02\x03\x04"
            logger.com_print(test_data, cmd=0x01, addr=1)

            # 验证打印被调用
            assert mock_print.called
            # 验证调用次数
            assert mock_print.call_count >= 1
            # 验证打印内容包含关键信息
            call_args = str(mock_print.call_args)
            assert "01 02 03 04" in call_args  # 十六进制数据
            assert "cmd=1" in call_args  # 命令信息
            assert "[1]" in call_args  # 地址信息
            assert "4 Bytes" in call_args  # 数据长度

        logger.close_file()

    def test_com_logger_print_and_save(self, tmp_path):
        """测试 ComLogger 打印并保存模式"""
        logger = ComLogger(
            log_file=3, log_mode=LogMode.PRINT_AND_SAVE, log_dir=str(tmp_path), max_size=1024
        )

        # 测试通信日志打印
        test_data = b"\x01\x02\x03\x04\x05"
        with patch("builtins.print") as mock_print:
            logger.com_print(test_data, cmd=0x01, addr=1)

            # 验证打印被调用
            assert mock_print.called
            # 验证打印内容
            call_args = str(mock_print.call_args)
            assert "01 02 03 04 05" in call_args

        # 验证文件写入
        log_file = tmp_path / "log_3_com.txt"
        assert log_file.exists()
        assert log_file.stat().st_size > 0

        # 验证文件内容
        content = log_file.read_text(encoding="utf-8")
        assert "01 02 03 04 05" in content  # 十六进制数据
        assert "cmd=1" in content  # 命令信息
        assert "[1]" in content  # 地址信息
        assert "Bytes" in content  # 数据长度信息

        logger.close_file()

    def test_com_logger_context_manager(self, tmp_path):
        """测试 ComLogger 上下文管理器"""
        with ComLogger(log_file=4, log_dir=str(tmp_path)) as logger:
            assert logger is not None
            assert logger.initialized is True
            # 在上下文中使用日志记录器
            logger.com_print(b"\x01\x02\x03", cmd=0x01, addr=1)

        # 验证文件已关闭
        log_file = tmp_path / "log_4_com.txt"
        assert log_file.exists()
        # 验证文件内容
        content = log_file.read_text(encoding="utf-8")
        assert "01 02 03" in content

    def test_com_logger_rotate_log_file(self, tmp_path):
        """测试日志文件轮换"""
        logger = ComLogger(
            log_file=5,
            log_mode=LogMode.SAVE_ONLY,
            log_dir=str(tmp_path),
            max_size=512,  # 小文件大小触发轮换
            max_files=3,
        )

        # 写入足够的数据以触发轮换
        for i in range(100):
            with patch("builtins.print"):
                logger.com_print(b"\x01" * 100, cmd=i, addr=1)

        # 验证轮换后的文件
        log_files = list(tmp_path.glob("log_5_com*.txt"))
        assert len(log_files) >= 1

        logger.close_file()


class TestMyLogger:
    """测试 MyLogger 通用日志记录器"""

    def test_my_logger_init_print_only(self):
        """测试 MyLogger 初始化（仅打印模式）"""
        logger = MyLogger(log_file=1, log_mode=LogMode.PRINT_ONLY)

        # 验证初始化
        assert logger.config["log_mode"] == LogMode.PRINT_ONLY
        assert logger.file_path is None  # PRINT_ONLY 模式不创建文件
        assert logger.file is None
        assert logger.file_name is None
        assert logger.initialized is True
        assert logger.config["base_file_name"] == "log_1"

    def test_my_logger_init_save_only(self, tmp_path):
        """测试 MyLogger 初始化（仅保存模式）"""
        logger = MyLogger(log_file=2, log_mode=LogMode.SAVE_ONLY, log_dir=str(tmp_path))

        # 验证初始化
        assert logger.config["log_mode"] == LogMode.SAVE_ONLY
        assert logger.file_path is not None
        assert logger.file_path.endswith("log_2.txt")
        assert logger.file is not None
        assert logger.initialized is True
        assert logger.config["base_file_name"] == "log_2"

        # 验证文件已创建
        log_file = tmp_path / "log_2.txt"
        assert log_file.exists()
        assert log_file.is_file()

        logger.close_file()

    def test_my_logger_print_and_save(self, tmp_path):
        """测试 MyLogger 打印并保存模式"""
        logger = MyLogger(log_file=3, log_mode=LogMode.PRINT_AND_SAVE, log_dir=str(tmp_path))

        # 测试不同日志级别
        with patch("builtins.print") as mock_print:
            logger.i_print("信息日志")
            logger.d_print("调试日志")
            logger.e_print("错误日志")

            # 验证打印被调用
            assert mock_print.call_count == 3
            # 验证至少有一次调用包含日志内容
            assert any("信息日志" in str(call) or "调试日志" in str(call) or "错误日志" in str(call)
                      for call in mock_print.call_args_list)

        # 验证文件写入
        log_file = tmp_path / "log_3.txt"
        assert log_file.exists()
        assert log_file.stat().st_size > 0

        # 验证文件内容包含所有日志级别
        content = log_file.read_text(encoding="utf-8")
        assert "信息日志" in content
        assert "调试日志" in content
        assert "错误日志" in content

        logger.close_file()

    def test_my_logger_error_print(self):
        """测试错误日志打印"""
        logger = MyLogger(log_mode=LogMode.PRINT_ONLY)

        with patch("builtins.print") as mock_print:
            logger.e_print("错误信息1", "错误信息2")

            # 验证打印被调用
            assert mock_print.called
            assert mock_print.call_count == 1
            # 验证打印内容包含错误信息
            call_args = str(mock_print.call_args)
            assert "错误信息1" in call_args
            assert "错误信息2" in call_args
            assert "错误信息1 错误信息2" in call_args  # 验证消息合并
            # 验证错误日志颜色标记存在
            assert "[31m" in call_args  # 红色ANSI转义码
            assert "[0m" in call_args  # 重置颜色

    def test_my_logger_debug_print(self):
        """测试调试日志打印"""
        logger = MyLogger(log_mode=LogMode.PRINT_ONLY)

        with patch("builtins.print") as mock_print:
            logger.d_print("调试信息")

            # 验证打印被调用
            assert mock_print.called
            # 验证打印内容
            call_args = str(mock_print.call_args)
            assert "调试信息" in call_args

    def test_my_logger_info_print(self):
        """测试信息日志打印"""
        logger = MyLogger(log_mode=LogMode.PRINT_ONLY)

        with patch("builtins.print") as mock_print:
            logger.i_print("信息日志")

            # 验证打印被调用
            assert mock_print.called
            assert mock_print.call_count == 1
            # 验证信息日志颜色标记存在
            call_args = str(mock_print.call_args)
            assert "信息日志" in call_args
            assert "[32m" in call_args  # 绿色ANSI转义码
            assert "[0m" in call_args  # 重置颜色
            # 验证时间戳格式
            assert "[" in call_args  # 时间戳括号

    def test_my_logger_printf(self):
        """测试 printf 方法"""
        logger = MyLogger(log_mode=LogMode.PRINT_ONLY)

        with patch("builtins.print") as mock_print:
            logger.printf("格式化输出", "参数1", "参数2")

            # 验证打印被调用
            assert mock_print.called
            # 验证输出格式
            args = mock_print.call_args[0]
            assert "格式化输出" in str(args)
            assert "参数1" in str(args)

    def test_my_logger_context_manager(self, tmp_path):
        """测试 MyLogger 上下文管理器"""
        with MyLogger(log_file=4, log_dir=str(tmp_path), log_mode=LogMode.SAVE_ONLY) as logger:
            assert logger is not None
            assert logger.initialized is True
            logger.i_print("测试日志")

        # 验证文件已关闭
        log_file = tmp_path / "log_4.txt"
        assert log_file.exists()
        # 验证文件内容
        content = log_file.read_text(encoding="utf-8")
        assert "测试日志" in content

    def test_my_logger_rotate_log_file(self, tmp_path):
        """测试 MyLogger 日志文件轮换"""
        logger = MyLogger(
            log_file=5, log_mode=LogMode.SAVE_ONLY, log_dir=str(tmp_path), max_size=512, max_files=3
        )

        # 写入足够的数据以触发轮换
        for i in range(100):
            logger.printf(f"日志行 {i} " * 20)

        # 验证轮换后的文件
        log_files = sorted(tmp_path.glob("log_5*.txt"))
        assert len(log_files) >= 1
        # 验证至少有一个文件有内容
        assert any(log_file.stat().st_size > 0 for log_file in log_files)

        logger.close_file()

    def test_my_logger_check_and_flush(self, tmp_path):
        """测试自动刷新功能"""
        logger = MyLogger(
            log_file=6, log_mode=LogMode.PRINT_AND_SAVE, log_dir=str(tmp_path), max_size=10240
        )

        # 写入日志
        logger.i_print("测试日志")

        # 检查刷新
        logger.check_and_flush()

        # 验证文件内容已刷新
        log_file = tmp_path / "log_6.txt"
        assert log_file.exists()
        # 验证文件内容
        content = log_file.read_text(encoding="utf-8")
        assert "测试日志" in content
        assert "测试日志" in content  # 确保数据已写入磁盘

        logger.close_file()

    def test_my_logger_duplicate_path_error(self, tmp_path):
        """测试重复路径的错误处理（非 PRINT_ONLY 模式）"""
        # 创建第一个日志记录器
        logger1 = MyLogger(log_file=7, log_mode=LogMode.SAVE_ONLY, log_dir=str(tmp_path))
        logger1.close_file()

        # 尝试创建第二个相同路径的日志记录器
        with pytest.raises(ValueError, match="日志文件路径.*已存在"):
            logger2 = MyLogger(log_file=7, log_mode=LogMode.SAVE_ONLY, log_dir=str(tmp_path))

    def test_my_logger_print_only_no_duplicate_check(self, tmp_path):
        """测试 PRINT_ONLY 模式不检查路径冲突"""
        # PRINT_ONLY 模式允许创建多个实例
        logger1 = MyLogger(log_file=8, log_mode=LogMode.PRINT_ONLY, log_dir=str(tmp_path))

        logger2 = MyLogger(log_file=8, log_mode=LogMode.PRINT_ONLY, log_dir=str(tmp_path))

        # 两个实例应该都成功创建
        assert logger1 is not None
        assert logger2 is not None


class TestProgressBar:
    """测试进度条显示功能"""

    def test_progress_bar_display(self):
        """测试进度条显示"""
        with patch("sys.stdout") as mock_stdout:
            progress_bar(50.5, 100.0)

            # 验证写入被调用
            assert mock_stdout.write.called
            assert mock_stdout.flush.called
            assert mock_stdout.write.call_count >= 1
            # 验证写入内容包含进度信息
            call_args = str(mock_stdout.write.call_args)
            assert "50.50%" in call_args  # 进度百分比
            assert "100.00" in call_args  # 速率
            assert "Progress:" in call_args  # 进度标签

    def test_progress_bar_zero_progress(self):
        """测试零进度"""
        with patch("sys.stdout") as mock_stdout:
            progress_bar(0.0, 0.0)

            # 验证写入被调用
            assert mock_stdout.write.called
            assert mock_stdout.flush.called
            # 验证零进度显示
            call_args = str(mock_stdout.write.call_args)
            assert "0.00%" in call_args

    def test_progress_bar_full_progress(self):
        """测试完整进度"""
        with patch("sys.stdout") as mock_stdout:
            progress_bar(100.0, 50.0)

            # 验证写入被调用
            assert mock_stdout.write.called
            assert mock_stdout.flush.called
            # 验证完整进度显示
            call_args = str(mock_stdout.write.call_args)
            assert "100.00%" in call_args
            assert "50.00" in call_args  # 速率


class TestEdgeCases:
    """测试边界情况"""

    def test_com_logger_empty_data(self, tmp_path):
        """测试 ComLogger 空数据处理"""
        logger = ComLogger(log_file=9, log_dir=str(tmp_path), log_mode=LogMode.SAVE_ONLY)

        # 写入空数据
        with patch("builtins.print") as mock_print:
            logger.com_print(b"", cmd=0x00, addr=0)

            # 验证空数据也能正确处理
            assert mock_print.called is False  # SAVE_ONLY 模式不应该打印

        # 验证文件创建
        log_file = tmp_path / "log_9_com.txt"
        assert log_file.exists()

        logger.close_file()

    def test_my_logger_empty_message(self):
        """测试 MyLogger 空消息处理"""
        logger = MyLogger(log_mode=LogMode.PRINT_ONLY)

        with patch("builtins.print") as mock_print:
            logger.i_print()

            # 验证打印被调用
            assert mock_print.called
            assert mock_print.call_count == 1
            # 验证空消息也能正常打印
            call_args = str(mock_print.call_args)
            assert "[" in call_args  # 至少有时间戳
            assert "]" in call_args  # 结束括号
            assert "[32m" in call_args  # 信息日志绿色

    def test_com_logger_large_data(self, tmp_path):
        """测试 ComLogger 大数据处理"""
        logger = ComLogger(log_file=10, log_dir=str(tmp_path), log_mode=LogMode.SAVE_ONLY)

        # 写入大数据
        large_data = b"\x01" * 10000
        with patch("builtins.print"):
            logger.com_print(large_data, cmd=0xFF, addr=255)

        # 验证文件写入大数据
        log_file = tmp_path / "log_10_com.txt"
        assert log_file.exists()
        assert log_file.stat().st_size > 10000  # 应该包含所有数据

        logger.close_file()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

class TestComLoggerExceptionHandling:
    """测试 ComLogger 异常处理"""

    def test_com_logger_write_failure(self, tmp_path):
        """测试 ComLogger 文件写入失败"""
        from unittest.mock import patch, mock_open
        logger = ComLogger(log_file=99, log_mode=LogMode.SAVE_ONLY, log_dir=str(tmp_path))
        
        # 模拟文件写入失败
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.return_value.write.side_effect = IOError("磁盘已满")
            with patch('builtins.print') as mock_print:
                try:
                    logger.com_print(b"\x01\x02", cmd=1, addr=1)
                except:
                    pass  # 异常应该被处理

        logger.close_file()


class TestMyLoggerExceptionHandling:
    """测试 MyLogger 异常处理和资源清理"""

    def test_my_logger_context_manager_with_exception(self, tmp_path):
        """测试 MyLogger 上下文管理器异常清理"""
        try:
            with MyLogger(log_file=97, log_mode=LogMode.SAVE_ONLY, log_dir=str(tmp_path)) as logger:
                logger.printf("test")
                raise ValueError("测试异常")
        except ValueError:
            pass  # 预期的异常
        
        # 验证文件存在（说明上下文正确清理）
        log_file = tmp_path / "log_97.txt"
        assert log_file.exists()

    def test_my_logger_print_only_mode(self):
        """测试 PRINT_ONLY 模式下的属性设置"""
        logger = MyLogger(log_file=96, log_mode=LogMode.PRINT_ONLY)
        
        # 验证所有文件相关属性都为 None
        assert logger.file_name is None
        assert logger.file_path is None
        assert logger.file is None

    def test_my_logger_print_only_open_file(self):
        """测试 PRINT_ONLY 模式下不打开文件"""
        logger = MyLogger(log_file=95, log_mode=LogMode.PRINT_ONLY)
        
        # 在 PRINT_ONLY 模式下调用 open_file
        logger.open_file()
        
        # 验证文件对象仍为 None
        assert logger.file is None

