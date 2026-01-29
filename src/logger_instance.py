from src.m_print import LogMode, MyLogger

# 创建一个 MyLogger 实例，仅保存到文件，不打印到终端
# 这样可以避免在GUI模式下大量日志输出导致性能问题
log = MyLogger("sys", LogMode.SAVE_ONLY)
