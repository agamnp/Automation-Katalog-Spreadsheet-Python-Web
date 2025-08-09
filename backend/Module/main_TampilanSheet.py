import gspread
from google.oauth2.service_account import Credentials
import time
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from gspread.utils import a1_range_to_grid_range, rowcol_to_a1
import re
import logging



def safe_logger(msg, logger=print):
    try:
        logger(msg)
    except UnicodeEncodeError:
        logger(msg.encode('ascii', errors='ignore').decode())  # hilangkan emoji


#pemangilan menu utama
def main_tampilan_sheet(logger=print):
 safe_logger("✅ Menjalankan tampilan sheet...", logger)

# Konfigurasi logging
# logging.basicConfig(
#     filename='log_proses_katalog.txt',
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S',
#     encoding='utf-8'  # ✅ Tambahkan ini
# )

# Setup autentikasi
# Load environment variables dari .env file
def setup_google_sheets():
    load_dotenv()
    creds_path = os.getenv("GOOGLE_CREDS_PATH")
    if not creds_path or not os.path.exists(creds_path):
        raise FileNotFoundError(f"File credentials.json tidak ditemukan di path: {creds_path}")

    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(creds)

# Autofill kolom
def autofill_column_general(sheet, col_letter, start_row, value_or_formula, mode='static', start_number=1,logger=print):
    total_rows = len(sheet.col_values(3))  # Kolom C sebagai acuan
    last_row = max(total_rows, start_row)
    num_rows = last_row - start_row + 1
    autofill_range = f'{col_letter}{start_row}:{col_letter}{last_row}'
    if mode == 'number':
        values = [[start_number + i] for i in range(num_rows)]
    elif mode == 'dynamic':
        values = [[value_or_formula.format(row=row)] for row in range(start_row, last_row + 1)]
    else:
        values = [[value_or_formula]] * num_rows
    try:
        sheet.update(range_name=autofill_range, values=values, value_input_option='USER_ENTERED')
    except Exception as e:
       
         safe_logger(f"⚠️ Gagal mengisi kolom {col_letter}: {e}", logger)
    time.sleep(1)  # Hindari over-quota    
    
# Tambahkan rumus rekap
def add_formulas(sheet,retries=3,logger=print):
    max_rows = len(sheet.col_values(3))
    max_rows = max(max_rows, 10)
    for attempt in range(retries):
        try:
            sheet.spreadsheet.values_batch_update(
                {   "valueInputOption": "USER_ENTERED",
                    "data": [
                        {"range": f"{sheet.title}!G2", "values": [[f'=COUNTA(C10:C{max_rows})']]},
                        {"range": f"{sheet.title}!G3", "values": [[f'=SUM(Y10:Y{max_rows})']]},
                        {"range": f"{sheet.title}!G4", "values": [[f'=AVERAGE(Y10:Y{max_rows})']]},
                        {"range": f"{sheet.title}!J2", "values": [[f'=COUNTA(Z10:Z{max_rows})']]},
                        {"range": f"{sheet.title}!J3", "values": [[f'=SUM(Z10:Z{max_rows})']]},
                        {"range": f"{sheet.title}!J4", "values": [[f'=SUM(AA10:AA{max_rows})']]},
                        {"range": f"{sheet.title}!J5", "values": [[f'=AVERAGEIF(Z10:Z{max_rows}, ">0", AA10:AA{max_rows})']]}
                        ]})
            break  # keluar loop jika berhasil
        except Exception as e:
            safe_logger(f"✅ Gagal menambahkan rumus rekap (Attempt {attempt + 1}): {e}", logger)
            time.sleep(5)  # tunggu sebelum coba lagi
    else:
            safe_logger("❌ Gagal menambahkan rumus rekap setelah beberapa percobaan", logger)

#tambahkan filter
def ensure_filter_and_freeze(sheet,logger=print):
    try:
        # Cari jumlah kolom dari baris header (baris 9)
        header_values = sheet.row_values(9)
        last_col_index = len(header_values)
        if last_col_index == 0:
         return
       # Konversi index ke notasi kolom (misal 27 → 'AA')
        last_col_letter = gspread.utils.rowcol_to_a1(1, last_col_index).rstrip('1')
        filter_range = f"A9:{last_col_letter}9"
        # Set filter dinamis
        sheet.set_basic_filter(filter_range)
        safe_logger(f"🔍 Filter     : {filter_range}", logger)
                       
        # Set freeze ke baris 9 dan kolom 10 (kolom J)
        sheet.freeze(rows=9, cols=10)
        
        
        safe_logger(f"❄️  Freeze     : Baris 9, Kolom J", logger)
        
    except Exception as e:
        safe_logger(f"⚠️  Gagal mengatur filter/freeze: {e}")

#nomor urut di spreadsheet
def rename_sheets_from_index(spreadsheet, sheet_order_start, zero_pad=3):
    """
    Rename semua sheet mulai dari urutan ke-N (bukan index ke-N).
    Penomoran juga dimulai dari N.
    """
    sheet_index_start = sheet_order_start - 1  # karena list index mulai dari 0
    sheets = spreadsheet.worksheets()[sheet_index_start:]
    for i, sheet in enumerate(sheets, start=sheet_order_start):
        sheet_number = f"{i:0{zero_pad}}"  # Contoh: 070, 071, ...
        rename_sheet_with_number(spreadsheet, sheet, sheet_number)

# Rename sheet individual
def rename_sheet_with_number(spreadsheet, sheet, sheet_number,logger=print):
    old_title = sheet.title
    parts = old_title.split('.', 1)
    base_title = parts[1].strip() if len(parts) > 1 and parts[0].isdigit() else old_title
    base_title = base_title.replace('.', '')  # ganti titik jadi strip
    new_title = f"{sheet_number}.{base_title}"
    if new_title != old_title:
        try:
            sheet.update_title(new_title)
            safe_logger(f"✅ Rename     : '{old_title}' → '{new_title}'", logger)
            sheet = spreadsheet.worksheet(new_title)
        except Exception as e:
            safe_logger(f"⚠️ Gagal mengganti nama sheet '{old_title}': {e}", logger)
            return sheet, old_title
    return sheet, new_title

# === Rename Named Range ===
def create_named_range_from_sheet_name(spreadsheet_id, sheet, header_row=9, col_start='A', col_end='Z', logger=print):
    """
    Membuat named range berdasarkan nama sheet (dibersihkan jadi hanya huruf),
    dan range dari baris header sampai baris terakhir data aktual.
    """
    sheet_name = sheet.title
    clean_name = re.sub(r'[^a-zA-Z]', '', sheet_name)
    if not clean_name:
        safe_logger(f"✅ Nama sheet '{sheet_name}' kosong setelah dibersihkan. Skip.", logger)
       
        return

    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_CREDS_PATH"),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = next((s['properties']['sheetId'] for s in spreadsheet['sheets']
                     if s['properties']['title'] == sheet_name), None)
    if sheet_id is None:
        safe_logger(f"⚠️ Sheet ID untuk '{sheet_name}' tidak ditemukan.", logger)

        return

    gc = setup_google_sheets()
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(sheet_name)

    col_index = ord(col_start.upper()) - 64
    col_values = ws.col_values(col_index)
    last_row = len(col_values)
    if last_row < header_row:
        safe_logger(f"⚠️ Sheet '{sheet_name}' tidak punya data setelah baris header.", logger)
        return

    # Clean named range name
    clean_name = re.sub(r'[^a-zA-Z]', '', sheet_name)
    if not clean_name:
        safe_logger(f"⚠️ Nama sheet '{sheet_name}' kosong setelah dibersihkan.", logger)
        return

    # Range tanpa sheet name untuk konversi
    a1_notation_only = f"{col_start}{header_row}:{col_end}{last_row}"
    range_a1 = f"'{sheet_name}'!{a1_notation_only}"
    grid_range = a1_range_to_grid_range(a1_notation_only, sheet_id)

    # Hapus existing range dengan nama yang sama
    existing_ranges = spreadsheet.get("namedRanges", [])
    existing_id = next((r["namedRangeId"] for r in existing_ranges if r["name"] == clean_name), None)

    requests = []
    if existing_id:
            requests.append({"deleteNamedRange": {"namedRangeId": existing_id}})
    requests.append({
            "addNamedRange": {
                "namedRange": {
                    "name": clean_name,
                    "range": grid_range
                }
            }
        })

    service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

    
    safe_logger( f"🏷️ Named range '{clean_name}' Range → {range_a1}", logger)
    
# Fungsi utama
def main_tampilan_sheet(logger=print):
 try:
    safe_logger("✅ Menjalankan tampilan sheet...", logger)
    spreadsheet_name = 'Tes Katalog Automasi'
    excluded_sheets = ['Form Pengadaan', 'Hasil Seleksi', 'Referensi']
    Sheet_mulai = 1
    START_SHEET_INDEX = Sheet_mulai + 2
    START_ROW = 10
    gc = setup_google_sheets()
    sh = gc.open(spreadsheet_name)
    worksheets = sh.worksheets()

  
    safe_logger(f"🔄 Mulai proses semua sheet...\n", logger)
   
    
    sheet_number = Sheet_mulai if Sheet_mulai > 0 else 1


    for i, sheet in enumerate(worksheets[START_SHEET_INDEX:], start=START_SHEET_INDEX):
        if sheet.title in excluded_sheets:
            
            
            safe_logger(f"➡️ Sheet '{sheet.title}' dilewati.", logger)
            
            continue

        # Rename sheet dulu agar nama yang dipakai konsisten
        sheet, new_title = rename_sheet_with_number(sh, sheet, sheet_number)
        sheet_number += 1

       
        safe_logger( f"✅ Memproses Sheet: {new_title}", logger)
        


        # Nomor urut di kolom A
        autofill_column_general(sheet, 'A', START_ROW, '', mode='number')
        
        safe_logger( "✅ Nomor urut di kolom A selesai", logger)
        

        autofill_column_general(sheet, 'B', START_ROW,'=HYPERLINK("https://mocostore.moco.co.id/catalog/"&AB{row};"Klik Disini")',mode='dynamic')
       
        safe_logger( "✅ Kolom B diisi hyperlink", logger)
        
        autofill_column_general(sheet, 'AA', START_ROW, '=Y{row}*Z{row}', mode='dynamic')
       
        safe_logger(f"✅ Kolom AA dihitung dari Y*Z", logger)
        
        # Tambah filter dan freeze jika belum
        ensure_filter_and_freeze(sheet,logger=print)
        # Tambahkan rumus rekap
        add_formulas(sheet,logger=print)

        # ✅ Tambah named range dari nama sheet (bersih)
        create_named_range_from_sheet_name(
        spreadsheet_id=sh.id,
        sheet=sheet,
        header_row=10,
        col_start='J',
        col_end='J'
        )
        safe_logger(f"✅ Proses sheet '{new_title}' selesai.", logger)
        safe_logger("", logger)

    safe_logger("🎉 Semua sheet selesai diproses!", logger)
 except Exception as e:
        safe_logger(f"❌ Terjadi error saat proses utama: {e}", logger)  

if __name__ == '__main__':
    main_tampilan_sheet(logger=print)