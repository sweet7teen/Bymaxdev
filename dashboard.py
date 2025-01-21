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

    # List toko yang masuk di SMD
    smd_toko_in = [item["toko"] for item in data_list if item["kdcbg"] == "G050"]

    # List detail toko yang kurang
    smd_kurang_details = [
        item for item in data_list if item["kdcbg"] == "G050" and item["toko"] not in smd_toko_in
    ]

    # AKSES HR IRIS
    api_url_iris = "http://172.24.52.4:7171/api/hariris/"
    headers = {
        "Authorization": f"Bearer {token_cache}",
        "Content-Type": "application/json",
    }
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
        tanggal=yesterday,
        content=content,
    )