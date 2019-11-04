/*
 * Copyright (c) 2017-2019 The University of Manchester
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <spin1_api.h>
#include <sark.h>
#include <data_specification.h>
#include <simulation.h>
#include <stdint.h>

void handle_sdp(uint msg, uint unused) {
    use(unused);
    sdp_msg_t *sdp = (sdp_msg_t *) msg;
    uint dest_port = sdp->dest_port;
    uint dest_addr = sdp->dest_addr;

    sdp->dest_port = sdp->srce_port;
    sdp->srce_port = dest_port;

    sdp->dest_addr = sdp->srce_addr;
    sdp->srce_addr = dest_addr;
    sdp->length = 12;
    sdp->cmd_rc = RC_OK;
    spin1_send_sdp_msg(sdp, 10);
    sark_msg_free(sdp);
}

void handle_big_data(uint msg, uint unused) {
    use(unused);
    udp_hdr_t *udp = (udp_hdr_t *) msg;
    // io_printf(IO_BUF, "Received %u bytes of data\n", udp->length);
    while (!sark_send_big_data(udp)) {
        // Do Nothing, just keep hammering
    }
    sark_free(udp);
}

void c_main() {
    spin1_callback_on(SDP_PACKET_RX, handle_sdp, 0);
    spin1_callback_on(BIG_DATA_RX, handle_big_data, 0);
    spin1_start(SYNC_NOWAIT);
}
