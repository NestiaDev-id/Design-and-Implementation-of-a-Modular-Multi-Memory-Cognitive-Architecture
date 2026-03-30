import os
from transformers import AutoTokenizer

# Path model Anda (gunakan r"" agar backslash aman)
MODEL_PATH = r"E:\models\qwen\qwen2.5-1.5b-instruct"

print(f"--- DIAGNOSTIC START ---")
print(f"Testing Path: {MODEL_PATH}")

# 1. Cek apakah folder ada
if not os.path.exists(MODEL_PATH):
    print("FATAL: Folder path does NOT exist!")
    exit()
else:
    print("STATUS: Folder exists.")

# 2. List isi folder untuk memastikan file tokenizer ada
print("\nFiles in folder:")
files = os.listdir(MODEL_PATH)
for f in files:
    print(f" - {f}")

if "tokenizer_config.json" not in files:
    print("\n[WARNING] 'tokenizer_config.json' NOT FOUND! This causes errors.")
if "tokenizer.json" not in files:
    print("\n[WARNING] 'tokenizer.json' NOT FOUND! This might cause errors.")

# 3. Coba load Tokenizer saja
print("\nAttempting to load Tokenizer...")
try:
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH, 
        trust_remote_code=True,
        local_files_only=True # Memaksa baca lokal
    )
    print("SUCCESS: Tokenizer loaded successfully!")
except Exception as e:
    print(f"FAIL: Error loading tokenizer: {e}")
    # Print detail type error
    import traceback
    traceback.print_exc()

print("--- DIAGNOSTIC END ---")