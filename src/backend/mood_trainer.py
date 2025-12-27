import sqlite3
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import joblib
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mood_trainer')

DB_NAME = 'moodmend.db'
MODEL_PATH = 'models/mood_model.joblib'

def train_model():
    """Extract feedback data and train a new ML model."""
    try:
        # 1. Connect and Extract Data
        # Use absolute path if needed, but here we assume it's run from src/backend
        db_path = os.path.join(os.path.dirname(__file__), 'moodmend.db')
        if not os.path.exists(db_path):
            # Fallback for dev environment
            db_path = 'moodmend.db'
            
        conn = sqlite3.connect(db_path)
        query = "SELECT user_input, actual_mood FROM mood_feedback"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if len(df) < 5:
            logger.warning(f"Not enough data to train (Minimum 5 samples, found {len(df)}). Using a dummy model.")
            # For cold start, we could still build the pipeline structure
            # but maybe just return for now or create a very basic one
            return False

        logger.info(f"Training on {len(df)} samples...")

        # 2. Build Pipeline
        # TfidfVectorizer handles text tokenization and weight calculation
        # RandomForest is robust for small-to-medium datasets
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=1000, ngram_range=(1, 2))),
            ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
        ])

        # 3. Fit Model
        pipeline.fit(df['user_input'], df['actual_mood'])

        # 4. Save Model
        models_dir = os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(models_dir, exist_ok=True)
        save_path = os.path.join(models_dir, 'mood_model.joblib')
        
        joblib.dump(pipeline, save_path)
        logger.info(f"Model successfully saved to {save_path}")
        return True

    except Exception as e:
        logger.error(f"Training failed: {e}")
        return False

if __name__ == "__main__":
    train_model()
