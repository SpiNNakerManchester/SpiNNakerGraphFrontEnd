#include "../../db-typedefs.h"

static uint32_t q_generated_id = 0;

extern bool send_spiDBquery(spiDBquery* q);
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

typedef enum {
    FAILED  = -1,
    NOT_RUN = 0,
    PASSED  = 1
} TestResult;

char* resultStr(TestResult result){
    switch(result){
        case FAILED: return "FAILED ";
        case PASSED: return "       ";
        case NOT_RUN:return "NOT_RUN";
        default:     return "?";
    }
}

static spiDBquery*    puts_sent[100];
static TestResult     puts_results[100];
static int            total_puts_sent     = 0;
static int            total_puts_received = 0;
static int            total_puts_passed   = 0;

static spiDBquery*    pulls_sent[100];
static TestResult     pulls_results[100];
static int            total_pulls_sent     = 0;
static int            total_pulls_received = 0;
static int            total_pulls_passed   = 0;

/*static {
    for(uint i = 0; i < 100; i++){
        puts_results[i]  = NOT_RUN;
        pulls_results[i] = NOT_RUN;
    }
}*/

void print_results(){
    log_debug("       PUT     PULL");
    for(uint i = 0; i < 100; i++){
        if(puts_sent[i]){
            log_debug("%3d: %s- %s-> %s", i, resultStr(puts_results[i]),
                                                    resultStr(pulls_results[i]), puts_sent[i]->k_v);
        }
    }
}

typedef struct spiDBquerySent {
    spiDBquery* q;
    bool        sent;
} spiDBquerySent;

spiDBquerySent createAndSendQuery(spiDBcommand cmd,
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

    spiDBquerySent qs;
    qs.q = q;
    qs.sent = send_spiDBquery(q);

    return qs;
}

size_t size(var_type t, char* c){
    switch(t){
        case STRING: return strlen(c);
        case UINT32: return sizeof(uint32_t);
        default:     return 0;
    }
}


void record_result(spiDBcommand cmd, uint32_t test_id, bool passed){
    if(test_id >= 0){

        TestResult result = passed ? PASSED : FAILED;

        switch(cmd){
            case PUT_REPLY:
                if(puts_results[test_id] == NOT_RUN){
                    puts_results[test_id] = result;
                    total_puts_received++;
                    if(result == PASSED){
                       total_puts_passed++;
                    }
                }
                else{
                    log_debug("Warning.... received multiple test results...");
                }
                break;
            case PULL_REPLY:
                if(pulls_results[test_id] == NOT_RUN){
                    pulls_results[test_id] = result;
                    total_pulls_received++;
                    if(result == PASSED){
                       total_pulls_passed++;
                    }
                }
                else{
                    log_debug("Warning.... received multiple test results...");
                }
                break;
            default:
                log_debug("Invalid cmd %d", cmd);
                break;
        }
    }
}

void test_put(bool expected_sent, var_type k_type, char* k, var_type v_type, char* v){
    spiDBquerySent qs = createAndSendQuery(PUT, k_type, size(k_type,k), k, v_type, size(v_type,v), v);
    spiDBquery* q = qs.q;
    //TODO PROBLEM IF THE PULL ARRIVES BEFORE AND INCREASES THE ID
    puts_sent[q->id] = q;
    total_puts_sent++;

    if(!qs.sent){
        record_result(PUT_REPLY, q->id, expected_sent ? FAILED : PASSED);
    }
}

void test_pull_with_size(var_type k_type, size_t k_size, char* k, uint32_t put_id){
    spiDBquerySent qs = createAndSendQuery(PULL, k_type, k_size, k, 0, 0, NULL);
    spiDBquery* q = qs.q;

    pulls_sent[put_id] = q;
    total_pulls_sent++;

     if(!qs.sent){
        record_result(PULL_REPLY, q->id, FAILED);
    }
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

#define assert_t(condition, passed_ptr, message, ...)                  \
    do {                                                               \
        if (!(condition))                                              \
            __log(LOG_DEBUG, "[ASSERT]    ", message, ##__VA_ARGS__);  \
        *passed_ptr &= condition;                                      \
    } while (0)


bool test_receive_sdp_msg(sdp_msg_t* reply_msg){

    if(!reply_msg){
        log_debug("sdp_msg_t* reply_msg is NULL");
        return false;
    }

    //todo if some values are null. COMPLAIN and QUIT

    bool passed = true;
    uint32_t test_id = -1;

    unreplied_query* q = NULL;

    switch(reply_msg->cmd_rc){
        case PUT_REPLY:
            log_debug("===== Testing PUT %s =====", reply_msg->data);

            q = get_unreplied_query(unreplied_puts, reply_msg->seq);

            assert_t(q != NULL, &passed, "PUT_REPLY of id: %d was not found on unreplied_puts", reply_msg->seq);

            test_pull_with_size(k_type_from_info(q->msg->arg1), k_size_from_info(q->msg->arg1),
                                q->msg->data, q->msg->seq);

            test_id = q->msg->seq;

            break;
        case PULL_REPLY:
            q = get_unreplied_query(unreplied_pulls, reply_msg->seq);
            assert_t(q != NULL, &passed, "PULL_REPLY of id: %d was not found on unreplied_pulls", reply_msg->seq);

            uchar*   expected_v = NULL;
            var_type expected_v_type = 0;
            size_t   expected_v_size = 0;

            for(int i = 0; i < 100; i++){
                spiDBquery* put_query = puts_sent[i];

                if(!put_query){
                    continue;
                }

                size_t k_size = k_size_from_info(q->msg->arg1);

                //find from the pull that we sent, what the key was
                if(k_size == put_query->k_size && arr_equals(put_query->k_v, q->msg->data, k_size)){
                    log_debug("===== Testing PULL %s =====", put_query->k_v);

                    test_id = put_query->id;

                    expected_v = &put_query->k_v[put_query->k_size];

                    expected_v_size = put_query->v_size;
                    expected_v_type = put_query->v_type;

                    break;
                }
            }

            if(expected_v == NULL){
                log_debug("[WARNING] Cound not find put_query for this PULL");
            }

            var_type reply_v_type = v_type_from_info(reply_msg->arg1);
            size_t reply_v_size   = v_size_from_info(reply_msg->arg1);

            assert_t(reply_v_type == expected_v_type, &passed,
                                  "reply_v_type (%d) is different than expected (%d)", reply_v_type, expected_v_type);

            assert_t(reply_v_size == expected_v_size, &passed,
                                  "reply_v_size (%d) is different than expected (%d)", reply_v_size, expected_v_size);

            assert_t(arr_equals(reply_msg->data, expected_v, reply_v_size), &passed,
                                  "reply_msg->data (s: %s - on %d chars) is different than expected (s: %s)",
                                  reply_msg->data, reply_v_size, expected_v);

            break;
        default:
            log_debug("===== Testing (cmd_rc:%d) %s =====", reply_msg->cmd_rc, reply_msg->data);
            print_msg(reply_msg);
            assert_t(false, &passed, "Received invalid cmd_rc: %d (id: %d)", reply_msg->cmd_rc, reply_msg->seq);
            break;
    }

    assert_t(q->msg != NULL, &passed, "Unreplied query message (q->msg) is NULL");

    assert_t(reply_msg->seq == q->msg->seq, &passed,
                          "reply_msg->seq (%04x) != q->msg->seq (%04x)", reply_msg->seq, q->msg->seq);
    assert_t(isReplyOf(reply_msg, q->msg), &passed,
                          "reply_msg is NOT a reply of q->msg");

    assert_t(reply_msg->dest_addr == q->msg->srce_addr, &passed,
                          "reply_msg->dest_addr (%02x) != q->msg->srce_addr (%02x)", reply_msg->dest_addr, q->msg->srce_addr);
    assert_t(reply_msg->dest_port == q->msg->srce_port, &passed,
                          "reply_msg->dest_port (%02x) != q->msg->srce_port (%02x)", reply_msg->dest_port, q->msg->srce_port);

    assert_t(reply_msg->srce_addr == q->msg->dest_addr, &passed,
                          "reply_msg->srce_addr (%02x) != q->msg->dest_addr (%02x)", reply_msg->srce_addr, q->msg->dest_addr);
    assert_t(reply_msg->srce_port == q->msg->dest_port, &passed,
                           "reply_msg->srce_port (%02x) != q->msg->dest_port (%02x)", reply_msg->srce_port, q->msg->dest_port);

    assert_t(reply_msg->arg1 != 0, &passed, "reply_msg->arg1 is not set");

    record_result(reply_msg->cmd_rc, test_id, passed);

    return passed;
}

void test_message(sdp_msg_t* reply_msg){
    bool passed = test_receive_sdp_msg(reply_msg);

    if(!passed){
        log_debug("!!! ----- FAILED ---- !!!!");
    }
}

void tests_summary(){
    log_debug("==============================================================");
    log_debug("======================= TESTS FINISHED =======================");
    log_debug("==============================================================");
    log_debug("");
    log_debug("  PUT   - Received %d/%d", total_puts_received, total_puts_sent);
    log_debug("        - Passes:  %d/%d", total_puts_passed, total_puts_received);
    log_debug("");
    log_debug("  PULL  - Received %d/%d", total_pulls_received, total_pulls_sent);
    log_debug("        - Passes:  %d/%d", total_pulls_passed, total_pulls_received);
    log_debug("");
    log_debug("==============================================================");
    log_debug("");
    print_results();
    log_debug("");
    log_debug("==============================================================");
}

char* p(char* c, size_t n){
    for(uint i = 0; i < n; i++){
        log_debug("c[%d] = %c", i, c[i]);
    }
}

char* c(uint32_t i){
    return (char*)&i;
}

void run_put_tests(){
    //non printable chars

    //Test String success
    test_put(true, STRING, "Hello",     STRING, "World");
    test_put(true, STRING, "Helloo",    STRING, "foo");
    test_put(true, STRING, "Hell",      STRING, "bar");
    test_put(true, STRING, "Hello1",    STRING, "GG");
    test_put(true, STRING, "HELLO",     STRING, "World");
    test_put(true, STRING, "hello",     STRING, "World");
    test_put(true, STRING, "H",         STRING, "World");

    test_put(true, STRING, ".",         STRING, "!");

    test_put(true, STRING, "1234",      STRING, "5678");
    test_put(true, STRING, "A1B2C3",    STRING, "ABCD");
    test_put(true, STRING, "A1",        STRING, "Test");
    test_put(true, STRING, "1A",        STRING, "Test");
    test_put(true, STRING, "456",       STRING, "Test");
    test_put(true, STRING, "IntValue",  STRING, "159");

    test_put(true, STRING, "A relatively long string... with spaces and other characters in it!", STRING, "uhul");
    test_put(true, STRING, "uhul",      STRING, "A relatively long string... with spaces and other characters in it!");

    //Test String failures
    test_put(false, STRING, "",         STRING, "value");
    test_put(false, STRING, "key",      STRING, "");
    test_put(false, STRING, "",         STRING, "");

    #define INVALID_TYPE -1

    test_put(false, INVALID_TYPE, 234,  UINT32,         456);
    test_put(false, UINT32,       345,  INVALID_TYPE,   567);
    test_put(false, INVALID_TYPE, 234,  UINT32,         456);

    //Test int success
    //todo test very long

    test_put(true, UINT32, c(123),     UINT32, c(456));
    test_put(true, UINT32, c(12),      UINT32, c(456));
    test_put(true, UINT32, c(1234),    UINT32, c(456));

    //Test mixed
    test_put(true, UINT32, c(741),          STRING, "string value");
    test_put(true, STRING, "string key",    UINT32, c(741));

    for(int i = -2; i <= 2; i++)
        test_put(true, UINT32, c(i), UINT32, c(i));

/*
    test_put(0xFF,   "Invalid type", STRING,    "value");
    test_put(STRING, "Valid type",   0xFF,      "value");
    test_put(0xFF,   "Both invalid", 0xFF,      "value");
*/
    //wait for results to arrive....

    //test putting the same value again...
/*

    for(int i = -2; i <= 2; i++)
        for(int j = -2; j <= 2; j++)
            test_put(UINT32, i, UINT32, j);


*/

/*
    uchar longstring[256];
    for(int i = 0; i < 256; i++){
        longstring[i] = 'A';
    }

    test_put(STRING, longstring, STRING, "ABCD");
    */
}