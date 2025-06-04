import jwt
import time
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import pytz

# 设置上海时区
SHANGHAI_TZ = pytz.timezone('Asia/Shanghai')

def is_token_expired(token: str, wallet_address: Optional[str] = None) -> bool:
    """
    判断 JWT token 是否过期或即将过期（提前3分钟视为过期）
    
    Args:
        token (str): JWT token 字符串
        wallet_address (str, optional): 钱包地址，用于日志记录
        
    Returns:
        bool: 如果 token 已过期或即将过期返回 True，否则返回 False
    """
    try:
        # 解析 token（不验证签名）
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # 获取当前时间戳
        current_time = int(time.time())
        
        # 如果剩余时间小于3分钟，视为过期
        remaining_time = decoded['exp'] - current_time
        
        # 如果剩余时间小于3分钟，视为过期
        if remaining_time <= 180:  # 3分钟 = 180秒
            if wallet_address:
                logging.info(f'[{wallet_address}] Token已过期或即将过期，剩余时间: {remaining_time}秒')
            return True
            
        if wallet_address:
            logging.info(f'[{wallet_address}] Token有效，剩余时间: {remaining_time}秒')
        return False
            
    except jwt.InvalidTokenError as e:
        if wallet_address:
            logging.error(f'[{wallet_address}] Token格式无效: {str(e)}')
        return True
    except Exception as e:
        if wallet_address:
            logging.error(f'[{wallet_address}] 检查token时出错: {str(e)}')
        return True


def can_claim(last_claim_time: Optional[str], wallet_address: Optional[str] = None) -> bool:
    """
    判断是否可以领取奖励（每天9点后可以领取一次）

    Args:
        last_claim_time (str): 上次领取时间的字符串，格式为 SQLite 的 TIMESTAMP
        wallet_address (str, optional): 钱包地址，用于日志记录

    Returns:
        bool: 如果可以领取返回 True，否则返回 False
    """
    try:
        if not last_claim_time:
            if wallet_address:
                logging.info(f'[{wallet_address}] 首次领取')
            return True

        # 将字符串转换为datetime对象（默认UTC）
        last_claim = datetime.strptime(last_claim_time, '%Y-%m-%d %H:%M:%S')
        last_claim = pytz.utc.localize(last_claim)  # 设置为UTC时间
        last_claim = last_claim.astimezone(SHANGHAI_TZ)  # 转换为上海时间

        # 获取当前上海时间
        now = datetime.now(SHANGHAI_TZ)

        # 获取今天的早上9点（上海时间）
        today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)

        # 添加调试日志
        if wallet_address:
            logging.info(f'[{wallet_address}] 时间信息:')
            logging.info(f'当前时间（上海）: {now}')
            logging.info(f'今天9点（上海）: {today_9am}')
            logging.info(f'上次领取（原始）: {last_claim_time}')
            logging.info(f'上次领取（上海）: {last_claim}')

        # 新的判断逻辑：
        # 1. 如果现在还没到9点，不能领取
        if now < today_9am:
            if wallet_address:
                logging.info(f'[{wallet_address}] 还未到领取时间（北京时间早上9点）')
            return False

        # 2. 如果上次领取是在今天之前，可以领取
        if last_claim.date() < now.date():
            if wallet_address:
                logging.info(f'[{wallet_address}] 可以领取奖励（上次领取是在今天之前）')
            return True

        # 3. 如果上次领取是今天，且现在已经过了9点，就可以领取
        if now >= today_9am:
            if wallet_address:
                logging.info(f'[{wallet_address}] 可以领取奖励（今天9点后可领取）')
            return True

        # 4. 其他情况不能领取
        if wallet_address:
            logging.info(f'[{wallet_address}] 暂时不能领取')
        return False

    except Exception as e:
        logging.error(f"检查领取时间时出错: {str(e)}")
        return False


def get_token_info(token: str) -> Dict[str, Any]:
    """
    获取 token 的详细信息
    
    Args:
        token (str): JWT token 字符串
        
    Returns:
        Dict[str, Any]: token 信息字典，包含以下字段：
            - userId: 用户ID
            - t3UserId: T3用户ID
            - nickName: 昵称
            - ethAddress: 钱包地址
            - t3LoginType: 登录类型
            - timestamp: 时间戳
            - iat: 签发时间
            - exp: 过期时间
            - remaining_time: 剩余有效时间（秒）
            - is_expired: 是否已过期（包括即将过期）
    """
    try:
        # 解析 token（不验证签名）
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # 获取当前时间戳
        current_time = int(time.time())
        
        # 计算剩余时间
        remaining_time = decoded['exp'] - current_time
        
        # 添加额外信息
        decoded['remaining_time'] = remaining_time
        decoded['is_expired'] = remaining_time <= 180  # 3分钟 = 180秒
        
        return decoded
            
    except jwt.InvalidTokenError as e:
        return {'error': f'Token格式无效: {str(e)}'}
    except Exception as e:
        return {'error': f'解析token时出错: {str(e)}'}
