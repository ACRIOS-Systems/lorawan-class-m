#ifndef _LORAGW_DEBUG_H
#define _LORAGW_DEBUG_H

#include <stdbool.h>

struct debug_flags {
		bool aux;
		bool spi;
		bool reg;
		bool hal;
		bool gps;
		bool gpio;
		bool lbt;
	};

#endif