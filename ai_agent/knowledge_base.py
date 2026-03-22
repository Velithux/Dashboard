#!/usr/bin/env python3
import json
import os
import time
import statistics
import glob
from datetime import datetime
from loguru import logger
from data_collector import contract, fetch_last_ai_decisions, read_latest_prediction
from evaluator import load_evaluations
from config import CONTRACT_ADDRESS

KNOWLEDGE_FILE = 'data/knowledge_base.json'

CACHE_PATH = 'data/last_market_data.json'

def load_cached_market_data():
    """Load cached market data, fallback to live if stale/missing."""
    if os.path.exists(CACHE_PATH) and (time.time() - os.path.getmtime(CACHE_PATH)) < 3600:
        with open(CACHE_PATH, 'r') as f:
            return json.load(f)
    logger.warning("No recent cache, falling back to live collect")
    from data_collector import collect_market_data
    return collect_market_data()

# Static project facts
STATIC_FACTS = {
    "token_name": "Velith",
    "symbol": "VLTH",
    "total_supply": "1000000000",
    "contract_address": "0x25C9440C28c4a357A991A207CFf671Cf924671B1",
    "distribution": {
        "public_sale": "40%",
        "treasury": "25%",
        "team": "15%",
        "ecosystem": "12%",
        "liquidity": "8%"
    },
    "fee_rate": "5%",
    "burn_mechanism": "70% of accumulated protocol fees auto-burned when threshold reached, plus AI manual burns",
    "gnosis_safe": "0x00388Ea274fce6B2a6773852E1C1693739d675b0",
    "dashboard_url": "https://picsoucoin.vercel.app",
    "whitepaper_url": "https://github.com/Velithux/Dashboard/blob/main/WhitePaper/VELITH_WHITEPAPER.md"
}

def get_last_report_info():
    """Get latest weekly report date and summary."""
    reports_dir = 'reports'
    if not os.path.exists(reports_dir):
        return {"last_report_date": None, "weekly_burned": 0, "decisions_week": 0, "commentary_excerpt": "No reports yet"}
    
    pdf_files = glob.glob(os.path.join(reports_dir, 'VELA_Weekly_Report_*.pdf'))
    if not pdf_files:
        return {"last_report_date": None, "weekly_burned": 0, "decisions_week": 0, "commentary_excerpt": "No reports generated"}
    
    latest_pdf = max(pdf_files, key=os.path.getctime)
    date_str = os.path.basename(latest_pdf).replace('VELA_Weekly_Report_', '').replace('.pdf', '')
    try:
        last_date = datetime.strptime(date_str, '%Y-%m-%d').isoformat()
    except:
        last_date = date_str
    
    # Compute weekly summary from data (approx last 7 days)
    now = int(time.time())
    week_ago = now - 7*24*3600
    decisions = fetch_last_ai_decisions(50)
    week_decisions = [d for d in decisions if d['timestamp'] >= week_ago]
    weekly_burned = sum(d['value'] for d in week_decisions if d['action'] == 'BURN')
    decisions_week = len(week_decisions)
    excerpt = "Weekly summary computed from recent decisions."
    
    return {
        "last_report_date": last_date,
        "total_burned_week": f"{weekly_burned:.0f}",
        "decisions_made_week": decisions_week,
        "commentary_excerpt": excerpt
    }

def build_knowledge_base():
    """Build complete knowledge base JSON."""
    market_data = load_cached_market_data()
    decisions = fetch_last_ai_decisions(5)
    evals = load_evaluations()
    
    # Live on-chain
    live_data = {
        "current_price_usd": f"{(market_data.get('picsou_price_usd', 0.0) or 0.0):.6f}",
        "circulating_supply": f"{(market_data.get('circulating_supply', 0.0) or 0.0):.0f}",
        "total_burned": f"{(market_data.get('total_burned', 0.0) or 0.0):.0f}",
        "treasury_fee_balance": f"{(market_data.get('treasury_fee_balance', 0.0) or 0.0):.0f}",
        "ai_decision_count": contract.functions.getAIDecisionCount().call(),
        "last_5_decisions": [
            {
                "action": d['action'],
                "reason": d['reason'][:100],
                "value": f"{(d.get('value', 0.0) or 0.0):.0f}",
                "timestamp": datetime.fromtimestamp(d['timestamp']).isoformat()
            } for d in decisions
        ]
    }
    
    # VELA performance
    scores = [e.get('score', 0) for e in evals if 'score' in e]
    avg_score = statistics.mean(scores) if scores else 0.0
    total_decisions = contract.functions.getAIDecisionCount().call()
    burn_count = sum(1 for d in fetch_last_ai_decisions(total_decisions) if d['action'] == 'BURN')
    none_count = total_decisions - burn_count - sum(1 for d in fetch_last_ai_decisions(total_decisions) if d['action'] == 'PRICE')
    
    pred = read_latest_prediction()
    last_pred = {
        "prediction": pred.get('prediction', 'N/A') if pred else 'N/A',
        "confidence": f"{(pred.get('confidence', 0.0) or 0.0):.2f}" if pred else '0.00'
    } if pred else {"prediction": "N/A", "confidence": "0.00"}
    
    operating_mode = 'CONSERVATIVE' if avg_score < 0 else 'NEUTRAL' if avg_score < 0.3 else 'AGGRESSIVE'
    
    performance = {
        "total_decisions_made": total_decisions,
        "burn_count": burn_count,
        "none_count": none_count,
        "avg_evaluation_score": f"{(avg_score or 0.0):.3f}",
        "current_operating_mode": operating_mode,
        "last_prediction": last_pred
    }
    
    # Weekly
    weekly = get_last_report_info()
    
    kb = {
        "last_updated": datetime.now().isoformat(),
        "project_facts": STATIC_FACTS,
        "live_onchain_data": live_data,
        "vela_performance": performance,
        "weekly_report_summary": weekly
    }
    
    os.makedirs('data', exist_ok=True)
    with open(KNOWLEDGE_FILE, 'w') as f:
        json.dump(kb, f, indent=2)
    
    logger.info(f"Knowledge base built: {KNOWLEDGE_FILE}")
    return kb

def update_knowledge_base():
    """Update live/dynamic sections every hour."""
    if not os.path.exists(KNOWLEDGE_FILE):
        logger.warning("No KB file, building full first")
        return build_knowledge_base()
    
    with open(KNOWLEDGE_FILE, 'r') as f:
        kb = json.load(f)
    
    # Update dynamic parts only
    market_data = load_cached_market_data()
    decisions = fetch_last_ai_decisions(5)
    evals = load_evaluations()
    
    # Live
    kb['live_onchain_data'] = {
        "current_price_usd": f"{market_data.get('picsou_price_usd', 0):.6f}",
        "circulating_supply": f"{market_data.get('circulating_supply', 0):.0f}",
        "total_burned": f"{market_data.get('total_burned', 0):.0f}",
        "treasury_fee_balance": f"{market_data.get('treasury_fee_balance', 0):.0f}",
        "ai_decision_count": contract.functions.getAIDecisionCount().call(),
        "last_5_decisions": [
            {
                "action": d['action'],
                "reason": d['reason'][:100],
                "value": f"{d['value']:.0f}",
                "timestamp": datetime.fromtimestamp(d['timestamp']).isoformat()
            } for d in decisions
        ]
    }
    
    # Performance
    scores = [e.get('score', 0) for e in evals if 'score' in e]
    avg_score = statistics.mean(scores) if scores else 0.0
    total_decisions = contract.functions.getAIDecisionCount().call()
    # Recompute counts (approx from recent + total)
    all_decisions = fetch_last_ai_decisions(min(100, total_decisions))  # Approx
    burn_count = sum(1 for d in all_decisions if d['action'] == 'BURN')
    none_count = sum(1 for d in all_decisions if d['action'] == 'NONE')
    
    pred = read_latest_prediction()
    last_pred = {
        "prediction": pred.get('prediction', 'N/A') if pred else 'N/A',
        "confidence": f"{pred.get('confidence', 0):.2f}" if pred else '0.00'
    } if pred else {"prediction": "N/A", "confidence": "0.00"}
    
    operating_mode = 'CONSERVATIVE' if avg_score < 0 else 'NEUTRAL' if avg_score < 0.3 else 'AGGRESSIVE'
    
    kb['vela_performance'] = {
        "total_decisions_made": total_decisions,
        "burn_count": burn_count,
        "none_count": none_count,
        "avg_evaluation_score": f"{(avg_score or 0.0):.3f}",
        "current_operating_mode": operating_mode,
        "last_prediction": last_pred
    }
    
    # Weekly
    kb['weekly_report_summary'] = get_last_report_info()
    
    kb['last_updated'] = datetime.now().isoformat()
    
    with open(KNOWLEDGE_FILE, 'w') as f:
        json.dump(kb, f, indent=2)
    
    logger.info("Knowledge base updated")

if __name__ == '__main__':
    build_knowledge_base()
