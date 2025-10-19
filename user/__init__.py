import logging
import pyodbc
import azure.functions as func
import os
import json
import requests
from jose import jwt

# Configuration Keycloak


CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET")
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL")
CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "my-python-api")
TOKEN_URL = f"{KEYCLOAK_URL}/protocol/openid-connect/token"
JWKS_URL = f"{KEYCLOAK_URL}/protocol/openid-connect/certs"
AUDIENCE = os.environ.get("KEYCLOAK_CLIENT_ID")
ALGORITHM = "RS256"
# Get public keys from Keycloak (JWKS)

def verify_token(req: func.HttpRequest):
    """Vérifie le token JWT envoyé dans l'en-tête Authorization"""
    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "Missing or invalid Authorization header"

    token = auth_header.split(" ")[1]
    try:

        logging.info('Verifying token...')
        jwks = requests.get(JWKS_URL, timeout=30, verify=False).json()
        payload = jwt.decode(token, jwks, algorithms=[ALGORITHM], audience=AUDIENCE)
        logging.info('Token verified successfully')

        return payload, None
    except Exception as e:
        logging.error(f"Token verification failed: {e}")
        return None, str(e)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing user request...')


    action = req.route_params.get("action")

    # ---------------------------
    # 1. Route spéciale : /token
    # ---------------------------
    if action == "token" and req.method == "POST":
        try:
            data = req.get_json()
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return func.HttpResponse(
                    json.dumps({"error": "Missing username or password"}),
                    status_code=400,
                    mimetype="application/json"
                )

            payload = {
                "client_id": AUDIENCE,
                "grant_type": "password",
                "username": username,
                "password": password
            }
            if CLIENT_SECRET:
                payload["client_secret"] = CLIENT_SECRET

            resp = requests.post(TOKEN_URL, data=payload, verify=False)
            return func.HttpResponse(
                resp.text,
                status_code=resp.status_code,
                mimetype="application/json"
            )
        except Exception as e:
            return func.HttpResponse(
                json.dumps({"error": "Token request failed", "details": str(e)}),
                status_code=500,
                mimetype="application/json"
            )



    # OAuth2 Verification
    user, error = verify_token(req)
    if error:
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "details": error}),
            status_code=401,
            mimetype="application/json"
        )

    conn_str = os.environ.get("SQL_CONNECTION_STRING")
    if not conn_str:
        return func.HttpResponse(
            json.dumps({"error": "Missing SQL connection string"}),
            status_code=500,
            mimetype="application/json"
        )

    method = req.method

    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            if method == "POST":
                try:
                    data = req.get_json()
                    name, email = data.get("name"), data.get("email")
                    if not name or not email:
                        return func.HttpResponse(
                            json.dumps({"error": "Missing name or email"}),
                            status_code=400,
                            mimetype="application/json"
                        )
                    cursor.execute("INSERT INTO Users (name, email) VALUES (?, ?)", name, email)
                    conn.commit()
                    return func.HttpResponse(
                        json.dumps({"message": "User added", "by": user.get("preferred_username")}),
                        status_code=201,
                        mimetype="application/json"
                    )
                except ValueError:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid JSON body"}),
                        status_code=400,
                        mimetype="application/json"
                    )

            elif method == "GET":
                user_id = req.params.get("id")
                if user_id:
                    cursor.execute("SELECT * FROM Users WHERE id=?", user_id)
                    row = cursor.fetchone()
                    if row:
                        return func.HttpResponse(
                            json.dumps({"id": row[0], "name": row[1], "email": row[2]}),
                            mimetype="application/json"
                        )
                    else:
                        return func.HttpResponse(
                            json.dumps({"error": "User not found"}),
                            status_code=404,
                            mimetype="application/json"
                        )
                else:
                    cursor.execute("SELECT * FROM Users")
                    rows = cursor.fetchall()
                    users = [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]
                    return func.HttpResponse(
                        json.dumps(users),
                        mimetype="application/json"
                    )

            elif method == "PUT":
                data = req.get_json()
                user_id, name, email = data.get("id"), data.get("name"), data.get("email")
                if not user_id or not name or not email:
                    return func.HttpResponse(
                        json.dumps({"error": "Missing id, name or email"}),
                        status_code=400,
                        mimetype="application/json"
                    )
                cursor.execute("UPDATE Users SET name=?, email=? WHERE id=?", name, email, user_id)
                conn.commit()
                return func.HttpResponse(
                    json.dumps({"message": "User updated"}),
                    status_code=200,
                    mimetype="application/json"
                )

            elif method == "DELETE":
                user_id = req.params.get("id")
                if not user_id:
                    return func.HttpResponse(
                        json.dumps({"error": "Missing id parameter"}),
                        status_code=400,
                        mimetype="application/json"
                    )
                cursor.execute("DELETE FROM Users WHERE id=?", user_id)
                conn.commit()
                return func.HttpResponse(
                    json.dumps({"message": "User deleted"}),
                    status_code=200,
                    mimetype="application/json"
                )

            else:
                return func.HttpResponse(
                    json.dumps({"error": "Unsupported method"}),
                    status_code=405,
                    mimetype="application/json"
                )

    except Exception as e:
        logging.error(f"Database operation failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
