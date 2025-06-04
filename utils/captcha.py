import requests
import time
import sys
import os

# 添加父目录到Python路径，确保可以导入config模块
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from config import CAPTCHA_SOLVER_API_KEY

def capsolver() -> str | None:
    """
    使用 Capsolver API 解决 reCAPTCHA v3 验证码
    
    Returns:
        str | None: 成功时返回验证码响应字符串，失败时返回 None
    """
    api_key = CAPTCHA_SOLVER_API_KEY
    payload = {
        'clientKey': api_key,
        'task': {
            'type': 'ReCaptchaV3TaskProxyLess',
            'websiteKey': '6LenESAqAAAAAL9ZymIB_A4Y03U3s3cPhBYKfcnU',
            'websiteURL': 'https://testnet.humanity.org',
            'pageAction': 'LOGIN'
        }
    }

    try:
        res = requests.post('https://api.capsolver.com/createTask', json=payload)
        res_data = res.json()
        task_id = res_data.get('taskId')
        
        if not task_id:
            print('Failed to create task:', res_data)
            return None

        while True:
            time.sleep(1)  # 延迟1秒

            get_result_payload = {
                'clientKey': api_key,
                'taskId': task_id
            }
            
            resp = requests.post('https://api.capsolver.com/getTaskResult', 
                               json=get_result_payload)
            resp_data = resp.json()
            status = resp_data.get('status')

            if status == 'ready':
                return resp_data['solution']['gRecaptchaResponse']
            
            if status == 'failed' or resp_data.get('errorId'):
                print('Solve failed! response:', resp_data)
                return None

    except Exception as error:
        print('Error:', str(error))
        return None 