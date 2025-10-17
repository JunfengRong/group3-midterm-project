import logging
import pyodbc
import azure.functions as func
import os
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing user request...')
    conn_str = os.environ["SQL_CONNECTION_STRING"]
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    method = req.method

    if method == "POST":  # 添加
        data = req.get_json()
        cursor.execute("INSERT INTO Users (name, email) VALUES (?, ?)", data["name"], data["email"])
        conn.commit()
        return func.HttpResponse("User added", status_code=201)

    elif method == "GET":  # 查询
        user_id = req.params.get("id")
        if user_id:
            cursor.execute("SELECT * FROM Users WHERE id=?", user_id)
            row = cursor.fetchone()
            if row:
                return func.HttpResponse(json.dumps({"id": row[0], "name": row[1], "email": row[2]}), mimetype="application/json")
            else:
                return func.HttpResponse("Not found", status_code=404)
        else:
            cursor.execute("SELECT * FROM Users")
            rows = cursor.fetchall()
            users = [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]
            return func.HttpResponse(json.dumps(users), mimetype="application/json")

    elif method == "PUT":  # 修改
        data = req.get_json()
        cursor.execute("UPDATE Users SET name=?, email=? WHERE id=?", data["name"], data["email"], data["id"])
        conn.commit()
        return func.HttpResponse("User updated", status_code=200)

    elif method == "DELETE":  # 删除
        user_id = req.params.get("id")
        cursor.execute("DELETE FROM Users WHERE id=?", user_id)
        conn.commit()
        return func.HttpResponse("User deleted", status_code=200)

    else:
        return func.HttpResponse("Unsupported method", status_code=405)
