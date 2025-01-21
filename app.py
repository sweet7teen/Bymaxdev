from flask import Flask, render_template, request, redirect, url_for, abort, g
import requests
import os
import jwt as pyjwt
import time
from datetime import datetime, timedelta
import logging
import mysql.connector
from functools import wraps

# logging.basicConfig(filename='debug.log', level=logging.INFO)

app = Flask(__name__)

# Konfigurasi koneksi MySQL
DB_CONFIG = {
    'host': '192.168.26.78',  # IP database (localhost kalau di Laragon)
    'user': 'root',       # Username MySQL
    'password': '',       # Password MySQL (default kosong di Laragon)
    'database': 'lokal'
}

def get_user_by_ip(ip):
    """Ambil username berdasarkan IP dari database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT username FROM baymax_users WHERE ip = %s', (ip,))
        row = cursor.fetchone()
        conn.close()
        return row['username'] if row else None
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

@app.before_request
def load_user():
    """Load user before processing request."""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    g.username = get_user_by_ip(client_ip)  # Set username ke Flask global object

@app.context_processor
def inject_user():
    """Inject user into all templates."""
    return {"username": g.get("username", None)}  # Tambahkan username ke template context

def require_registered_ip(func):
    """Decorator untuk membatasi akses hanya untuk IP yang terdaftar."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not g.get("username"):  # Periksa apakah IP terdaftar
            abort(403)  # Forbidden jika tidak terdaftar
        return func(*args, **kwargs)
    return wrapper


token_cache = None  # Variabel global untuk menyimpan token

@app.context_processor
def inject_user():
    """Inject username ke semua template."""
    return {"username": g.get("username", None)}

@app.route("/")
def index():
    content = "Homepage"    
    return render_template("index.html", content=content)

@app.route("/homepage/")
def homepage():
    content = "homepage"
    return render_template("homepage.html", content=content)

@app.route("/error401/")
def error401():
    content = "Error 401"
    return render_template("401.html", content=content)

token_cache = {"access_token": None, "refresh_token": None}

def refresh_token():
    global token_cache
    refresh_url = "http://172.24.52.4:7171/api/refresh"
    response = requests.post(refresh_url, json={"refresh_token": token_cache["refresh_token"]})
    if response.status_code == 200:
        data = response.json()
        token_cache["access_token"] = data.get("access_token")
        token_cache["refresh_token"] = data.get("refresh_token", token_cache["refresh_token"])
    else:
        raise Exception(f"Failed to refresh token, status code: {response.status_code}")

def get_token():
    global token_cache

    def is_token_expired(token, margin=300):  # Tambah margin 5 menit
        try:
            payload = pyjwt.decode(token, options={"verify_signature": False})
            exp = payload.get("exp", 0)  # Ambil expiration time
            return time.time() > (exp - margin)  # True kalau expired
        except pyjwt.DecodeError:
            return True  # Kalau token gak valid, anggap expired

    if not token_cache["access_token"] or is_token_expired(token_cache["access_token"]):
        if token_cache["refresh_token"]:
            try:
                refresh_token()  # Coba refresh token
            except Exception:
                pass  # Kalau gagal, lanjut login
        if not token_cache["access_token"]:
            # Login baru
            login_url = "http://172.24.52.4:7171/api/login"
            login_data = {"username": "2013114380", "password": "2013114380"}
            response = requests.post(login_url, json=login_data)
            if response.status_code == 200:
                data = response.json()
                token_cache["access_token"] = data.get("token")
                token_cache["refresh_token"] = data.get("refresh_token")
            else:
                raise Exception(f"Failed to login, status code: {response.status_code}")
    return token_cache["access_token"]



@app.route("/dashboard/")
def dashboard():
    # Ambil token
    token = get_token()
    if not token:
        return redirect(url_for("error401"))  # Redirect kalau token gagal

    content = "Dashboard"
    # Hitung tanggal H-1
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    kemarin = str(yesterday)

    # Pisahin jadi yy, mm, dd
    yy = kemarin[2:4]  # Ini bakal ambil karakter di index 2 sampai 4
    mm = kemarin[5:7]  # Ambil bulan
    dd = kemarin[8:10]  # Ambil hari

    periodehr = yy + mm + dd
    periodemm = yy + mm

    path_v = "V:\\DTHR\\HR" + periodemm

    kdcbg_list = os.listdir(path_v)

    data_list = []

    for kdcbg in kdcbg_list:
        folder_path = os.path.join(path_v, kdcbg)

        # Cek apakah itu folder
        if os.path.isdir(folder_path):
            # Ngelist file di dalam folder
            files = os.listdir(folder_path)
            for file in files:
                # Cek apakah nama file sesuai format yang diinginkan
                if (file.startswith("FR") or file.startswith("HR")) and file[
                    2:8
                ] == periodehr:
                    # Ambil KDCBG
                    kdcbg = kdcbg
                    # Ambil nama toko
                    if file.startswith("FR"):
                        toko = (
                            "F" + file[-3:]
                        )  # Ambil 3 karakter terakhir untuk nama toko
                    elif file.startswith("HR"):
                        toko = (
                            "T" + file[-3:]
                        )  # Ambil 3 karakter terakhir untuk nama toko
                    else:
                        toko = "Unknown"

                    # Tambahkan data ke dalam list
                    data_list.append({"kdcbg": kdcbg, "toko": toko, "file": file})

    hr_g050 = [item for item in data_list if item["kdcbg"] == "G050"]
    hr_g241 = [item for item in data_list if item["kdcbg"] == "G241"]
    hr_g242 = [item for item in data_list if item["kdcbg"] == "G242"]
    smd_in = len(hr_g050)
    bul_in = len(hr_g241)
    tar_in = len(hr_g242)
    
    # AKSES HR IRIS
    api_url_iris = "http://172.24.52.4:7171/api/hariris/"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload_iris = {
        "kdcab": "16,58,60",
        "tanggal": yesterday,
    }

    response_iris = requests.post(api_url_iris, json=payload_iris, headers=headers)

    # Cek hasil response_iris
    if response_iris.status_code == 200:
        datas = response_iris.json()
        rekap_data = datas.get("rekapdata", [])
        lr = datas.get("lr", [])
        ts = datas.get("ts", [])
        listdata = datas.get("listdata", [])
        # print(listdata)

        # Ambil data scraping dengan kdcbg G050
        smd_scraping = [item for item in listdata if item.get("kdcab") == "G050"]
        bul_scraping = [item for item in listdata if item.get("kdcab") == "G241"]
        tar_scraping = [item for item in listdata if item.get("kdcab") == "G242"]

        # Bandingkan dengan hr_g050 untuk toko yang belum masuk
        smd_kurang_details = [
            item for item in smd_scraping if item.get("kdtk") not in [toko["toko"] for toko in hr_g050]
        ]        
        bul_kurang_details = [
            item for item in bul_scraping if item.get("kdtk") not in [toko["toko"] for toko in hr_g241]
        ]
        tar_kurang_details = [
            item for item in tar_scraping if item.get("kdtk") not in [toko["toko"] for toko in hr_g242]
        ]


        # # Debug: Print detail toko yang belum masuk
        # if not smd_kurang_details:
        #     print("Semua toko aktif sudah masuk di lokal!")
        # else:
        #     print("Detail toko yang belum masuk:")
        #     for toko in smd_kurang_details:
        #         print(f"KDCBG: {toko['kdcab']}, Toko: {toko['kdtk']}")

        # Ambil total toko dari setiap kdcab
        # TOKO AKTIF
        total_toko_aktif = sum(int(item.get("total_toko", 0)) for item in rekap_data)
        # TOKO SUDAH PROSES
        total_toko_sudah = sum(int(item.get("sudah", 0)) for item in rekap_data)
        # TOKO BELUM PROSES
        total_toko_belum = sum(int(item.get("belum", 0)) for item in rekap_data)
        # TOKO NOK
        # Buat set buat nyimpen toko/kdtk yang udah ada biar nggak double
        toko_set = set()
        # Ambil data dari lr, cek dulu apakah toko belum ada di set
        toko_lr = []
        for item in lr:
            toko = item.get("toko")
            if toko and toko not in toko_set:
                toko_lr.append(item)
                toko_set.add(toko)  # Simpen ke set biar nggak duplicate nanti
        total_lr = len(toko_lr)
        # Ambil data dari ts, cek dulu apakah kdtk belum ada di set
        toko_ts = []
        for item in ts:
            kdtk = item.get("kdtk")
            if kdtk and kdtk not in toko_set:
                toko_ts.append(item)
                toko_set.add(kdtk)  # Simpen ke set biar nggak duplicate nanti
        total_ts = len(toko_ts)
        # Total toko NOK tanpa duplikat
        total_toko_nok = total_lr + total_ts
        detil_toko_nok = toko_lr + toko_ts


        # DETIL BELUM PROSES
        belum_proses_data = [
            item for item in listdata if item.get("proses") == "Belum Proses"
        ]

        # GET TOTAL TOKO AKTIF UNTUK LOCAL
        smd = sum(
            int(item.get("total_toko", 0))
            for item in rekap_data
            if item.get("kdcab") == "G050"
        )
        bul = sum(
            int(item.get("total_toko", 0))
            for item in rekap_data
            if item.get("kdcab") == "G241"
        )
        tar = sum(
            int(item.get("total_toko", 0))
            for item in rekap_data
            if item.get("kdcab") == "G242"
        )
        
        smd_kurang = smd - smd_in
        bul_kurang = bul - bul_in
        tar_kurang = tar - tar_in

        


    else:
        return f"Error: {response_iris.status_code}", 500

    # AKSES HR TAMPUNG
    api_url_tampung = "http://172.24.52.4:7171/api/hrtampung/"
    payload_tampung = {
        "kdcab": "16,58,60",
        "tanggal": yesterday,
    }

    response_tampung = requests.post(
        api_url_tampung, json=payload_tampung, headers=headers
    )

    if response_tampung.status_code == 200:
        datas = response_tampung.json()
        total_toko = datas.get("total_toko", [])
        total_sudah = datas.get("total_sudah", [])
        total_belum = datas.get("total_belum", [])
        total_closing = datas.get("total_sudah_closing", [])
        total_blm_closing = datas.get("total_belum_closing", [])
        total_listener_nok = datas.get("listener_nok", [])
        tampung_detil_belum = datas.get("detailbelum", [])

        # DETIL lISTENER NOK
        tampung_detil_nok = [
            item
            for item in tampung_detil_belum
            if item.get("task_last_resp_msg") == "Listener NOK"
        ]

    else:
        return f"Error: {response_tampung.status_code}", 500

    # Kirim hasil total_toko_sum ke template
    return render_template(
        "dashboard.html",
        periodehr=periodehr,
        toko_aktif=total_toko_aktif,
        toko_nok=total_toko_nok,
        toko_sudah=total_toko_sudah,
        toko_belum=total_toko_belum,
        detil_nok=detil_toko_nok,
        detil_belum=belum_proses_data,
        tampung_toko=total_toko,
        tampung_sudah=total_sudah,
        tampung_belum=total_belum,
        tampung_closing=total_closing,
        tampung_blm_closing=total_blm_closing,
        tampung_nok=total_listener_nok,
        detil_tampung_belum=tampung_detil_belum,
        detil_tampung_nok=tampung_detil_nok,
        smd=smd,
        bul=bul,
        tar=tar,
        smd_in=smd_in,
        bul_in=bul_in,
        tar_in=tar_in,
        smd_kurang=smd_kurang,
        bul_kurang=bul_kurang,
        tar_kurang=tar_kurang,
        smd_kurang_details=smd_kurang_details,
        bul_kurang_details=bul_kurang_details,
        tar_kurang_details=tar_kurang_details,
        tanggal=yesterday,
        content=content,
    )


# @app.route("/hriris/")
# def hriris():
#     content = "HR IRIS & Tampung"
    

#     return render_template("hriris.html", content=content)

@app.route("/hriris/", methods=["GET", "POST"])
def hriris():
    content = "HR IRIS & Tampung"
    rekap_data = []
    list_data_belum = []
    rekap_cabang = []
    detail_belum = []

    if request.method == "POST":
        # Ambil input dari form
        kdcab = request.form.getlist("kdcab")
        tanggal = request.form["tanggal"]

        # Ambil token
        token = get_token()
        if not token:
            return redirect(url_for("error401"))  # Redirect kalau token gagal

        # Gunakan token untuk request berikutnya
        api_url_iris = "http://172.24.52.4:7171/api/hariris/"
        api_url_tampung = "http://172.24.52.4:7171/api/hrtampung/"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"kdcab": kdcab, "tanggal": tanggal}

        # Request ke API IRIS
        try:
            response_iris = requests.post(api_url_iris, json=payload, headers=headers)
            response_iris.raise_for_status()
            datas_iris = response_iris.json()
            rekap_data = datas_iris.get("rekapdata", [])
            list_data = datas_iris.get("listdata", [])
            list_data_belum = [item for item in list_data if item.get("proses") == "Belum Proses"]
        except requests.exceptions.RequestException as e:
            return f"Error IRIS: {str(e)}", 500

        # Request ke API Tampung
        try:
            response_tampung = requests.post(api_url_tampung, json=payload, headers=headers)
            response_tampung.raise_for_status()
            datas_tampung = response_tampung.json()
            rekap_cabang = datas_tampung.get("rekap_percabang", [])
            detail_belum = datas_tampung.get("detailbelum", [])
        except requests.exceptions.RequestException as e:
            return f"Error Tampung: {str(e)}", 500

    # Render template
    return render_template(
        "hriris.html",
        content=content,
        rekap_data=rekap_data,
        list_data_belum=list_data_belum,
        rekap_cabang=rekap_cabang,
        detail_belum=detail_belum,
    )




#Route buat login dan dapetin data
@app.route("/result_iris", methods=["POST"])
def result_iris():
    content = "Result IRIS & Tampung"
    # Ambil input dari form
    kdcab = request.form.getlist("kdcab")
    tanggal = request.form["tanggal"]

    # Ambil token
    token = get_token()
    if not token:
        return redirect(url_for("error401"))  # Redirect kalau token gagal

    # Gunakan token untuk request berikutnya
    api_url_iris = "http://172.24.52.4:7171/api/hariris/"
    api_url_tampung = "http://172.24.52.4:7171/api/hrtampung/"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"kdcab": kdcab, "tanggal": tanggal}
    response_iris = requests.post(api_url_iris, json=payload, headers=headers)
    response_tampung = requests.post(api_url_tampung, json=payload, headers=headers)

    # Cek hasil response
    if response_iris.status_code == 200:
        datas = response_iris.json()
        rekap_data = datas.get("rekapdata", [])
        list_data = datas.get("listdata", [])

        list_data_belum = [item for item in list_data if item.get("proses") == "Belum Proses"]
        # print("Data diterima:", rekap_data)
        # Render hasil ke HTML
        
    else:
        return f"Error: {response_iris.status_code}", 500
    
    # Cek hasil response
    if response_tampung.status_code == 200:
        datas = response_tampung.json()
        rekap_cabang = datas.get("rekap_percabang", [])
        detail_belum = datas.get("detailbelum", [])

        # detail_belum = [item for item in detail_belum if item.get("proses") == "Belum Proses"]
        # print("Data diterima:", rekap_cabang)
        # Render hasil ke HTML
        
    else:
        return f"Error: {response_tampung.status_code}", 500
    

    return render_template("result_iris.html", 
                           content=content, 
                           rekap_data=rekap_data, 
                           list_data_belum=list_data_belum,
                           rekap_cabang=rekap_cabang,
                           detail_belum=detail_belum)

    
# @app.route("/hrtampung/")
# def hrtampung():
#     content = "HR Tampung"
#     return render_template("hrtampung.html", content=content)

@app.route("/hrwrc/")
def hrwrc():
    content = "HR WRC"
    return render_template("hrwrc.html", content=content)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
