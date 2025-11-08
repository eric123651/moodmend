# aliyun_config.py
# 阿里云服务配置
import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

class Config:
    # 访问密钥 - 从环境变量读取，提供默认值作为示例
    ALIYUN_ACCESS_KEY_ID = os.getenv("ALIYUN_ACCESS_KEY_ID", "your_access_key_id_here")
    ALIYUN_ACCESS_KEY_SECRET = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "your_access_key_secret_here")
    
    # 通义千问API Key - 从环境变量读取
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "your_dashscope_api_key_here")
    
    # 区域配置 - 从环境变量读取，默认为cn-hangzhou
    REGION_ID = os.getenv("REGION_ID", "cn-hangzhou")
    
    # 智能语音交互服务配置 - 从环境变量读取
    NLS_APP_KEY = os.getenv("NLS_APP_KEY", "your_nls_app_key_here")
    NLS_ENDPOINT = os.getenv("NLS_ENDPOINT", "http://nls-gateway-cn-shanghai.aliyuncs.com")

# 创建配置实例供其他模块导入使用
config = Config()