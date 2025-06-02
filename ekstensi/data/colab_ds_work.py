
!pip install requests tqdm together

import os
import time
import json
import random
import hashlib
import concurrent.futures
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict, Any, Optional
import uuid

try:
    from together import Together
except ImportError:
    print("KESALAHAN: Pustaka 'together' tidak ditemukan. Pastikan sudah diinstal dengan '!pip install together'")
    raise

MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
API_KEY = "fd39b47d2d1f77cc8771bfd5e3019459247bbe26ce4e4fbc0fd9c75466a1009c"

try:
    if not API_KEY:
        raise ValueError("API_KEY tidak boleh kosong.")
    CLIENT = Together(api_key=API_KEY)
except Exception as e:
    print(f"KESALAHAN KRITIS: Gagal menginisialisasi klien Together: {e}")
    print("Pastikan API Key valid dan pustaka 'together' terinstal dengan benar.")
    raise

DATASET_SIZE = 5
BATCH_SIZE = 20
NUM_WORKERS = 2
OUTPUT_DIR = "mql5_dataset_together_lib"
CHECKPOINT_INTERVAL = 5

Path(OUTPUT_DIR).mkdir(exist_ok=True, parents=True)

MQL5_DATA_TEMPLATES = [
    "Kumpulkan {strategy} trading yang memiliki winrate diatas 80% dan sudah teruji.",
    "Jelaskan strategi trading '{strategy}' dengan implementasi kode MQL5 lengkap dan backtest.",
    "Buatkan dokumentasi dan contoh penggunaan indikator '{indicator}' dalam MQL5.",
    "Bagaimana cara membuat Expert Advisor untuk strategi '{strategy}' dalam MQL5?",
    "Jelaskan konsep {concept} dalam MQL5 dengan contoh kode."
]

MQL5_DATA_FIELDS = {
    "function": ["OrderSend", "iMA", "CopyRates", "ObjectCreate", "Print"],
    "strategy": ["Moving Average Crossover", "RSI Divergence", "Scalping", "Price Action"],
    "indicator": ["Moving Average", "RSI", "MACD", "Bollinger Bands"],
    "concept": ["Event Handling", "Custom Indicators", "Expert Advisors", "Order Management"]
}

MQL5_DATA_SCHEMAS = [
    {
        "type": "tutorial",
        "fields": ["id", "title", "description", "content", "code_examples"]
    },
    {
        "type": "strategy",
        "fields": ["id", "name", "description", "implementation", "parameters"]
    },
    {
        "type": "indicator",
        "fields": ["id", "name", "description", "code", "usage_examples"]
    },
    {
        "type": "expert_advisor",
        "fields": ["id", "name", "description", "strategy_type", "code"]
    },
    {
        "type": "concept_explanation",
        "fields": ["id", "concept", "description", "examples"]
    }
]

def get_prompt_variation() -> (str, str):
    template = random.choice(MQL5_DATA_TEMPLATES)
    chosen_schema = random.choice(MQL5_DATA_SCHEMAS)

    placeholders = [key for key in MQL5_DATA_FIELDS if f"{{{key}}}" in template]
    for field_key in placeholders:
        if MQL5_DATA_FIELDS[field_key]:
            template = template.replace(f"{{{field_key}}}", random.choice(MQL5_DATA_FIELDS[field_key]))
        else:
            template = template.replace(f"{{{field_key}}}", f"[data untuk {field_key}]")

    schema_desc = f"Hasilkan dalam format JSON dengan fields: {', '.join(chosen_schema['fields'])}. Type data: {chosen_schema['type']}"
    unique_id_example = str(uuid.uuid4())

    full_prompt = f"""Sebagai pakar MQL5/MetaTrader5, tolong:

{template}

{schema_desc}

Pastikan hasilnya adalah valid JSON, memiliki semua fields yang diminta dari skema di atas, dan berisi informasi detail dan akurat tentang MQL5/MetaTrader5.
Untuk field 'id', gunakan format UUID versi 4 (contoh: '{unique_id_example}').
Hasilkan HANYA JSON lengkap tanpa teks atau penjelasan tambahan di luar blok JSON itu sendiri. Jangan gunakan markdown (seperti ```json ... ```) di sekitar output JSON.
"""
    return full_prompt, chosen_schema['type']

def call_together_api_streaming(prompt: str, retries: int = 2) -> Optional[str]:
    global CLIENT, MODEL_NAME
    if not CLIENT:
        print("ERROR: Klien Together tidak diinisialisasi.")
        return None

    messages = [
        {"role": "system", "content": "You are an expert in MQL5/MetaTrader5 programming. Generate accurate and detailed JSON data based on the user's request. Output ONLY the JSON object. Do not use markdown."},
        {"role": "user", "content": prompt}
    ]

    for attempt in range(retries):
        try:
            print(f"    DEBUG: Attempting API call (attempt {attempt+1}/{retries}) with model {MODEL_NAME} (streaming)")
            response_stream = CLIENT.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=3500,
                temperature=0.5,
                top_p=0.9,
                stream=True
            )

            accumulated_content = []
            for chunk in response_stream:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        accumulated_content.append(delta_content)

            full_response_str = "".join(accumulated_content)
            if not full_response_str.strip():
                print(f"    WARNING: API call attempt {attempt+1} menghasilkan respons kosong.")
                if attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
                else:
                    return None

            print(f"    DEBUG: API call successful. Respons (awal): {full_response_str[:100]}...")
            return full_response_str

        except Exception as e:
            print(f"    ERROR: API call attempt {attempt+1} failed: {type(e).__name__} - {str(e)}")
            if "authentication" in str(e).lower() or "api key" in str(e).lower() or "401" in str(e):
                print("    CRITICAL ERROR: Masalah otentikasi dengan API Key. Hentikan proses.")
                raise ConnectionAbortedError(f"Authentication error with Together API: {e}") from e

            if attempt < retries - 1:
                print(f"    Retrying in {10 * (attempt + 1)} seconds...")
                time.sleep(10 * (attempt + 1))
            else:
                print("    CRITICAL ERROR: Semua percobaan API call gagal setelah retries.")
                return None
    return None

def extract_json_from_string(json_string: str) -> Optional[Dict[str, Any]]:
    if not json_string or not isinstance(json_string, str):
        print("DEBUG: extract_json - Input string kosong atau bukan string.")
        return None

    text_content = json_string.strip()

    json_start_index = text_content.find('{')
    json_end_index = text_content.rfind('}')

    if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
        potential_json_str = text_content[json_start_index : json_end_index + 1]
        try:
            parsed_json = json.loads(potential_json_str)
            if 'id' not in parsed_json or not parsed_json.get('id'):
                parsed_json['id'] = str(uuid.uuid4())
                print("DEBUG: extract_json - Menambahkan UUID karena 'id' tidak ada atau kosong di JSON yang diparsing.")
            return parsed_json
        except json.JSONDecodeError as e:
            print(f"DEBUG: extract_json - Gagal decode blok JSON yang diekstrak: {e}")
            print(f"DEBUG: extract_json - String yang dicoba (blok): {potential_json_str[:200]}...")
            try:
                parsed_json_full = json.loads(text_content)
                if 'id' not in parsed_json_full or not parsed_json_full.get('id'):
                    parsed_json_full['id'] = str(uuid.uuid4())
                return parsed_json_full
            except json.JSONDecodeError:
                print(f"DEBUG: extract_json - Gagal parse seluruh string juga. String: {text_content[:200]}...")
                return None
    else:
        print(f"DEBUG: extract_json - Tidak menemukan blok JSON ('{{'...'}}') yang valid dalam string. String: {text_content[:200]}...")
        try:
            parsed_json_direct = json.loads(text_content)
            if 'id' not in parsed_json_direct or not parsed_json_direct.get('id'):
                parsed_json_direct['id'] = str(uuid.uuid4())
            return parsed_json_direct
        except json.JSONDecodeError:
            print(f"DEBUG: extract_json - Gagal parse langsung seluruh string.")
            return None

def validate_data(data: Dict[str, Any], expected_schema_type: str) -> bool:
    if not data or not isinstance(data, dict):
        print(f"DEBUG: validate_data - Data kosong atau bukan dictionary.")
        return False

    current_schema = next((s for s in MQL5_DATA_SCHEMAS if s['type'] == expected_schema_type), None)
    if not current_schema:
        print(f"DEBUG: validate_data - Tidak ditemukan skema untuk tipe yang diharapkan: {expected_schema_type}")
        return False

    if 'id' not in data or not data['id']:
        print(f"DEBUG: validate_data - Data tidak valid: field 'id' hilang atau kosong. Skema: {current_schema['type']}")
        return False

    required_fields = current_schema['fields']
    present_fields_count = sum(1 for field in required_fields if field in data and data[field] is not None)
    threshold_percentage = 0.6
    min_fields_present = max(1 if len(required_fields) <=2 else 2, int(len(required_fields) * threshold_percentage))

    if present_fields_count < min_fields_present:
        print(f"DEBUG: validate_data - Data tidak valid: Kurang dari {min_fields_present} field yang ada untuk skema {current_schema['type']}. Ditemukan: {present_fields_count} dari {len(required_fields)}.")
        return False

    print(f"DEBUG: validate_data - Data valid untuk skema '{expected_schema_type}'.")
    return True

def generate_single_item() -> Optional[Dict[str, Any]]:
    prompt, expected_schema_type = get_prompt_variation()
    print(f"  DEBUG: generate_single_item - Menghasilkan item dengan prompt untuk skema: {expected_schema_type}")

    full_response_string = call_together_api_streaming(prompt)

    if not full_response_string:
        print(f"  ERROR: generate_single_item - Gagal mendapatkan respons string dari API.")
        return None

    extracted_data = extract_json_from_string(full_response_string)
    if extracted_data and validate_data(extracted_data, expected_schema_type):
        if 'type' not in extracted_data:
            extracted_data['type'] = expected_schema_type
        elif extracted_data['type'] != expected_schema_type:
            print(f"  WARNING: generate_single_item - Tipe JSON ({extracted_data['type']}) beda dari harapan ({expected_schema_type}). Menggunakan tipe harapan.")
            extracted_data['type'] = expected_schema_type

        print(f"  INFO: generate_single_item - Item berhasil dibuat dan divalidasi (ID: {extracted_data.get('id', 'N/A')}).")
        return extracted_data
    else:
        print(f"  ERROR: generate_single_item - Item gagal diekstrak atau divalidasi dari string: '{full_response_string[:100]}...'")
        if extracted_data:
             print(f"    DEBUG: Data yang diekstrak (sebelum validasi gagal): {str(extracted_data)[:200]}")
        return None

def generate_data_worker(worker_id: int, total_items_for_worker: int, _: int) -> List[Dict[str, Any]]:
    worker_output_dir = Path(OUTPUT_DIR) / f"worker_{worker_id}"
    worker_output_dir.mkdir(exist_ok=True, parents=True)

    generated_items_list = []
    items_processed_this_session = 0
    session_num = 0

    print(f"INFO: Worker {worker_id}: Memulai. Target: {total_items_for_worker} item.")

    while len(generated_items_list) < total_items_for_worker:
        session_num += 1
        print(f"  INFO: Worker {worker_id}, Sesi {session_num}, Item ke-{len(generated_items_list) + 1}:")
        try:
            item = generate_single_item()
            if item:
                generated_items_list.append(item)
                items_processed_this_session +=1

                if items_processed_this_session % BATCH_SIZE == 0 or len(generated_items_list) == total_items_for_worker :
                    timestamp = int(time.time())
                    start_index_for_save = max(0, len(generated_items_list) - items_processed_this_session)
                    items_to_save_now = generated_items_list[start_index_for_save:]

                    if items_to_save_now:
                        filename = worker_output_dir / f"minibatch_{session_num}_{timestamp}.json"
                        try:
                            with open(filename, 'w', encoding='utf-8') as f:
                                json.dump(items_to_save_now, f, indent=2, ensure_ascii=False)
                            print(f"INFO: Worker {worker_id}: Menyimpan {len(items_to_save_now)} item ke {filename}.")
                            items_processed_this_session = 0
                        except Exception as e_save:
                            print(f"ERROR: Worker {worker_id} - Gagal menyimpan minibatch ke file: {e_save}")
            else:
                print(f"  WARNING: Worker {worker_id} - Gagal menghasilkan item valid, mencoba item berikutnya.")

            time.sleep(2.0 + random.uniform(0,1))

        except ConnectionAbortedError as e_auth:
            print(f"  CRITICAL ERROR in Worker {worker_id}: {e_auth}. Menghentikan worker ini.")
            break
        except Exception as e_item_loop:
            print(f"  ERROR: Worker {worker_id} - Exception di loop utama item: {e_item_loop}. Melanjutkan setelah jeda.")
            time.sleep(5)

        if len(generated_items_list) >= total_items_for_worker:
            print(f"INFO: Worker {worker_id}: Telah mencapai target {total_items_for_worker} item.")
            break

    if items_processed_this_session > 0:
        timestamp = int(time.time())
        start_index_for_final_save = max(0, len(generated_items_list) - items_processed_this_session)
        final_items_to_save = generated_items_list[start_index_for_final_save:]
        if final_items_to_save:
            filename = worker_output_dir / f"minibatch_final_{timestamp}.json"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(final_items_to_save, f, indent=2, ensure_ascii=False)
                print(f"INFO: Worker {worker_id}: Menyimpan sisa {len(final_items_to_save)} item ke {filename}.")
            except Exception as e_save_final_worker:
                print(f"ERROR: Worker {worker_id} - Gagal menyimpan sisa item: {e_save_final_worker}")

    print(f"INFO: Worker {worker_id}: Selesai. Total item dihasilkan oleh worker ini: {len(generated_items_list)}")
    return generated_items_list

def merge_data_files():
    print("\n" + "="*25 + " Menggabungkan File Data " + "="*25)
    all_data_from_files = []
    output_path = Path(OUTPUT_DIR)
    json_files_found = list(output_path.glob("worker_*/*.json"))

    if not json_files_found:
        print("INFO: Tidak ada file .json yang ditemukan untuk digabungkan.")
        return []

    print(f"INFO: Ditemukan {len(json_files_found)} file JSON untuk digabungkan.")
    for file_path in tqdm(json_files_found, desc="Membaca file JSON worker"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip(): continue
                batch_data = json.loads(content)
                if isinstance(batch_data, list):
                    all_data_from_files.extend(batch_data)
                elif isinstance(batch_data, dict):
                    all_data_from_files.append(batch_data)
        except Exception as e:
            print(f"ERROR: Gagal membaca/decode file {file_path}: {e}. Dilewati.")

    if not all_data_from_files:
        print("INFO: Tidak ada data yang berhasil dibaca dari file-file JSON worker.")
        return []

    print(f"INFO: Total data dari file sebelum deduplikasi: {len(all_data_from_files)}")
    unique_data = {}
    for item in all_data_from_files:
        if isinstance(item, dict) and 'id' in item and item['id']:
            unique_data[item['id']] = item

    final_data_list = list(unique_data.values())
    print(f"INFO: Total data unik setelah deduplikasi: {len(final_data_list)}")
    final_output_path = output_path / "mql5_dataset_final_together_lib.json"
    try:
        with open(final_output_path, 'w', encoding='utf-8') as f:
            json.dump(final_data_list, f, indent=2, ensure_ascii=False)
        print(f"INFO: Dataset final ({len(final_data_list)} item) disimpan ke: {final_output_path}")
    except Exception as e_save_final:
        print(f"ERROR: Gagal menyimpan dataset final: {e_save_final}")

    print("="*25 + " Penggabungan Selesai " + "="*25 + "\n")
    return final_data_list

def main():
    start_time = time.time()
    print("=" * 80)
    print("Self-Supervised Generative Data Farming (Together Library, Streaming)")
    print(f"Menggunakan Model: {MODEL_NAME}")
    print(f"PERINGATAN: Kunci API ('{API_KEY[:4]}...{API_KEY[-4:]}') di-hardcode.")
    print("-" * 80)

    print(f"INFO: Target Dataset: {DATASET_SIZE} item data")
    print(f"INFO: Direktori Output: {OUTPUT_DIR}")
    print(f"INFO: Ukuran Mini-Batch Simpan per Worker: {BATCH_SIZE}")
    print(f"INFO: Jumlah Worker: {NUM_WORKERS}")
    print("-" * 80)

    all_generated_data_accumulated = []

    if NUM_WORKERS > 1:
        items_per_worker = DATASET_SIZE // NUM_WORKERS
        remaining_items = DATASET_SIZE % NUM_WORKERS

        worker_tasks_args = []
        for i in range(NUM_WORKERS):
            num_items_for_this_worker = items_per_worker + (1 if i < remaining_items else 0)
            if num_items_for_this_worker > 0:
                worker_tasks_args.append((i + 1, num_items_for_this_worker, BATCH_SIZE))

        if not worker_tasks_args:
            print("INFO: Tidak ada item yang perlu dihasilkan.")
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
                future_to_worker_id = {executor.submit(generate_data_worker, *task_args): task_args[0] for task_args in worker_tasks_args}

                for future in tqdm(concurrent.futures.as_completed(future_to_worker_id), total=len(future_to_worker_id), desc="Progress Worker"):
                    worker_id = future_to_worker_id[future]
                    try:
                        worker_results = future.result()
                        all_generated_data_accumulated.extend(worker_results)
                        print(f"INFO: Worker {worker_id} selesai, mengembalikan {len(worker_results)} item.")
                    except Exception as exc:
                        print(f'ERROR: Worker {worker_id} menghasilkan exception tidak tertangani: {exc}')
    else:
        if DATASET_SIZE > 0:
            print("INFO: Menjalankan dalam mode single worker.")
            try:
                worker_results = generate_data_worker(1, DATASET_SIZE, BATCH_SIZE)
                all_generated_data_accumulated.extend(worker_results)
            except Exception as exc_single_worker:
                 print(f'ERROR: Single worker menghasilkan exception tidak tertangani: {exc_single_worker}')
        else:
            print("INFO: DATASET_SIZE adalah 0, tidak ada data yang akan dihasilkan.")

    print(f"\nINFO: Semua proses generasi data (jika ada) telah selesai.")

    if DATASET_SIZE > 0 :
        final_merged_data = merge_data_files()
        print(f"INFO: Total item unik setelah penggabungan akhir: {len(final_merged_data)}")
    else:
        print("INFO: Proses penggabungan dilewati karena tidak ada target data.")

    end_time = time.time()
    total_time = end_time - start_time
    print(f"\nProses data farming selesai dalam {total_time:.2f} detik.")
    print(f"Data (jika ada) tersimpan di direktori: {Path(OUTPUT_DIR).resolve()}")

if __name__ == "__main__":
    main()
