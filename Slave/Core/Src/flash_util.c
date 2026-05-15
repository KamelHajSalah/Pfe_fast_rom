/*
 * flash_util.c
 *
 *  Created on: Apr 16, 2026
 *      Author: Mega-PC
 */


#include "main.h"      // Indispensable pour HAL_StatusTypeDef et les fonctions HAL_FLASH
#include <stdint.h>    // Indispensable pour les types uint32_t, uint8_t, etc.
#include <string.h>    // Indispensable pour memcpy
#include "flash_util.h"

/* --- Fonctions Utilitaires Flash (Slave G4) --- */

/**
  * @brief Écrit un bloc de données en Flash par Double-Word (64 bits).
  * @note Le buffer data doit être aligné sur 8 octets[cite: 1093, 1094].
  */
HAL_StatusTypeDef Flash_Write_Block(uint32_t address, uint8_t *data, uint16_t size) {
    HAL_StatusTypeDef status = HAL_OK;

    HAL_FLASH_Unlock();

    // L'écriture sur G4 se fait impérativement par 64 bits (8 octets) [cite: 1094, 1096]
    for (uint16_t i = 0; i < size; i += 8) {
        uint64_t double_word = 0;
        memcpy(&double_word, &data[i], 8);

        status = HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, address + i, double_word);

        if (status != HAL_OK) {
            break;
        }
    }

    HAL_FLASH_Lock();
    return status;
}

/**
  * @brief Efface une page spécifique de la mémoire Flash.
  */
void Flash_Erase_Sector(uint32_t page_addr) {
    uint32_t PageError = 0;
    FLASH_EraseInitTypeDef EraseInitStruct;

    HAL_FLASH_Unlock();

    EraseInitStruct.TypeErase = FLASH_TYPEERASE_PAGES;
    EraseInitStruct.Banks     = FLASH_BANK_1;
    // Calcul du numéro de page (0-127 pour le Bank 1 du G474)
    EraseInitStruct.Page      = (page_addr - FLASH_BASE) / FLASH_PAGE_SIZE;
    EraseInitStruct.NbPages   = 1;

    HAL_FLASHEx_Erase(&EraseInitStruct, &PageError);

    HAL_FLASH_Lock();
}
