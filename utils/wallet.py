from eth_account.messages import encode_defunct
from eth_account.account import LocalAccount
from eth_typing import HexStr
from mnemonic import Mnemonic
from eth_account import Account
from web3 import Web3
import secrets

# 启用HD钱包功能
Account.enable_unaudited_hdwallet_features()

class EthereumAccountManager:
    def __init__(self, private_key=None):
        self.mnemo = Mnemonic("english")
        self.address = None
        self.private_key = None
        self.words = None

        if private_key:
            # 如果提供了私钥，直接用私钥生成账户
            self.private_key = private_key
            self.address = self.to_account(private_key).address
        else:
            # 如果没有私钥，生成助记词、私钥和地址
            self.create_account()

    def check_address(self):
        checksum_address = Web3.to_checksum_address(self.address)
        return checksum_address

    def create_account(self):
        # 生成助记词
        self.words = self.mnemo.generate(strength=128)

        # 通过助记词生成种子
        seed = self.mnemo.to_seed(self.words)

        # 使用种子生成以太坊账户
        account = Account.from_mnemonic(self.words)

        self.address = account.address
        self.private_key = account.key.hex()

    def sign_message(self, message: str) -> HexStr:
        if not self.private_key:
            raise ValueError("No account found. Please create an account first.")
        account = self.to_account(self.private_key)
        message = encode_defunct(text=message)
        signed_message = account.sign_message(message)
        return HexStr(signed_message.signature.hex())

    def to_account(self, private_key: str) -> LocalAccount:
        # 创建本地账户对象
        return Account.from_key(private_key)
