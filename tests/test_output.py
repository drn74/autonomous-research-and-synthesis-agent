import os
from pathlib import Path

def test_final_guide():
    output_dir = Path("output")
    files = list(output_dir.glob("FINAL_GUIDE_*.md"))
    
    if not files:
        print("❌ ERRORE: Nessun file FINAL_GUIDE trovato nella cartella output/")
        return
        
    for file_path in files:
        size = os.path.getsize(file_path)
        if size > 1000:
            print(f"✅ SUCCESSO: File '{file_path.name}' generato correttamente (Dimensione: {size / 1024:.2f} KB).")
            with open(file_path, 'r', encoding='utf-8') as f:
                head = f.read(500)
                print("\n--- Anteprima del Frontmatter e Inizio Documento ---")
                print(head)
                print("----------------------------------------------------\n")
        else:
            print(f"⚠️ ATTENZIONE: Il file '{file_path.name}' esiste ma sembra troppo piccolo o vuoto ({size} bytes).")

if __name__ == "__main__":
    test_final_guide()
