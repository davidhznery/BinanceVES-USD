import json
import requests
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Headers optimizados para la petición a Binance P2P
            headers = {
                "Accept": "*/*",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive"
            }

            # Parsear parámetros de la URL de forma más robusta
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Parámetros con valores por defecto
            asset = query_params.get('asset', ['USDT'])[0].upper()
            fiat = query_params.get('fiat', ['VES'])[0].upper()
            trade_type = query_params.get('tradeType', ['SELL'])[0].upper()
            page = int(query_params.get('page', ['1'])[0])
            rows = int(query_params.get('rows', ['10'])[0])

            # Validar parámetros
            valid_assets = ['BTC', 'ETH', 'BNB', 'USDT', 'USDC', 'ADA', 'DOT', 'LINK', 'UNI', 'LTC']
            valid_fiats = ['VES', 'USD', 'EUR', 'ARS', 'BRL', 'COP']
            valid_trade_types = ['BUY', 'SELL']

            if asset not in valid_assets:
                asset = 'USDT'
            if fiat not in valid_fiats:
                fiat = 'VES'
            if trade_type not in valid_trade_types:
                trade_type = 'SELL'

            # Datos para la petición a Binance P2P (según documentación oficial)
            data = {
                "asset": asset,
                "fiat": fiat,
                "tradeType": trade_type,
                "page": page,
                "rows": rows,
                "merchantCheck": False,
                "payTypes": [],
                "publisherType": None
            }

            # Endpoint oficial de Binance P2P
            url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

            # Hacer la petición a Binance con timeout
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()  # Lanza excepción si hay error HTTP
            result = response.json()

            # Procesar los resultados con validación
            offers = []
            prices = []
            
            if result.get("success") and result.get("data"):
                for offer in result["data"]:
                    try:
                        # Extraer información detallada de cada oferta
                        adv = offer.get("adv", {})
                        advertiser = offer.get("advertiser", {})
                        
                        price = float(adv.get("price", 0))
                        min_single_trans_amount = float(adv.get("minSingleTransAmount", 0))
                        max_single_trans_amount = float(adv.get("maxSingleTransAmount", 0))
                        available_amount = float(adv.get("tradableQuantity", 0))
                        
                        # Solo incluir ofertas válidas
                        if price > 0 and available_amount > 0:
                            prices.append(price)
                            offers.append({
                                "price": price,
                                "minAmount": min_single_trans_amount,
                                "maxAmount": max_single_trans_amount,
                                "availableAmount": available_amount,
                                "paymentMethods": adv.get("tradeMethods", []),
                                "advertiserId": advertiser.get("userNo", ""),
                                "advertiserName": advertiser.get("nickName", ""),
                                "completionRate": advertiser.get("monthFinishRate", 0)
                            })
                    except (ValueError, KeyError) as e:
                        # Saltar ofertas con datos inválidos
                        continue

            # Calcular estadísticas
            avg_price = sum(prices) / len(prices) if prices else 0
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0

            # Respuesta mejorada con más detalles
            response_data = {
                "success": True,
                "asset": asset,
                "fiat": fiat,
                "tradeType": trade_type,
                "statistics": {
                    "averagePrice": round(avg_price, 2),
                    "minPrice": round(min_price, 2),
                    "maxPrice": round(max_price, 2),
                    "priceRange": round(max_price - min_price, 2) if prices else 0,
                    "totalOffers": len(offers),
                    "validOffers": len(prices)
                },
                "offers": offers[:5],  # Solo las primeras 5 ofertas para no sobrecargar
                "timestamp": result.get("timestamp", ""),
                "message": f"Precios P2P obtenidos exitosamente para {asset}/{fiat}"
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

        except requests.exceptions.Timeout:
            error_response = {
                "success": False,
                "error": "Timeout al conectar con Binance P2P",
                "message": "El servidor de Binance no respondió a tiempo"
            }
            self._send_error_response(500, error_response)
            
        except requests.exceptions.RequestException as e:
            error_response = {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "message": "No se pudo conectar con Binance P2P"
            }
            self._send_error_response(502, error_response)
            
        except json.JSONDecodeError:
            error_response = {
                "success": False,
                "error": "Respuesta inválida de Binance",
                "message": "Binance devolvió una respuesta no válida"
            }
            self._send_error_response(502, error_response)
            
        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "message": "Error inesperado en el servidor"
            }
            self._send_error_response(500, error_response)

    def _send_error_response(self, status_code, error_data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(error_data, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
