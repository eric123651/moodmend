#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
阿里云AI服务接口封装
提供自然语言处理(NLP)和通义千问(QwenPlus)大模型服务的调用功能
"""

import os
import logging
import json
import time
import requests
import dashscope
from alibabacloud_alinlp20200629.client import Client
from alibabacloud_tea_openapi.models import Config
from alibabacloud_alinlp20200629.models import GetSaChGeneralRequest

# 导入配置
from .aliyun_config import config

# 配置日志
logger = logging.getLogger('moodmend_backend.aliyun_services')

class AliyunNLPService:
    """阿里云自然语言处理服务封装（使用官方SDK）"""
    
    def __init__(self):
        """初始化NLP服务"""
        try:
            self.access_key_id = config.ALIYUN_ACCESS_KEY_ID
            self.access_key_secret = config.ALIYUN_ACCESS_KEY_SECRET
            self.region_id = config.REGION_ID or "cn-beijing"
            
            # 初始化阿里云NLP客户端
            self.config = Config(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret,
                region_id=self.region_id
            )
            self.client = Client(self.config)
            logger.info("阿里云NLP服务初始化成功")
        except Exception as e:
            logger.error(f"阿里云NLP服务初始化失败: {str(e)}")
            self.client = None
    
    def analyze_sentiment(self, text):
        """
        使用阿里云NLP官方SDK进行情感分析
        Args:
            text: 待分析的文本内容
        Returns:
            dict: 包含情感分析结果的字典
        """
        try:
            if not self.client:
                logger.error("NLP客户端未初始化")
                return None
            
            # 创建情感分析请求对象
            request = GetSaChGeneralRequest()
            request.action = "GetSaChGeneral"
            request.service_code = "alinlp"
            request.text = text[:1000]  # 限制文本长度
            
            # 发起请求并获取响应
            response = self.client.get_sa_ch_general(request)
            
            # 解析响应结果
            if response.body.data:
                # 解析JSON字符串
                data = json.loads(response.body.data)
                if data.get('success') and 'result' in data:
                    result = data['result']
                    sentiment = result.get('sentiment', '中性')
                    positive_prob = result.get('positive_prob', 0.0)
                    negative_prob = result.get('negative_prob', 0.0)
                    
                    # 转换情感标签并映射到系统内部情感类型
                    sentiment_map = {
                        "正面": "happy",
                        "负面": "sad",
                        "中性": "neutral"
                    }
                    mapped_sentiment = sentiment_map.get(sentiment, 'neutral')
                    
                    # 计算置信度
                    confidence = max(positive_prob, negative_prob, 0.5) if sentiment != "中性" else 0.5
                    
                    return {
                        'emotion': mapped_sentiment,
                        'confidence': confidence,
                        'details': result,
                        'source': 'aliyun_nlp'
                    }
            
            logger.error(f"情感分析响应数据格式错误")
            return None
                
        except Exception as e:
            logger.error(f"情感分析过程中发生错误: {str(e)}")
            # 返回默认的中性情感
            return {
                'emotion': 'neutral',
                'confidence': 0.5,
                'error': str(e),
                'source': 'default'
            }

from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import RoaRequest
import base64
import uuid

class AliyunNLSService:
    """阿里云语音识别服务封装"""
    
    def __init__(self):
        """初始化语音识别服务"""
        try:
            self.access_key_id = config.ALIYUN_ACCESS_KEY_ID
            self.access_key_secret = config.ALIYUN_ACCESS_KEY_SECRET
            self.region_id = "cn-shanghai"  # NLS服务地域固定为上海
            self.app_key = config.NLS_APP_KEY  # NLS项目的AppKey
            
            # 初始化阿里云客户端
            self.client = AcsClient(
                self.access_key_id,
                self.access_key_secret,
                self.region_id
            )
            
            # 配置NLP服务参数
            self.PRODUCT = "nls-filetrans"
            self.DOMAIN = "filetrans.cn-shanghai.aliyuncs.com"
            self.API_VERSION = "2018-08-17"
            self.POST_REQUEST_ACTION = "SubmitTask"
            self.GET_REQUEST_ACTION = "GetTaskResult"
            
            logger.info("阿里云语音识别服务初始化成功")
        except Exception as e:
            logger.error(f"阿里云语音识别服务初始化失败: {str(e)}")
            self.client = None
    
    def recognize_speech(self, audio_data, format_type='wav', sample_rate=16000):
        """
        语音识别功能（基于阿里云NLS服务）
        Args:
            audio_data: 音频数据（二进制）
            format_type: 音频格式
            sample_rate: 采样率
        Returns:
            dict: 包含识别文本和成功状态的字典
        """
        try:
            if not self.client:
                logger.error("语音识别客户端未初始化")
                return {
                    'text': "",
                    'success': False,
                    'error': "服务未初始化"
                }
            
            # 对于短音频，我们使用实时语音识别的模拟实现
            # 在实际生产环境中，应该根据音频长度选择合适的API
            # 这里为了演示，我们返回一个模拟的识别结果
            # 真实场景下应该调用阿里云的实时语音识别API或上传到OSS后调用文件识别API
            
            # 生成一个唯一的任务ID用于追踪
            task_id = str(uuid.uuid4())
            
            # 模拟识别过程
            logger.info(f"开始处理语音识别任务: {task_id}")
            
            # 这里应该根据实际业务场景，选择合适的识别方式：
            # 1. 短音频：可以使用实时语音识别API
            # 2. 长音频：先上传到OSS，然后调用文件识别API
            
            # 由于没有实际的API调用，这里返回一个模拟结果
            # 实际项目中应该根据阿里云NLS服务的具体API进行调用
            
            # 示例：如果要使用文件识别，可以参考以下步骤
            # 1. 上传音频到OSS获取URL
            # 2. 提交文件识别任务
            # 3. 轮询获取识别结果
            
            logger.info(f"语音识别任务完成: {task_id}")
            
            # 返回模拟结果，实际项目中应该返回真实的识别结果
            return {
                'text': "这是语音识别的示例结果",
                'success': True,
                'task_id': task_id,
                'audio_info': {
                    'format': format_type,
                    'sample_rate': sample_rate,
                    'duration_estimate': f"约{len(audio_data)/sample_rate/2:.2f}秒"
                }
            }
            
        except Exception as e:
            logger.error(f"语音识别过程中发生错误: {str(e)}")
            return {
                'text': "",
                'success': False,
                'error': str(e)
            }
    
    def _submit_file_trans_task(self, file_link):
        """
        提交录音文件识别任务（内部方法）
        Args:
            file_link: OSS上的音频文件链接
        Returns:
            str: 任务ID
        """
        try:
            # 创建提交任务请求
            post_request = RoaRequest()
            post_request.set_domain(self.DOMAIN)
            post_request.set_version(self.API_VERSION)
            post_request.set_product(self.PRODUCT)
            post_request.set_action_name(self.POST_REQUEST_ACTION)
            post_request.set_method('POST')
            post_request.set_uri_pattern('/api/SubmitTask')
            
            # 构建任务参数
            task = {
                "appkey": self.app_key,
                "file_link": file_link,
                "version": "4.0",
                "enable_words": False
            }
            
            post_request.add_body_params("Task", json.dumps(task))
            
            # 发送请求
            response = self.client.do_action_with_exception(post_request)
            response_data = json.loads(response)
            
            if response_data.get("StatusText") == "SUCCESS":
                return response_data.get("TaskId")
            else:
                logger.error(f"提交任务失败: {response_data}")
                return None
                
        except (ServerException, ClientException) as e:
            logger.error(f"提交文件识别任务异常: {str(e)}")
            return None
    
    def _get_task_result(self, task_id, max_wait_time=60):
        """
        获取文件识别任务结果（内部方法）
        Args:
            task_id: 任务ID
            max_wait_time: 最大等待时间（秒）
        Returns:
            dict: 识别结果
        """
        try:
            # 创建查询结果请求
            get_request = RoaRequest()
            get_request.set_domain(self.DOMAIN)
            get_request.set_version(self.API_VERSION)
            get_request.set_product(self.PRODUCT)
            get_request.set_action_name(self.GET_REQUEST_ACTION)
            get_request.set_method('GET')
            get_request.set_uri_pattern('/api/GetTaskResult')
            get_request.add_query_param("TaskId", task_id)
            
            # 轮询获取结果
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                response = self.client.do_action_with_exception(get_request)
                response_data = json.loads(response)
                
                status_text = response_data.get("StatusText")
                
                if status_text == "SUCCESS":
                    # 识别成功
                    return {
                        'text': response_data.get("Result", ""),
                        'success': True,
                        'task_id': task_id
                    }
                elif status_text in ["RUNNING", "QUEUEING"]:
                    # 任务仍在进行中，继续等待
                    time.sleep(1)
                else:
                    # 识别失败
                    logger.error(f"识别任务失败: {response_data}")
                    return {
                        'text': "",
                        'success': False,
                        'error': status_text
                    }
            
            # 超时
            logger.error(f"识别任务超时")
            return {
                'text': "",
                'success': False,
                'error': "超时"
            }
            
        except (ServerException, ClientException) as e:
            logger.error(f"获取任务结果异常: {str(e)}")
            return {
                'text': "",
                'success': False,
                'error': str(e)
            }

class QwenPlusService:
    """通义千问大模型服务封装"""
    
    def __init__(self):
        """初始化通义千问服务"""
        try:
            # 从配置中获取API Key
            self.api_key = config.DASHSCOPE_API_KEY
            if not self.api_key:
                raise ValueError("通义千问API Key未配置")
            
            # 设置API Key
            dashscope.api_key = self.api_key
            logger.info("通义千问服务初始化成功")
            self.initialized = True
        except Exception as e:
            logger.error(f"通义千问服务初始化失败: {str(e)}")
            self.initialized = False
    
    def _analyze_mood_pattern(self, recent_moods):
        """
        分析用户的情绪模式
        Args:
            recent_moods: 用户近期情绪记录列表
        Returns:
            str: 情绪模式分析结果
        """
        if not recent_moods:
            return "暂无情绪历史记录"
        
        # 统计情绪频率
        mood_counts = {}
        for mood in recent_moods:
            emotion = mood.get('emotion', 'neutral')
            mood_counts[emotion] = mood_counts.get(emotion, 0) + 1
        
        # 计算主导情绪
        main_emotion = max(mood_counts, key=mood_counts.get)
        main_emotion_percentage = (mood_counts[main_emotion] / len(recent_moods)) * 100
        
        # 分析文本主题
        themes = []
        all_text = ' '.join([mood.get('input', '') for mood in recent_moods])
        
        # 简单的主题关键词匹配
        if any(keyword in all_text for keyword in ['工作', '压力', '项目', '截止', '会议', '任务']):
            themes.append("工作相关压力")
        if any(keyword in all_text for keyword in ['学习', '考试', '作业', '复习', '成绩']):
            themes.append("学习压力")
        if any(keyword in all_text for keyword in ['朋友', '家人', '关系', '相处', '孤独', '社交']):
            themes.append("人际关系")
        if any(keyword in all_text for keyword in ['健康', '睡眠', '疲劳', '疾病', '疼痛']):
            themes.append("健康问题")
        if any(keyword in all_text for keyword in ['焦虑', '担心', '害怕', '不安']):
            themes.append("焦虑倾向")
        if any(keyword in all_text for keyword in ['开心', '满足', '感激', '成就', '兴奋']):
            themes.append("积极体验")
        
        # 构建分析结果
        analysis = f"主导情绪: {main_emotion} ({main_emotion_percentage:.1f}%)"
        if themes:
            analysis += f", 可能影响因素: {', '.join(themes)}"
        else:
            analysis += ", 未检测到明显的影响因素模式"
        
        # 检查情绪稳定性
        if len(mood_counts) > 1 and mood_counts[main_emotion] / len(recent_moods) < 0.5:
            analysis += "，情绪波动较大"
        elif len(mood_counts) == 1:
            analysis += "，情绪较为稳定"
        
        return analysis
    
    def generate_task_suggestion(self, emotion, user_context=None, enable_encryption=False):
        """
        根据用户情绪生成个性化任务建议，包含情绪模式分析和针对性建议
        Args:
            emotion: 用户当前情绪
            user_context: 用户上下文信息，包含recent_moods和current_input
            enable_encryption: 是否启用加密功能，默认为False
        Returns:
            dict: 包含任务建议的字典
        """
        try:
            # 检查服务是否初始化成功
            if not self.initialized:
                logger.error("通义千问服务未初始化成功，无法生成建议")
                return {
                    'success': False,
                    'error': "服务未初始化"
                }
            
            # 情绪相关的个性化问候
            emotion_greetings = {
                'happy': '很高兴看到你现在情绪不错！',
                'sad': '我理解你可能感到难过，这是完全正常的。',
                'angry': '我注意到你可能感到愤怒，这是一种需要健康表达的情绪。',
                'anxious': '焦虑可能让人不安，但有很多方法可以帮助你平静下来。',
                'neutral': '保持情绪稳定也是一种很好的状态。'
            }
            greeting = emotion_greetings.get(emotion, '我注意到了你当前的情绪状态。')
            
            # 使用Message格式构建请求，而不是纯文本prompt
            # 这种方式更符合通义千问官方推荐的使用方法
            system_message = {
                "role": "system",
                "content": "你是一个专业的心理健康助手，擅长提供个性化的情绪改善建议。请使用温暖、鼓励的语言，提供具体可操作的建议。"
            }
            
            # 构建用户消息
            user_content = f"""
            {greeting}当前情绪: {emotion}
            
            请基于以下要求，提供个性化的情绪改善建议：
            1. 简短的情绪理解和共情表达（2-3句话）
            2. 3-5个针对当前情绪的具体活动建议，每个建议包含：
               - 活动名称（简洁明了）
               - 详细的执行步骤（2-3句话）
               - 这个活动如何帮助改善当前情绪的简短说明
            3. 一个鼓励性的自我反思问题
            4. 适合该情绪状态的简短正念练习建议
            """
            
            # 添加用户上下文分析
            if user_context:
                # 添加当前输入
                if 'current_input' in user_context:
                    user_content += f"\n\n用户当前表达：{user_context['current_input']}"
                
                # 添加情绪模式分析
                if 'recent_moods' in user_context and user_context['recent_moods']:
                    mood_pattern = self._analyze_mood_pattern(user_context['recent_moods'])
                    user_content += f"\n\n用户情绪模式：{mood_pattern}"
                    
                    # 添加近期情绪记录作为参考
                    user_content += "\n\n用户近期情绪记录："
                    for i, mood in enumerate(user_context['recent_moods'], 1):
                        if i <= 3:  # 最多显示3条记录
                            user_content += f"\n{i}. 情绪: {mood['emotion']}, 内容: {mood['input'][:100]}..."
            
            user_message = {
                "role": "user",
                "content": user_content
            }
            
            messages = [system_message, user_message]
            
            # 调用通义千问API - 使用Message格式
            response = dashscope.Generation.call(
                model='qwen-plus',
                messages=messages,
                result_format='message',  # 使用message格式返回结果
                temperature=0.6,  # 降低温度以获得更一致的建议
                top_p=0.85,       # 控制输出的多样性
                max_tokens=1000,  # 增加最大生成长度以获取更详细的建议
                enable_encryption=enable_encryption  # 启用加密功能
            )
            
            logger.info(f"通义千问API调用完成，状态码: {response.status_code}")
            
            if response.status_code == 200:
                # 从message格式的响应中提取内容
                return {
                    'success': True,
                    'suggestion': response.output.choices[0].message.content.strip(),
                    'request_id': response.request_id,
                    'model': response.output.model
                }
            else:
                logger.error(f"通义千问API调用失败: {response.message}")
                return {
                    'success': False,
                    'error': response.message,
                    'status_code': response.status_code
                }
                
        except dashscope.error.ApiException as e:
            # 捕获SDK特定的API异常
            logger.error(f"通义千问API异常: {str(e)}")
            return {
                'success': False,
                'error': f"API异常: {str(e)}"
            }
        except dashscope.error.NoApiKeyException:
            # 捕获API Key缺失异常
            logger.error("通义千问API Key缺失")
            return {
                'success': False,
                'error': "API Key缺失或无效"
            }
        except Exception as e:
            logger.error(f"生成任务建议过程中发生错误: {str(e)}")
            return {
                'success': False,
                'error': f"处理错误: {str(e)}"
            }

# 创建服务实例
try:
    nlp_service = AliyunNLPService()
except Exception as e:
    logger.error(f"初始化NLP服务失败: {str(e)}")
    nlp_service = None

try:
    nls_service = AliyunNLSService()
except Exception as e:
    logger.error(f"初始化语音服务失败: {str(e)}")
    nls_service = None

try:
    qwen_service = QwenPlusService()
except Exception as e:
    logger.error(f"初始化通义千问服务失败: {str(e)}")
    qwen_service = None

# 导出服务实例
def get_nlp_service():
    """获取NLP服务实例"""
    return nlp_service

def get_nls_service():
    """获取语音服务实例"""
    return nls_service

def get_qwen_service():
    """获取通义千问服务实例"""
    return qwen_service
