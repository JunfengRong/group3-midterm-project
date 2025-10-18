import logging
import pyodbc
import azure.functions as func
import os
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing user request...')
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

            if method == "POST":  # 添加
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
                        json.dumps({"message": "User added"}),
                        status_code=201,
                        mimetype="application/json"
                    )
                except ValueError:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid JSON body"}),
                        status_code=400,
                        mimetype="application/json"
                    )

            elif method == "GET":  # 查询
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

            elif method == "PUT":  # 修改
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

            elif method == "DELETE":  # 删除
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