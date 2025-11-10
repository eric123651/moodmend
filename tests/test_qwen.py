import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.aliyun_services import QwenPlusService

class TestQwenPlusService(unittest.TestCase):
    
    def setUp(self):
        """设置测试环境"""
        pass
    
    @patch('backend.aliyun_services.dashscope')
    @patch('backend.aliyun_services.config')
    @patch('backend.aliyun_services.logger')
    def test_initialization_success(self, mock_logger, mock_config, mock_dashscope):
        """测试初始化成功的情况"""
        # 配置模拟
        mock_config.DASHSCOPE_API_KEY = 'test-api-key'
        
        # 创建服务实例
        service = QwenPlusService()
        
        # 验证结果
        self.assertTrue(service.initialized)
        mock_dashscope.api_key = 'test-api-key'
        mock_logger.info.assert_called_with("通义千问服务初始化成功")
    
    @patch('backend.aliyun_services.dashscope')
    @patch('backend.aliyun_services.config')
    @patch('backend.aliyun_services.logger')
    def test_initialization_failure_no_api_key(self, mock_logger, mock_config, mock_dashscope):
        """测试API Key缺失时的初始化失败情况"""
        # 配置模拟
        mock_config.DASHSCOPE_API_KEY = None
        
        # 创建服务实例
        service = QwenPlusService()
        
        # 验证结果
        self.assertFalse(service.initialized)
        mock_logger.error.assert_called_with("通义千问服务初始化失败: 通义千问API Key未配置")
    
    @patch('backend.aliyun_services.dashscope')
    @patch('backend.aliyun_services.config')
    @patch('backend.aliyun_services.logger')
    def test_generate_suggestion_success(self, mock_logger, mock_config, mock_dashscope):
        """测试成功生成建议的情况"""
        # 配置模拟
        mock_config.DASHSCOPE_API_KEY = 'test-api-key'
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.request_id = 'test-request-id'
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "这是测试建议内容"
        mock_choice.message = mock_message
        mock_response.output.choices = [mock_choice]
        mock_response.output.model = 'qwen-plus'
        mock_dashscope.Generation.call.return_value = mock_response
        
        # 创建服务实例
        service = QwenPlusService()
        service.initialized = True  # 确保初始化状态为True
        
        # 调用方法
        result = service.generate_task_suggestion('happy')
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['suggestion'], "这是测试建议内容")
        self.assertEqual(result['request_id'], 'test-request-id')
        self.assertEqual(result['model'], 'qwen-plus')
    
    @patch('backend.aliyun_services.dashscope')
    @patch('backend.aliyun_services.config')
    @patch('backend.aliyun_services.logger')
    def test_generate_suggestion_api_failure(self, mock_logger, mock_config, mock_dashscope):
        """测试API调用失败的情况"""
        # 配置模拟
        mock_config.DASHSCOPE_API_KEY = 'test-api-key'
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.message = 'API调用失败'
        mock_dashscope.Generation.call.return_value = mock_response
        
        # 创建服务实例
        service = QwenPlusService()
        service.initialized = True  # 确保初始化状态为True
        
        # 调用方法
        result = service.generate_task_suggestion('sad')
        
        # 验证结果
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'API调用失败')
        self.assertEqual(result['status_code'], 400)
    
    @patch('backend.aliyun_services.dashscope')
    @patch('backend.aliyun_services.config')
    @patch('backend.aliyun_services.logger')
    def test_not_initialized(self, mock_logger, mock_config, mock_dashscope):
        """测试未初始化时调用方法的情况"""
        # 配置模拟
        mock_config.DASHSCOPE_API_KEY = 'test-api-key'
        
        # 创建服务实例
        service = QwenPlusService()
        service.initialized = False  # 确保初始化状态为False
        
        # 调用方法
        result = service.generate_task_suggestion('anxious')
        
        # 验证结果
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "服务未初始化")
    
    @patch('backend.aliyun_services.dashscope')
    @patch('backend.aliyun_services.config')
    @patch('backend.aliyun_services.logger')
    def test_with_user_context(self, mock_logger, mock_config, mock_dashscope):
        """测试带有用户上下文的情况"""
        # 配置模拟
        mock_config.DASHSCOPE_API_KEY = 'test-api-key'
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.request_id = 'test-request-id'
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "带上下文的建议内容"
        mock_choice.message = mock_message
        mock_response.output.choices = [mock_choice]
        mock_response.output.model = 'qwen-plus'
        mock_dashscope.Generation.call.return_value = mock_response
        
        # 创建服务实例
        service = QwenPlusService()
        service.initialized = True  # 确保初始化状态为True
        
        # 准备用户上下文
        user_context = {
            'current_input': '我今天感觉很累',
            'recent_moods': [
                {'emotion': 'tired', 'input': '工作压力太大了，感觉身心俱疲'},
                {'emotion': 'anxious', 'input': '担心明天的重要会议'}
            ]
        }
        
        # 调用方法
        result = service.generate_task_suggestion('tired', user_context)
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['suggestion'], "带上下文的建议内容")
    
    @patch('backend.aliyun_services.dashscope')
    @patch('backend.aliyun_services.config')
    @patch('backend.aliyun_services.logger')
    def test_enable_encryption(self, mock_logger, mock_config, mock_dashscope):
        """测试启用加密功能的情况"""
        # 配置模拟
        mock_config.DASHSCOPE_API_KEY = 'test-api-key'
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.request_id = 'test-request-id'
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "加密模式下的建议内容"
        mock_choice.message = mock_message
        mock_response.output.choices = [mock_choice]
        mock_response.output.model = 'qwen-plus'
        mock_dashscope.Generation.call.return_value = mock_response
        
        # 创建服务实例
        service = QwenPlusService()
        service.initialized = True  # 确保初始化状态为True
        
        # 调用方法，启用加密
        result = service.generate_task_suggestion('neutral', enable_encryption=True)
        
        # 验证DashScope调用参数
        mock_dashscope.Generation.call.assert_called()
        call_args = mock_dashscope.Generation.call.call_args[1]
        self.assertTrue(call_args['enable_encryption'])
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['suggestion'], "加密模式下的建议内容")

if __name__ == '__main__':
    unittest.main()