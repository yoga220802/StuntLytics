import os
import joblib
import pandas as pd
import streamlit as st
from typing import Dict, Any

MODEL_PATH = "models/stunting_model.joblib"

@st.cache_resource(show_spinner="Memuat model klasifikasi...")
def load_model():
    if not os.path.exists(MODEL_PATH):
        st.error(f"File model tidak ditemukan di '{MODEL_PATH}'. Pastikan file ada di folder /models.")
        return None
    try:
        model = joblib.load(MODEL_PATH)
        return model
    except Exception as e:
        st.error(f"Gagal memuat model: {e}")
        return None

def predict_local(model, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Melakukan prediksi lokal dengan mereplikasi langkah-langkah preprocessing dari notebook.
    """
    if model is None:
        return {"error": "Model tidak berhasil dimuat."}

    try:
        # 1. Konversi input dictionary menjadi DataFrame
        df_input = pd.DataFrame([input_data])

        # 2. Replikasi Preprocessing dari Notebook (Mapping Lengkap)
        df_input['jenis_kelamin_anak'] = df_input['jenis_kelamin_anak'].map({'Laki-laki': 0, 'Perempuan': 1})
        df_input['akses_air_bersih'] = df_input['akses_air_bersih'].map({'Layak': 0, 'Tidak Layak': 1})
        df_input['status_imunisasi_anak'] = df_input['status_imunisasi_anak'].map({'Dasar Tidak Lengkap': 0, 'Lengkap': 1, 'Tidak Lengkap': 2})
        df_input['asi_eksklusif'] = df_input['asi_eksklusif'].map({'Ya': 1, 'Tidak': 0})
        df_input['jenis_pekerjaan_orang_tua'] = df_input['jenis_pekerjaan_orang_tua'].map({'Buruh': 0, 'Lainnya': 1, 'PNS': 2, 'Petani': 3, 'Wiraswasta': 4})
        df_input['pendidikan_ibu'] = df_input['pendidikan_ibu'].map({'Diploma': 0, 'S1': 1, 'SD': 2, 'SMA': 3, 'SMP': 4})
        df_input['status_pernikahan'] = df_input['status_pernikahan'].map({'Belum Menikah': 0, 'Menikah': 1})
        df_input['hipertensi_ibu'] = df_input['hipertensi_ibu'].map({'Tidak': 0, 'Ya': 1})
        df_input['diabetes_ibu'] = df_input['diabetes_ibu'].map({'Tidak': 0, 'Ya': 1})
        df_input['kepatuhan_ttd'] = df_input['kepatuhan_ttd'].map({'Baik': 0, 'Kurang': 1})
        df_input['paparan_asap_rokok'] = df_input['paparan_asap_rokok'].map({'Tidak': 0, 'Ya': 1})
        df_input['kepesertaan_program_bantuan'] = df_input['kepesertaan_program_bantuan'].map({'BPNT': 0, 'PKH': 1, 'Tidak Ada': 2})

        st.warning("Simulasi prediksi tanpa standard scaling. Akurasi mungkin berbeda dari notebook.", icon="🔬")

        # 3. Pastikan urutan kolom sama persis dengan saat training (19 FITUR)
        final_features_order = [
            'jenis_kelamin_anak', 'jenis_pekerjaan_orang_tua', 'pendidikan_ibu',
            # 'status_pernikahan',
            'jumlah_anak', 'akses_air_bersih', 'status_imunisasi_anak',
            'berat_lahir_gram', 'asi_eksklusif', 'usia_anak_bulan',
            'tinggi_badan_ibu_cm', 'lila_saat_hamil_cm', 'bmi_pra_hamil',
            'hb_g_dl', 'kenaikan_bb_hamil_kg', 'usia_ibu_saat_hamil_tahun',
            'jarak_kehamilan_sebelumnya_bulan',
            # 'hipertensi_ibu',
            # 'diabetes_ibu',
            'kunjungan_anc_x', 'kepatuhan_ttd',
            # 'paparan_asap_rokok',
            'kepesertaan_program_bantuan'
        ]
        df_processed = df_input.reindex(columns=final_features_order)

        # 4. Lakukan Prediksi
        prediction_proba = model.predict_proba(df_processed)[:, 1]
        prediction_label_num = model.predict(df_processed)[0]

        # 5. Format Output
        risk_score = float(prediction_proba[0])
        risk_label = "Stunting" if prediction_label_num == 1 else "Tidak Stunting"

        return {
            "risk_score": risk_score,
            "risk_label": risk_label
        }
    except Exception as e:
        st.error(f"Terjadi error saat prediksi lokal: {e}")
        return {"error": str(e)}

