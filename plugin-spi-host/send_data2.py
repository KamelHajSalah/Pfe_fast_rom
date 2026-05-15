#!/usr/bin/env python3
"""
Script de transmission UART pour NUCLEO-F767ZI
Envoie un fichier binaire RANDOM par paquets de 512 octets avec CRC XOR
"""

import struct
import serial
import time
import os
import sys
from pathlib import Path

# --- PARAMÈTRES ---
PORT_COM = 'COM9'  # À adapter selon votre gestionnaire de périphériques
BAUD_RATE = 115200
FRAME_SIZE = 512
FRAME_TOTAL_SIZE = 520  # 1 (cmd) + 4 (addr) + 2 (len) + 512 (data) + 1 (crc)
FILE_NAME = "test_fastrom.bin"
DELAY_BETWEEN_FRAMES = 0.05  # 50ms entre les trames

# --- STATS ---
class TransferStats:
    def __init__(self):
        self.total_frames = 0
        self.frames_sent = 0
        self.bytes_sent = 0
        self.start_time = 0
        self.end_time = 0
        self.errors = 0
    
    def print_summary(self):
        elapsed = self.end_time - self.start_time
        throughput = (self.bytes_sent / elapsed) if elapsed > 0 else 0
        print(f"\n{'='*50}")
        print(f"RÉSUMÉ DU TRANSFERT")
        print(f"{'='*50}")
        print(f"Trames envoyées: {self.frames_sent}/{self.total_frames}")
        print(f"Octets envoyés: {self.bytes_sent}")
        print(f"Temps total: {elapsed:.2f}s")
        print(f"Débit: {throughput/1024:.2f} KB/s")
        print(f"Erreurs: {self.errors}")
        print(f"{'='*50}\n")

stats = TransferStats()

def calculate_crc(data):
    """Calcule le CRC XOR du bloc de données."""
    crc = 0
    for byte in data:
        crc ^= byte
    return crc

def generate_frame(cmd, addr, data):
    """Génère une trame complète au format binaire."""
    # Correction syntaxe padding: b'\x00' (1 seul backslash)
    data_padded = data.ljust(FRAME_SIZE, b'\x00')[:FRAME_SIZE]
    
    # Calcul du CRC XOR
    crc = calculate_crc(data_padded)
    
    # Packing: cmd(B), addr(I), len(H), data(512s), crc(B)
    frame = struct.pack(
        f'<BIH{FRAME_SIZE}sB',
        cmd, addr, FRAME_SIZE, data_padded, crc
    )
    return frame

def generate_test_file(size_kb=4):
    """Génère un fichier binaire avec des données ALÉATOIRES."""
    print(f"[*] Génération de données aléatoires ({size_kb} KB)...")
    # Utilisation de os.urandom pour du contenu random à chaque test
    data = os.urandom(size_kb * 1024)
    with open(FILE_NAME, 'wb') as f:
        f.write(data)
    print(f"[+] Fichier généré: {FILE_NAME} ({len(data)} octets)")
    return len(data)

def stream_to_nucleo():
    """Envoie le fichier par trames UART à la NUCLEO."""
    file_size = generate_test_file()
    stats.total_frames = (file_size + FRAME_SIZE - 1) // FRAME_SIZE
    stats.start_time = time.time()
    
    try:
        print(f"\n[*] Connexion à {PORT_COM} @ {BAUD_RATE} baud...")
        ser = serial.Serial(PORT_COM, BAUD_RATE, timeout=2)
        print(f"[+] Connexion établie!\n")
        
        with open(FILE_NAME, 'rb') as f:
            addr = 0x08008000
            frame_num = 0
            
            while True:
                data_block = f.read(FRAME_SIZE)
                if not data_block:
                    break
                
                frame_num += 1
                frame = generate_frame(0x01, addr, data_block)
                
                try:
                    bytes_written = ser.write(frame)
                    stats.frames_sent += 1
                    stats.bytes_sent += bytes_written
                    
                    progress = (frame_num / stats.total_frames) * 100
                    # Correction syntaxe padding dans le print également
                    current_crc = calculate_crc(data_block.ljust(FRAME_SIZE, b'\x00'))
                    print(f"[{frame_num:3d}/{stats.total_frames}] Trame @ 0x{addr:08X} | "
                          f"Progression: {progress:5.1f}% | "
                          f"CRC: 0x{current_crc:02X}", end='\r')
                    
                    addr += FRAME_SIZE
                    time.sleep(DELAY_BETWEEN_FRAMES)
                    
                except Exception as e:
                    stats.errors += 1
                    print(f"\n[!] Erreur lors de l'envoi de la trame {frame_num}: {e}")
        
        print(f"\n[+] Transfert terminé!")
        time.sleep(0.5)
        ser.close()
        
    except serial.SerialException as e:
        print(f"[!] Erreur de port série: {e}")
        stats.errors += 1
    finally:
        stats.end_time = time.time()
        stats.print_summary()

def list_available_ports():
    """Liste les ports COM disponibles."""
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        if ports:
            print("\n[*] Ports COM disponibles:")
            for port, desc, hwid in ports:
                print(f"    {port}: {desc}")
        else:
            print("\n[!] Aucun port COM trouvé")
    except:
        pass

def main():
    """Fonction principale."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║   NUCLEO-F767ZI - RANDOM File Transfer Tool                    ║
╚════════════════════════════════════════════════════════════════╝
    """)
    list_available_ports()
    print(f"\n[?] Port configuré: {PORT_COM}")
    response = input("[?] Procéder au transfert RANDOM? (o/n): ").lower()
    
    if response in ['o', 'yes', 'y']:
        stream_to_nucleo()
    else:
        print("[*] Annulation")

if __name__ == "__main__":
    main()