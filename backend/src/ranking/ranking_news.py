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

    analysis_stock = moex_stock_analyzer.analyze_stocks()
    if not analysis_stock:
        return False, None 
    
    count_up_change = len(analysis_stock[analysis_stock["change"] > change_stock])
    count_down_change = len(analysis_stock[analysis_stock["change"] < -change_stock])
    count_up_change_2 = len(analysis_stock[analysis_stock["change"] > 2 * change_stock])
    count_down_change_2 = len(analysis_stock[analysis_stock["change"] < -2 * change_stock])

    if count_up_change_2 > count_down_change_2 or (count_up_change > count_down_change and tonality["label"] == "POSITIVE"):
        return True, Post(text=post.text,
                          tonality=1, channel_id=post.channel_id, channel_title=post.channel_title, timestamp=post.timestamp)
    elif count_up_change_2 < count_down_change_2 or (count_up_change < count_down_change and tonality["label"] == "NEGATIVE"):
        return True, Post(text=post.text,
                          tonality=-1, channel_id=post.channel_id, channel_title=post.channel_title, timestamp=post.timestamp)

    if not stack_embs:
        start_stack_embs = datetime.now()
        
    stack_embs.append(emb)

    return False, None