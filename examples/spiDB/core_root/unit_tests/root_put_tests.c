#include "../../db-typedefs.h"

static uint32_t q_generated_id = 0;

extern void send_spiDBquery(spiDBquery* q);
extern double_linked_list* unreplied_puts;
extern double_linked_list* unreplied_pulls;

void printQuery(spiDBquery* q){
  log_info("=============================================");
  log_info("=================== QUERY ===================");
  log_info("  id:        %08x", q->id);
  log_info("  cmd:       %04x", q->cmd);
  log_info("                                             ");
  log_info("  k_type:    %04x", q->k_type);
  log_info("  k_size:    %04x", q->k_size);
  log_info("                                             ");
  log_info("  v_type:    %04x", q->v_type);
  log_info("  v_size:    %04x", q->v_size);
  log_info("                                             ");
  log_info("  k_v:       %s", q->k_v);
  log_info("=============================================");
}

static uint32_t       puts_i = 0;
static spiDBquery*    puts_sent[100];

spiDBquery* createAndSendQuery(spiDBcommand cmd,
                        var_type k_type, size_t k_size, char* k,
                        var_type v_type, size_t v_size, char* v){

    spiDBquery* q = (spiDBquery*)sark_alloc(1, sizeof(spiDBquery));

    q->id       = q_generated_id++;
    q->cmd      = cmd;
    q->k_type   = k_type;
    q->k_size   = k_size;
    q->v_type   = v_type;
    q->v_size   = v_size;

    memcpy(q->k_v,          k, k_size);
    memcpy(&q->k_v[k_size], v, v_size);

    send_spiDBquery(q);

    return q;
}

size_t size(var_type t, char* c){
    switch(t){
        case STRING: return strlen(c);
        case UINT32: return sizeof(uint32_t);
        default:     return 0;
    }
}

uint32_t tests_sent     = 0;
uint32_t tests_received = 0;
uint32_t tests_passed   = 0;

void test_put(var_type k_type, char* k, var_type v_type, char* v){
    puts_sent[puts_i++] = createAndSendQuery(PUT, k_type, size(k_type,k), k, v_type, size(v_type,v), v);
    tests_sent++;
}

void test_pull_with_size(var_type k_type, size_t k_size, char* k){
    createAndSendQuery(PULL, k_type, k_size, k, 0, 0, NULL);
    tests_sent++;
}

void test_pull(var_type k_type, char* k){
    createAndSendQuery(PULL, k_type, size(k_type,k), k, 0, 0, NULL);
    tests_sent++;
}

bool isReplyType(sdp_msg_t* msg){
    return msg->cmd_rc == PUT_REPLY || msg->cmd_rc == PULL_REPLY;
}

bool isReplyOf(sdp_msg_t* reply, sdp_msg_t* msg){
    if(!isReplyType(reply)){
        return false;
    }

    switch(msg->cmd_rc){
        case PUT:
            return reply->cmd_rc == PUT_REPLY;
        case PULL:
            return reply->cmd_rc == PULL_REPLY;
        default:
            return false;
    }
}

bool test_receive_sdp_msg(sdp_msg_t* reply_msg){

    assert_info(reply_msg, "sdp_msg_t* reply_msg is NULL");

    unreplied_query* q = NULL;

    switch(reply_msg->cmd_rc){
        case PUT_REPLY:
            log_debug("===== Testing PUT %s =====", reply_msg->data);

            q = get_unreplied_query(unreplied_puts, reply_msg->seq);
            assert_info(q, "PUT_REPLY of id: %d was not found on unreplied_puts", reply_msg->seq);

            test_pull_with_size(k_type_from_info2(q->msg->arg1), k_size_from_info2(q->msg->arg1), q->msg->data);

            break;
        case PULL_REPLY:
            q = get_unreplied_query(unreplied_pulls, reply_msg->seq);
            assert_info(q, "PULL_REPLY of id: %d was not found on unreplied_pulls", reply_msg->seq);

            uchar*   expected_v = NULL;
            var_type expected_v_type = 0;
            size_t   expected_v_size = 0;

            for(int i = 0; i < 100; i++){
                spiDBquery* put_query = puts_sent[i];

                //find from the pull that we sent, what the key was
                if(arr_equals(put_query->k_v, q->msg->data, put_query->k_size)){
                    expected_v = &put_query->k_v[put_query->k_size];

                    expected_v_size = put_query->v_size;
                    expected_v_type = put_query->v_type;

                    log_debug("===== Testing PULL %s =====", put_query->k_v);
                    break;
                }
            }

            var_type reply_v_type = reply_msg->arg1;
            size_t reply_v_size = reply_msg->arg2;

            assert_info(reply_v_type == expected_v_type,
                                  "reply_v_type (%d) is different than expected (%d)", reply_v_type, expected_v_type);

            assert_info(reply_v_size == expected_v_size,
                                  "reply_v_size (%d) is different than expected (%d)", reply_v_size, expected_v_size);

            assert_info(arr_equals(reply_msg->data, expected_v, reply_v_size),
                                  "reply_msg->data (s: %s - on %d chars) is different than expected (s: %s)",
                                  reply_msg->data, reply_v_size, expected_v);

            break;
        default:
            log_debug("===== Testing (cmd_rc:%d) %s =====", reply_msg->cmd_rc, reply_msg->data);
            print_msg(reply_msg);
            assert_info(false, "Received invalid cmd_rc: %d (id: %d)", reply_msg->cmd_rc, reply_msg->seq);
            break;
    }

    assert_info(q->msg, "Unreplied query message (q->msg) is NULL");

    assert_info(reply_msg->seq == q->msg->seq,
                          "reply_msg->seq (%04x) != q->msg->seq (%04x)", reply_msg->seq, q->msg->seq);
    assert_info(isReplyOf(reply_msg, q->msg),
                          "reply_msg is NOT a reply of q->msg");

    assert_info(reply_msg->dest_addr == q->msg->srce_addr,
                          "reply_msg->dest_addr (%02x) != q->msg->srce_addr (%02x)", reply_msg->dest_addr, q->msg->srce_addr);
    assert_info(reply_msg->dest_port == q->msg->srce_port,
                          "reply_msg->dest_port (%02x) != q->msg->srce_port (%02x)", reply_msg->dest_port, q->msg->srce_port);

    assert_info(reply_msg->srce_addr == q->msg->dest_addr,
                          "reply_msg->srce_addr (%02x) != q->msg->dest_addr (%02x)", reply_msg->srce_addr, q->msg->dest_addr);
    assert_info(reply_msg->srce_port == q->msg->dest_port,
                           "reply_msg->srce_port (%02x) != q->msg->dest_port (%02x)", reply_msg->srce_port, q->msg->dest_port);

    assert_info(reply_msg->arg1, "reply_msg->arg1 is not set");

    return true;
}

void test_message(sdp_msg_t* reply_msg){
    bool passed = test_receive_sdp_msg(reply_msg);

    if(passed){
        tests_passed++;
        //log_debug("***** PASSED *****");
    }
    else{
        log_debug("!");
        log_debug("!!!!! FAILED !!!!!");
    }

    tests_received++;

    if(tests_received == tests_sent){
        log_debug("%%%%%%%%%%%%%%%%%%%%%%% TESTS FINISHED %%%%%%%%%%%%%%%%%%%%%%%");
        log_debug("%%%%%%%%%%%%%%%%%%%%%%% %d/%d PASSED %%%%%%%%%%%%%%%%%%%%%%%", tests_passed, tests_sent);
    }
    else if(tests_received > tests_sent){
        log_debug("!!!!!!!! Received more tests than we sent. Sent %d, received %d.", tests_sent, tests_received);
    }
}

void run_put_tests(){
    //non printable chars

    test_put(STRING, "Hello", STRING, "World");

    test_put(STRING, "Helloo", STRING, "foo");

    test_put(STRING, "Hell", STRING, "bar");

    test_put(STRING, "A", STRING, "World");

    test_put(STRING, "1234", STRING, "5678");

    test_put(STRING, ".", STRING, "!");

    test_put(STRING, "A1B2C3", STRING, "ABCD");

/*

    test_put(STRING, "A relatively long string... with spaces and other characters in it!", STRING, "uhul");

    test_put(STRING, "uhul", STRING, "A relatively long string... with spaces and other characters in it!");

    uchar longstring[256];
    for(int i = 0; i < 256; i++){
        longstring[i] = 'A';
    }

    test_put(STRING, longstring, STRING, "ABCD");
    */
}