import sqlite3
import uuid
import datetime
import random

# 创建数据库连接
db_path = 'moodmend.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 清理旧数据（如果存在schema不匹配的表）
print("清理旧数据...")
cursor.execute("DROP TABLE IF EXISTS user_emotions")
cursor.execute("DROP TABLE IF EXISTS logs")
cursor.execute("DROP TABLE IF EXISTS users")

# 创建users表 - 使用TEXT类型的UUID作为主键（匹配后端）
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

# 创建logs表 - user_id改为TEXT类型
cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    log_id TEXT PRIMARY KEY,
    user_id TEXT,
    email TEXT NOT NULL,
    time TEXT NOT NULL,
    emotion TEXT NOT NULL,
    task TEXT NOT NULL,
    nft TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
''')

# 创建user_emotions表 - 匹配后端schema (user_id, last_emotion, last_update)
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_emotions (
    user_id TEXT PRIMARY KEY,
    last_emotion TEXT,
    last_update TEXT,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
''')

# 生成测试用户的UUID
test_user_id = str(uuid.uuid4())

# 插入测试用户 - 使用UUID
cursor.execute('''
INSERT OR REPLACE INTO users (user_id, email, password, user_name, created_at) 
VALUES (?, ?, ?, ?, ?)
''', (test_user_id, 'test@test.com', '123', '测试用户', datetime.datetime.now().isoformat()))

print(f"创建测试用户: {test_user_id}")

# 准备情绪类型和对应的任务和NFT徽章
emotions = {
    'happy': {
        'tasks': ['計劃一個小慶祝活動。', '分享你的喜悅給朋友。', '記錄今天的開心時刻。', '給自己一個小獎勵。', '做一件讓別人開心的事。'],
        'nfts': ['⭐ 星光徽章 - 喜悅守護', '🌈 彩虹徽章 - 快樂使者', '☀️ 陽光徽章 - 正能量傳播者']
    },
    'sad': {
        'tasks': ['與信任的朋友談談你的感受。', '出去走走，呼吸新鮮空氣。', '做一件讓自己放鬆的事。', '記下你的感受，釋放情緒。', '傾聽喜歡的音樂。'],
        'nfts': ['🌧️ 雨滴徽章 - 情緒覺察者', '💧 水滴徽章 - 內心探索者', '🌦️ 風雨徽章 - 勇敢面對']
    },
    'angry': {
        'tasks': ['深呼吸，冷靜一下。', '做一些放鬆的伸展運動。', '寫下讓你生氣的原因。', '暫時遠離刺激源。', '練習冥想，平靜心靈。'],
        'nfts': ['⚡ 雷霆徽章 - 情緒管理師', '🔥 火焰徽章 - 能量轉化者', '🌪️ 旋風徽章 - 冷靜思考者']
    },
    'calm': {
        'tasks': ['保持當下的平靜狀態。', '練習正念冥想。', '欣賞周圍的美好事物。', '記錄平靜帶給你的感受。', '與自然連接，感受寧靜。'],
        'nfts': ['🌊 海洋徽章 - 內心平靜', '🍃 葉子徽章 - 隨遇而安', '🌙 月光徽章 - 寧靜守護者']
    }
}

# 生成29条测试日志
print("生成测试日志...")
for i in range(29):
    # 随机选择情绪
    emotion_type = random.choice(list(emotions.keys()))
    emotion_data = emotions[emotion_type]
    
    # 随机选择任务和NFT
    task = random.choice(emotion_data['tasks'])
    nft = random.choice(emotion_data['nfts'])
    
    # 生成随机完成状态
    completed = random.randint(0, 1)
    
    # 生成过去30天内的随机时间
    days_ago = random.randint(1, 30)
    log_time = datetime.datetime.now() - datetime.timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
    
    # 生成唯一的log_id
    log_id = str(uuid.uuid4())
    
    # 插入日志 - 包含user_id
    cursor.execute('''
    INSERT INTO logs (log_id, user_id, email, time, emotion, task, nft, completed)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (log_id, test_user_id, 'test@test.com', log_time.isoformat(), emotion_type, task, nft, completed))

# 插入最后一次情绪记录
last_emotion = random.choice(list(emotions.keys()))
cursor.execute('''
INSERT OR REPLACE INTO user_emotions (user_id, last_emotion, last_update)
VALUES (?, ?, ?)
''', (test_user_id, last_emotion, datetime.datetime.now().isoformat()))

# 提交事务并关闭连接
conn.commit()
conn.close()

print("测试数据初始化完成！")
print("测试账号：")
print("邮箱: test@test.com")
print("密码: 123")
print(f"用户ID: {test_user_id}")