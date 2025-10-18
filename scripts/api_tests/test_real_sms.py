"""
测试真实的阿里云短信发送
"""
import os
import sys
import random
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量读取配置
ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
SIGN_NAME = os.getenv("SMS_SIGN_NAME")
TEMPLATE_CODE = os.getenv("SMS_TEMPLATE_CODE")

# 验证配置
if not all([ACCESS_KEY_ID, ACCESS_KEY_SECRET, SIGN_NAME, TEMPLATE_CODE]):
    print("❌ 错误：请先在 .env 文件中配置以下环境变量：")
    print("  - OSS_ACCESS_KEY_ID")
    print("  - OSS_ACCESS_KEY_SECRET")
    print("  - SMS_SIGN_NAME")
    print("  - SMS_TEMPLATE_CODE")
    sys.exit(1)

def send_sms(phone: str, code: str):
    """发送短信"""
    # 创建客户端配置
    config = open_api_models.Config(
        access_key_id=ACCESS_KEY_ID,
        access_key_secret=ACCESS_KEY_SECRET
    )
    config.endpoint = 'dysmsapi.aliyuncs.com'
    
    # 创建客户端
    client = Dysmsapi20170525Client(config)
    
    # 创建请求
    request = dysmsapi_20170525_models.SendSmsRequest(
        phone_numbers=phone,
        sign_name=SIGN_NAME,
        template_code=TEMPLATE_CODE,
        template_param=f'{{"code":"{code}"}}'
    )
    
    try:
        # 发送请求
        print(f"\n发送短信验证码...")
        print(f"手机号: {phone}")
        print(f"验证码: {code}")
        print(f"签名: {SIGN_NAME}")
        print(f"模板代码: {TEMPLATE_CODE}")
        
        response = client.send_sms(request)
        
        print(f"\n响应状态: {response.body.code}")
        print(f"响应消息: {response.body.message}")
        print(f"请求ID: {response.body.request_id}")
        print(f"业务ID: {response.body.biz_id}")
        
        if response.body.code == 'OK':
            print("\n✅ 短信发送成功！")
            return True
        else:
            print(f"\n❌ 短信发送失败: {response.body.message}")
            return False
            
    except Exception as e:
        print(f"\n❌ 发送失败，错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("阿里云短信服务测试")
    print("=" * 60)
    
    # 提示输入手机号
    phone = input("\n请输入要接收验证码的手机号: ").strip()
    
    if not phone:
        print("❌ 手机号不能为空")
        sys.exit(1)
    
    # 生成6位随机验证码
    code = str(random.randint(100000, 999999))
    
    success = send_sms(phone, code)
    
    if success:
        print("\n✅ 请查收手机短信！")
    else:
        print("\n❌ 请检查配置和阿里云账户余额。")
