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

# 导入配置
from aliyun_config import config

# 配置日志
logger = logging.getLogger('moodmend_backend.aliyun_services')

class AliyunNLPService:
    """阿里云自然语言处理服务封装（使用HTTP API）"""
    
    def __init__(self):
        """初始化NLP服务"""
        try:
            self.access_key_id = config.ALIYUN_ACCESS_KEY_ID
            self.access_key_secret = config.ALIYUN_ACCESS_KEY_SECRET
            self.region_id = config.REGION_ID
            self.api_version = "2019-11-11"
            self.endpoint = f"nlp-automl.{self.region_id}.aliyuncs.com"
            logger.info("阿里云NLP服务初始化成功")
        except Exception as e:
            logger.error(f"阿里云NLP服务初始化失败: {str(e)}")
    
    def analyze_sentiment(self, text):
        """
        使用通义千问进行情感分析
        Args:
            text: 待分析的文本内容
        Returns:
            dict: 包含情感分析结果的字典
        """
        try:
            # 使用通义千问进行情感分析
            messages = [
                {"role": "system", "content": "你是一个情感分析助手，请分析用户输入的文本情感，只返回'positive'、'negative'或'neutral'中的一个，不要返回其他内容。"},
                {"role": "user", "content": text}
            ]
            
            response = dashscope.Generation.call(
                model="qwen-plus",
                messages=messages,
                api_key=config.DASHSCOPE_API_KEY
            )
            
            if response.status_code == 200:
                sentiment = response.output.choices[0].message.content.strip()
                
                # 转换情感标签并映射到系统内部情感类型
                sentiment_map = {
                    "positive": "happy",
                    "negative": "sad",
                    "neutral": "neutral"
                }
                mapped_sentiment = sentiment_map.get(sentiment.lower(), 'neutral')
                
                return {
                    'emotion': mapped_sentiment,
                    'confidence': 0.9,  # 默认置信度
                    'details': response.output,
                    'source': 'dashscope'
                }
            else:
                logger.error(f"情感分析请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"阿里云NLP服务客户端异常: {str(e)}")
            return None
        except ServerException as e:
            logger.error(f"阿里云NLP服务服务端异常: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"情感分析过程中发生未知错误: {str(e)}")
            return None

class AliyunNLSService:
    """阿里云语音识别服务封装（简化版）"""
    
    def __init__(self):
        """初始化语音识别服务"""
        try:
            self.api_key = config.DASHSCOPE_API_KEY
            logger.info("语音识别服务初始化成功")
        except Exception as e:
            logger.error(f"语音识别服务初始化失败: {str(e)}")
    
    def recognize_speech(self, audio_data, format_type='wav', sample_rate=16000):
        """
        语音识别功能（简化版）
        Args:
            audio_data: 音频数据
            format_type: 音频格式
            sample_rate: 采样率
        Returns:
            dict: 识别结果
        """
        try:
            # 暂时返回模拟结果，实际项目中需要接入真实的语音识别服务
            return {
                'text': "模拟语音识别结果",
                'success': True
            }
        except Exception as e:
            logger.error(f"语音识别失败: {str(e)}")
            return None

class QwenPlusService:
    """通义千问大模型服务封装"""
    
    def __init__(self):
        """初始化通义千问服务"""
        dashscope.api_key = config.DASHSCOPE_API_KEY
        logger.info("通义千问服务初始化成功")
    
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
    
    def generate_task_suggestion(self, emotion, user_context=None):
        """
        根据用户情绪生成个性化任务建议，包含情绪模式分析和针对性建议
        Args:
            emotion: 用户当前情绪
            user_context: 用户上下文信息，包含recent_moods和current_input
        Returns:
            dict: 包含任务建议的字典
        """
        try:
            # 情绪相关的个性化问候
            emotion_greetings = {
                'happy': '很高兴看到你现在情绪不错！',
                'sad': '我理解你可能感到难过，这是完全正常的。',
                'angry': '我注意到你可能感到愤怒，这是一种需要健康表达的情绪。',
                'anxious': '焦虑可能让人不安，但有很多方法可以帮助你平静下来。',
                'neutral': '保持情绪稳定也是一种很好的状态。'
            }
            greeting = emotion_greetings.get(emotion, '我注意到了你当前的情绪状态。')
            
            # 构建提示词
            prompt = f"""
            你是一个专业的心理健康助手，擅长提供个性化的情绪改善建议。
            
            {greeting}当前情绪: {emotion}
            
            请基于以下要求，提供个性化的情绪改善建议：
            1. 简短的情绪理解和共情表达（2-3句话）
            2. 3-5个针对当前情绪的具体活动建议，每个建议包含：
               - 活动名称（简洁明了）
               - 详细的执行步骤（2-3句话）
               - 这个活动如何帮助改善当前情绪的简短说明
            3. 一个鼓励性的自我反思问题
            4. 适合该情绪状态的简短正念练习建议
            
            建议应该具体可操作，考虑情绪的强度和特点，使用温暖鼓励的语言。
            """
            
            # 添加用户上下文分析
            if user_context:
                # 添加当前输入
                if 'current_input' in user_context:
                    prompt += f"\n\n用户当前表达：{user_context['current_input']}"
                
                # 添加情绪模式分析
                if 'recent_moods' in user_context and user_context['recent_moods']:
                    mood_pattern = self._analyze_mood_pattern(user_context['recent_moods'])
                    prompt += f"\n\n用户情绪模式：{mood_pattern}"
                    
                    # 添加近期情绪记录作为参考
                    prompt += "\n\n用户近期情绪记录："
                    for i, mood in enumerate(user_context['recent_moods'], 1):
                        if i <= 3:  # 最多显示3条记录
                            prompt += f"\n{i}. 情绪: {mood['emotion']}, 内容: {mood['input'][:100]}..."
            
            # 调用通义千问API
            response = dashscope.Generation.call(
                model='qwen-plus',
                prompt=prompt,
                result_format='text',
                temperature=0.6,  # 降低温度以获得更一致的建议
                top_p=0.85,       # 控制输出的多样性
                max_tokens=1000   # 增加最大生成长度以获取更详细的建议
            )
            
            logger.info(f"通义千问API调用完成: {response.status_code}")
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'suggestion': response.output.text.strip(),
                    'request_id': response.request_id
                }
            else:
                logger.error(f"通义千问API调用失败: {response.message}")
                return {
                    'success': False,
                    'error': response.message
                }
                
        except Exception as e:
            logger.error(f"生成任务建议过程中发生错误: {str(e)}")
            return {
                'success': False,
                'error': str(e)
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
