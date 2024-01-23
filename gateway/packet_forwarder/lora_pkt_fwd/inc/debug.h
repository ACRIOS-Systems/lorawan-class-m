#ifndef _DEBUG_H
#define _DEBUG_H

#define MSG(args...) printf(args) /* message that is destined to the user */

struct debug_flags_fwd {
	bool pkt_fwd;
	bool jit;
	bool jit_error;
	bool timersync;
	bool beacon;
	bool log;
};

#endif