import struct
import serial
import time
import os

# --- PARAMÈTRES MATÉRIELS ---
FLASH_PAGE_SIZE = 2048   # 2KB sur STM32G4
FRAME_SIZE = 512         # Taille bloc de données par trame
# Zone de nettoyage fixée à 64 Ko (32 pages)
CLEAN_ZONE_MAX = 65536  

def generate_frame(cmd, addr, data, length=FRAME_SIZE):
    if len(data) < FRAME_SIZE:
        data = data.ljust(FRAME_SIZE, b'\x00')
    else:
        data = data[:FRAME_SIZE]
    
    crc = 0
    for b in data:
        crc ^= b
        
    return struct.pack('<BIH512sB', cmd, addr, length, data, crc)

def calculate_local_checksum(file_path):
    checksum = 0
    with open(file_path, 'rb') as f:
        content = f.read()
        for byte in content:
            checksum ^= byte
    return checksum

def write_file_to_flash(file_path, port_com, start_addr):
    if not os.path.exists(file_path):
        print(f"Erreur : Fichier '{file_path}' introuvable.")
        return

    file_size = os.path.getsize(file_path)
    num_blocks = (file_size + (FRAME_SIZE - 1)) // FRAME_SIZE
    
    # On efface au minimum 64 Ko, ou plus si le fichier dépasse cette taille
    max_size_to_erase = max(file_size, CLEAN_ZONE_MAX)
    num_pages_to_erase = (max_size_to_erase + (FLASH_PAGE_SIZE - 1)) // FLASH_PAGE_SIZE

    print(f"--- Démarrage du Flash Bridge (Clean 64KB) ---")
    print(f"Fichier : {file_path} ({file_size} octets)")
    print(f"Zone d'effacement : {max_size_to_erase // 1024} KB")

    try:
        ser = serial.Serial(port_com, 115200, timeout=2)
        
        # --- PHASE 0 : EFFACEMENT DE SÉCURITÉ ---
        print(f"\nNettoyage de la Flash ({num_pages_to_erase} pages)...")
        for i in range(num_pages_to_erase):
            addr_to_erase = start_addr + (i * FLASH_PAGE_SIZE)
            print(f"  Effacement @ {hex(addr_to_erase)} ({i+1}/{num_pages_to_erase})", end='\r')
            ser.write(generate_frame(0x02, addr_to_erase, b''))
            ser.flush()
            time.sleep(0.06) 
        print("\nMémoire prête (vierge de 0x8008000 à " + hex(start_addr + max_size_to_erase) + ").")

        # --- PHASE 1 : ÉCRITURE ---
        print("\nÉcriture du fichier...")
        with open(file_path, 'rb') as f:
            for i in range(num_blocks):
                current_addr = start_addr + (i * FRAME_SIZE)
                data_block = f.read(FRAME_SIZE)
                
                print(f"  > Bloc {i+1}/{num_blocks} @ {hex(current_addr)}", end='\r')
                ser.write(generate_frame(0x01, current_addr, data_block))
                ser.flush()
                time.sleep(0.08)

        print("\n\n--- Transfert terminé ---")

        # --- PHASE 2 : VÉRIFICATION ---
        if file_size <= 65535:
            print("Vérification Checksum...")
            pc_checksum = calculate_local_checksum(file_path)
            
            verify_frame = generate_frame(0x04, start_addr, b'', length=file_size)
            ser.write(verify_frame)
            ser.flush()

            slave_checksum_raw = ser.read(1)
            if slave_checksum_raw:
                slave_checksum = struct.unpack('B', slave_checksum_raw)[0]
                print(f"Checksum PC    : {hex(pc_checksum)}")
                print(f"Checksum Slave : {hex(slave_checksum)}")
                if pc_checksum == slave_checksum:
                    print("\n✅ RÉSULTAT : Succès. Zone nettoyée et fichier vérifié.")
                else:
                    print("\n❌ RÉSULTAT : Erreur Checksum.")
            else:
                print("\n⚠️ Pas de réponse du Slave.")

        ser.close()

    except Exception as e:
        print(f"\nErreur : {e}")

if __name__ == "__main__":
    write_file_to_flash("test900.bin", "COM9", 0x08008000)