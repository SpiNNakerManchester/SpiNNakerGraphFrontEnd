#ifndef _PUT_TESTS_
#define _PUT_TESTS_

#include <sark.h>
#include "../../db-typedefs.h"
#include "../../test.h"

// ========== ONE =============================
// send one PUT, get one back. one dest.
// try PULLING it

// send two of the same. get both back. one dest

// overflow one dest

// ========= TWO =============================
//send PUTs to two cores

// ========= MULTIPLE =======================
// overflow

// ========= ALL =============================
//involve all cores
// overflow

// send shit loads of messages. See how many get lost.
// make sure we can deal with lost packages!!!!!!!!!!


void run_sdp_tests() {
    log_info("Started SDP tests.");

    log_info("Finished running tests.");
 }

#endif