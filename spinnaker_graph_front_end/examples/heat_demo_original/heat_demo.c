/****a* heat_demo.c/heat_demo_summary
 *
 * SUMMARY
 *  a very, very simple 2D Heat equation SpiNNaker application
 *  one core does one point!
 *
 * AUTHOR
 *  Luis Plana - luis.plana@manchester.ac.uk
 *
 * DETAILS
 *  Created on       : 27 Jul 2011
 *  Version          : $Revision: 2531 $
 *  Last modified on : $Date: 2013-08-20 12:34:21 +0100 (Tue, 20 Aug 2013) $
 *  Last modified by : $Author: plana $
 *  $Id: heat_demo.c 2531 2013-08-20 11:34:21Z plana $
 *  $HeadURL: https://solem.cs.man.ac.uk/svn/demos/heat_demo/heat_demo.c $
 *
 * COPYRIGHT
 *  Copyright (c) The University of Manchester, 2011. All rights reserved.
 *  SpiNNaker Project
 *  Advanced Processor Technologies Group
 *  School of Computer Science
 *
 *******/

// SpiNNaker API
#include <spin1_api.h>
#include <data_specification.h>

// ------------------------------------------------------------------------
// DEBUG parameters
// ------------------------------------------------------------------------
//#define DEBUG              TRUE

#define VERBOSE            TRUE

// the visualiser has a bug with negative temperatures!
#define POSITIVE_TEMP      TRUE

// ------------------------------------------------------------------------
// simulation parameters
// ------------------------------------------------------------------------
//#define TIMER_TICK_PERIOD  1000
#define TIMER_TICK_PERIOD  2500
//#define TIMER_TICK_PERIOD  25000

#define PARAM_CX           0.03125
#define PARAM_CY           0.03125

#define NORTH_INIT         (40 << 16)
#define EAST_INIT          (10 << 16)
#define SOUTH_INIT         (10 << 16)
#define WEST_INIT          (40 << 16)

#define NORTH              3
#define SOUTH              2
#define EAST               1
#define WEST               0

#define NORTH_ARRIVED      (1 << NORTH)
#define SOUTH_ARRIVED      (1 << SOUTH)
#define EAST_ARRIVED       (1 << EAST)
#define WEST_ARRIVED       (1 << WEST)
#define NONE_ARRIVED       0
#define NS_ARRIVED         (NORTH_ARRIVED | SOUTH_ARRIVED)
#define EW_ARRIVED         (EAST_ARRIVED | WEST_ARRIVED)
#define ALL_ARRIVED        (NS_ARRIVED | EW_ARRIVED)

// ------------------------------------------------------------------------
// variables
// ------------------------------------------------------------------------
uint coreID;
uint chipID;
uint board_loc;

/* multicast routing keys to communicate with neighbours */
uint my_key;
uint north_key;
uint south_key;
uint east_key;
uint west_key;

/* multicast routing keys for commands */
uint stop_key;
uint pause_key;
uint resume_key;
uint temp_north_key;
uint temp_south_key;
uint temp_east_key;
uint temp_west_key;

/* determine if this core listens to new parameters and/or initialises the
 * temperature */
uint is_northernmost;
uint is_southernmost;
uint is_easternmost;
uint is_westernmost;

/* temperature values */
int my_temp = 0;  // any initial value will do!
int old_temp = 0;  // any initial value will do!

// get temperatures from 4 neighbours
// make sure to have room for two values from each neighbour
// given that the communication is asynchronous
volatile int neighbours_temp[2][4];

/* coefficients to compute new temperature value */
/* adjust for 16.16 fixed-point representation  */
int cx_adj = (int) (PARAM_CX * (1 << 16));
int cy_adj = (int) (PARAM_CY * (1 << 16));

/* keep track of which neighbours have sent data */
/* cores in the border need special values! */
volatile uint arrived[2];
uint init_arrived;
volatile uint now = 0;
volatile uint next = 1;

volatile uchar updating = TRUE;

sdp_msg_t my_msg;

/* report results in shared memory */
static volatile int *core_temp;

#ifdef DEBUG
uint dbg_packs_recv = 0;
uint * dbg_keys_recv;
uint dbg_timeouts = 0;
uint * dbg_stime;
#endif

void data_init() {

    // Get the address this core's DTCM data starts at from SRAM
    uint32_t* address = data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(address)) {
        io_printf(IO_BUF, "failed to read the data spec header");
        rt_error(RTE_SWERR);
    }

    // Read the data
    uint *data = (uint *) data_specification_get_region(0, address);
    my_key = data[0];
    north_key = data[1];
    south_key = data[2];
    east_key = data[3];
    west_key = data[4];
    is_northernmost = data[5];
    is_southernmost = data[6];
    is_easternmost = data[7];
    is_westernmost = data[8];
    stop_key = data[9];
    pause_key = data[10];
    resume_key = data[11];
    temp_north_key = data[12];
    temp_south_key = data[13];
    temp_east_key = data[14];
    temp_west_key = data[15];

    io_printf(IO_BUF,
        "my_key = 0x%08x, north_key = 0x%08x, south_key = 0x%08x,"
        " east_key = 0x%08x, west_key = 0x%08x\n",
        my_key, north_key, south_key, east_key, west_key);

    init_arrived = NONE_ARRIVED;
    if (is_northernmost) {
        io_printf(IO_BUF, "North\n");
        neighbours_temp[now][NORTH]  = NORTH_INIT;
        neighbours_temp[next][NORTH] = NORTH_INIT;
        init_arrived |= NORTH_ARRIVED;
    }
    if (is_southernmost) {
        io_printf(IO_BUF, "South\n");
        neighbours_temp[now][SOUTH]  = SOUTH_INIT;
        neighbours_temp[next][SOUTH] = SOUTH_INIT;
        init_arrived |= SOUTH_ARRIVED;
    }
    if (is_easternmost) {
        io_printf(IO_BUF, "East\n");
        neighbours_temp[now][EAST]  = EAST_INIT;
        neighbours_temp[next][EAST] = EAST_INIT;
        init_arrived |= EAST_ARRIVED;
    }
    if (is_westernmost) {
        io_printf(IO_BUF, "West\n");
        neighbours_temp[now][WEST]  = WEST_INIT;
        neighbours_temp[next][WEST] = WEST_INIT;
        init_arrived |= WEST_ARRIVED;
    }
    arrived[now] = init_arrived;
    arrived[next] = init_arrived;
}

/****f* heat_demo.c/send_temps_to_host
 *
 * SUMMARY
 *  This function is called at application exit.
 *  It's used to report the final temperatures to the host
 *
 * SYNOPSIS
 *  void send_temps_to_host ()
 *
 * SOURCE
 */
void send_temps_to_host() {
    // copy temperatures into message buffer and set message length
    uint len = 16 * sizeof(uint);
    spin1_memcpy(my_msg.data, (void *) core_temp, len);
    my_msg.length = sizeof(sdp_hdr_t) + sizeof(cmd_hdr_t) + len;

    // and send SDP message!
    (void) spin1_send_sdp_msg(&my_msg, 100); // 100ms timeout
}
/*
 *******/

/****f* heat_demo.c/sdp_init
 *
 * SUMMARY
 *  This function is used to initialise SDP message buffer
 *
 * SYNOPSIS
 *  void sdp_init ()
 *
 * SOURCE
 */
void sdp_init() {
    // fill in SDP destination fields
    my_msg.tag = 1;                    // IPTag 1
    my_msg.dest_port = PORT_ETH;       // Ethernet
    my_msg.dest_addr = sv->eth_addr;   // Nearest Ethernet chip

    // fill in SDP source & flag fields
    my_msg.flags = 0x07;
    my_msg.srce_port = coreID;
    my_msg.srce_addr = sv->p2p_addr;
}
/*
 *******/

/****f* heat_demo.c/report_temp
 *
 * SUMMARY
 *  This function is used to report current temp
 *
 * SYNOPSIS
 *  void report_temp (uint ticks)
 *
 * SOURCE
 */
void report_temp(uint ticks) {
    // report temperature in shared memory
    core_temp[coreID - 1] = my_temp;

    // send results to host
    // only the lead application core does this
    if (leadAp) {
        // spread out the reporting to avoid SDP packet drop
        //##    if ((ticks % (NUMBER_OF_XCHIPS * NUMBER_OF_YCHIPS)) == my_chip)
        if ((ticks % 64) == board_loc) {
            send_temps_to_host();
        }
    }
}
/*
 *******/

/****f* heat_demo.c/report_results
 *
 * SUMMARY
 *  This function is called at application exit.
 *  It's used to report some statistics and say goodbye.
 *
 * SYNOPSIS
 *  void report_results ()
 *
 * SOURCE
 */
void report_results() {
    /* report temperature in shared memory */
    core_temp[coreID - 1] = my_temp;

    /* report final temperature */
//  /* skew io_printfs to avoid overloading tubotron */
//  spin1_delay_us (200 * ((chipID << 5) + coreID));
    io_printf(IO_BUF, "T = %7.3f\n", my_temp);
}
/*
 *******/

/****f* heat_demo.c/receive_data
 *
 * SUMMARY
 *  This function is used as a callback for packet received events.
 * receives data from 4 (NSEW) neighbours and updates the checklist
 *
 * SYNOPSIS
 *  void receive_data (uint key, uint payload)
 *
 * INPUTS
 *   uint key: packet routing key - provided by the RTS
 *   uint payload: packet payload - provided by the RTS
 *
 * SOURCE
 */
void receive_data(uint key, uint payload) {
    sark.vcpu->user1++;

#ifdef DEBUG
    dbg_keys_recv[dbg_packs_recv++] = key;
    if (dbg_packs_recv == DEBUG_KEYS) {
        dbg_packs_recv = 0;
    }
#endif

    if (key == north_key) {
        if (arrived[now] & NORTH_ARRIVED) {
            neighbours_temp[next][NORTH] = payload;
            arrived[next] |= NORTH_ARRIVED;
        } else {
            neighbours_temp[now][NORTH] = payload;
            arrived[now] |= NORTH_ARRIVED;
        }
    } else if (key == south_key) {
        if (arrived[now] & SOUTH_ARRIVED) {
            neighbours_temp[next][SOUTH] = payload;
            arrived[next] |= SOUTH_ARRIVED;
        } else {
            neighbours_temp[now][SOUTH] = payload;
            arrived[now] |= SOUTH_ARRIVED;
        }
    } else if (key == east_key) {
        if (arrived[now] & EAST_ARRIVED) {
            neighbours_temp[next][EAST] = payload;
            arrived[next] |= EAST_ARRIVED;
        } else {
            neighbours_temp[now][EAST] = payload;
            arrived[now] |= EAST_ARRIVED;
        }
    } else if (key == west_key) {
        if (arrived[now] & WEST_ARRIVED) {
            neighbours_temp[next][WEST] = payload;
            arrived[next] |= WEST_ARRIVED;
        } else {
            neighbours_temp[now][WEST] = payload;
            arrived[now] |= WEST_ARRIVED;
        }
    } else if (key == temp_north_key) {
        if (is_northernmost) {
            neighbours_temp[now][NORTH] = payload;
            neighbours_temp[next][NORTH] = payload;
        }
    } else if (key == temp_east_key) {
        if (is_easternmost) {
            neighbours_temp[now][EAST] = payload;
            neighbours_temp[next][EAST] = payload;
        }
    } else if (key == temp_south_key) {
        if (is_southernmost) {
            neighbours_temp[now][SOUTH] = payload;
            neighbours_temp[next][SOUTH] = payload;
        }
    } else if (key == temp_west_key) {
        if (is_westernmost) {
            neighbours_temp[now][WEST] = payload;
            neighbours_temp[next][WEST] = payload;
        }
    } else if (key == stop_key) {
        spin1_exit(0);
    } else if (key == pause_key) {
        updating = FALSE;
    } else if (key == resume_key) {
        updating = TRUE;
    } else {
        // unexpected packet!
#ifdef DEBUG
        io_printf (IO_STD, "!\n");
#endif
    }
}
/*
 *******/

/****f* heat_demo.c/send_first_value
 *
 * SUMMARY
 *
 * SYNOPSIS
 *  void send_first_value (uint a, uint b)
 *
 * SOURCE
 */
void send_first_value(uint a, uint b) {
    /* send data to neighbours */
    spin1_send_mc_packet(my_key, my_temp, WITH_PAYLOAD);
}
/*
 *******/

/****f* heat_demo.c/update
 *
 * SUMMARY
 *
 * SYNOPSIS
 *  void update (uint ticks, uint b)
 *
 * SOURCE
 */
void update(uint ticks, uint b) {
    sark.vcpu->user0++;

    if (updating) {
        /* report if not all neighbours' data arrived */
#ifdef DEBUG
        if (arrived[now] != ALL_ARRIVED) {
            io_printf (IO_STD, "@\n");
            dbg_timeouts++;
        }
#endif

        // if a core does not receive temperature from a neighbour
        // it uses it's own as an estimate for the nieghbour's.
        if (arrived[now] != ALL_ARRIVED) {
            if (!(arrived[now] & NORTH_ARRIVED)) {
                neighbours_temp[now][NORTH] = my_temp;
            }

            if (!(arrived[now] & SOUTH_ARRIVED)) {
                neighbours_temp[now][SOUTH] = my_temp;
            }

            if (!(arrived[now] & EAST_ARRIVED)) {
                neighbours_temp[now][EAST] = my_temp;
            }

            if (!(arrived[now] & WEST_ARRIVED)) {
                neighbours_temp[now][WEST] = my_temp;
            }
        }

        /* compute new temperature */
        /* adjust for 16.16 fixed-point representation  */
        int tmp1 = neighbours_temp[now][EAST] + neighbours_temp[now][WEST]
                - 2 * my_temp;
        int tmp2 = neighbours_temp[now][NORTH] + neighbours_temp[now][SOUTH]
                - 2 * my_temp;
        /* adjust for 16.16 fixed-point representation  */
        int tmp3 = (int) (((long long) cx_adj * (long long) tmp1) >> 16);
        int tmp4 = (int) (((long long) cy_adj * (long long) tmp2) >> 16);
        my_temp = my_temp + tmp3 + tmp4;

#ifdef POSITIVE_TEMP
        // avoids a problem with negative temperatures in the visualiser!
        my_temp = (my_temp > 0) ? my_temp : 0;
#endif

        /* send new data to neighbours */
        spin1_send_mc_packet(my_key, my_temp, WITH_PAYLOAD);

        /* prepare for next iteration */
        arrived[now] = init_arrived;
        now = 1 - now;
        next = 1 - next;

        /* report current temp */
        report_temp(ticks);
    }
}
/*
 *******/

/****f* heat_demo.c/host_data
 *
 * SUMMARY
 *
 * SYNOPSIS
 *  void host_data (uint *mailbox, uint port)
 *
 * INPUTS
 *   uint mailbox: mailbox where the message is stored
 *   uint port: destination port of the SDP message
 *
 * SOURCE
 */
void host_data(uint mailbox, uint port) {
    sdp_msg_t *msg = (sdp_msg_t *) mailbox;
    uint *data = (uint *) msg->data;

    io_printf(IO_BUF, "cmd: %d\n", msg->cmd_rc);
    if (msg->cmd_rc == 1) {
        io_printf(IO_BUF, "N: %7.3f\n", data[0]);
        io_printf(IO_BUF, "E: %7.3f\n", data[1]);
        io_printf(IO_BUF, "S: %7.3f\n", data[2]);
        io_printf(IO_BUF, "W: %7.3f\n", data[3]);
    }

    switch (msg->cmd_rc) {
    case 0: // stop
        spin1_send_mc_packet(stop_key, 0, NO_PAYLOAD);
        break;

    case 1: // new border temperatures
        spin1_send_mc_packet(temp_north_key, data[0], WITH_PAYLOAD);
        spin1_send_mc_packet(temp_east_key, data[1], WITH_PAYLOAD);
        spin1_send_mc_packet(temp_south_key, data[2], WITH_PAYLOAD);
        spin1_send_mc_packet(temp_west_key, data[3], WITH_PAYLOAD);
        break;

    case 2: // pause
        spin1_send_mc_packet(pause_key, 0, NO_PAYLOAD);
        break;

    case 3: // resume
        spin1_send_mc_packet(resume_key, 0, NO_PAYLOAD);
        break;

    default:
        // unexpected packet!
#ifdef DEBUG
        io_printf (IO_STD, "!SDP\n");
#endif
        break;
    }

    spin1_msg_free(msg);
}
/*
 *******/

/****f* heat_demo.c/c_main
 *
 * SUMMARY
 *  This function is called at application start-up.
 *  It is used to register event callbacks and begin the simulation.
 *
 * SYNOPSIS
 *  int c_main()
 *
 * SOURCE
 */
void c_main() {
#ifdef VERBOSE
    // say hello
    io_printf(IO_BUF, "starting heat_demo\n");
#endif

    // get this core's ID
    coreID = spin1_get_core_id();
    chipID = spin1_get_chip_id();

    board_loc = ((sv->board_addr >> 5) | sv->board_addr) & 63;

    // set timer tick value to 1ms (in microseconds)
    // slow down simulation to allow users to appreciate changes
    spin1_set_timer_tick(TIMER_TICK_PERIOD);

    // register callbacks
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, 0);
    spin1_callback_on(TIMER_TICK, update, 0);
    spin1_callback_on(SDP_PACKET_RX, host_data, 0);

    data_init();

    // initialise SDP message buffer
    sdp_init();

    // initialise temperatures (for absent cores!)

    core_temp = (volatile int *) sv->sysram_base; //##

    if (leadAp) {
        for (uint i = 1; i <= 16; i++) {
            core_temp[i - 1] = 0;
        }
    }

#ifdef DEBUG
    // initialise variables
    dbg_keys_recv = spin1_malloc(DEBUG_KEYS * 4 * sizeof(uint));
    // record start time somewhere in SDRAM
    dbg_stime = (uint *) (SPINN_SDRAM_BASE + 4 * coreID);
    *dbg_stime = sv->clock_ms;
#endif

    // kick-start the update process
    spin1_schedule_callback(send_first_value, 0, 0, 3);

    // go
    spin1_start(SYNC_WAIT);	//##

#ifdef VERBOSE
    // report results
    report_results();
#endif

#ifdef VERBOSE
    // say goodbye
    io_printf(IO_BUF, "stopping heat_demo\n");
#endif
}
/*
 *******/
