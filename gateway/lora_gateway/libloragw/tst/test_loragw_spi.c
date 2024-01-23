/*
 / _____)             _              | |
( (____  _____ ____ _| |_ _____  ____| |__
 \____ \| ___ |    (_   _) ___ |/ ___)  _ \
 _____) ) ____| | | || |_| ____( (___| | | |
(______/|_____)_|_|_| \__)_____)\____)_| |_|
  (C)2013 Semtech-Cycleo

Description:
    Minimum test program for the loragw_spi 'library'
    Use logic analyser to check the results.

License: Revised BSD License, see LICENSE.TXT file include in the project
Maintainer: Sylvain Miermont
*/


/* -------------------------------------------------------------------------- */
/* --- DEPENDANCIES --------------------------------------------------------- */

#include <stdint.h>
#include <stdio.h>
#include <getopt.h>

#include "loragw_spi.h"
#include "loragw_debug.h" /* debug stuff */

/* -------------------------------------------------------------------------- */
/* --- PUBLIC VARIABLES ----------------------------------------------------- */
struct debug_flags debug_flags = {
        .aux=false,
        .spi=false,
        .reg=false,
        .hal=false,
        .gps=false,
        .gpio=false,
        .lbt=false
    };
/* -------------------------------------------------------------------------- */
/* --- PRIVATE MACROS ------------------------------------------------------- */

#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))

/* -------------------------------------------------------------------------- */
/* --- PRIVATE CONSTANTS ---------------------------------------------------- */

#define BURST_TEST_SIZE 2500 /* >> LGW_BURST_CHUNK */
#define TIMING_REPEAT   1    /* repeat transactions multiple times for timing characterisation */

/* -------------------------------------------------------------------------- */
/* --- MAIN FUNCTION -------------------------------------------------------- */

int main(int argc, char *argv[])
{
    int i;
    void *spi_target = NULL;
    const char *spi_path = NULL;
    int opt;
    uint8_t data = 0;
    uint8_t dataout[BURST_TEST_SIZE];
    uint8_t datain[BURST_TEST_SIZE];
    uint8_t spi_mux_mode = LGW_SPI_MUX_MODE0;
    int spi_speed = 0;


    while ((opt = getopt(argc, argv, ":s:S:") != -1)) {
        switch (opt) {
            case 's':
                spi_path = optarg;
                break;
            case 'S':
                i = sscanf(optarg, "%i", &spi_speed);
                if ((i != 1)) {
                    printf("ERROR: invalid number of SPI clock\n");
                    return -1;
                }
                break;
            case ':':
                fprintf(stderr, "-s parameter requires path\n");
                return 1;
            default:
                fprintf(stderr, "Usage: %s [-s <spi_dev_path>]\n", argv[0]);
                return 1;
            }
    }

    if (!spi_path) {
        spi_path = "/dev/spi0";
    }

    for (i = 0; i < BURST_TEST_SIZE; ++i) {
        dataout[i] = 0x30 + (i % 10); /* ASCCI code for 0 -> 9 */
        datain[i] = 0x23; /* garbage data, to be overwritten by received data */
    }

    printf("INFO: Using SPI device: %s\n", spi_path);
    printf("Beginning of test for loragw_spi.c\n");
    lgw_spi_open(&spi_target, spi_path, spi_speed);

    /* normal R/W test */
    for (i = 0; i < TIMING_REPEAT; ++i)
        lgw_spi_w(spi_target, spi_mux_mode, LGW_SPI_MUX_TARGET_SX1301, 0xAA, 0x96);
    for (i = 0; i < TIMING_REPEAT; ++i)
        lgw_spi_r(spi_target, spi_mux_mode, LGW_SPI_MUX_TARGET_SX1301, 0x55, &data);

    /* burst R/W test, small bursts << LGW_BURST_CHUNK */
    for (i = 0; i < TIMING_REPEAT; ++i)
        lgw_spi_wb(spi_target, spi_mux_mode, LGW_SPI_MUX_TARGET_SX1301, 0x55, dataout, 16);
    for (i = 0; i < TIMING_REPEAT; ++i)
        lgw_spi_rb(spi_target, spi_mux_mode, LGW_SPI_MUX_TARGET_SX1301, 0x55, datain, 16);

    /* burst R/W test, large bursts >> LGW_BURST_CHUNK */
    for (i = 0; i < TIMING_REPEAT; ++i)
        lgw_spi_wb(spi_target, spi_mux_mode, LGW_SPI_MUX_TARGET_SX1301, 0x5A, dataout, ARRAY_SIZE(dataout));
    for (i = 0; i < TIMING_REPEAT; ++i)
        lgw_spi_rb(spi_target, spi_mux_mode, LGW_SPI_MUX_TARGET_SX1301, 0x5A, datain, ARRAY_SIZE(datain));

    /* last read (blocking), just to be sure no to quit before the FTDI buffer is flushed */
    lgw_spi_r(spi_target, spi_mux_mode, LGW_SPI_MUX_TARGET_SX1301, 0x55, &data);
    printf("data received (simple read): %d\n",data);

    lgw_spi_close(spi_target);
    printf("End of test for loragw_spi.c\n");

    return 0;
}

/* --- EOF ------------------------------------------------------------------ */
