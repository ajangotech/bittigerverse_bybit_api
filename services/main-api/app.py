import hashlib
import hmac
import logging
import time

from flask import Flask, jsonify

from common import require_api_keys, get_api

import requests
try:
    from flask_cors import CORS
except ImportError:
    CORS = None

app = Flask(__name__)
application = app

if CORS:
    CORS(app, resources={r"/*": {"origins": "*"}})

logging.getLogger("bybit_p2p._p2p_manager").setLevel(logging.CRITICAL)

@app.route("/", methods=["GET"])
def home():
    return jsonify(
        {"status": "success", "message": "Welcome to ByBit Main API", "service": "main-api", "version": "1.0"}
    )

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "main-api", "version": "1.0"}), 200

@app.route("/api/update-ad", methods=["POST"])
@require_api_keys
def update_ad(data):
    try:
        api = get_api(data)

        payment_ids = extract_payment_ids(data)
        trading_pref = build_trading_pref(data.get("tradingPreferenceSet"))

        result = api.update_ad(
            id=data.get("id"),
            priceType=int(data.get("priceType", 0)),
            premium=float(data.get("premium", 0)),
            price=float(data.get("price")),
            minAmount=float(data.get("minAmount")),
            maxAmount=float(data.get("maxAmount")),
            remark=data.get("remark", ""),
            tradingPreferenceSet=trading_pref,
            paymentIds=payment_ids,
            actionType="MODIFY",
            quantity=str(data.get("quantity") or data.get("lastQuantity", "1")),
            paymentPeriod=int(data.get("paymentPeriod", 15)),
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 📈 GET MAXIMUM AD PRICE
# =========================
# Strategy:
#  1. Serve cached bounds if fresh (< _PRICE_LIMIT_TTL seconds old).
#  2. Otherwise acquire a per-ad lock so overlapping concurrent requests
#     share a SINGLE Bybit probe (the rest wait, then read the cache).
#  3. One Bybit API call per TTL window — no flood, no 75-line burst.

@app.route("/api/payment-types", methods=["POST"])
@require_api_keys
def payment_types(data):
    try:
        api = get_api(data)
        result = api.get_user_payment_types()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 💰 BALANCE
# =========================

@app.route("/api/balance", methods=["POST"])
@require_api_keys
def balance(data):
    try:
        api = get_api(data)
        result = api.get_current_balance(
            accountType=data.get("accountType", "FUND"),
            coin=data.get("coin", "USDC"),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 👤 ACCOUNT INFO
# =========================

@app.route("/api/account", methods=["POST"])
@require_api_keys
def account(data):
    try:
        api = get_api(data)
        result = api.get_account_information()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 📢 ADS LIST
# =========================

@app.route("/api/ads", methods=["POST"])
@require_api_keys
def ads(data):
    try:
        api = get_api(data)
        sort_by = data.get("sortBy", "completion_rate")
        allowed_sorting = {
            "price": "price",
            "orders": "orders",
            "completion_rate": "completion_rate",
        }

        if sort_by not in allowed_sorting:
            return jsonify({
                "error": (
                    "Invalid sortBy value. Allowed values are: price, orders,"
                    " completion_rate"
                ),
                "allowed": list(allowed_sorting.keys()),
            }), 400

        result = api.get_ads_list(sort_by=allowed_sorting[sort_by])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 📄 AD DETAILS
# =========================

@app.route("/api/ad-details", methods=["POST"])
@require_api_keys
def ad_details(data):
    try:
        api = get_api(data)
        result = api.get_ad_details(itemId=data.get("itemId"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# ❌ REMOVE AD
# =========================

@app.route("/api/remove-ad", methods=["POST"])
@require_api_keys
def remove_ad(data):
    try:
        api = get_api(data)
        result = api.remove_ad(itemId=data.get("itemId"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 📦 ORDERS
# =========================

@app.route("/api/orders", methods=["POST"])
@require_api_keys
def orders(data):
    try:
        api = get_api(data)
        result = api.get_orders(
            page=data.get("page", 1), size=data.get("size", 10)
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 💰 REFERENCE PRICE
# =========================

@app.route("/api/reference-price", methods=["POST"])
@require_api_keys
def reference_price(data):
    try:
        api_key = data.get("api_key")
        api_secret = data.get("api_secret")
        symbol = data.get("symbol", "BTC-USD")

        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        query_string = f"symbol={symbol}"

        signature_payload = timestamp + api_key + recv_window + query_string
        signature = hmac.new(
            api_secret.encode("utf-8"),
            signature_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        url = f"https://api.bybit.com/v5/fiat/reference-price?{query_string}"
        headers = {
            "X-BAPI-SIGN": signature,
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers, timeout=20)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": False, "error": str(e)}), 500


# =========================
# ⏳ PENDING ORDERS
# =========================

@app.route("/api/pending-orders", methods=["POST"])
@require_api_keys
def pending_orders(data):
    try:
        api = get_api(data)
        result = api.get_pending_orders(
            page=data.get("page", 1), size=data.get("size", 10)
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 📊 MARKET ANALYSIS
# =========================

@app.route("/api/analyze-market", methods=["POST"])
@require_api_keys
def analyze_market(data):
    try:
        api = get_api(data)

        token_id = data.get("tokenId", "BTC")
        currency_id = data.get("currencyId", "USD")
        side = str(data.get("side", "0"))
        min_amount = float(data.get("minAmount", 0))
        margin_pct = float(data.get("marginPct", 4))
        sort_by = str(data.get("sortBy", "price")).lower()

        ads = api.get_online_ads(
            tokenId=token_id,
            currencyId=currency_id,
            side=side,
            size="30",
            vaMaker=True,
            authMaker=False,
            bulkMaker=False,
            canTrade=False,
            verificationFilter=0,
            sortType="OVERALL_RANKING",
            sortStrategyCode="DEFAULT_BUY",
            itemRegion=1,
            tradeWith=False,
        )

        items = []
        if isinstance(ads, dict):
            items = ads.get("result", {}).get("items", [])

        competitors = []
        for ad in items:
            try:
                price = float(ad.get("price", 0))
                if price <= 0:
                    continue

                ad_min = float(ad.get("minAmount", 0))
                ad_max = float(ad.get("maxAmount", 0))

                if min_amount > 0 and ad_max < min_amount:
                    continue

                raw_orders = ad.get("recentOrderNum", 0)
                try:
                    recent_orders = int(raw_orders) if raw_orders is not None else 0
                except (ValueError, TypeError):
                    recent_orders = 0

                raw_rate = ad.get("recentExecuteRate", 0)
                try:
                    recent_rate = (
                        float(str(raw_rate).replace("%", "").strip())
                        if raw_rate is not None
                        else 0.0
                    )
                except (ValueError, TypeError):
                    recent_rate = 0.0

                competitors.append({
                    "id": ad.get("id"),
                    "nickName": ad.get("nickName"),
                    "price": price,
                    "minAmount": ad_min,
                    "maxAmount": ad_max,
                    "quantity": ad.get("quantity"),
                    "recentOrderNum": recent_orders,
                    "recentExecuteRate": recent_rate,
                    "paymentPeriod": ad.get("paymentPeriod"),
                })
            except Exception:
                continue

        if not competitors:
            return jsonify(
                {"status": False, "error": "No valid competitor ads found"}
            ), 404

        if side == "0":
            top_competitor_price = max(c["price"] for c in competitors)
            recommended_price = top_competitor_price * (1 + (margin_pct / 100))
        else:
            top_competitor_price = min(c["price"] for c in competitors)
            recommended_price = top_competitor_price * (1 - (margin_pct / 100))

        if sort_by == "orders":
            competitors = sorted(
                competitors, key=lambda x: x["recentOrderNum"], reverse=True
            )
        elif sort_by == "completion_rate":
            competitors = sorted(
                competitors, key=lambda x: x["recentExecuteRate"], reverse=True
            )
        else:
            competitors = sorted(
                competitors, key=lambda x: x["price"], reverse=(side == "0")
            )

        top_10 = competitors[:30]

        return jsonify({
            "status": True,
            "tokenId": token_id,
            "currencyId": currency_id,
            "side": side,
            "sort_by": sort_by,
            "ads_found": len(competitors),
            "top_competitor_price": round(top_competitor_price, 2),
            "margin_percent": margin_pct,
            "recommended_price": round(recommended_price, 2),
            "top_10_competitors": top_10,
        })

    except Exception as e:
        return jsonify({"status": False, "error": str(e)}), 500


# =========================
# 🌐 ONLINE ADS
# =========================

@app.route("/api/online-ads", methods=["POST"])
@require_api_keys
def online_ads(data):
    try:
        api = get_api(data)
        result = api.get_online_ads(
            tokenId=data.get("tokenId", "BTC"),
            currencyId=data.get("currencyId", "USD"),
            side=data.get("side", "0"),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 💳 MARK AS PAID
# =========================

@app.route("/api/mark-as-paid", methods=["POST"])
@require_api_keys
def mark_as_paid(data):
    try:
        api = get_api(data)
        result = api.mark_as_paid(
            orderId=data.get("orderId"),
            paymentType=str(data.get("paymentType")),
            paymentId=str(data.get("paymentId")),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090, debug=False)
