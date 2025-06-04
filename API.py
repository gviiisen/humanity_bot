import curl_cffi
from curl_cffi import requests
import json
from typing import Optional, Dict, Any
import secrets
import string
from datetime import datetime, timedelta, timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from utils.logger_utils import logger
from utils.wallet import EthereumAccountManager
from utils.captcha import capsolver
from database import AccountDatabase

class HumanityBotAPI:
    def __init__(
        self,
        base_url: str = "https://api.example.com",
        timeout: int = 30,
        private_key: Optional[str] = None,
        db: Optional[AccountDatabase] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # 设置默认请求头
        self.headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'access-control-allow-origin': 'https://terminal3.humanity.org/api',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://testnet.humanity.org',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://testnet.humanity.org/',
            'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
        }
            
        # 初始化HTTP客户端
        self.http_client = requests.Session()
        self.http_client.headers.update(self.headers)
        
        # 初始化数据库
        self.db = db or AccountDatabase()
        
        # 初始化钱包
        if private_key:
            self.wallet = EthereumAccountManager(private_key=private_key)
            self.address = self.wallet.address
            # 尝试添加账号到数据库
            self.db.add_account(self.address, private_key)
        else:
            self.wallet = None
            self.address = None
            
        self.token = None
        self.code = None
        self.hpToken = None

    def _make_url(self, endpoint: str) -> str:
        """
        构建完整的API URL

        Args:
            endpoint: API端点路径

        Returns:
            完整的API URL
        """
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _handle_response(self, response) -> Dict[str, Any]:
        """
        处理API响应

        Args:
            response: API响应对象

        Returns:
            解析后的响应数据

        Raises:
            Exception: 当API请求失败时抛出异常
        """
        if response.status_code >= 400:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")

        try:
            return response.json()
        except json.JSONDecodeError:
            return {"raw_response": response.text}


    def get_nonce(self, length: int = 17) -> str:
        """
        生成指定长度的随机 nonce 字符串

        Args:
            length: nonce 字符串的长度，默认为17

        Returns:
            生成的随机 nonce 字符串
        """
        charset = string.ascii_letters + string.digits  # 等同于 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(secrets.choice(charset) for _ in range(length))


    def collect(self):
        try:
            # 从数据库获取账号信息
            if not self.wallet and self.address:
                account_data = self.db.get_account(self.address)
                if account_data:
                    self.wallet = EthereumAccountManager(private_key=account_data['private_key'])
            
            nonce = self.get_nonce()
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

            sign_message = f"testnet.humanity.org wants you to sign in with your Ethereum account:\n{self.address}\n\nConnect to Humanity\n\nURI: https://testnet.humanity.org\nVersion: 1\nChain ID: 7080969\nNonce: {nonce}\nIssued At: {timestamp}"
            signature = self.wallet.sign_message(sign_message)
            
            cap_res = capsolver()
            if cap_res is None:
                logger.info("打码失败，请检查config.py的CAPTCHA_SOLVER_API_KEY是否正确")
            message = json.dumps({
                "domain": "testnet.humanity.org",
                "address": self.address,
                "statement": "Connect to Humanity",
                "uri": "https://testnet.humanity.org",
                "version": "1",
                "chainId": 7080969,
                "nonce": nonce,
                "issuedAt": timestamp
            })
            json_data = {
                'message': message,
                'signature': signature,
                'wallet': self.address,
                'chain_id': '7080969',
                'attributed_client_id': 1,
                'method': 'wallet',
                'recaptcha_token': cap_res,
            }
            res = self.http_client.post(url='https://terminal3.humanity.org/api/user/v3/connect', json=json_data)
            response_data = res.json()
            self.token = response_data.get('data', {}).get('token')
            if not self.token:
                raise Exception("Failed to get token from response")
                
            # 更新数据库中的token
            self.db.update_tokens(self.address, token=self.token)
            logger.info(f"[{self.address}] 钱包sign成功")
            return True
        except Exception as e:
            logger.error(f"收集过程中出错: {str(e)}")
            logger.error(f"响应状态码: {res.status_code}")
            logger.error(f"响应内容: {res.text[:500]}")
            raise


    def auth(self):
        # 设置请求头，包含所有必要的信息
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-site',
            'upgrade-insecure-requests': '1',
            'referer': 'https://testnet.humanity.org/'
        }


        # 构造请求参数
        params = {
            'client_id': '8Lr7zhdHSPWqLcEZaVDLeq7xYP4qAfyT',
            'redirect_uri': 'https://testnet.humanity.org/dashboard',
            'response_type': 'code',
            'scope': 'openid',
            'state': 't3',
            'token': self.token
        }

        # 构造完整的URL
        from urllib.parse import urlencode
        url = f'https://terminal3.humanity.org/v1/openidc/authorize?{urlencode(params)}'

        # # 创建新的请求会话，禁用自动重定向
        # import curl_cffi.requests as requests
        new_session = requests.Session()
        new_session.headers.update(headers)

        # 尝试两种方式获取授权码
        try:
            # 首先尝试直接获取重定向URL
            new_session.curl.setopt(curl_cffi.CurlOpt.FOLLOWLOCATION, 0)
            response = new_session.get(url, allow_redirects=False)

            # 检查是否有重定向
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('location')
                if location and 'code=' in location:
                    code = location.split('code=')[1].split('&')[0]
                    # print("从重定向获取到 Authorization Code:", code)
                    self.code = code
                    return code

            # 如果没有重定向，尝试发送带有token的POST请求
            post_url = 'https://terminal3.humanity.org/v1/openidc/token'
            post_data = {
                'grant_type': 'authorization_code',
                'client_id': '8Lr7zhdHSPWqLcEZaVDLeq7xYP4qAfyT',
                'token': self.token
            }
            
            token_response = new_session.post(post_url, json=post_data)
            if token_response.status_code == 200:
                token_data = token_response.json()
                if 'access_token' in token_data:
                    print("成功获取访问令牌")
                    return token_data['access_token']
            
            # 如果以上方法都失败，尝试从URL参数中获取code
            import re
            html_content = response.text
            code_match = re.search(r'code=([^&"\']+)', html_content)
            if code_match:
                code = code_match.group(1)
                print("从HTML内容中获取到 Authorization Code:", code)
                self.http_client.headers.update({'referer': f'https://testnet.humanity.org/dashboard?code={code}&state=t3'})
                self.code = code
                return code
            
            raise Exception("无法获取授权码或访问令牌")
            
        except Exception as e:
            print(f"认证过程中出错: {str(e)}")
            print("响应状态码:", response.status_code if 'response' in locals() else 'N/A')
            print("响应头:", response.headers if 'response' in locals() else 'N/A')
            print("响应内容:", response.text[:500] if 'response' in locals() else 'N/A')
            raise Exception("认证失败") from e

    def loginAndRegister(self):
        try:
            json_data = {
                'code': self.code,
            }
            res = self.http_client.post(url='https://testnet.humanity.org/api/user/loginAndRegister', json=json_data)
            response_data = res.json()
            self.hpToken = response_data.get('data', {}).get('token')
            self.http_client.headers.update({'authorization': f'Bearer {self.hpToken}'})
            self.http_client.headers.update({'token': self.hpToken})
            
            # 更新数据库中的hp_token
            self.db.update_tokens(self.address, hp_token=self.hpToken)
            logger.info(f"[{self.address}] 登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            logger.error(f"响应状态码: {res.status_code}")
            logger.error(f"响应内容: {res.text[:500]}")
            raise 

    def check(self):
        try:
            json_data = {}
            res = self.http_client.post('https://testnet.humanity.org/api/rewards/daily/check', json=json_data)
            response_data = res.json()
            message = response_data.get('message')
            available = response_data.get('available')

            amount = response_data.get('amount')
            next_daily_award = response_data.get('next_daily_award')
            print(message, available, amount, next_daily_award)
            return available
        except Exception as e:
            logger.error(f"检查失败: {str(e)}")
            logger.error(f"响应状态码: {res.status_code}")
            logger.error(f"响应内容: {res.text[:500]}")
            raise

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=4, max=10)  # 指数退避，等待时间在4-10秒之间
    )
    def claim(self):
        try:
            json_data = {}
            res = self.http_client.post(
                'https://testnet.humanity.org/api/rewards/daily/claim',
                json=json_data,
                timeout=30  # 添加超时设置
            )
            response_data = res.json()
            message = response_data.get('message')
            daily_claimed = response_data.get('daily_claimed')
            amount = response_data.get('amount')
            available = response_data.get('available')
            if not available:
                # 更新数据库中的领取时间
                if daily_claimed:
                    self.db.update_claim_time(self.address)

                logger.info(f"[{self.address}] 领取成功: {message}, {daily_claimed}, {amount}")
                return True
            else:
                logger.info(f"[{self.address}] 领取失败: {message}")
        except (requests.RequestTimeout, requests.ConnectionError) as e:
            logger.error(f"网络请求错误: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"领取过程中出错: {str(e)}")
            logger.error(f"响应状态码: {res.status_code}")
            logger.error(f"响应内容: {res.text[:500]}")
            raise

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()


if __name__ == "__main__":
    # 创建数据库实例
    db = AccountDatabase()
    
    # 示例：使用数据库管理多个账号
    private_key = '0x9c506b998505c7891c2caead27f34fb519f0***********'
    api = HumanityBotAPI(private_key=private_key, db=db)
    
    # 运行主流程
    api.collect()
    api.auth()
    api.loginAndRegister()
    api.check()
    
    # 关闭数据库连接
    db.close()

