# MoodMend 后端服务 - 优化版
# 作者: AI Assistant
# 版本: 4.0
# 运行: python moodmend_backend.py

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from datetime import datetime, timedelta
import re
import json
import os
import logging
import uuid
import bcrypt
import sqlite3
import threading
from functools import wraps
from dotenv import load_dotenv
from textblob import TextBlob
from snownlp import SnowNLP
import joblib

# ML Model global variable
ML_MODEL = None

# Load environment variables
load_dotenv()

# 配置日志
# 设置默认编码为UTF-8
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 创建自定义的StreamHandler，确保UTF-8编码
class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # 尝试编码为系统默认编码，替换无法编码的字符
            msg = self.format(record)
            if hasattr(stream, 'encoding'):
                msg = msg.encode(stream.encoding, errors='replace').decode(stream.encoding)
            stream.write(msg + self.terminator)
            self.flush()

# Get log configuration from environment
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'moodmend.log')

logging.basicConfig(level=getattr(logging, LOG_LEVEL), 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'),
                              UnicodeStreamHandler()])
logger = logging.getLogger('moodmend_backend')

# Flask应用配置 - serve frontend from same app
# Get the path to frontend directory (relative to backend)
import os.path
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app = Flask(__name__, 
            static_folder=FRONTEND_DIR,
            static_url_path='',
            template_folder=FRONTEND_DIR)


# Get configuration from environment
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    logger.warning("SECRET_KEY not set in environment, using random key (not suitable for production)")
    SECRET_KEY = os.urandom(24)
else:
    SECRET_KEY = SECRET_KEY.encode('utf-8')

app.config['SECRET_KEY'] = SECRET_KEY

# CORS configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
CORS(app, origins=CORS_ORIGINS, methods=['GET', 'POST', 'OPTIONS'], allow_headers=['*'])

# 数据库配置
DB_NAME = os.getenv('DATABASE_PATH', 'moodmend.db')
logger.info(f"Using database: {DB_NAME}")

# 线程锁，用于并发安全
db_lock = threading.RLock()

# 模拟数据库（将在启动时从数据库加载）
users_db = {}
logs_db = []
user_last_emotion = {}

# 初始化数据库
def init_db():
    try:
        with db_lock, sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_login TEXT
                )
            ''')
            
            # 检查并添加缺失的user_name列（兼容旧数据库）
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN user_name TEXT NOT NULL DEFAULT '用户'")
                conn.commit()
            except:
                # 如果列已存在，忽略错误
                pass
            # 创建日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    email TEXT,
                    time TEXT,
                    emotion TEXT,
                    task TEXT,
                    nft TEXT,
                    completed BOOLEAN,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            # 创建用户情绪表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_emotions (
                    user_id TEXT PRIMARY KEY,
                    last_emotion TEXT,
                    last_update TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            # 创建反馈表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mood_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_input TEXT NOT NULL,
                    predicted_mood TEXT NOT NULL,
                    actual_mood TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        logger.info("資料庫初始化成功")
    except Exception as e:
        logger.error(f"資料庫初始化失敗: {e}")

def load_ml_model():
    """Load the trained ML model from disk."""
    global ML_MODEL
    try:
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'mood_model.joblib')
        if os.path.exists(model_path):
            ML_MODEL = joblib.load(model_path)
            logger.info("ML 模型載入成功")
        else:
            logger.info("未發現 ML 模型，將使用規則基礎分析")
    except Exception as e:
        logger.error(f"ML 模型載入失敗: {e}")

# ==============================
# 增強版情緒分析系統 v2.0
# ==============================

# 擴展的情緒關鍵字字典 (中英文支持，包含強度權重)
EMOTION_KEYWORDS = {
    'anxious': [
        # 中文關鍵詞
        ('焦慮', 3), ('擔心', 2), ('壓力', 3), ('緊張', 2), ('不安', 2),
        ('害怕', 3), ('恐慌', 4), ('慌張', 2), ('緊繃', 2), ('坐立不安', 3),
        ('忐忑', 2), ('煩憂', 2), ('煩惱', 2), ('憂慮', 2), ('焦慮不安', 3),
        ('心慌', 3), ('惶恐', 3), ('擔憂', 2), ('心煩', 2), ('煩躁不安', 3),
        ('壓力大', 3), ('喘不過氣', 4), ('快窒息', 4), ('好怕', 3), ('很怕', 3),
        ('有點怕', 1), ('有點緊張', 1), ('有點擔心', 1), ('很焦慮', 4), ('超焦慮', 4),
        ('神經緊繃', 3), ('心跳加速', 3), ('手心冒汗', 3), ('不知所措', 3), ('沒安全感', 3),
        ('胡思亂想', 2), ('靜不下心', 3), ('心神不寧', 3), ('憂心忡忡', 3), ('如履薄冰', 4),
        # 英文關鍵詞
        ('anxious', 3), ('worried', 2), ('stressed', 3), ('nervous', 2), ('panic', 4),
        ('scared', 3), ('afraid', 3), ('tense', 2), ('uneasy', 2), ('restless', 2),
        ('apprehensive', 3), ('fretful', 2), ('overwhelmed', 3), ('agitated', 3), ('jittery', 2),
        ('terrified', 4), ('alarmed', 3), ('fearful', 3), ('dread', 4), ('anxiety', 3)
    ],
    'sad': [
        # 中文關鍵詞
        ('傷心', 3), ('難過', 3), ('沮喪', 3), ('孤單', 2), ('悲傷', 3),
        ('失落', 2), ('絕望', 4), ('惆悵', 2), ('憂鬱', 3), ('傷感', 2),
        ('空虛', 3), ('鬱悶', 2), ('難受', 2), ('想哭', 3), ('寂寞', 2),
        ('心痛', 3), ('心碎', 4), ('無助', 3), ('悲觀', 3), ('低落', 2),
        ('不開心', 2), ('不快樂', 2), ('失望', 2), ('灰心', 2), ('很難過', 4),
        ('好難過', 4), ('超難過', 4), ('有點難過', 1), ('有點傷心', 1),
        ('哭了', 3), ('淚流', 3), ('眼淚', 2), ('痛苦', 4), ('心酸', 3),
        ('落寞', 2), ('憔悴', 3), ('消沉', 3), ('哀傷', 3), ('心灰意冷', 4),
        ('萬念俱灰', 4), ('孤苦伶仃', 3), ('悶悶不樂', 2), ('鬱鬱寡歡', 3), ('悲憤', 3),
        # 英文關鍵詞
        ('sad', 3), ('depressed', 4), ('lonely', 2), ('hopeless', 4), ('heartbroken', 4),
        ('disappointed', 2), ('upset', 2), ('crying', 3), ('grief', 4), ('sorrow', 3),
        ('miserable', 4), ('gloomy', 2), ('melancholy', 3), ('tearful', 3), ('unhappy', 2),
        ('despair', 4), ('blue', 2), ('dejected', 3), ('mournful', 4), ('wretched', 4)
    ],
    'angry': [
        # 中文關鍵詞
        ('生氣', 3), ('憤怒', 4), ('煩躁', 2), ('氣憤', 3), ('不滿', 2),
        ('惱火', 3), ('惱怒', 3), ('暴跳如雷', 4), ('氣炸', 4), ('憤慨', 3),
        ('不悅', 1), ('不爽', 2), ('討厭', 2), ('厭煩', 2), ('惱恨', 3),
        ('火大', 3), ('很氣', 3), ('超氣', 4), ('氣死', 4), ('受夠', 3),
        ('煩死', 3), ('抓狂', 4), ('崩潰', 4), ('爆炸', 4), ('忍不住', 2),
        ('不公平', 2), ('被欺負', 3), ('被冤枉', 3), ('有點生氣', 1),
        ('憤憤不平', 3), ('怒氣沖天', 4), ('大發雷霆', 4), ('火冒三丈', 4), ('怨恨', 3),
        ('反感', 2), ('敵意', 3), ('怒不可遏', 4), ('氣急敗壞', 4), ('不甘心', 2),
        # 英文關鍵詞
        ('angry', 3), ('furious', 4), ('frustrated', 2), ('annoyed', 2), ('mad', 3),
        ('pissed', 3), ('irritated', 2), ('hate', 3), ('rage', 4), ('outraged', 4),
        ('enraged', 4), ('resentful', 3), ('indignant', 3), ('hostile', 3), ('bitter', 2),
        ('fuming', 4), ('livid', 4), ('irate', 4), ('vexed', 2), ('wrath', 4)
    ],
    'happy': [
        # 中文關鍵詞
        ('快樂', 3), ('開心', 3), ('興奮', 3), ('愉快', 2), ('滿足', 2),
        ('開朗', 2), ('欣喜', 3), ('高興', 3), ('歡喜', 2), ('雀躍', 3),
        ('愉悅', 2), ('欣慰', 2), ('幸福', 3), ('開懷', 2), ('喜悅', 3),
        ('感恩', 2), ('感謝', 2), ('太棒', 3), ('太好', 2), ('真好', 2),
        ('好開心', 4), ('超開心', 4), ('很開心', 4), ('好幸福', 4), ('很幸福', 4),
        ('謝謝', 1), ('棒', 2), ('讚', 2), ('爽', 2), ('期待', 2),
        ('自在', 2), ('放鬆', 2), ('舒心', 2), ('得意', 2), ('神采奕奕', 3),
        ('樂開懷', 3), ('喜滋滋', 3), ('心花怒放', 4), ('悠然自得', 2), ('歡天喜地', 4),
        # 英文關鍵詞
        ('happy', 3), ('excited', 3), ('joyful', 3), ('grateful', 2), ('blessed', 2),
        ('wonderful', 2), ('amazing', 3), ('great', 2), ('awesome', 3), ('love', 2),
        ('cheerful', 2), ('delighted', 3), ('content', 2), ('ecstatic', 4), ('glad', 2),
        ('thrilled', 4), ('radiant', 3), ('elated', 4), ('blissful', 4), ('jolly', 2)
    ],
    'neutral': [
        # 中文關鍵詞
        ('平靜', 2), ('正常', 1), ('沒事', 1), ('一般', 1), ('平常', 1),
        ('普通', 1), ('淡定', 2), ('無感', 1), ('穩定', 2), ('還好', 1),
        ('可以', 1), ('沒什麼', 1), ('一般般', 1), ('馬馬虎虎', 1),
        ('冷靜', 2), ('安穩', 2), ('泰然', 2), ('如常', 1), ('還可以', 1),
        ('不痛不癢', 1), ('心平氣和', 2), ('波瀾不驚', 2), ('隨遇而安', 2), ('老樣子', 1),
        # 英文關鍵詞
        ('ok', 1), ('okay', 1), ('fine', 1), ('normal', 1), ('calm', 2), ('peaceful', 2),
        ('steady', 2), ('composed', 2), ('indifferent', 1), ('neutral', 1), ('average', 1),
        ('collected', 2), ('serene', 2), ('tranquil', 2), ('unmoved', 1), ('alright', 1)
    ]
}


# 情境觸發詞 (用於生成針對性建議)
CONTEXT_TRIGGERS = {
    'work_stress': {
        'keywords': ['工作', '老闆', '同事', '加班', '開會', '報告', 'deadline', '專案', '客戶', '業績', '績效', '上班', 'work', 'boss', 'colleague', 'meeting', 'report', 'client', 'office'],
        'tips': {
            'zh-CN': [
                '工作壓力需要適當釋放，試著設定明確的下班時間，不帶工作回家。',
                '列出今天最重要的3件事，專注完成它們，其他的可以等明天。',
                '每工作50分鐘，起來走動5分鐘，看看窗外或做簡單伸展。'
            ],
            'en-US': [
                'Work pressure needs proper release. Try setting a clear clock-out time and don\'t bring work home.',
                'List the 3 most important things today and focus on completing them; others can wait until tomorrow.',
                'Every 50 minutes of work, get up and walk for 5 minutes, look out the window or do some simple stretching.'
            ]
        }
    },
    'study_pressure': {
        'keywords': ['考試', '讀書', '功課', '學校', '老師', '作業', '成績', '分數', '大學', '研究所', 'exam', 'study', 'homework', 'school', 'teacher', 'grade', 'score', 'university', 'college'],
        'tips': {
            'zh-CN': [
                '學習需要休息，試試番茄工作法：25分鐘專注學習，5分鐘休息。',
                '把大任務分解成小步驟，完成一個就給自己一個小獎勵。',
                '找一個安靜的環境，把手機調成飛航模式，專注30分鐘。'
            ],
            'en-US': [
                'Learning requires rest. Try the Pomodoro Technique: focus for 25 minutes, then rest for 5 minutes.',
                'Break large tasks into smaller steps and give yourself a small reward for completing one.',
                'Find a quiet environment, turn your phone to airplane mode, and focus for 30 minutes.'
            ]
        }
    },
    'relationship': {
        'keywords': ['吵架', '分手', '感情', '男友', '女友', '老公', '老婆', '伴侶', '朋友', '家人', '父母', '失戀', 'fight', 'breakup', 'relationship', 'boyfriend', 'girlfriend', 'husband', 'wife', 'partner', 'friend', 'family', 'parents'],
        'tips': {
            'zh-CN': [
                '關係中的衝突需要雙方冷靜後再溝通，先給彼此一些空間。',
                '試著用「我覺得...因為...」的句型表達感受，避免指責。',
                '不管結果如何，照顧好自己的情緒是最重要的。'
            ],
            'en-US': [
                'Conflicts in relationships require both parties to calm down before communicating; give each other some space first.',
                'Try expressing feelings using "I feel... because..." to avoid blame.',
                'Regardless of the outcome, taking care of your own emotions is the most important thing.'
            ]
        }
    },
    'sleep_issues': {
        'keywords': ['失眠', '睡不著', '睡不好', '做惡夢', '早醒', '很累', '好累', '沒精神', '疲憊', 'insomnia', 'cannot sleep', 'nightmare', 'tired', 'exhausted', 'fatigue'],
        'tips': {
            'zh-CN': [
                '睡前1小時放下手機，做些放鬆的事如閱讀或泡腳。',
                '試試4-7-8呼吸法：吸氣4秒、憋氣7秒、呼氣8秒，重複3次。',
                '房間保持涼爽、黑暗，睡眠品質會更好。'
            ],
            'en-US': [
                'Put down your phone an hour before bed and do something relaxing like reading or soaking your feet.',
                'Try the 4-7-8 breathing method: inhale for 4 seconds, hold for 7 seconds, exhale for 8 seconds, repeat 3 times.',
                'Keep the room cool and dark; sleep quality will be better.'
            ]
        }
    },
    'health': {
        'keywords': ['生病', '身體', '不舒服', '頭痛', '胃痛', '感冒', '發燒', '看醫生', '醫院', 'sick', 'body', 'uncomfortable', 'headache', 'stomachache', 'cold', 'fever', 'doctor', 'hospital'],
        'tips': {
            'zh-CN': [
                '身體不適時要多休息，不要硬撐，健康最重要。',
                '多喝溫水，讓身體有足夠的水分來恢復。',
                '如果持續不適，建議諮詢專業醫療人員。'
            ],
            'en-US': [
                'When feeling physically unwell, get more rest; don\'t push yourself, health is the most important.',
                'Drink plenty of warm water to give your body enough hydration to recover.',
                'If discomfort persists, it is recommended to consult a professional medical person.'
            ]
        }
    },
    'financial': {
        'keywords': ['錢', '薪水', '經濟', '負債', '貸款', '房租', '物價', '太貴', '省錢', 'money', 'salary', 'economy', 'debt', 'loan', 'rent', 'expensive', 'saving'],
        'tips': {
            'zh-CN': [
                '記錄每日開銷，了解錢都花在哪裡，是改善財務的第一步。',
                '把必要支出和想要的東西分開，優先處理必要的。',
                '財務壓力需要時間解決，先專注在能控制的事情上。'
            ],
            'en-US': [
                'Recording daily expenses and understanding where the money goes is the first step to improving finances.',
                'Separate essential expenses from things you want, and prioritize the essentials.',
                'Financial pressure takes time to resolve; focus on the things you can control first.'
            ]
        }
    }
}

# 強度程度詞
INTENSITY_MODIFIERS = {
    'high': [
        '很', '非常', '超', '太', '極', '好', '超級', '特別', '真的很', '實在太', '快', '要', '受不了',
        'very', 'really', 'extremely', 'so', 'too', 'incredibly', 'highly', 'deeply', 'absolutely'
    ],
    'low': [
        '有點', '有些', '稍微', '一點', '一些', '略微',
        'a bit', 'a little', 'slightly', 'somewhat', 'kind of'
    ]
}

# 調節建議模板 (移除網站推薦，更豐富的建議)
# 多語言調節建議
SUGGESTIONS = {
    'zh-CN': {
        'anxious': {
            'tips': [
                '深呼吸練習：吸氣4秒，憋氣4秒，吐氣4秒，重複5次。',
                '試試「5-4-3-2-1」練習：說出5個看到的、4個聽到的、3個摸到的、2個聞到的、1個嚐到的。',
                '把擔心的事寫下來，區分「能控制」和「不能控制」的，專注在能控制的部分。'
            ],
            'daily_task': [
                '今天花10分鐘做一件讓你放鬆的事，例如聽音樂或散步。',
                '列出3件今天感恩的小事，轉移注意力。',
                '找一個安靜的地方，閉眼休息5分鐘，什麼都不想。'
            ],
            'advice': [
                '焦慮是身體想保護你的信號，但你可以告訴自己：「這只是感覺，它會過去的。」',
                '試著問自己：「這件事最壞的結果是什麼？我能應對嗎？」通常答案是肯定的。',
                '把大問題拆解成小步驟，一次只處理一步，會感覺更有掌控感。'
            ],
            'color': 'anxious'
        },
        'sad': {
            'tips': [
                '聽一首喜歡的歌，或散步10分鐘接觸陽光。',
                '給自己一個溫暖的擁抱（真的抱自己），這能釋放安慰的荷爾蒙。',
                '如果想哭，就哭吧。眼淚是釋放情緒的方式，哭完會輕鬆一些。'
            ],
            'daily_task': [
                '今天和一個關心你的人說說話，不一定要聊煩惱，只是聊聊也好。',
                '做一件以前讓你開心的事，即使現在沒那麼開心，也給自己機會。',
                '寫下3件讓你微笑的小事，可以是回憶也可以是期待的事。'
            ],
            'advice': [
                '難過是正常的情緒，不需要假裝沒事。給自己時間和空間去感受。',
                '記住：這個感覺是暫時的，就像天氣會變化，心情也會慢慢好轉。',
                '照顧好基本需求：吃飽、睡夠、喝水，身體狀態會影響心情。'
            ],
            'color': 'sad'
        },
        'angry': {
            'tips': [
                '快走5分鐘或做20個開合跳，用運動釋放身體裡的能量。',
                '拿張紙把氣話寫下來，然後撕掉或揉成一團丟掉，象徵性地放下。',
                '用力握拳10秒，然後慢慢鬆開，重複3次，感受從緊繃到放鬆的變化。'
            ],
            'daily_task': [
                '今天做5分鐘運動來釋放積壓的能量。',
                '如果對某人生氣，等24小時再決定要不要說什麼，給自己冷靜的時間。',
                '問自己：「現在最重要的是什麼？」幫自己回到當下。'
            ],
            'advice': [
                '生氣是正常的，但我們可以選擇如何表達它。給自己一些時間再反應。',
                '試著理解是什麼讓你生氣——是事件本身，還是它觸發了某個敏感點？',
                '問自己：「這件事10年後還重要嗎？」很多事情其實沒那麼大不了。'
            ],
            'color': 'angry'
        },
        'happy': {
            'tips': [
                '記錄這一刻！寫下或拍照，以後回顧時會更加珍惜。',
                '分享你的喜悅給一個人，快樂會因分享而加倍。',
                '趁著好心情，完成一件一直拖延的小事。'
            ],
            'daily_task': [
                '計劃一個小慶慶祝活動，犒賞自己。',
                '寫下今天讓你開心的事，建立「快樂存摺」。',
                '趁心情好，給未來的自己寫一封鼓勵的信。'
            ],
            'advice': [
                '好好享受這份快樂，你值得開心！',
                '思考是什麼帶來了這份快樂，以後可以創造更多這樣的時刻。',
                '保持這份正能量，它會感染身邊的人。'
            ],
            'color': 'happy'
        },
        'neutral': {
            'tips': [
                '維持平衡：喝杯水，伸展身體，呼吸新鮮空氣。',
                '這是很好的狀態，趁現在做些自我照顧的事。',
                '可以做個簡單的冥想，保持這份平靜。'
            ],
            'daily_task': [
                '反思一下：今天有什麼值得感謝的？',
                '趁著心情平穩，整理一下待辦事項。',
                '做一件小事讓自己開心，例如吃喜歡的點心。'
            ],
            'advice': [
                '平靜是很棒的狀態，好好珍惜。',
                '趁現在思考一下，有沒有什麼目標想達成？',
                '保持規靈作息，維持這份平衡的感覺。'
            ],
            'color': 'neutral'
        }
    },
    'en-US': {
        'anxious': {
            'tips': [
                'Deep breathing: inhale for 4s, hold for 4s, exhale for 4s. Repeat 5 times.',
                'Try the "5-4-3-2-1" exercise: Name 5 things you see, 4 you hear, 3 you can touch, 2 you can smell, and 1 you can taste.',
                'Write down your worries. Distinguish between controllable and uncontrollable factors, and focus on the controllable.'
            ],
            'daily_task': [
                'Spend 10 minutes doing something relaxing, like listening to music or taking a walk.',
                'List 3 small things you are grateful for today to shift your focus.',
                'Find a quiet place, close your eyes, and rest for 5 minutes with a clear mind.'
            ],
            'advice': [
                'Anxiety is a signal from your body trying to protect you. Remind yourself: "This is just a feeling, and it will pass."',
                'Ask yourself: "What is the worst that could happen? Can I handle it?" The answer is usually yes.',
                'Break down big problems into small steps. Handling one step at a time provides a sense of control.'
            ],
            'color': 'anxious'
        },
        'sad': {
            'tips': [
                'Listen to a favorite song or spend 10 minutes in the sunlight.',
                'Give yourself a warm hug (literally), this releases comforting hormones.',
                'If you need to cry, just do it. Tears are a way of releasing emotions, and you will feel lighter afterwards.'
            ],
            'daily_task': [
                'Talk to someone who cares about you today. You don\'t even have to talk about your worries; just a chat is fine.',
                'Do something that used to make you happy, even if you don\'t feel like it right now.',
                'Write down 3 small things that make you smile – memories or things you look forward to.'
            ],
            'advice': [
                'Sadness is a normal emotion. Don\'t feel pressured to pretend you\'re okay. Give yourself time and space.',
                'Remember: this feeling is temporary. Just like the weather changes, your mood will gradually improve.',
                'Take care of basic needs: eat well, get enough sleep, and stay hydrated. Body state affects mind state.'
            ],
            'color': 'sad'
        },
        'angry': {
            'tips': [
                'Take a fast 5-minute walk or do 20 jumping jacks to release energy from your body.',
                'Write down your angry thoughts on a piece of paper, then tear it up or crumple it – symbolically letting go.',
                'Clench your fists tightly for 10 seconds, then release slowly. Repeat 3 times to feel the shift from tension to relaxation.'
            ],
            'daily_task': [
                'Do 5 minutes of exercise today to release pent-up energy.',
                'If you are angry at someone, wait 24 hours before deciding to say anything. Give yourself time to cool down.',
                'Ask yourself: "What is most important right now?" to help bring yourself back to the present.'
            ],
            'advice': [
                'It\'s okay to feel angry, but we can choose how to express it. Give yourself time before reacting.',
                'Try to understand why you are angry – is it the event itself, or did it trigger a specific sensitive point?',
                'Ask yourself: "Will this matter in 10 years?" Many things aren\'t as big of a deal as they seem.'
            ],
            'color': 'angry'
        },
        'happy': {
            'tips': [
                'Record this moment! Write it down or take a photo to cherish it later.',
                'Share your joy with someone; happiness doubles when shared.',
                'While in a good mood, complete a small task you\'ve been procrastinating on.'
            ],
            'daily_task': [
                'Plan a small celebration or treat for yourself.',
                'Write down what made you happy today to build your "Happiness Bank."',
                'While you feel good, write an encouraging letter to your future self.'
            ],
            'advice': [
                'Enjoy this happiness to the fullest – you deserve to be happy!',
                'Reflect on what brought this joy so you can create more moments like this in the future.',
                'Keep this positive energy going; it will naturally inspire those around you.'
            ],
            'color': 'happy'
        },
        'neutral': {
            'tips': [
                'Maintain balance: drink water, stretch, and breathe fresh air.',
                'This is a great state – take a moment for some self-care.',
                'Do a simple meditation to maintain this sense of calm.'
            ],
            'daily_task': [
                'Reflect: What are you grateful for today?',
                'While your mind is steady, organize your to-do list.',
                'Do something small for yourself, like enjoying a favorite snack.'
            ],
            'advice': [
                'Calmness is a wonderful state to be in. Cherish it.',
                'Take this time to think about any goals you want to achieve.',
                'Keep a regular routine to maintain this balanced feeling.'
            ],
            'color': 'neutral'
        }
    }
}

# 多語言 NFT 徽章
NFT_BADGES = {
    'zh-CN': {
        'anxious': '🛡️ 勇者徽章 - 戰勝焦慮',
        'sad': '🌈 彩虹徽章 - 擁抱療癒',
        'angry': '🔥 鳳凰徽章 - 轉化怒火',
        'happy': '⭐ 星光徽章 - 喜悅守護',
        'neutral': '⚖️ 平衡徽章 - 平靜之源'
    },
    'en-US': {
        'anxious': '🛡️ Brave Badge - Conquered Anxiety',
        'sad': '🌈 Rainbow Badge - Embracing Healing',
        'angry': '🔥 Phoenix Badge - Transformed Anger',
        'happy': '⭐ Starlight Badge - Joy Protector',
        'neutral': '⚖️ Balance Badge - Source of Calm'
    }
}

# 負面情緒定義 (用於轉移偵測)
NEGATIVE_EMOTIONS = {'anxious', 'sad', 'angry'}
POSITIVE_EMOTIONS = {'happy', 'neutral'}

# 增强的情緒偵測函數 v2.0
def detect_emotion(text):
    """偵測文本中的主要情緒，使用加權評分系統 + NLP 情感分析"""
    if not text or not isinstance(text, str):
        return 'neutral', 0
    
    text_lower = text.lower()
    scores = {emotion: 0 for emotion in EMOTION_KEYWORDS}
    matched_keywords = []
    
    # 1. 關鍵詞匹配 (基礎分數)
    for emotion, keyword_list in EMOTION_KEYWORDS.items():
        for kw, weight in keyword_list:
            if kw.lower() in text_lower:
                scores[emotion] += weight
                matched_keywords.append((kw, emotion, weight))
    
    # 2. 否定詞模式處理
    negation_patterns = [
        ('不開心', 'sad', 2), ('不快樂', 'sad', 2), ('不高興', 'sad', 2),
        ('不想', 'sad', 1), ('不好', 'sad', 1), ('不行', 'anxious', 1),
        ('受不了', 'angry', 3), ('忍不住', 'angry', 2)
    ]
    for pattern, emotion, weight in negation_patterns:
        if pattern in text_lower:
            scores[emotion] += weight
            matched_keywords.append((pattern, emotion, weight))

    # 3. NLP 情感分析 (輔助分數)
    try:
        # 英文分析 (TextBlob)
        if any(ord(c) < 128 for c in text):
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            if polarity > 0.5:
                scores['happy'] += 2
            elif polarity < -0.5:
                scores['sad'] += 1
                scores['angry'] += 1
        
        # 中文分析 (SnowNLP)
        if any(ord(c) > 127 for c in text):
            s = SnowNLP(text)
            sent = s.sentiments # 0 to 1, 1 is positive
            if sent > 0.8:
                scores['happy'] += 2
            elif sent < 0.2:
                scores['sad'] += 1
                scores['anxious'] += 1
    except Exception as nlp_e:
        logger.warning(f"NLP 分析失敗 (跳過): {nlp_e}")

    # 4. ML 模型預測 (高優先級，如果可用且置信度高)
    if ML_MODEL:
        try:
            # Predict labels
            prediction = ML_MODEL.predict([text])[0]
            # RandomForest doesn't easily give a single 'score' like our keywords, 
            # but we can check probabilities if needed. For now, we add weight.
            scores[prediction] += 2
            logger.info(f"ML 預測結果: {prediction}")
        except Exception as ml_e:
            logger.error(f"ML 預測失敗: {ml_e}")

    # 计算总分数
    total_score = sum(scores.values())
    
    if total_score == 0:
        # 最后尝试一些常见的中性表达
        neutral_phrases = ['沒什麼', '還好', '一般般', '普通', '正常', '可以', '還行']
        for phrase in neutral_phrases:
            if phrase.lower() in text_lower:
                return 'neutral', 1
        return 'neutral', 0
    
    # 返回得分最高的情绪及其分数
    dominant = max(scores, key=scores.get)
    return dominant, scores[dominant]

def detect_intensity(text, emotion_score):
    """檢測情緒強度：mild(輕微), moderate(中等), severe(嚴重)"""
    if not text:
        return 'moderate'
    
    text_lower = text.lower()
    
    # 檢查高強度詞
    high_intensity_count = sum(1 for mod in INTENSITY_MODIFIERS['high'] if mod in text_lower)
    
    # 檢查低強度詞
    low_intensity_count = sum(1 for mod in INTENSITY_MODIFIERS['low'] if mod in text_lower)
    
    # 根據分數和修飾詞判斷強度
    if high_intensity_count > 0 or emotion_score >= 6:
        return 'severe'
    elif low_intensity_count > 0 or emotion_score <= 2:
        return 'mild'
    else:
        return 'moderate'

def detect_context(text):
    """檢測文本中的情境觸發詞，返回相關情境列表"""
    if not text:
        return []
    
    text_lower = text.lower()
    detected_contexts = []
    
    for context_name, context_data in CONTEXT_TRIGGERS.items():
        for keyword in context_data['keywords']:
            if keyword.lower() in text_lower:
                detected_contexts.append(context_name)
                break  # 一個情境只需匹配一次
    
    return detected_contexts

def generate_personalized_feedback(emotion, intensity, contexts, original_text, lang='zh-CN'):
    """根據情緒、強度和情境生成個性化回饋"""
    import random
    
    # 获取对应语言的建议
    lang_suggestions = SUGGESTIONS.get(lang, SUGGESTIONS['zh-CN'])
    pkg = lang_suggestions.get(emotion, lang_suggestions['neutral'])
    
    # 從列表中隨機選擇建議（如果是列表）
    def get_suggestion(field):
        value = pkg.get(field, '')
        if isinstance(value, list) and len(value) > 0:
            return random.choice(value)
        return value
    
    tips = get_suggestion('tips')
    daily_task = get_suggestion('daily_task')
    advice = get_suggestion('advice')
    
    # 如果有情境觸發，添加情境特定建議
    context_tips = []
    for context in contexts[:2]:  # 最多取2個情境
        if context in CONTEXT_TRIGGERS:
            # 这里的Trigger也可能需要翻译，但目前主要是Tips
            context_tip = random.choice(CONTEXT_TRIGGERS[context]['tips'])
            context_tips.append(context_tip)
    
    # 根據強度調整語氣
    intensity_prefix = ''
    if lang == 'en-US':
        if intensity == 'severe':
            intensity_prefixes = [
                'I understand your feelings are very strong right now.',
                'It sounds like you are going through a difficult time.',
                'This feeling is indeed not easy.'
            ]
            intensity_prefix = random.choice(intensity_prefixes)
        elif intensity == 'mild':
            intensity_prefixes = [
                'It is normal to feel this way.',
                'Small emotional fluctuations are normal.',
                'This feeling will pass.'
            ]
            intensity_prefix = random.choice(intensity_prefixes)
    else: # Default zh-CN
        if intensity == 'severe':
            intensity_prefixes = [
                '我理解你現在感受很強烈。',
                '聽起來你正在經歷困難的時刻。',
                '這種感覺確實很不容易。'
            ]
            intensity_prefix = random.choice(intensity_prefixes)
        elif intensity == 'mild':
            intensity_prefixes = [
                '這是很正常的感受。',
                '小小的情緒波動很正常。',
                '這種感覺會過去的。'
            ]
            intensity_prefix = random.choice(intensity_prefixes)
    
    return {
        'tips': tips,
        'daily_task': daily_task,
        'advice': (intensity_prefix + ' ' + advice).strip() if intensity_prefix else advice,
        'context_tips': context_tips,
        'intensity': intensity,
        'detected_contexts': contexts,
        'color': pkg.get('color', 'neutral')
    }


# 生成基本NFT徽章
def generate_nft_badge(emotion, lang='zh-CN'):
    lang_badges = NFT_BADGES.get(lang, NFT_BADGES['zh-CN'])
    badge = lang_badges.get(emotion, lang_badges['neutral'])
    logger.info(f"生成NFT徽章: {badge} (情绪: {emotion}, 语言: {lang})")
    return badge

# 增强的特殊轉移NFT
def generate_transition_nft(prev_emotion, current_emotion, lang='zh-CN'):
    # 从负面到正面的转移
    if prev_emotion in NEGATIVE_EMOTIONS and current_emotion in POSITIVE_EMOTIONS:
        if lang == 'en-US':
            transition_mapping = {
                ('anxious', 'happy'): '🌟 Star of Calmness - Transition from Anxious to Happy',
                ('anxious', 'neutral'): '✨ Power of Peace - Transition from Anxious to Calm',
                ('sad', 'happy'): '🌈 Joyful Rebirth - Transformation from Sad to Happy',
                ('sad', 'neutral'): '🌊 Calm as the Sea - Healing from Sad to Calm',
                ('angry', 'happy'): '🌞 Messenger of Peace - Transformation from Angry to Happy',
                ('angry', 'neutral'): '🌿 Heart of Cooling - Control from Angry to Calm'
            }
            default_badge = '🌟 Success Mitigation Badge - Victory in Emotion Management'
        else:
            transition_mapping = {
                ('anxious', 'happy'): '🌟 平復之星 - 從焦慮到喜悅的轉變',
                ('anxious', 'neutral'): '✨ 平靜之力 - 從焦慮到平靜的轉變',
                ('sad', 'happy'): '🌈 快樂重生 - 從傷心到喜悅的蛻變',
                ('sad', 'neutral'): '🌊 平靜如海 - 從傷心到平靜的治癒',
                ('angry', 'happy'): '🌞 和平使者 - 從憤怒到喜悅的轉化',
                ('angry', 'neutral'): '🌿 冷靜之心 - 從憤怒到平靜的掌控'
            }
            default_badge = '🌟 成功緩和徽章 - 情緒管理的勝利'
            
        special_badge = transition_mapping.get((prev_emotion, current_emotion), default_badge)
        logger.info(f"生成特殊NFT: {special_badge} (从{prev_emotion}到{current_emotion})")
        return special_badge
    
    # 连续保持正面情绪的奖励
    if prev_emotion in POSITIVE_EMOTIONS and current_emotion in POSITIVE_EMOTIONS:
        if lang == 'en-US':
            return '🏆 Perseverance Badge - Achievement in Maintaining Positive Mindset'
        return '🏆 持之以恆徽章 - 保持積極心態的成就'
    
    return None

# 工具函数: 验证邮箱格式
def is_valid_email(email):
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_pattern, email) is not None

# 工具函数: 获取数据库连接
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row  # Set row_factory to allow accessing columns by name
    return g.db

# API: 註冊
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        user_name = data.get('user_name')
        confirm_password = data.get('confirm_password')  # 获取确认密码
        
        # 验证输入
        if not email or not password or not user_name:
            return jsonify({
                'success': False,
                'message': '電子郵件、密碼和使用者名稱不能為空'
                }), 400
        
        if not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '請輸入有效的電子郵件地址'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': '密碼長度不能少於6位'
            }), 400
            
        if len(user_name) < 2 or len(user_name) > 20:
            return jsonify({
                'success': False,
                'message': '使用者名稱長度應在2-20個字符之間'
            }), 400
            
        # 验证确认密码
        if confirm_password is not None and password != confirm_password:
            return jsonify({
                'success': False,
                'message': '两次輸入的密碼不一致'
            }), 400
        
        # 检查邮箱是否已存在
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            return jsonify({
                'success': False,
                'message': '該電子郵件已被註冊'
            }), 409
        
        # 密码加密
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_id = str(uuid.uuid4())
        
        # 插入用户
        cursor.execute(
            'INSERT INTO users (user_id, email, password, user_name, created_at) VALUES (?, ?, ?, ?, ?)',
            (user_id, email, hashed_password.decode('utf-8'), user_name, datetime.now().isoformat())
        )
        conn.commit()
        
        # 更新内存中的用户数据
        users_db[email] = {
            'user_id': user_id,
            'password': hashed_password.decode('utf-8'),
            'user_name': user_name
        }
        
        logger.info(f"新用戶註冊成功: {email}, 使用者名稱: {user_name}")
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'email': email,
            'user_name': user_name
        }), 201
        
    except Exception as e:
        logger.error(f"註冊失敗: {e}")
        return jsonify({
            'success': False,
            'message': '註冊失敗，請稍後重試'   
        }), 500

# API: 登錄
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        # 验证输入
        if not email or not password:
            return jsonify({
                'success': False,
                'message': '電子郵件和密碼不能為空'
            }), 400
        
        # 优先处理测试账号
        if email == 'test@test.com' and password == '123':
            logger.info("演示用戶登錄成功")
            return jsonify({
                'success': True,
                'user_id': '1',
                'email': email,
                'user_name': '測試用戶',
                'message': '演示用戶登錄成功'
            })
        
        # 检查用户
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({
                'success': False,
                'message': '電子郵件或密碼錯誤'
            }), 401
        
        # 验证密码
        try:
            if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                return jsonify({
                    'success': False,
                    'message': '電子郵件或密碼錯誤'
                }), 401
        except Exception as e:
            logger.error(f"密碼驗證失敗: {e}")
            return jsonify({
                'success': False,
                'message': '密碼驗證失敗，請聯繫管理員'
            }), 500
        
        # 更新最後登錄時間
        cursor.execute('UPDATE users SET last_login = ? WHERE user_id = ?',
                      (datetime.now().isoformat(), user['user_id']))
        conn.commit()
        
        logger.info(f"用戶登錄成功: {email}, 用戶名稱: {user['user_name']}")
        
        return jsonify({
            'success': True,
            'user_id': user['user_id'],
            'email': user['email'],
            'user_name': user['user_name']
        })
        
    except Exception as e:
        logger.error(f"登錄失敗: {e}")
        return jsonify({
            'success': False,
            'message': '登錄失敗，請稍後重試'
        }), 500

# API: 處理情緒輸入
@app.route('/api/process-emotion', methods=['POST'])
def process_emotion():
    try:
        data = request.json
        user_input = data.get('input', '')
        email = data.get('email')
        task_completed = data.get('task_completed', False)
        
        # 增强的输入类型验证和处理
        # 确保data是字典
        if not isinstance(data, dict):
            data = {}
        
        # 重新获取user_input，确保正确的变量引用
        user_input = data.get('input', '')
        
        # 确保user_input是字符串 - 全面的类型处理
        if user_input is None:
            user_input = ''
        elif not isinstance(user_input, str):
            # 如果是字典，尝试各种方式提取字符串内容
            if isinstance(user_input, dict):
                # 1. 尝试获取text字段
                if 'text' in user_input:
                    user_input = user_input['text']
                # 2. 尝试获取第一个非空值
                elif user_input:
                    for key, value in user_input.items():
                        if isinstance(value, str) and value.strip():
                            user_input = value
                            break
                    # 如果没有找到合适的值，使用第一个值
                    else:
                        first_value = next(iter(user_input.values()), '')
                        user_input = str(first_value)
                else:
                    user_input = ''
            # 对于其他非字符串类型，转换为字符串
            else:
                try:
                    user_input = str(user_input)
                except:
                    user_input = ''
        
        # 去除首尾空白字符
        user_input = user_input.strip()
        
        # 验证输入
        if not user_input:
            return jsonify({
                'success': False,
                'message': '情緒描述不能為空'
            }), 400
        
        if not email or not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '無效的用戶信息'
            }), 401
        
        # 偵測情緒 (v2.0 - 返回情緒和分數)
        emotion, emotion_score = detect_emotion(user_input)
        
        # 偵測情緒強度
        intensity = detect_intensity(user_input, emotion_score)
        
        # 偵測情境觸發詞
        contexts = detect_context(user_input)
        
        # 獲取語言偏好
        lang = data.get('lang', 'zh-CN')
        
        # 生成個性化回饋
        pkg = generate_personalized_feedback(emotion, intensity, contexts, user_input, lang)
        
        # 生成基本NFT
        nft = generate_nft_badge(emotion, lang)
        
        # 檢查情緒轉移
        transition_nft_str = ''
        conn = get_db()
        cursor = conn.cursor()
        
        # 从数据库获取上次情绪
        cursor.execute('SELECT last_emotion FROM user_emotions WHERE user_id = (SELECT user_id FROM users WHERE email = ?)', (email,))
        result = cursor.fetchone()
        prev_emotion = result[0] if result else None
        
        # 或者从内存中获取
        if not prev_emotion and email in user_last_emotion:
            prev_emotion = user_last_emotion[email]
        
        if prev_emotion and task_completed:
            transition_nft = generate_transition_nft(prev_emotion, emotion, lang)
            if transition_nft:
                transition_nft_str = ' + ' + transition_nft
                nft += transition_nft_str
        
        # 更新数据库中的上次情绪
        user_id = None
        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
        user_result = cursor.fetchone()
        if user_result:
            user_id = user_result[0]
            cursor.execute(
                'INSERT OR REPLACE INTO user_emotions (user_id, last_emotion, last_update) VALUES (?, ?, ?)',
                (user_id, emotion, datetime.now().isoformat())
            )
            conn.commit()
        
        # 更新内存中的上次情绪
        user_last_emotion[email] = emotion
        
        logger.info(f"處理情緒成功: 用戶={email}, 輸入='{user_input[:30]}...', 情緒={emotion}, 強度={intensity}, 情境={contexts}")
        
        return jsonify({
            'success': True,
            'emotion': emotion,
            'package': {
                'tips': pkg['tips'],
                'daily_task': pkg['daily_task'],
                'advice': pkg['advice'],
                'context_tips': pkg.get('context_tips', []),
                'intensity': pkg.get('intensity', 'moderate'),
                'color': pkg['color']
            },
            'nft': nft,
            'transition_nft': transition_nft_str
        })
        
    except Exception as e:
        logger.error(f"處理情緒失敗: {e}")
        return jsonify({
            'success': False,
            'message': '處理情緒失敗，請稍後重試'
        }), 500

# API: 記錄日誌
@app.route('/api/add-log', methods=['POST'])
def add_log():
    try:
        data = request.json
        email = data.get('email')
        emotion = data.get('emotion')
        task = data.get('task')
        badge = data.get('nft')  # 从UI传过来的是nft
        completed = data.get('completed', False)
        
        # 验证输入
        if not all([email, emotion, task, badge]):
            return jsonify({
                'success': False,
                'message': '缺少必要的日誌信息'
            }), 400
        
        if not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '無效的用戶信息'
            }), 401
        
        # 生成日誌ID和時間戳
        log_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # 保存到数据库
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
        user_result = cursor.fetchone()
        
        if not user_result:
            return jsonify({
                'success': False,
                'message': '用戶不存在'
            }), 404
        
        user_id = user_result[0]
        
        cursor.execute(
            '''INSERT INTO logs 
               (log_id, user_id, email, time, emotion, task, nft, completed) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (log_id, user_id, email, timestamp, emotion, task, badge, completed)
        )
        conn.commit()
        
        # 更新内存中的日志（用于缓存）
        log_entry = {
            'log_id': log_id,
            'time': timestamp,
            'email': email,
            'emotion': emotion,
            'task': task,
            'nft': badge,
            'completed': completed
        }
        logs_db.append(log_entry)
        
        # 限制内存日志数量，避免内存泄漏
        if len(logs_db) > 1000:
            logs_db.pop(0)
        
        logger.info(f"日誌記錄成功: 用戶={email}, 情緒={emotion}")
        
        return jsonify({
            'success': True,
            'log': log_entry
        })
        
    except Exception as e:
        logger.error(f"記錄日誌失敗: {e}")
        return jsonify({
            'success': False,
            'message': '記錄日誌失敗，請稍後重試'
        }), 500

# API: 提交情緒反饋 (ML Phase 1)
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.json
        user_input = data.get('user_input')
        predicted_mood = data.get('predicted_mood')
        actual_mood = data.get('actual_mood')
        
        if not all([user_input, predicted_mood, actual_mood]):
            return jsonify({'success': False, 'message': '缺少必要參數'}), 400
            
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO mood_feedback (user_input, predicted_mood, actual_mood) VALUES (?, ?, ?)',
            (user_input, predicted_mood, actual_mood)
        )
        conn.commit()
        
        logger.info(f"收到情緒反饋: 輸入='{user_input[:20]}', 預測={predicted_mood}, 實際={actual_mood}")
        return jsonify({'success': True, 'message': '感謝您的回饋！'})
        
    except Exception as e:
        logger.error(f"提交反饋失敗: {e}")
        return jsonify({'success': False, 'message': '提交失敗'}), 500

# API: 获取日志列表
@app.route('/api/get-logs', methods=['GET'])
def get_logs():
    try:
        email = request.args.get('email')
        emotion_filter = request.args.get('emotion')
        date_filter = request.args.get('date')
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        # 验证输入
        if not email or not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '無效的用戶信息'
            }), 401
        
        # 构建查詢
        conn = get_db()
        cursor = conn.cursor()
        
        # 基礎查詢
        query = '''SELECT log_id, time, emotion, task, nft, completed 
                  FROM logs 
                  WHERE email = ?''' 
        params = [email]
        
        # 添加過濾條件
        if emotion_filter:
            query += " AND emotion = ?"
            params.append(emotion_filter)
        
        if date_filter:
            query += " AND time LIKE ?"
            params.append(f"{date_filter}%")
            
        # Add date range filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            query += " AND time >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND time <= ?"
            params.append(end_date)
        
        # 添加排序和分页
        query += " ORDER BY time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # 执行查询
        cursor.execute(query, params)
        logs = []
        for row in cursor.fetchall():
            log = {
                'log_id': row[0],
                'time': row[1],
                'emotion': row[2],
                'task': row[3],
                'nft': row[4],
                'completed': row[5] == 1
            }
            logs.append(log)
        
        # 获取总数
        count_query = "SELECT COUNT(*) as count FROM logs WHERE email = ?"
        count_params = [email]
        
        if emotion_filter:
            count_query += " AND emotion = ?"
            count_params.append(emotion_filter)
        
        if date_filter:
            count_query += " AND time LIKE ?"
            count_params.append(f"{date_filter}%")
            
        if start_date:
            count_query += " AND time >= ?"
            count_params.append(start_date)
            
        if end_date:
            count_query += " AND time <= ?"
            count_params.append(end_date)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]  # 使用索引访问而不是字典访问，因为没有设置row_factory
        
        logger.info(f"查詢日誌成功: 用戶={email}, 數量={len(logs)}, 總數={total}")
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"查詢日誌失敗: {e}")
        return jsonify({
            'success': False,
            'message': '查詢日誌失敗，請稍後重試'
        }), 500

# API: 获取 AI 统计数据 (ML Phase 2)
@app.route('/api/ai-stats', methods=['GET'])
def get_ai_stats():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取总反馈数
        cursor.execute("SELECT COUNT(*) FROM mood_feedback")
        total_feedback = cursor.fetchone()[0]
        
        # 获取准确率 (如果预测 == 实际)
        cursor.execute("SELECT COUNT(*) FROM mood_feedback WHERE predicted_mood = actual_mood")
        correct_predictions = cursor.fetchone()[0]
        
        accuracy = (correct_predictions / total_feedback * 100) if total_feedback > 0 else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'total_contributions': total_feedback,
                'accuracy': round(accuracy, 1),
                'model_loaded': ML_MODEL is not None,
                'next_milestone': 100 # Example milestone
            }
        })
    except Exception as e:
        logger.error(f"獲取 AI 統計失敗: {e}")
        return jsonify({'success': False, 'message': '獲取失敗'}), 500

# API: 触发模型重訓 (Admin/Internal)
@app.route('/api/admin/retrain', methods=['POST'])
def trigger_retrain():
    try:
        from mood_trainer import train_model
        success = train_model()
        if success:
            load_ml_model() # Reload
            return jsonify({'success': True, 'message': '模型重訓並載入成功'})
        else:
            return jsonify({'success': False, 'message': '重訓失敗或數據不足'})
    except Exception as e:
        logger.error(f"重訓請求失敗: {e}")
        return jsonify({'success': False, 'message': '請求發生錯誤'}), 500

# API: 获取统计数据
@app.route('/api/get-stats', methods=['GET'])
def get_stats():
    try:
        email = request.args.get('email')
        period = request.args.get('period', 'all')  # all, week, month
        
        # 验证输入
        if not email or not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '無效的用戶信息'
            }), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 构建時間過濾條件
        time_filter = ""
        params = [email]
        
        if period == 'week':
            # 过去7天
            time_filter = " AND time >= ?"
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            params.append(week_ago)
        elif period == 'month':
            # 过去30天
            time_filter = " AND time >= ?"
            month_ago = (datetime.now() - timedelta(days=30)).isoformat()
            params.append(month_ago)
        
        # 查询总数和完成数
        query = f"""
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
            FROM logs 
            WHERE email = ? {time_filter}
        """
        cursor.execute(query, params)
        result = cursor.fetchone()
        total = result[0] or 0
        completed = result[1] or 0
        
        # 查询情绪转移数
        transition_query = f"""
            SELECT COUNT(*) as count 
            FROM logs 
            WHERE email = ? AND nft LIKE ? {time_filter}
        """
        cursor.execute(transition_query, params + ['%成功緩和%'])
        transitions = cursor.fetchone()[0]
        
        # 查询情绪分布
        emotion_query = f"""
            SELECT emotion, COUNT(*) as count 
            FROM logs 
            WHERE email = ? {time_filter}
            GROUP BY emotion
        """
        cursor.execute(emotion_query, params)
        
        chart_data = {
            'anxious': 0,
            'sad': 0,
            'neutral': 0,
            'happy': 0,
            'angry': 0
        }
        
        for row in cursor.fetchall():
            if row[0] in chart_data:
                chart_data[row[0]] = row[1]
        
        # 计算完成率
        completion_rate = round((completed/total)*100) if total > 0 else 0
        
        # 获取连续打卡天数
        streak_query = f"""
            SELECT DISTINCT date(time) as log_date 
            FROM logs 
            WHERE email = ? AND completed = 1 
            ORDER BY log_date DESC
        """
        cursor.execute(streak_query, [email])
        dates = [row[0] for row in cursor.fetchall()]
        
        streak = 0
        current_date = datetime.now().date()
        
        for log_date_str in dates:
            log_date = datetime.strptime(log_date_str, '%Y-%m-%d').date()
            if (current_date - log_date).days == streak:
                streak += 1
            else:
                break
        
        logger.info(f"查詢統計數據成功: 用戶={email}, 完成率={completion_rate}%, 轉移次數={transitions}")
        
        return jsonify({
            'success': True,
            'completion_rate': completion_rate,
            'transitions': transitions,
            'chart_data': chart_data,
            'total_logs': total,
            'streak': streak,
            'period': period
        })
        
    except Exception as e:
        logger.error(f"查詢統計數據失敗: {e}")
        return jsonify({
            'success': False,
            'message': '查詢統計數據失敗，請稍後重試'
        }), 500

# 从数据库加载用户数据
def load_users_from_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, email, password, user_name FROM users')
        rows = cursor.fetchall()
        for row in rows:
            if row[0]:  # Only load users with valid user_id
                users_db[row[1]] = {
                    'user_id': row[0],
                    'password': row[2],
                    'user_name': row[3]
                }
        conn.close()
        logger.info(f"从数据库加载用户成功，共{len(users_db)}个用户")
    except Exception as e:
        logger.error(f"從數據庫加載用戶數據失敗: {e}")
        
# 從數據庫加載最近的日誌
def load_recent_logs_from_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # 只加載最近100條日誌到內存
        cursor.execute('SELECT log_id, time, email, emotion, task, nft, completed FROM logs ORDER BY time DESC LIMIT 100')
        for row in cursor.fetchall():
            log_entry = {
                'log_id': row[0],
                'time': row[1],
                'email': row[2],
                'emotion': row[3],
                'task': row[4],
                'nft': row[5],
                'completed': row[6] == 1
            }
            logs_db.append(log_entry)
        conn.close()
        logger.info(f"從數據庫加載日誌成功，共{len(logs_db)}條")
    except Exception as e:
        logger.error(f"加載日誌數據失敗: {e}")

# 從數據庫加載用戶情緒數據
def load_user_emotions_from_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ue.user_id, u.email, ue.last_emotion 
            FROM user_emotions ue 
            JOIN users u ON ue.user_id = u.user_id
        ''')
        for row in cursor.fetchall():
            user_last_emotion[row[1]] = row[2]
        conn.close()
        logger.info(f"從資料庫載入使用者情緒資料成功，共{len(user_last_emotion)}條")
    except Exception as e:
        logger.error(f"從數據庫加載用戶情緒資料失敗: {e}")

# 定期清理过期的內存緩存
def cleanup_memory_cache():
    try:
        # 限制內存中的日誌數量
        global logs_db
        if len(logs_db) > 500:
            # 只保留最近的300條
            logs_db = logs_db[:300]
        
        # 清理長時間未活動的用戶情緒資料
        global user_last_emotion
        # 這裡可以根據需要實現更複雜的清理邏輯
        
        logger.info(f"內存緩存清理完成，當前日誌數: {len(logs_db)}, 用戶情緒資料數: {len(user_last_emotion)}")  
    except Exception as e:
        logger.error(f"清理內存緩存失敗: {e}")

# 應用上下文處理器
@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

# 根路徑 - serve frontend UI
@app.route('/')
def index():
    from flask import send_from_directory
    return send_from_directory(app.static_folder, 'index.html')
  

# 健康检查端点
@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': 'V1.0.4'
        })
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# 數據庫備份端點
@app.route('/api/backup-db', methods=['POST'])
def backup_database():
    try:
        # 簡單的數據庫備份邏輯
        backup_file = f'moodmend_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        import shutil
        shutil.copy2(DB_NAME, backup_file)
        
        logger.info(f"數據庫備份成功: {backup_file}")
        
        return jsonify({
            'success': True,
            'message': '數據庫備份成功',
            'backup_file': backup_file
        })
    except Exception as e:
        logger.error(f"數據庫備份失敗: {e}")
        return jsonify({
            'success': False,
            'message': '數據庫備份失敗'
        }), 500

# 定时任务初始化
import atexit
from threading import Timer

def schedule_cleanup():
    # 每小时执行一次内存清理
    cleanup_memory_cache()
    t = Timer(3600, schedule_cleanup)
    t.daemon = True
    t.start()

# API: Health Check (simple, for Railway monitoring)
@app.route('/health', methods=['GET'])
def health_check_simple():
    """Simple health check endpoint for Railway/cloud monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.2.1'
    }), 200


if __name__ == '__main__':
    try:
        # 初始化数据库
        init_db()
        
        # 加载数据
        load_users_from_db()
        load_recent_logs_from_db()
        load_user_emotions_from_db()
        
        # 載入 ML 模型
        load_ml_model()
        
        # 启动定时任务
        schedule_cleanup()
        
        # 注册程序退出时的清理函数
        atexit.register(cleanup_memory_cache)
        
        logger.info("MoodMend後端服務啟動")
        
        # 在生產環境中，應該使用適當的WSGI服務器
        # 這裡為了演示，使用Flask的開發服務器
        port = int(os.getenv('PORT', 3000))
        app.run(debug=True, port=port, host='0.0.0.0')
        
    except Exception as e:
        logger.critical(f"服務啟動失敗: {e}")
        raise e
else:
    # For production (Gunicorn), initialize on import
    try:
        init_db()
        load_users_from_db()
        load_recent_logs_from_db()
        load_user_emotions_from_db()
        load_ml_model()
        schedule_cleanup()
        atexit.register(cleanup_memory_cache)
        logger.info("MoodMend後端服務啟動 (via Gunicorn)")
    except Exception as e:
        logger.critical(f"服務啟動失敗: {e}")
        raise e