import os
from functools import wraps

from bybit_p2p import P2P
from dotenv import load_dotenv
from flask import jsonify, request

load_dotenv()

def require_api_keys(f):
    @wraps(f)
    def wrapper():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400
        if not data.get("api_key") or not data.get("api_secret"):
            return jsonify({"error": "api_key and api_secret are required"}), 400
        return f(data)
    return wrapper

def get_api(data=None):
    data = data or {}
    return P2P(
        testnet=False,
        api_key=data.get("api_key", os.getenv("BYBIT_API_KEY")),
        api_secret=data.get("api_secret", os.getenv("BYBIT_API_SECRET")),
    )

# Trading-preference helpers live in the dedicated update-ads service.

def build_trading_pref(tp):
    tp = tp or {}
    return {
        "hasUnPostAd": int(tp.get("hasUnPostAd", 0)),
        "isKyc": int(tp.get("isKyc", 0)),
        "isEmail": int(tp.get("isEmail", 0)),
        "isMobile": int(tp.get("isMobile", 0)),
        "hasRegisterTime": int(tp.get("hasRegisterTime", 0)),
        "registerTimeThreshold": int(tp.get("registerTimeThreshold", 0)),
        "orderFinishNumberDay30": int(tp.get("orderFinishNumberDay30", 0)),
        "hasOrderFinishNumberDay30": int(tp.get("hasOrderFinishNumberDay30", 0)),
        "hasCompleteRateDay30": int(tp.get("hasCompleteRateDay30", 0)),
        "hasNationalLimit": int(tp.get("hasNationalLimit", 0)),
        "completeRateDay30": tp.get("completeRateDay30", ""),
        "nationalLimit": tp.get("nationalLimit", ""),
    }

def extract_payment_ids(data):
    return [
        p.get("id")
        for p in data.get("paymentTerms", [])
        if isinstance(p, dict) and p.get("id")
    ]
