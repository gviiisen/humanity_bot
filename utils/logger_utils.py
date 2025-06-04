import logging
import traceback
import inspect
import os

class Logger:
    def __init__(self, name=None):
        self.logger = logging.getLogger(name or self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        
        # 禁用向上传播，防止日志被重复处理
        self.logger.propagate = False
        
        # 如果还没有处理器，添加一个
        if not self.logger.handlers:
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 创建文件处理器
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            file_handler = logging.FileHandler(
                os.path.join(log_dir, 'humanity.log'),
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            
            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            # 添加处理器
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)

    def _get_caller_info(self):
        """获取调用者的信息"""
        frame = inspect.currentframe().f_back.f_back
        filename = os.path.basename(frame.f_code.co_filename)
        lineno = frame.f_lineno
        return f"{filename}:{lineno}"

    def info(self, message):
        caller_info = self._get_caller_info()
        self.logger.info(f"[{caller_info}] {message}")

    def error(self, message):
        caller_info = self._get_caller_info()
        self.logger.error(f"[{caller_info}] {message}")

    def warning(self, message):
        caller_info = self._get_caller_info()
        self.logger.warning(f"[{caller_info}] {message}")

    def debug(self, message):
        caller_info = self._get_caller_info()
        self.logger.debug(f"[{caller_info}] {message}")

    def exception(self, message):
        caller_info = self._get_caller_info()
        self.logger.error(f"[{caller_info}] {message}\n{traceback.format_exc()}")

# 确保根日志记录器不会处理我们已经处理过的日志
logging.getLogger().setLevel(logging.WARNING)

# 创建全局日志实例
logger = Logger('humanity')