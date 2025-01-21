from flask import Flask, render_template, request, redirect, url_for
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# File tempat nyimpen token
token_file = "token.txt"


# Fungsi untuk dapetin token dari file
def get_token():
    try:
        with open(token_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


# Fungsi untuk simpen token ke file
def save_token(token):
    with open(token_file, "w") as f:
        f.write(token)


@app.route("/")
def index():
    content = "Index"
    return render_template("index.html", content=content)


# LOGIC DASHBOARD
def run_query(token, yy, mm, dd, yesterday):
    # URL API
    api_url = "http://172.24.52.4:7171/api/vquery/selectquery"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Query pertama
    payload1 = {
        "listCabangVquery": "4,6,10,11,16,18,19,31,37,38,39,58,60,61,63",
        "datavquery": f"SELECT kdcab, count(toko) as toko FROM m_toko_aktif_{yy}{mm} WHERE tanggal='{yesterday}';",
    }

    # Eksekusi query pertama
    response1 = requests.post(api_url, json=payload1, headers=headers)
    if response1.status_code == 200:
        result1 = response1.json().get("data", [])
        # Ambil total toko dari setiap kdcab

    else:
        result1 = None

    # Query kedua
    payload2 = {
        "listCabangVquery": "4,6,10,11,16,18,19,31,37,38,39,58,60,61,63",
        "datavquery": f"SELECT a.kdcab as cabang, COUNT(DISTINCT b.shop) AS dt_masuk FROM m_toko_aktif_{yy}{mm} a JOIN DT_{yy}{mm}{dd} b ON a.toko=b.shop WHERE a.tanggal='{yesterday}';",
    }

    # Eksekusi query kedua
    response2 = requests.post(api_url, json=payload2, headers=headers)
    if response2.status_code == 200:
        result2 = response2.json().get("data", [])
    else:
        result2 = None

    # Query ketiga
    payload3 = {
        "listCabangVquery": "4,6,10,11,16,18,19,31,37,38,39,58,60,61,63",
        "datavquery": f"select count(DISTINCT(l.toko)) as toko_off from m_toko_libur l left JOIN m_toko_tutup t on(t.toko=l.toko);",
    }

    # Eksekusi query kedua
    response3 = requests.post(api_url, json=payload3, headers=headers)
    if response3.status_code == 200:
        result3 = response3.json().get("data", [])
    else:
        result3 = None

    return result1, result2, result3


@app.route("/dashboard/")
def dashboard():
    content = "Dashboard"
    # Hitung tanggal H-1
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    kemarin = str(yesterday)

    # Pisahin jadi yy, mm, dd
    yy = kemarin[2:4]  # Ini bakal ambil karakter di index 2 sampai 4
    mm = kemarin[5:7]  # Ambil bulan
    dd = kemarin[8:10]  # Ambil hari

    # Cek apakah token udah ada
    token = get_token()

    if not token:
        # Token belum ada, login untuk dapetin token baru
        login_url = "http://172.24.52.4:7171/api/login"
        login_data = {"username": "2013114380", "password": "2013114380"}
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            token = response.json().get("token")
            save_token(token)  # Simpen token ke file
        else:
            return "Login gagal", 401

    # Eksekusi beberapa query
    result1, result2, result3 = run_query(token, yy, mm, dd, yesterday)

    if result1 is None or result2 is None or result3 is None:
        return "Error executing queries", 500

    # # Gabungkan hasil dari query 1 dan query 2
    # combined_results = {"toko": result1, "dt_masuk": result2}

    total_toko_aktif = sum(int(item.get("toko", 0)) for item in result1)
    total_toko_proses = sum(int(item.get("dt_masuk", 0)) for item in result2)
    total_toko_off = sum(int(item.get("toko_off", 0)) for item in result3)

    # Kirim hasil ke template HTML
    return render_template(
        "dashboard.html",
        tokoaktif=total_toko_aktif,
        tokooff=total_toko_off,
        tokoproses=total_toko_proses,
        tanggal=yesterday,
        content=content,
    )


@app.route("/hriris/")
def hriris():
    content = "HR IRIS"
    return render_template("hriris.html", content=content)


# Route buat login dan dapetin data
@app.route("/submit", methods=["POST"])
def submit():
    content = "HR IRIS"
    # Ambil input dari form
    kdcab = request.form["kdcab"]
    tanggal = request.form["tanggal"]

    # Cek apakah token udah ada
    token = get_token()

    if not token:
        # Token belum ada, login untuk dapetin token baru
        login_url = "http://172.24.52.4:7171/api/login"
        login_data = {"username": "2013114380", "password": "2013114380"}
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            token = response.json().get("token")
            save_token(token)  # Simpen token ke file
        else:
            return "Login gagal", 401

    # Gunakan token untuk request berikutnya
    api_url = "http://172.24.52.4:7171/api/hrtampung/"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"kdcab": kdcab, "tanggal": tanggal}
    response = requests.post(api_url, json=payload, headers=headers)

    # Cek hasil response
    if response.status_code == 200:
        data = response.json()
        # Render hasil ke HTML
        return render_template("result_iris.html", data=data)
    else:
        return f"Error: {response.status_code}", 500


@app.route("/hrtampung/")
def hrtampung():
    content = "HR Tampung"
    return render_template("hrtampung.html", content=content)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
