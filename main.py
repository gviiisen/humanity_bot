import traceback

from web3 import Web3
from colorama import init, Fore
import sys
import time
from datetime import datetime
import requests
from urllib.parse import urlparse
import os
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from web3.exceptions import TimeExhausted

# 初始化 colorama
init(autoreset=True)

class HumanityProtocolBot:
    def __init__(self, max_workers=5, wait_for_receipt=True, receipt_timeout=30):
        self.rpc_url = 'https://rpc.testnet.humanity.org'
        self.contract_address = '0xa18f6FCB2Fd4884436d10610E69DB7BFa1bFe8C7'
        self.max_workers = max_workers  # 设置最大并发数
        self.wait_for_receipt = wait_for_receipt  # 是否等待交易收据
        self.receipt_timeout = receipt_timeout  # 等待交易收据的超时时间（秒）
        self.contract_abi = [
            {"inputs":[],"name":"AccessControlBadConfirmation","type":"error"},
            {"inputs":[{"internalType":"address","name":"account","type":"address"},{"internalType":"bytes32","name":"neededRole","type":"bytes32"}],"name":"AccessControlUnauthorizedAccount","type":"error"},
            {"inputs":[],"name":"InvalidInitialization","type":"error"},
            {"inputs":[],"name":"NotInitializing","type":"error"},
            {"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint64","name":"version","type":"uint64"}],"name":"Initialized","type":"event"},
            {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"from","type":"address"},{"indexed":True,"internalType":"address","name":"to","type":"address"},{"indexed":False,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":False,"internalType":"bool","name":"bufferSafe","type":"bool"}],"name":"ReferralRewardBuffered","type":"event"},
            {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"user","type":"address"},{"indexed":True,"internalType":"enum IRewards.RewardType","name":"rewardType","type":"uint8"},{"indexed":False,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"RewardClaimed","type":"event"},
            {"anonymous":False,"inputs":[{"indexed":True,"internalType":"bytes32","name":"role","type":"bytes32"},{"indexed":True,"internalType":"bytes32","name":"previousAdminRole","type":"bytes32"},{"indexed":True,"internalType":"bytes32","name":"newAdminRole","type":"bytes32"}],"name":"RoleAdminChanged","type":"event"},
            {"anonymous":False,"inputs":[{"indexed":True,"internalType":"bytes32","name":"role","type":"bytes32"},{"indexed":True,"internalType":"address","name":"account","type":"address"},{"indexed":True,"internalType":"address","name":"sender","type":"address"}],"name":"RoleGranted","type":"event"},
            {"anonymous":False,"inputs":[{"indexed":True,"internalType":"bytes32","name":"role","type":"bytes32"},{"indexed":True,"internalType":"address","name":"account","type":"address"},{"indexed":True,"internalType":"address","name":"sender","type":"address"}],"name":"RoleRevoked","type":"event"},
            {"inputs":[],"name":"DEFAULT_ADMIN_ROLE","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},
            {"inputs":[],"name":"claimBuffer","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[],"name":"claimReward","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[],"name":"currentEpoch","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
            {"inputs":[],"name":"cycleStartTimestamp","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"bytes32","name":"role","type":"bytes32"}],"name":"getRoleAdmin","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"bytes32","name":"role","type":"bytes32"},{"internalType":"address","name":"account","type":"address"}],"name":"grantRole","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"bytes32","name":"role","type":"bytes32"},{"internalType":"address","name":"account","type":"address"}],"name":"hasRole","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"address","name":"vcContract","type":"address"},{"internalType":"address","name":"tkn","type":"address"}],"name":"init","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"bytes32","name":"role","type":"bytes32"},{"internalType":"address","name":"callerConfirmation","type":"address"}],"name":"renounceRole","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"bytes32","name":"role","type":"bytes32"},{"internalType":"address","name":"account","type":"address"}],"name":"revokeRole","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"uint256","name":"startTimestamp","type":"uint256"}],"name":"start","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[],"name":"stop","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"bytes4","name":"interfaceId","type":"bytes4"}],"name":"supportsInterface","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"userBuffer","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint256","name":"epochID","type":"uint256"}],"name":"userClaimStatus","outputs":[{"components":[{"internalType":"uint256","name":"buffer","type":"uint256"},{"internalType":"bool","name":"claimStatus","type":"bool"}],"internalType":"struct IRewards.UserClaim","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"userGenesisClaimStatus","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"}
        ]
        # 添加线程锁，保护打印输出和文件操作
        self.print_lock = threading.Lock()
        self.file_lock = threading.Lock()
        
        # 确保data目录存在
        self.data_dir = "data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # 获取当前日期，用于文件命名
        self.current_date = datetime.now().strftime("%Y_%m_%d")
        
        # 记录地址到私钥的映射，方便查询
        self.address_to_key = {}
        
        # 记录已处理的地址，避免重复写入
        self.claimed_addresses = self.load_addresses("claimed")
        self.failed_addresses = self.load_addresses("failed")

    def load_addresses(self, status_type):
        """加载已有的地址记录，避免重复"""
        addresses = set()
        file_path = os.path.join(self.data_dir, f"{status_type}_{self.current_date}.txt")
        
        # 检查当天的文件是否存在
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        if line.strip():
                            parts = line.strip().split('----')
                            if len(parts) >= 2:
                                address = parts[0]
                                private_key = parts[1]
                                addresses.add(address)
                                # 存储地址和私钥的映射关系
                                self.address_to_key[address] = private_key
            except Exception as e:
                print(Fore.RED + f"读取文件 {file_path} 时出错: {str(e)}")
        
        return addresses

    def record_address(self, status_type, address, private_key):
        """记录地址到对应的状态文件，并在状态变更时更新文件"""
        with self.file_lock:
            # 如果是标记为成功，且之前在失败列表中，则从失败列表移除
            if status_type == "claimed" and address in self.failed_addresses:
                self.remove_from_file("failed", address)
                self.failed_addresses.remove(address)
                with self.print_lock:
                    print(Fore.CYAN + f"地址 {address} 从失败记录中移除")
            
            # 如果地址已经在对应状态的列表中，则跳过
            if status_type == "claimed" and address in self.claimed_addresses:
                return
            if status_type == "failed" and address in self.failed_addresses:
                return
            
            # 保存地址与私钥的映射
            self.address_to_key[address] = private_key
            
            # 将地址写入对应状态的文件
            file_path = os.path.join(self.data_dir, f"{status_type}_{self.current_date}.txt")
            try:
                with open(file_path, 'a') as f:
                    f.write(f"{address}----{private_key}\n")
                
                # 将地址添加到对应的集合中
                if status_type == "claimed":
                    self.claimed_addresses.add(address)
                else:
                    self.failed_addresses.add(address)
                    
                with self.print_lock:
                    print(Fore.CYAN + f"地址 {address} 已记录到 {file_path}")
                    
            except Exception as e:
                with self.print_lock:
                    print(Fore.RED + f"记录地址 {address} 到 {file_path} 失败: {str(e)}")

    def remove_from_file(self, status_type, address):
        """从指定状态文件中移除地址"""
        file_path = os.path.join(self.data_dir, f"{status_type}_{self.current_date}.txt")
        if not os.path.exists(file_path):
            return
            
        # 读取文件内容
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
            # 过滤掉要移除的地址
            filtered_lines = [line for line in lines if not line.startswith(f"{address}----")]
            
            # 如果内容有变化，则写回文件
            if len(filtered_lines) != len(lines):
                with open(file_path, 'w') as f:
                    f.writelines(filtered_lines)
                    
                with self.print_lock:
                    print(Fore.CYAN + f"已从 {file_path} 移除地址 {address}")
        except Exception as e:
            with self.print_lock:
                print(Fore.RED + f"从 {file_path} 移除地址 {address} 失败: {str(e)}")

    @staticmethod
    def current_time():
        """返回当前时间的格式化字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def load_accounts_data():
        """加载私钥和对应的代理"""
        accounts_data = []

        try:
            with open('data/private_keys.txt', 'r') as f:
                private_keys = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(Fore.RED + "错误: 找不到 private_keys.txt 文件")
            sys.exit(1)

        try:
            with open('proxy.txt', 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(Fore.YELLOW + "未找到 proxy.txt 文件，所有账号将使用直连")
            proxies = [''] * len(private_keys)

        if len(proxies) < len(private_keys):
            print(Fore.YELLOW + f"代理数量({len(proxies)})少于私钥数量({len(private_keys)})，部分账号将使用直连")
            proxies.extend([''] * (len(private_keys) - len(proxies)))

        for private_key, proxy in zip(private_keys, proxies):
            accounts_data.append({
                'private_key': private_key,
                'proxy': proxy
            })

        return accounts_data

    @staticmethod
    def format_proxy(proxy):
        """格式化代理字符串"""
        if not proxy:
            return None
        
        try:
            if proxy.startswith('socks5://'):
                return {'http': proxy, 'https': proxy}
            elif proxy.startswith('http://') or proxy.startswith('https://'):
                return {'http': proxy, 'https': proxy}
            else:
                return {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        except Exception as e:
            print(Fore.RED + f"代理格式化错误: {str(e)}")
            return None

    def setup_blockchain_connection(self, proxy=None):
        """建立区块链连接"""
        try:
            if proxy:
                formatted_proxy = self.format_proxy(proxy)
                if formatted_proxy:
                    session = requests.Session()
                    session.proxies = formatted_proxy
                    web3 = Web3(Web3.HTTPProvider(
                        self.rpc_url,
                        session=session,
                        request_kwargs={"timeout": 30}
                    ))
                else:
                    web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            else:
                web3 = Web3(Web3.HTTPProvider(self.rpc_url))

            if web3.is_connected():
                with self.print_lock:
                    connection_msg = f"{self.current_time()} 成功连接到 Humanity Protocol"
                    connection_msg += f" (使用代理: {proxy})" if proxy else " (直连)"
                    print(Fore.GREEN + connection_msg)
                return web3
        except Exception as e:
            with self.print_lock:
                print(Fore.RED + f"连接错误: {str(e)}")
            return None

    def claim_rewards(self, private_key, web3, contract):
        """尝试领取奖励"""
        try:
            account = web3.eth.account.from_key(private_key)
            sender_address = account.address
            genesis_claimed = contract.functions.userGenesisClaimStatus(sender_address).call()
            current_epoch = contract.functions.currentEpoch().call()
            buffer_amount, claim_status = contract.functions.userClaimStatus(sender_address, current_epoch).call()

            if (genesis_claimed and not claim_status) or (not genesis_claimed):
                with self.print_lock:
                    print(Fore.GREEN + f"正在为地址 {sender_address} 领取奖励")
                self.process_claim(sender_address, private_key, web3, contract)
            else:
                with self.print_lock:
                    print(Fore.YELLOW + f"地址 {sender_address} 当前纪元 {current_epoch} 的奖励已领取")
                # 记录已领取的地址和私钥
                self.record_address("claimed", sender_address, private_key)

        except Exception as e:
            with self.print_lock:
                print(Fore.RED + f"处理地址 {sender_address} 时发生错误: {str(e)}")
            # 发生异常时将地址记录为失败
            self.record_address("failed", sender_address, private_key)

    def process_claim(self, sender_address, private_key, web3, contract):
        """处理领取奖励的交易"""
        try:
            gas_amount = contract.functions.claimReward().estimate_gas({
                'chainId': web3.eth.chain_id,
                'from': sender_address,
                'gasPrice': web3.eth.gas_price,
                'nonce': web3.eth.get_transaction_count(sender_address)
            })
            
            transaction = contract.functions.claimReward().build_transaction({
                'chainId': web3.eth.chain_id,
                'from': sender_address,
                'gas': gas_amount,
                'gasPrice': web3.eth.gas_price,
                'nonce': web3.eth.get_transaction_count(sender_address)
            })
            
            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            
            # 兼容不同版本的Web3.py
            if hasattr(signed_txn, 'rawTransaction'):
                tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            else:
                # 适用于新版Web3.py
                tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            if self.wait_for_receipt:
                try:
                    # 使用较短的超时时间
                    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=self.receipt_timeout)
                    with self.print_lock:
                        print(Fore.GREEN + f"地址 {sender_address} 交易成功，交易哈希: {web3.to_hex(tx_hash)}")
                    # 记录成功领取的地址
                    self.record_address("claimed", sender_address, private_key)
                except TimeExhausted:
                    # 超时但不报错，交易可能仍在处理中
                    with self.print_lock:
                        print(Fore.YELLOW + f"地址 {sender_address} 交易已提交但未确认，交易哈希: {web3.to_hex(tx_hash)}")
                    # 记录为失败（未确认）
                    self.record_address("failed", sender_address, private_key)
            else:
                # 不等待交易收据，直接返回
                with self.print_lock:
                    print(Fore.GREEN + f"地址 {sender_address} 交易已提交，交易哈希: {web3.to_hex(tx_hash)}")
                # 由于未等待确认，记录为失败
                self.record_address("failed", sender_address, private_key)

        except Exception as e:
            traceback.print_exc()
            with self.print_lock:
                print(Fore.RED + f"处理地址 {sender_address} 的交易时发生错误: {str(e)}")
            # 记录交易失败的地址
            self.record_address("failed", sender_address, private_key)

    def process_account(self, account):
        """处理单个账号的任务，用于多线程"""
        # 为账号建立独立的连接
        web3 = self.setup_blockchain_connection(account['proxy'])
        if not web3:
            with self.print_lock:
                print(Fore.RED + "连接失败，跳过当前账号...")
            return

        # 设置合约
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address), 
            abi=self.contract_abi
        )
        
        # 执行领取操作
        self.claim_rewards(account['private_key'], web3, contract)

    def run(self):
        """运行主循环"""
        with self.print_lock:
            print(Fore.CYAN + f"{self.current_time()} ╔═╗╔═╦╗─╔╦═══╦═══╦═══╦═══╗")
            print(Fore.CYAN + f"{self.current_time()} ╚╗╚╝╔╣║─║║╔══╣╔═╗║╔═╗║╔═╗║")
            print(Fore.CYAN + f"{self.current_time()} ─╚╗╔╝║║─║║╚══╣║─╚╣║─║║║─║║")
            print(Fore.CYAN + f"{self.current_time()} ─╔╝╚╗║║─║║╔══╣║╔═╣╚═╝║║─║║")
            print(Fore.CYAN + f"{self.current_time()} ╔╝╔╗╚╣╚═╝║╚══╣╚╩═║╔═╗║╚═╝║")
            print(Fore.CYAN + f"{self.current_time()} ╚═╝╚═╩═══╩═══╩═══╩╝─╚╩═══╝")
            print(Fore.CYAN + f"{self.current_time()} 当前并发数设置为: {self.max_workers}")
            print(Fore.CYAN + f"{self.current_time()} 等待交易收据: {'是' if self.wait_for_receipt else '否'}, 超时时间: {self.receipt_timeout if self.wait_for_receipt else 'N/A'}秒")
            print(Fore.CYAN + f"{self.current_time()} 数据记录目录: {self.data_dir}")
            print(Fore.CYAN + f"{self.current_time()} 已加载 {len(self.claimed_addresses)} 个已领取地址, {len(self.failed_addresses)} 个失败地址")
            print(Fore.CYAN + "脚本已启动，开始执行领取操作...")

        while True:
            try:
                # 加载账号数据
                accounts_data = self.load_accounts_data()
                total_accounts = len(accounts_data)
                
                # 使用线程池执行账号操作
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    with self.print_lock:
                        print(Fore.CYAN + f"{self.current_time()} 开始处理 {total_accounts} 个账号，并发数: {self.max_workers}")
                    
                    # 提交所有任务到线程池
                    futures = [executor.submit(self.process_account, account) for account in accounts_data]
                    
                    # 等待所有任务完成
                    for future in futures:
                        future.result()  # 这会抛出线程中的任何异常
                
                with self.print_lock:
                    print(Fore.CYAN + f"{self.current_time()} 本轮领取完成，等待6小时后继续运行...")
                    print(Fore.CYAN + f"{self.current_time()} 当前状态: {len(self.claimed_addresses)} 个已领取地址, {len(self.failed_addresses)} 个失败地址")
                time.sleep(6 * 60 * 60)  # 6小时

            except KeyboardInterrupt:
                with self.print_lock:
                    print(Fore.YELLOW + "\n程序已停止运行")
                sys.exit(0)
            except Exception as e:
                with self.print_lock:
                    print(Fore.RED + f"发生错误: {str(e)}")
                time.sleep(60)  # 发生错误时等待1分钟后继续

if __name__ == "__main__":

    max_workers = 3
    wait_for_receipt = True
    receipt_timeout = 15
    
    if len(sys.argv) > 1:
        try:
            max_workers = int(sys.argv[1])
            if max_workers < 1:
                max_workers = 1
            elif max_workers > 50:
                print(Fore.YELLOW + "警告: 并发数过高可能导致RPC节点拒绝服务，已限制为最大50")
                max_workers = 50
        except ValueError:
            print(Fore.RED + "并发数必须是整数，使用默认值3")
            max_workers = 3
    
    if len(sys.argv) > 2:
        # 第二个参数表示是否等待交易收据：0=不等待，1=等待
        wait_for_receipt = int(sys.argv[2]) != 0
    
    if len(sys.argv) > 3 and wait_for_receipt:
        # 第三个参数是等待交易收据的超时时间（秒）
        try:
            receipt_timeout = int(sys.argv[3])
            if receipt_timeout < 5:
                receipt_timeout = 5  # 至少等待5秒
        except ValueError:
            print(Fore.RED + "超时时间必须是整数，使用默认值15秒")
            receipt_timeout = 15
    
    bot = HumanityProtocolBot(max_workers=max_workers, wait_for_receipt=wait_for_receipt, receipt_timeout=receipt_timeout)
    bot.run()
