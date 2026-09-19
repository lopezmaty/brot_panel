"""
Script de prueba para inspeccionar el endpoint /comprobantesAsociados de Xubio.

Objetivo: ver si este endpoint devuelve el detalle de qué facturas
quedaron canceladas por una cobranza/pago puntual, o si trae otra cosa
(comprobantes pendientes de asociar, por ejemplo).

Uso:
    python test_comprobantes_asociados.py
"""

import requests
import json

# --- Credenciales (completar) ---
CLIENT_ID = "TU_CLIENT_ID"
CLIENT_SECRET = "TU_CLIENT_SECRET"

BASE_URL = "https://xubio.com/API/1.1"
TOKEN_URL = f"{BASE_URL}/TokenEndpoint"


def obtener_token():
    """Obtiene el access_token via OAuth2 client_credentials."""
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
    )
    response.raise_for_status()
    return response.json()["access_token"]


def obtener_comprobantes_asociados(token, cliente_id, tipo_comprobante):
    """
    tipo_comprobante: 1-Factura, 2-Nota de Débito, 3-Nota de Crédito,
                       6-Recibo, 10-Factura MiPyME, 11-ND MiPyME, 12-NC MiPyME
    """
    url = f"{BASE_URL}/comprobantesAsociados"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"clienteId": cliente_id, "tipoComprobante": tipo_comprobante}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    token = obtener_token()
    print("Token obtenido OK\n")

    # --- Completar con un cliente real que tenga cobranzas con varias facturas asociadas ---
    CLIENTE_ID_PRUEBA = 123  # <-- reemplazar por un id real

    print("=== Probando tipoComprobante=6 (Recibo/Cobranza) ===")
    data_recibos = obtener_comprobantes_asociados(token, CLIENTE_ID_PRUEBA, 6)
    print(json.dumps(data_recibos, indent=2, ensure_ascii=False))

    print("\n=== Probando tipoComprobante=1 (Factura) ===")
    data_facturas = obtener_comprobantes_asociados(token, CLIENTE_ID_PRUEBA, 1)
    print(json.dumps(data_facturas, indent=2, ensure_ascii=False))
