import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.aliyun_services import nls_service

class TestNLSService(unittest.TestCase):
    
    def test_recognize_speech(self):
        """测试语音识别服务"""
        # 创建模拟音频数据（生成一个简单的二进制数据）
        mock_audio_data = b'\x00\x01\x02\x03' * 100  # 模拟音频数据
        
        # 调用语音识别服务
        result = nls_service.recognize_speech(
            audio_data=mock_audio_data,
            format_type='wav',
            sample_rate=16000
        )
        
        # 验证结果格式
        self.assertIsNotNone(result, "语音识别服务应返回结果")
        self.assertIsInstance(result, dict, "返回结果应为字典类型")
        
        # 验证关键字段
        self.assertIn('text', result, "结果中应包含text字段")
        self.assertIn('success', result, "结果中应包含success字段")
        self.assertIn('task_id', result, "结果中应包含task_id字段")
        
        # 验证模拟文本内容
        self.assertTrue(result['text'], "识别文本不应为空")
        self.assertTrue(result['success'], "识别应成功")
        
        print(f"\n语音识别测试结果:")
        print(f"- 识别文本: {result['text']}")
        print(f"- 状态: {'成功' if result['success'] else '失败'}")
        print(f"- 任务ID: {result['task_id']}")
        if 'audio_info' in result:
            print(f"- 音频信息: {result['audio_info']}")
    
    def test_client_initialization(self):
        """测试客户端初始化状态"""
        self.assertTrue(hasattr(nls_service, 'client'), "服务应具有client属性")
        print("\n客户端初始化测试通过")

if __name__ == '__main__':
    unittest.main()
