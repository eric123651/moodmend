#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
情绪分析工具模块
提供情绪检测和云端情绪分析功能
"""

import logging
import sys

# 导入阿里云服务
try:
    # 使用正确的相对导入路径
    from backend.aliyun_services import get_nlp_service
    nlp_service = get_nlp_service()
except Exception as e:
    logging.error(f"无法导入阿里云服务: {str(e)}")
    nlp_service = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('emotion_utils')

# 情绪分类（参考用）
NEGATIVE_EMOTIONS = ['sad', 'anxious', 'angry']
POSITIVE_EMOTIONS = ['happy']

# 情绪映射字典，用于中英文转换
EMOTION_MAP = {
    'happy': 'happy',
    'sad': 'sad',
    'angry': 'angry',
    'anxious': 'anxious',
    'fear': 'fear',
    'surprise': 'surprise',
    'neutral': 'neutral',
    'calm': 'calm',
    '開心': 'happy',
    '伤心': 'sad',
    '愤怒': 'angry',
    '焦虑': 'anxious',
    '恐惧': 'fear',
    '惊讶': 'surprise',
    '中性': 'neutral',
    '平静': 'calm'
}

def cloud_emotion_analysis(text, language='zh'):
    """
    使用阿里云NLP服务进行情绪分析
    
    Args:
        text: 要分析的文本内容
        language: 语言，默认为中文
    
    Returns:
        情绪分析结果字典
    """
    if not nlp_service:
        logger.error("阿里云NLP服务未初始化")
        # 返回默认结果
        return {
            'emotion': 'neutral',
            'confidence': 0.5,
            'suggestion': '服务暂不可用，请稍后再试'
        }
    
    try:
        logger.info(f"开始情绪分析: {text[:50]}...")
        
        # 调用阿里云NLP服务
        result = nlp_service.analyze_sentiment(text)
        
        # 检查结果是否为None
        if result is None:
            logger.error("情绪分析返回结果为空")
            return {
                'emotion': 'neutral',
                'confidence': 0.5,
                'error': '服务返回结果为空'
            }
        
        # 处理结果
        emotion = result.get('emotion', 'neutral')
        confidence = result.get('confidence', 0.5)
        
        # 转换情绪为英文标准格式
        standard_emotion = EMOTION_MAP.get(emotion, emotion)
        
        logger.info(f"情绪分析完成: {standard_emotion}, 置信度: {confidence}")
        
        return {
            'emotion': standard_emotion,
            'confidence': confidence,
            **({} if 'error' not in result else {'error': result['error']})
        }
        
    except Exception as e:
        logger.error(f"情绪分析失败: {str(e)}")
        # 返回默认结果
        return {
            'emotion': 'neutral',
            'confidence': 0.5,
            'error': str(e)
        }

def detect_emotion(text):
    """
    检测文本中的情绪（兼容旧接口）
    
    Args:
        text: 要分析的文本内容
    
    Returns:
        情绪分析结果
    """
    # 直接调用云服务进行情绪分析
    return cloud_emotion_analysis(text)

def get_emotion_suggestion(emotion, intensity=None):
    """
    根据情绪提供建议
    
    Args:
        emotion: 情绪类型
        intensity: 情绪强度
    
    Returns:
        建议文本
    """
    suggestions = {
        'happy': [
            '保持这份好心情！',
            '太棒了！继续享受美好时光。',
            '分享你的快乐，让更多人感受正能量。'
        ],
        'sad': [
            '给自己一些时间，悲伤是正常的情绪。',
            '试试听一些舒缓的音乐或进行冥想。',
            '找朋友或家人聊聊天，分享你的感受。'
        ],
        'angry': [
            '深呼吸，数到10再做决定。',
            '尝试进行一些体育活动来释放压力。',
            '写下你的感受，然后暂时放下。'
        ],
        'anxious': [
            '专注于当下，做一些放松的练习。',
            '尝试冥想或深呼吸来缓解焦虑。',
            '将大问题分解成小步骤，逐步解决。'
        ],
        'fear': [
            '认识到恐惧是正常的，面对它是克服它的第一步。',
            '尝试渐进式暴露来面对你的恐惧。',
            '寻求专业帮助或与信任的人分享。'
        ],
        'neutral': [
            '平静也是一种很好的状态。',
            '考虑做一些让自己愉悦的事情。',
            '反思今天的经历，寻找小确幸。'
        ]
    }
    
    # 根据情绪强度调整建议
    if intensity:
        emotion_key = emotion.lower()
        if emotion_key in suggestions:
            # 根据强度选择不同的建议
            if intensity > 0.7:
                return suggestions[emotion_key][0]
            elif intensity > 0.4:
                return suggestions[emotion_key][1]
            else:
                return suggestions[emotion_key][2]
    
    # 返回默认建议
    return suggestions.get(emotion.lower(), suggestions['neutral'])[0]
