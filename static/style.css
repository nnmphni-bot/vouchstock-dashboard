import os
import json
import time
import asyncio
from datetime import datetime

import aiohttp
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

USDT_ADDRESS = "0x074b03699b5b354e293459347ba1803f82b1e5ef"
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
LTC_ADDRESS = "LcyginaTtsPeSp4xFaK5R47mbMaFbbZiat"

USED_FILE = "used_txids.json"
OLD_TX_BUFFER_SECONDS = 60


def load_used():
    if os.path.exists(USED_FILE):
        try:
            with open(USED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def save_used(data):
    with open(USED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(data), f, indent=2)


USED_TXIDS = load_used()


def clean_amount(amount):
    try:
        return float(str(amount).replace("$", "").replace("THB", "").strip())
    except:
        return None


async def bsc_rpc(method, params):
    url = "https://bsc-dataseed.binance.org/"
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as response:
            return await response.json(content_type=None)


async def get_ltc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            data = await response.json(content_type=None)

    return float(data["litecoin"]["usd"])


async def check_usdt(txid, expected_amount, started_at):
    txid = txid.strip()

    if not txid.startswith("0x"):
        txid = "0x" + txid

    if len(txid.replace("0x", "")) != 64:
        return False, "Invalid BSC TxID format."

    expected = clean_amount(expected_amount)

    if expected is None:
        return False, "Invalid amount."

    receipt_data = await bsc_rpc("eth_getTransactionReceipt", [txid])
    result = receipt_data.get("result")

    if result is None:
        return False, "Transaction not found on BSC."

    if result.get("status") != "0x1":
        return False, "BSC transaction failed."

    block_hex = result.get("blockNumber")
    block_data = await bsc_rpc("eth_getBlockByNumber", [block_hex, False])
    block = block_data.get("result")

    if not block or not block.get("timestamp"):
        return False, "Cannot read transaction time."

    tx_time = int(block["timestamp"], 16)

    if tx_time < started_at - OLD_TX_BUFFER_SECONDS:
        return False, "Old transaction. Please send a new payment after opening this page."

    received = 0.0

    for log in result.get("logs", []):
        if log.get("address", "").lower() != USDT_CONTRACT.lower():
            continue

        topics = log.get("topics", [])

        if len(topics) < 3:
            continue

        to_wallet = "0x" + topics[2][-40:]

        if to_wallet.lower() != USDT_ADDRESS.lower():
            continue

        raw = int(log.get("data", "0x0"), 16)
        received += raw / (10 ** 18)

    if received <= 0:
        return False, "USDT not sent to shop wallet."

    if received < expected:
        return False, f"Received only {received:.2f} USDT. Required {expected:.2f} USDT."

    return True, f"USDT verified. Received {received:.2f} USDT."


async def check_ltc(txid, expected_amount, started_at):
    expected = clean_amount(expected_amount)

    if expected is None:
        return False, "Invalid amount."

    url = f"https://api.blockcypher.com/v1/ltc/main/txs/{txid.strip()}"

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status != 200:
                return False, "Litecoin transaction not found."
            data = await response.json(content_type=None)

    tx_time_text = data.get("confirmed") or data.get("received")

    if tx_time_text:
        tx_time = int(datetime.fromisoformat(tx_time_text.replace("Z", "+00:00")).timestamp())

        if tx_time < started_at - OLD_TX_BUFFER_SECONDS:
            return False, "Old transaction. Please send a new payment after opening this page."

    if data.get("confirmations", 0) < 1:
        return False, "Waiting for Litecoin confirmation."

    received_ltc = 0.0

    for output in data.get("outputs", []):
        if LTC_ADDRESS in output.get("addresses", []):
            received_ltc += output.get("value", 0) / 100000000

    if received_ltc <= 0:
        return False, "LTC not sent to shop wallet."

    price = await get_ltc_price()

    if price is None:
        return True, f"LTC received: {received_ltc:.8f}. Cannot check USD price now."

    received_usd = received_ltc * price

    if received_usd < expected:
        return False, f"Received only ${received_usd:.2f}. Required ${expected:.2f}."

    return True, f"Litecoin verified. Received {received_ltc:.8f} LTC ≈ ${received_usd:.2f}."


@app.route("/")
def home():
    product = request.args.get("product", "Roblox Premium 450")
    amount = request.args.get("amount", "5")
    started_at = int(time.time())

    return render_template(
        "index.html",
        product=product,
        amount=amount,
        usdt=USDT_ADDRESS,
        ltc=LTC_ADDRESS,
        started_at=started_at
    )


@app.route("/verify", methods=["POST"])
def verify():
    data = request.json or {}

    method = data.get("method")
    txid = data.get("txid", "").strip()
    amount = data.get("amount")
    started_at = int(data.get("started_at", time.time()))

    if not txid:
        return jsonify({"ok": False, "message": "Please enter TxID."})

    normalized = f"{method}:{txid.lower()}"

    if normalized in USED_TXIDS:
        return jsonify({"ok": False, "message": "Duplicate TxID. This transaction was already used."})

    try:
        if method == "USDT":
            ok, msg = asyncio.run(check_usdt(txid, amount, started_at))
        elif method == "LTC":
            ok, msg = asyncio.run(check_ltc(txid, amount, started_at))
        else:
            ok, msg = False, "Unsupported payment method."
    except Exception as e:
        print("VERIFY ERROR:", e)
        return jsonify({"ok": False, "message": "System error while checking payment."})

    if ok:
        USED_TXIDS.add(normalized)
        save_used(USED_TXIDS)

    return jsonify({"ok": ok, "message": msg})


port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
