#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NFT生成工具模块
使用Pillow库生成基于情绪的NFT图像
"""

import os
import random
import logging
from PIL import Image, ImageDraw, ImageFont

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('nft_generator')

class NFTGenerator:
    """
    NFT生成器类
    """
    def __init__(self, output_dir=None):
        """
        初始化NFT生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'data', 'nft_images'
        )
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 情绪对应的颜色方案
        self.emotion_colors = {
            'happy': {'background': '#FFD700', 'accent': '#FF6B6B', 'text': '#2E8B57'},
            'sad': {'background': '#4682B4', 'accent': '#87CEEB', 'text': '#E0FFFF'},
            'angry': {'background': '#FF6347', 'accent': '#FFD700', 'text': '#FFFAFA'},
            'anxious': {'background': '#9370DB', 'accent': '#DDA0DD', 'text': '#F5DEB3'},
            'calm': {'background': '#20B2AA', 'accent': '#98FB98', 'text': '#006400'},
            'neutral': {'background': '#D3D3D3', 'accent': '#696969', 'text': '#FFFFFF'}
        }
    
    def generate_nft(self, emotion, user_id=None, text=None):
        """
        生成基于情绪的NFT图像
        
        Args:
            emotion: 情绪类型
            user_id: 用户ID（可选）
            text: 要包含的文本（可选）
        
        Returns:
            生成的图像文件路径
        """
        try:
            # 获取颜色方案
            colors = self.emotion_colors.get(
                emotion.lower(),
                self.emotion_colors['neutral']
            )
            
            # 创建图像
            width, height = 500, 500
            image = Image.new('RGB', (width, height), color=colors['background'])
            draw = ImageDraw.Draw(image)
            
            # 生成随机图案
            self._draw_pattern(draw, width, height, colors)
            
            # 添加情绪文字
            self._add_text(draw, width, height, emotion, colors['text'])
            
            # 添加自定义文本（如果提供）
            if text:
                self._add_custom_text(draw, width, height, text, colors['text'])
            
            # 生成文件名
            filename = f"nft_{emotion}_{random.randint(1000, 9999)}.png"
            if user_id:
                filename = f"nft_user_{user_id}_{emotion}_{random.randint(1000, 9999)}.png"
            
            # 保存图像
            filepath = os.path.join(self.output_dir, filename)
            image.save(filepath)
            
            logger.info(f"NFT生成成功: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"NFT生成失败: {str(e)}")
            return None
    
    def _draw_pattern(self, draw, width, height, colors):
        """
        绘制随机图案
        
        Args:
            draw: ImageDraw对象
            width: 图像宽度
            height: 图像高度
            colors: 颜色方案
        """
        # 随机生成几何形状
        shapes = random.randint(5, 15)
        
        for _ in range(shapes):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            
            # 随机选择形状类型
            shape_type = random.choice(['rectangle', 'ellipse', 'line'])
            
            if shape_type == 'rectangle':
                draw.rectangle(
                    [(x1, y1), (x2, y2)],
                    outline=colors['accent'],
                    width=random.randint(1, 5)
                )
            elif shape_type == 'ellipse':
                draw.ellipse(
                    [(x1, y1), (x2, y2)],
                    outline=colors['accent'],
                    width=random.randint(1, 5)
                )
            else:  # line
                draw.line(
                    [(x1, y1), (x2, y2)],
                    fill=colors['accent'],
                    width=random.randint(1, 3)
                )
        
        # 添加中心点装饰
        center_size = random.randint(50, 150)
        cx, cy = width // 2, height // 2
        draw.ellipse(
            [
                (cx - center_size // 2, cy - center_size // 2),
                (cx + center_size // 2, cy + center_size // 2)
            ],
            outline=colors['accent'],
            fill=colors['background'],
            width=random.randint(3, 8)
        )
    
    def _add_text(self, draw, width, height, emotion, text_color):
        """
        添加情绪文字
        
        Args:
            draw: ImageDraw对象
            width: 图像宽度
            height: 图像高度
            emotion: 情绪类型
            text_color: 文字颜色
        """
        try:
            # 尝试加载字体
            try:
                font = ImageFont.truetype("Arial.ttf", 40)
            except:
                # 如果Arial不可用，使用默认字体
                font = ImageFont.load_default()
            
            # 绘制情绪文字
            text = f"#{emotion.upper()}"
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # 计算居中位置
            x = (width - text_width) // 2
            y = (height - text_height) // 2 - 30
            
            draw.text((x, y), text, font=font, fill=text_color)
            
        except Exception as e:
            logger.warning(f"添加文字失败: {str(e)}")
            # 尝试简单的文字添加
            draw.text((50, 50), f"#{emotion.upper()}", fill=text_color)
    
    def _add_custom_text(self, draw, width, height, text, text_color):
        """
        添加自定义文本
        
        Args:
            draw: ImageDraw对象
            width: 图像宽度
            height: 图像高度
            text: 自定义文本
            text_color: 文字颜色
        """
        try:
            # 尝试加载字体
            try:
                font = ImageFont.truetype("Arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            # 简单的文本处理
            text = text[:50]  # 限制长度
            
            # 计算位置
            y = height - 60
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            x = (width - text_width) // 2
            
            draw.text((x, y), text, font=font, fill=text_color)
            
        except Exception as e:
            logger.warning(f"添加自定义文字失败: {str(e)}")

# 导出单例实例
generator = NFTGenerator()

def generate_emotion_nft(emotion, user_id=None, text=None):
    """
    便捷函数：生成情绪NFT
    
    Args:
        emotion: 情绪类型
        user_id: 用户ID（可选）
        text: 自定义文本（可选）
    
    Returns:
        生成的图像文件路径
    """
    return generator.generate_nft(emotion, user_id, text)
