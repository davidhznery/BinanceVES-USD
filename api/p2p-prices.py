import json
import requests
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Headers para la petición a Binance
            headers = {
                "Accept": "*/*",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            # Obtener parámetros de la URL
            if '?' in self.path:
                query_string = self.path.split('?')[1]
                params = dict(param.split('=') for param in query_string.split('&'))
                asset = params.get('asset', 'USDT')
                fiat = params.get('fiat', 'VES')
                trade_type = params.get('tradeType', 'SELL')
            else:
                asset = 'USDT'
                fiat = 'VES'
                trade_type = 'SELL'

            # Datos para la petición a Binance P2P
            data = {
                "asset": asset,
                "fiat": fiat,
                "tradeType": trade_type,
                "page": 1,
                "rows": 10,
                "merchantCheck": False,
                "payTypes": [],
                "publisherType": None
            }

            url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

            # Hacer la petición a Binance
            response = requests.post(url, headers=headers, json=data)
            result = response.json()

            # Procesar los resultados
            prices = []
            if result.get("success") and result.get("data"):
                for offer in result["data"]:
                    price = float(offer["adv"]["price"])
                    prices.append(price)

            # Calcular precio promedio
            avg_price = sum(prices) / len(prices) if prices else 0

            # Respuesta
            response_data = {
                "success": True,
                "asset": asset,
                "fiat": fiat,
                "tradeType": trade_type,
                "prices": prices,
                "averagePrice": avg_price,
                "count": len(prices)
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())

        except Exception as e:
            error_response = {
                "success": False,
                "error": str(e)
            }
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
