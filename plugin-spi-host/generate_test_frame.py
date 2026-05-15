import os

def generate_test_file(filename, size_kb):
    size_bytes = int(size_kb * 1024)
    data = bytearray()

    print(f"Génération de {filename} ({size_kb} KB)...")

    for i in range(size_bytes):
        # Motif de base (0 à 255)
        data.append(i % 256)

    # Marquage des blocs pour le débug
    # On écrit 'BL_XX' (4 octets) au début de chaque bloc de 512 octets
    for block_idx in range(0, size_bytes, 512):
        num_bloc = block_idx // 512
        marker = f"BL_{num_bloc:02d}".encode('ascii')
        data[block_idx : block_idx + len(marker)] = marker

    with open(filename, "wb") as f:
        f.write(data)
    
    print(f"Succès : {filename} créé ({len(data)} octets).")

if __name__ == "__main__":
    name = input("Nom du fichier à générer (ex: test.bin) : ")
    size = float(input("Taille du fichier en KB (ex: 3.5) : "))
    generate_test_file(name, size)