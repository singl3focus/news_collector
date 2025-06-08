from . import analysis_text
from .analysis_stock_market import MoexStockAnalyzer
from datetime import datetime, timedelta
from dataclasses import dataclass

moex_stock_analyzer = MoexStockAnalyzer()

start_stack_embs = datetime.now()
stack_embs = []

@dataclass
class Post:
    text: str
    tonality: int # 1 - good, -1 - bad
    trend: int # 1 - up, -1 - down
    volatility: int # 1 - high, 0 - low
    channel_id: str
    channel_title: str
    timestamp: int = 0

def is_good_news(post, change_stock=0.01) -> {bool, Post | None}:
    global start_stack_embs, stack_embs

    if (datetime.now() - start_stack_embs) >= timedelta(days=1):
        stack_embs.clear()
        start_stack_embs = datetime.now()  # Обновляем время сброса
    emb, tonality = analysis_text.get_info_text(post.text)

    if analysis_text.check_equality_emb(emb, stack_embs):
        return False, None 

    analysis_stock = moex_stock_analyzer.analyze_stocks(change_stock)
    if not analysis_stock:
        return False, None 
    
    # if max(analysis_stock['change']) - min(analysis_stock['change']) < change_stock or tonality["label"] == "NEUTRAL":
    #     return False, None

    if tonality["label"] == "POSITIVE":
        tonality = 1
    elif tonality["label"] == "NEGATIVE":
        tonality = -1

    trend = analysis_stock['trend'].value_counts().idxmax()
    volatility = analysis_stock['volatility'].value_counts().idxmax()
        

    if not stack_embs:
        start_stack_embs = datetime.now()
        
    stack_embs.append(emb)

    return True, Post(text=post.text,
                          tonality=tonality, trend=trend, volatility=volatility, channel_id=post.channel_id, channel_title=post.channel_title, timestamp=post.timestamp)