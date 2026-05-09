from flask import Flask, render_template, request
import os

app = Flask(__name__)

USDT_ADDRESS = "0x074b03699b5b354e293459347ba1803f82b1e5ef"
LTC_ADDRESS = "LcyginaTtsPeSp4xFaK5R47mbMaFbbZiat"

@app.route("/")
def home():
    product = request.args.get("product", "Roblox Premium 450")
    amount = request.args.get("amount", "350.00")

    return render_template(
        "index.html",
        product=product,
        amount=amount,
        usdt=USDT_ADDRESS,
        ltc=LTC_ADDRESS
    )

port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)