import logging
from flask import Flask, jsonify

from common import require_api_keys, get_api, build_trading_pref, extract_payment_ids

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
    return jsonify({
        "status": "success",
        "message": "Welcome to ByBit Update Ads API",
        "service": "update-ads",
        "version": "1.0",
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "update-ads", "version": "1.0"}), 200


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090, debug=False)
