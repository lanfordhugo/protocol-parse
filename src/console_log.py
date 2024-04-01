import os
import sys
import time

work_path = os.getcwd()

custom_time = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())

if not os.path.exists('parsed_log'):
    os.mkdir('parsed_log')


class ConsoleLog(object):
    def __init__(self, filename='{}/parsed_log/parsed_net_log_{}.txt'.format(work_path, custom_time),
                 stream=sys.stdout):
        self.terminal_out = stream
        self.log = open(filename, 'a', encoding='utf-8')

    def write(self, message):
        self.terminal_out.write(message)
        self.log.write(message)
        self.flush()

    def flush(self):
        self.log.flush()
