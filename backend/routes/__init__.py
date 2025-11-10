# 导出路由模块
from .auth import auth_bp
from .mood import mood_bp
from .log import log_bp

__all__ = ['auth_bp', 'mood_bp', 'log_bp']