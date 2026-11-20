import logging
import re
import threading
import time

from flask import Flask, jsonify

from common import require_api_keys, get_api, build_trading_pref, extract_payment_ids

app = Flask(__name__)
application = app

# CORS is intentionally enabled here because this service can be called directly
# inside the private Docker network or through the reverse proxy.
try:
    from flask_cors import CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
except ImportError:
    pass

logging.getLogger("bybit_p2p._p2p_manager").setLevel(logging.CRITICAL)

_PRICE_LIMIT_TTL = 10
_price_limit_cache = {}
_price_limit_lock = threading.Lock()
_price_limit_stats = {"bybit_calls": 0, "cache_hits": 0}

def _cached_price_limit(ad_id):
    entry = _price_limit_cache.get(ad_id)
    if entry and (time.time() - entry["ts"]) < _PRICE_LIMIT_TTL:
        return entry["payload"]
    return None

def _store_price_limit(ad_id, payload):
    _price_limit_cache[ad_id] = {"ts": time.time(), "payload": payload}

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "success",
        "message": "BitTiger Price Limit Service",
        "service": "price-limit",
        "version": "1.0",
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "price-limit", "version": "1.0"}), 200

@app.route("/api/ad-price-limit", methods=["POST"])
@require_api_keys
def ad_price_limit(data):
    ad_id = data.get("id")
    if not ad_id:
        return jsonify({"status": False, "error": "Ad id is required"}), 400

    requested_price = str(data.get("price", "0"))

    cached = _cached_price_limit(ad_id)
    if cached is not None:
        _price_limit_stats["cache_hits"] += 1
        app.logger.info(
            f"[ad-price-limit] CACHE HIT for ad {ad_id} "
            f"(bybit_calls={_price_limit_stats['bybit_calls']}, "
            f"cache_hits={_price_limit_stats['cache_hits']})"
        )
        return jsonify(cached)

    with _price_limit_lock:
        cached = _cached_price_limit(ad_id)
        if cached is not None:
            _price_limit_stats["cache_hits"] += 1
            return jsonify(cached)

        _price_limit_stats["bybit_calls"] += 1
        app.logger.info(
            f"[ad-price-limit] BYBIT CALL #{_price_limit_stats['bybit_calls']} "
            f"for ad {ad_id}"
        )

        api = get_api(data)
        payment_ids = extract_payment_ids(data)
        trading_pref = build_trading_pref(data.get("tradingPreferenceSet"))

        try:
            api.update_ad(
                id=ad_id,
                priceType=int(data.get("priceType", 0)),
                premium=float(data.get("premium", 0)),
                price=float(data.get("price")),
                minAmount=float(data.get("minAmount")),
                maxAmount=float(data.get("maxAmount")),
                remark=data.get("remark", ""),
                tradingPreferenceSet=trading_pref,
                paymentIds=payment_ids,
                actionType="MODIFY",
                quantity=str(data.get("quantity") or data.get("lastQuantity") or "1"),
                paymentPeriod=int(data.get("paymentPeriod", 15)),
            )

            payload = {
                "status": True,
                "price_limit": False,
                "price": requested_price,
            }
            _store_price_limit(ad_id, payload)
            return jsonify(payload)

        except Exception as e:
            error_message = str(e)
            pattern = r"lower than\s+([\d.]+)\s+or higher than\s+([\d.]+)"
            match = re.search(pattern, error_message)

            if match:
                minimum_price = match.group(1).rstrip(".")
                maximum_price = match.group(2).rstrip(".")
                req_val = float(requested_price)

                payload = {
                    "status": True,
                    "price_limit": True,
                    "price": maximum_price,
                    "minimum_price": minimum_price,
                    "maximum_price": maximum_price,
                    "requested_price": requested_price,
                    "price_exceeded": req_val > float(maximum_price),
                    "price_below_minimum": req_val < float(minimum_price),
                }
                _store_price_limit(ad_id, payload)
                return jsonify(payload)

            return jsonify({"status": False, "error": error_message}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090, debug=False)
