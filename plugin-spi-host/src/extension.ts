import * as vscode from 'vscode';
import { SerialPort } from 'serialport';
import * as fs from 'fs';
import * as path from 'path';

// --- PARAMÈTRES MATÉRIELS (Basés sur le protocole FastROM) ---
const FLASH_PAGE_SIZE = 2048; //
const FRAME_SIZE = 512;       //
const CLEAN_ZONE_MAX = 65536; //
const START_ADDR = 0x08008000;

function generateFrame(cmd: number, addr: number, data: Buffer): Buffer {
    const frame = Buffer.alloc(520);
    frame.writeUInt8(cmd, 0);
    frame.writeUInt32LE(addr, 1);
    frame.writeUInt16LE(FRAME_SIZE, 5);
    const dataToCopy = data.length > FRAME_SIZE ? data.subarray(0, FRAME_SIZE) : data;
    dataToCopy.copy(frame, 7);

    let crc = 0;
    for (let i = 0; i < FRAME_SIZE; i++) {
        crc ^= frame[7 + i];
    }
    frame.writeUInt8(crc, 519);
    return frame;
}

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand('plugin-spi-host.flash', async (uri: vscode.Uri) => {
        
        // --- ÉTAPE 1 : CHOIX DU PORT COM (AVANT TOUT) ---
        const ports = await SerialPort.list();
        if (ports.length === 0) {
            vscode.window.showErrorMessage("Aucun port série détecté. Vérifiez le branchement du ST-LINK V3.");
            return;
        }

        const selectedPort = await vscode.window.showQuickPick(
            ports.map(p => ({ label: p.path, description: p.manufacturer || "Périphérique série" })),
            { 
                placeHolder: "1. Sélectionnez le port COM de l'interface SPI Host",
                ignoreFocusOut: true 
            }
        );

        if (!selectedPort) { return; } // Annulation si l'utilisateur appuie sur Echap

        // --- ÉTAPE 2 : CHOIX DU FICHIER ---
        let filePath = uri ? uri.fsPath : undefined;
        if (!filePath) {
            const files = await vscode.window.showOpenDialog({
                canSelectMany: false,
                filters: { 'Binary files': ['bin'] },
                title: "2. Sélectionnez le fichier firmware (.bin) à flasher"
            });
            if (!files) { return; }
            filePath = files[0].fsPath;
        }

        // --- ÉTAPE 3 : PROCESSUS DE FLASHAGE ---
        const port = new SerialPort({
            path: selectedPort.label,
            baudRate: 115200,
            autoOpen: false
        });

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `FastROM: Flashage sur ${selectedPort.label}`,
            cancellable: false
        }, async (progress) => {

            try {
                await new Promise<void>((resolve, reject) => {
                    port.open((err) => err ? reject(err) : resolve());
                });

                const fileBuffer = fs.readFileSync(filePath!);
                const fileSize = fileBuffer.length;
                const numBlocks = Math.ceil(fileSize / FRAME_SIZE);
                const numPagesToErase = Math.ceil(Math.max(fileSize, CLEAN_ZONE_MAX) / FLASH_PAGE_SIZE);

                // PHASE 0 : EFFACEMENT
                progress.report({ message: "Effacement de la mémoire (Clean 64KB)...", increment: 0 });
                for (let i = 0; i < numPagesToErase; i++) {
                    const addrToErase = START_ADDR + (i * FLASH_PAGE_SIZE);
                    port.write(generateFrame(0x02, addrToErase, Buffer.alloc(0)));
                    await delay(60); //
                }

                // PHASE 1 : ÉCRITURE
                progress.report({ message: "Écriture des blocs de données..." });
                for (let i = 0; i < numBlocks; i++) {
                    const currentAddr = START_ADDR + (i * FRAME_SIZE);
                    const dataBlock = fileBuffer.subarray(i * FRAME_SIZE, (i + 1) * FRAME_SIZE);
                    port.write(generateFrame(0x01, currentAddr, dataBlock));
                    
                    progress.report({ increment: (100 / numBlocks) * 0.9 }); 
                    await delay(80); //
                }

                // PHASE 2 : VÉRIFICATION
                progress.report({ message: "Calcul du checksum distant..." });
                let pcChecksum = 0;
                for (const byte of fileBuffer) { pcChecksum ^= byte; }

                const verifyFrame = generateFrame(0x04, START_ADDR, Buffer.alloc(0));
                verifyFrame.writeUInt16LE(fileSize, 5); // Taille totale pour le calcul XOR

                await new Promise<void>((resolve) => {
                    port.once('data', (data) => {
                        const slaveChecksum = data[0];
                        if (slaveChecksum === pcChecksum) {
                            vscode.window.showInformationMessage(`✅ Succès ! Firmware vérifié sur ${selectedPort.label}`);
                        } else {
                            vscode.window.showErrorMessage(`❌ Erreur Checksum ! Attendu: 0x${pcChecksum.toString(16)}, Reçu: 0x${slaveChecksum.toString(16)}`);
                        }
                        resolve();
                    });
                    port.write(verifyFrame);
                    setTimeout(() => resolve(), 3000); // Timeout plus long pour le calcul XOR en flash
                });

            } catch (error: any) {
                vscode.window.showErrorMessage(`Échec du flashage: ${error.message}`);
            } finally {
                if (port.isOpen) { port.close(); }
            }
        });
    });

    context.subscriptions.push(disposable);
}

export function deactivate() {}