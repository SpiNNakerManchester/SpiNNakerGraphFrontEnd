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
#include "spin1_api.h"


// ------------------------------------------------------------------------
// DEBUG parameters
// ------------------------------------------------------------------------
//#define DEBUG              TRUE
#define DEBUG_KEYS         500

#define VERBOSE            TRUE

// the visualiser has a bug with negative temperatures!
#define POSITIVE_TEMP      TRUE

#define TIMER_TICK_PERIOD  -1

#define PARAM_CX           0.03125
#define PARAM_CY           0.03125

// use core 17 keys to distribute commands and data
#define STOP_KEY       ROUTING_KEY(0, 17)
#define PAUSE_KEY      ROUTING_KEY(1, 17)
#define RESUME_KEY     ROUTING_KEY(2, 17)
#define TEMP_NORTH_KEY ROUTING_KEY(16, 17)
#define TEMP_EAST_KEY  ROUTING_KEY(17, 17)
#define TEMP_SOUTH_KEY ROUTING_KEY(18, 17)
#define TEMP_WEST_KEY  ROUTING_KEY(19, 17)
#define CMD_MASK       0xfffffe1f

/* multicast routing keys to communicate with neighbours */
uint my_key;
uint north_key;
uint south_key;
uint east_key;
uint west_key;

/* temperature values */
int my_temp = 0;  // any initial value will do!
int old_temp = 0;  // any initial value will do!

// get temperatures from 4 neighbours
// make sure to have room for two values from each neighbour
// given that the communication is asynchronous
volatile int neighbours_temp[2][4];

/* coeficients to compute new temperature value */
/* adjust for 16.16 fixed-point representation  */
int cx_adj = (int) (PARAM_CX * (1 << 16));
int cy_adj = (int) (PARAM_CY * (1 << 16));

/* keep track of which neighbours have sent data */
/* cores in the boder need special values! */
volatile uint arrived[2];
uint init_arrived;
volatile uint now  = 0;
volatile uint next = 1;

volatile uchar updating = TRUE;

sdp_msg_t my_msg;

/* report results in shared memory */
#ifndef OLD_SARK
static volatile int *core_temp;
#else
#ifdef USE_SDRAM
  static volatile int * const core_temp =
                     (int *) (SPINN_SDRAM_BASE + 0x1000 + 16 * sizeof(uint));
#else  //SYSRAM
  static volatile int * const core_temp =
                     (int *) (SPINN_SYSRAM_BASE + (SPINN_SYSRAM_SIZE / 2));
#endif
#endif

#ifdef DEBUG
  uint   dbg_packs_recv = 0;
  uint * dbg_keys_recv;
  uint   dbg_timeouts = 0;
  uint * dbg_stime;
#endif

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
void send_temps_to_host ()
{
  // copy temperatures into msg buffer and set message length
  uint len = 16 * sizeof(uint);
  spin1_memcpy (my_msg.data, (void *) core_temp, len);
  my_msg.length = sizeof (sdp_hdr_t) + sizeof (cmd_hdr_t) + len;

  // and send SDP message!
  (void) spin1_send_sdp_msg (&my_msg, 100); // 100ms timeout
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
void sdp_init ()
{
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
void report_temp (uint ticks)
{
  // report temperature in shared memory
  core_temp[coreID - 1] = my_temp;

  // send results to host
  // only the lead application core does this
  if (leadAp)
  {
    // spread out the reporting to avoid SDP packet drop
    //##    if ((ticks % (NUMBER_OF_XCHIPS * NUMBER_OF_YCHIPS)) == my_chip)
    if ((ticks % 64) == board_loc)
    {
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
void report_results ()
{
  /* report temperature in shared memory */
  core_temp[coreID - 1] = my_temp;

  /* report final temperature */
//  /* skew io_printfs to avoid congesting tubotron */
//  spin1_delay_us (200 * ((chipID << 5) + coreID));

  io_printf (IO_BUF, "T = %7.3f\n", my_temp);
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
void receive_data (uint key, uint payload)
{
  sark.vcpu->user1++;

  #ifdef DEBUG
    dbg_keys_recv[dbg_packs_recv++] = key;
    if (dbg_packs_recv == DEBUG_KEYS)
    {
      dbg_packs_recv = 0;
    }
  #endif

  if (key == north_key)
  {
    if (arrived[now] & NORTH_ARRIVED)
    {
      neighbours_temp[next][NORTH] = payload;
      arrived[next] |= NORTH_ARRIVED;
    }
    else
    {
      neighbours_temp[now][NORTH] = payload;
      arrived[now] |= NORTH_ARRIVED;
    }
  }
  else if (key == south_key)
  {
    if (arrived[now] & SOUTH_ARRIVED)
    {
      neighbours_temp[next][SOUTH] = payload;
      arrived[next] |= SOUTH_ARRIVED;
    }
    else
    {
      neighbours_temp[now][SOUTH] = payload;
      arrived[now] |= SOUTH_ARRIVED;
    }
  }
  else if (key == east_key)
  {
    if (arrived[now] & EAST_ARRIVED)
    {
      neighbours_temp[next][EAST] = payload;
      arrived[next] |= EAST_ARRIVED;
    }
    else
    {
      neighbours_temp[now][EAST] = payload;
      arrived[now] |= EAST_ARRIVED;
    }
  }
  else if (key == west_key)
  {
    if (arrived[now] & WEST_ARRIVED)
    {
      neighbours_temp[next][WEST] = payload;
      arrived[next] |= WEST_ARRIVED;
    }
    else
    {
      neighbours_temp[now][WEST] = payload;
      arrived[now] |= WEST_ARRIVED;
    }
  }
  else if (key == TEMP_NORTH_KEY)
  {
    if ((IS_NORTHERNMOST_CHIP(my_x, my_y)) &&
        (IS_NORTHERNMOST_CORE(coreID))
       )
    {
      neighbours_temp[now][NORTH]  = payload;
      neighbours_temp[next][NORTH] = payload;
    }
  }
  else if (key == TEMP_EAST_KEY)
  {
    if ((IS_EASTERNMOST_CHIP(my_x, my_y)) &&
        (IS_EASTERNMOST_CORE(coreID))
       )
    {
      neighbours_temp[now][EAST]  = payload;
      neighbours_temp[next][EAST] = payload;
    }
  }
  else if (key == TEMP_SOUTH_KEY)
  {
    if ((IS_SOUTHERNMOST_CHIP(my_x, my_y)) &&
        (IS_SOUTHERNMOST_CORE(coreID))
       )
    {
      neighbours_temp[now][SOUTH]  = payload;
      neighbours_temp[next][SOUTH] = payload;
    }
  }
  else if (key == TEMP_WEST_KEY)
  {
    if ((IS_WESTERNMOST_CHIP(my_x, my_y)) &&
        (IS_WESTERNMOST_CORE(coreID))
       )
    {
      neighbours_temp[now][WEST]  = payload;
      neighbours_temp[next][WEST] = payload;
    }
  }
  else if (key == STOP_KEY)
  {
    spin1_exit (0);
  }
  else if (key == PAUSE_KEY)
  {
    updating = FALSE;
  }
  else if (key == RESUME_KEY)
  {
    updating = TRUE;
  }
  else
  {
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
void send_first_value (uint a, uint b)
{
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
void update (uint ticks, uint b)
{
  sark.vcpu->user0++;

  if (updating)
  {
    /* report if not all neighbours' data arrived */
    #ifdef DEBUG
      if (arrived[now] != ALL_ARRIVED)
      {
        io_printf (IO_STD, "@\n");
        dbg_timeouts++;
      }
    #endif

    // if a core does not receive temperature from a neighbour
    // it uses it's own as an estimate for the nieghbour's.
    if (arrived[now] != ALL_ARRIVED)
    {
      if (!(arrived[now] & NORTH_ARRIVED))
      {
        neighbours_temp[now][NORTH] = my_temp;
      }

      if (!(arrived[now] & SOUTH_ARRIVED))
      {
        neighbours_temp[now][SOUTH] = my_temp;
      }

      if (!(arrived[now] & EAST_ARRIVED))
      {
        neighbours_temp[now][EAST] = my_temp;
      }

      if (!(arrived[now] & WEST_ARRIVED))
      {
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
      // avoids a problem with negative temps in the visualiser!
      my_temp = (my_temp > 0) ? my_temp : 0;
    #endif

    /* send new data to neighbours */
    spin1_send_mc_packet(my_key, my_temp, WITH_PAYLOAD);

    /* prepare for next iteration */
    arrived[now] = init_arrived;
    now  = 1 - now;
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
void host_data (uint mailbox, uint port)
{
  sdp_msg_t *msg = (sdp_msg_t *) mailbox;
  uint *data = (uint *) msg->data;

  #ifdef DEBUG
    io_printf (IO_STD, "cmd: %d\n", msg->cmd_rc);
    if (msg->cmd_rc == 1)
    {
      io_printf (IO_STD, "N: %7.3f\n", data[0]);
      io_printf (IO_STD, "E: %7.3f\n", data[1]);
      io_printf (IO_STD, "S: %7.3f\n", data[2]);
      io_printf (IO_STD, "W: %7.3f\n", data[3]);
    }
  #endif

  switch (msg->cmd_rc)
  {
    case 0: // stop
      spin1_send_mc_packet(STOP_KEY, 0, NO_PAYLOAD);
      break;

    case 1: // new border temperatures
      spin1_send_mc_packet(TEMP_NORTH_KEY, data[0], WITH_PAYLOAD);
      spin1_send_mc_packet(TEMP_EAST_KEY,  data[1], WITH_PAYLOAD);
      spin1_send_mc_packet(TEMP_SOUTH_KEY, data[2], WITH_PAYLOAD);
      spin1_send_mc_packet(TEMP_WEST_KEY,  data[3], WITH_PAYLOAD);
      break;

    case 2: // pause
      spin1_send_mc_packet(PAUSE_KEY, 0, NO_PAYLOAD);
      break;

    case 3: // resume
      spin1_send_mc_packet(RESUME_KEY, 0, NO_PAYLOAD);
      break;

    default:
      // unexpected packet!
      #ifdef DEBUG
        io_printf (IO_STD, "!SDP\n");
      #endif
      break;
  }

  spin1_msg_free (msg);
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
void c_main()
{
  #ifdef VERBOSE
    // say hello
    io_printf (IO_BUF, "starting heat_demo\n");
  #endif

  // get this core's ID
  coreID = spin1_get_core_id();
  chipID = spin1_get_chip_id();

  // get this chip's coordinates for core map
  my_x = chipID >> 8;
  my_y = chipID & 0xff;
  my_chip = (my_x * NUMBER_OF_YCHIPS) + my_y;

  board_loc = ((sv->board_addr >> 5) | sv->board_addr) & 63;

  // operate only if in core map!
  if ((my_x < NUMBER_OF_XCHIPS) && (my_y < NUMBER_OF_YCHIPS)
       && ((core_map[my_x][my_y] & (1 << coreID)) != 0)
     )
  {
    // set the core map for the simulation
    //##    spin1_application_core_map(NUMBER_OF_XCHIPS, NUMBER_OF_YCHIPS, core_map);

    // set timer tick value to 1ms (in microseconds)
    // slow down simulation to alow users to appreciate changes
    spin1_set_timer_tick (TIMER_TICK_PERIOD);

    // register callbacks
    spin1_callback_on (MCPL_PACKET_RECEIVED, receive_data, 0);
    spin1_callback_on (TIMER_TICK, update, 0);
    spin1_callback_on (SDP_PACKET_RX, host_data, 0);

    // initialise SDP message buffer
    sdp_init ();

    // initialise temperatures (for absent cores!)

    core_temp = (volatile int *) sv->sysram_base; //##

    if (leadAp)
    {
      for (uint i = 1; i <= 16; i++)
      {
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
    spin1_start (SYNC_WAIT);	//##

    // restore router configuration
    rtr[RTR_CONTROL] = rtr_conf;

    #ifdef VERBOSE
      // report results
      report_results();
    #endif
  }

  #ifdef VERBOSE
    // say goodbye
    io_printf (IO_BUF, "stopping heat_demo\n");
  #endif
}
/*
*******/