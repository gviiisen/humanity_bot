import logging
import os
import time
import sys
import traceback
import threading
import concurrent.futures
from datetime import datetime

from utils.csv_tools import *
from utils.logger_utils import logger
from utils.JWT_utils import is_token_expired, can_claim

from API import HumanityBotAPI
from database import AccountDatabase

from config import concurrent_number

# 获取 exe 文件所在的目录
if getattr(sys, 'frozen', False):
    script_dir = os.path.dirname(sys.executable)
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))

# 获取上级目录（即项目根目录），然后添加 'data' 目录
data_dir = os.path.join(script_dir, 'data')
# 如果 data 文件夹不存在，就创建它
os.makedirs(data_dir, exist_ok=True)

resources = None

dir_deque= None
dir_deque_lock = threading.Lock()

check_fail_num = 0
run_success_num = 0

wallet_deque = None
wallet_deque_lock = threading.Lock()

SUCCESS_PATH = None
FAIL_PATH = None

# 创建数据库实例
db = AccountDatabase()

def work():
    global wallet_deque, db, SUCCESS_PATH,FAIL_PATH
    pageClient = None
    try:
        if len(wallet_deque) <= 0:
            return False

        pk = None
        with wallet_deque_lock:
            pk = wallet_deque.pop()

        if pk is None:
            return False

        logging.info(f'[{pk} 开始任务]')
        humanity_client = HumanityBotAPI(private_key=pk, db=db)
        address = humanity_client.address
        res = db.get_account(address)
        hp_token = res.get('hp_token')
        last_claim_time = res.get('last_claim_time')
        can_claim_flag = False
        if not can_claim(last_claim_time):
            logger.info(f"[{address} 上次claim时间为 {last_claim_time}, 暂时不能领取]")
            return True
        else:
            can_claim_flag = True
        login_flag = True
        if hp_token:
            if not is_token_expired(token=hp_token):
                login_flag = False
                humanity_client.http_client.headers.update({'authorization': f'Bearer {hp_token}'})
                humanity_client.http_client.headers.update({'token': hp_token})

        if login_flag:
            humanity_client.collect()
            humanity_client.auth()
            humanity_client.loginAndRegister()

        if can_claim_flag:
            humanity_client.claim()
        else:
            available = humanity_client.check()
            if available:
                if can_claim(last_claim_time, wallet_address=address):
                    humanity_client.claim()

        now = datetime.now()
        data = [address, pk, now]
        write_csv(SUCCESS_PATH, data)

    except Exception as e:
        traceback.print_exc()
        now = datetime.now()
        data = [pk, now]
        write_csv(FAIL_PATH, data)


if __name__ == '__main__':


    wallet_path = os.path.join(script_dir, 'data', 'private_keys.txt')
    wallet_deque = load_data_from_txt(wallet_path)

    # 获取程序启动时间并格式化为指定格式
    start_time = datetime.now().strftime('%m%d_%H%M')
    SUCCESS_PATH = os.path.join(script_dir, 'data', f'success_{start_time}.txt')
    FAIL_PATH = os.path.join(script_dir, 'data', f'fail_{start_time}.txt')

    pool_size = concurrent_number
    # 创建线程池，并发大小为3
    with concurrent.futures.ThreadPoolExecutor(max_workers=pool_size) as executor:
        # 使用列表推导式创建并提交1000个任务到线程池
        futures = [executor.submit(work) for i in range(len(wallet_deque))]
        # 等待所有任务完成
        for future in concurrent.futures.as_completed(futures):
            result = future.result()  # 获取每个任务的结果

    db.close()
    print("全部任务已完成!")
