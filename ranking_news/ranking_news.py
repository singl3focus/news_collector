import analysis_text
from analysis_stock_market import MoexStockAnalyzer

moex_stock_analyzer = MoexStockAnalyzer()

stack_embs = []

def is_good_news(news: str, change_stock=0.01):
    emb, tonality = analysis_text.get_info_text(news)

    if analysis_text.check_equality_emb(emb, stack_embs):
        return False

    analysis_stock = moex_stock_analyzer.analyze_stocks()
    if analysis_stock == []:
        return False
    count_up_change = len(analysis_stock[analysis_stock["change"] > change_stock])
    count_down_change = len(analysis_stock[analysis_stock["change"] < -change_stock])
    count_up_change_2 = len(analysis_stock[analysis_stock["change"] > 2 * change_stock])
    count_down_change_2 = len(analysis_stock[analysis_stock["change"] < -2 * change_stock])
    if count_up_change_2 > count_down_change_2 or (count_up_change > count_down_change and tonality["label"] == "POSITIVE"):
        return True
    elif count_up_change_2 < count_down_change_2 or (count_up_change < count_down_change and tonality["label"] == "NEGATIVE"):
        return True

    stack_embs.append(emb)


if __name__ == "__main__":
    print(is_good_news('Маск уволен'))