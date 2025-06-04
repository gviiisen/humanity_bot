# Humanity Bot

一个用于与Humanity Protocol测试网签到的自动化机器人，支持钱包连接、签名验证、打码登录、token存取、奖励领取功能。

## 推特
https://x.com/cythva
(欢迎私信交流)

## 功能

- 🎯 **验证码处理**：集成Capsolver自动解决reCAPTCHA
- 💰 **奖励领取**：自动领取每日奖励
- 📊 **多账户管理**：支持批量管理多个钱包账户

## 安装要求

- Python 3.8+
- pip

## 安装步骤

1. 克隆项目
```bash
git clone https://github.com/gviiisen/humanity_bot.git
cd humanity_bot
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 编辑 `config.py` 文件，填入你的配置：
   - `CAPTCHA_SOLVER_API_KEY`：从 [Capsolver](https://dashboard.capsolver.com/passport/register?inviteCode=V5F9qptdSjAj) 获取API密钥
   - `concurrent_number`：设置并发数（根据你的机器性能调整）

## 使用方法

### 批量多账户运行
```bash
python main_thread.py
```

### 私钥管理
在 `data/private_keys.txt` 文件中添加你的钱包私钥，每行一个：
```
0x私钥1
0x私钥2
0x私钥3
```

### 并发设置
在 `config.py` 中设置并发数：
```python
# 并发数量，建议根据机器性能设置1-5
concurrent_number = 3
```

### 代理设置
```
暂无设置代理，有需要的可以自行二次开发
```

## 主要文件说明

- `main.py` - 旧版本github开源代码主程序入口
- `main_thread.py` - 多线程批量处理
- `API.py` - Humanity Protocol API接口
- `database.py` - 数据库操作
- `utils/` - 工具函数目录
  - `captcha.py` - 验证码处理
  - `wallet.py` - 钱包操作
  - `JWT_utils.py` - JWT令牌处理

## 注意事项

⚠️ **重要提醒**：
- 请确保你的私钥安全，不要泄露给他人
- 本项目仅用于学习和测试目的
- 使用前请确保了解相关风险

## 许可证

MIT License
