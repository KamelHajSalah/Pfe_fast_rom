/*
 * flash_util.h
 *
 *  Created on: Apr 16, 2026
 *      Author: Mega-PC
 */

#ifndef INC_FLASH_UTIL_H_
#define INC_FLASH_UTIL_H_

#include "main.h"
#include <stdint.h>

/* Prototypes des fonctions */
HAL_StatusTypeDef Flash_Write_Block(uint32_t address, uint8_t *data, uint16_t size);
void Flash_Erase_Sector(uint32_t page_addr);

#endif /* INC_FLASH_UTIL_H_ */
