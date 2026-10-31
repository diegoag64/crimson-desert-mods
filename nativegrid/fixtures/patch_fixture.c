/* Generated resources are fixture-only and never included in release ZIPs. */
#include <windows.h>
#include <bcrypt.h>
#include <stdio.h>
#include <string.h>
#include "../runtime/native_grid_patch.h"
#include "native_grid_payloads.h"
#include "patch_fixture_data.h"

#define CHECK(value) do { if (!(value)) {fprintf(stderr,"failed line %d payload %u\n",__LINE__,i);return 1;} cases++; } while (0)
int main(void) {
    unsigned cases=0;
    for (unsigned i=0;i<PAYLOAD_COUNT;i++) {
        const struct Payload *p=&payloads[i];
        unsigned char *original=fixture_originals[i];
        const unsigned char *output=payload_prepare(p,original);
        CHECK(output && !memcmp(output,fixture_expected[i],p->after_size));
        payload_release(output);
        original[0]^=1;
        CHECK(!payload_prepare(p,original));
        original[0]^=1;
        struct Payload bad=*p;
        bad.after_digest[0]^=1;
        CHECK(!payload_prepare(&bad,original));
        bad=*p;
        struct PatchOp op={p->size,1,0};
        bad.ops=&op;bad.op_count=1;
        CHECK(!payload_prepare(&bad,original));
        op.offset=0;op.length=p->after_size+1;
        CHECK(!payload_prepare(&bad,original));
        op.kind=2;op.length=1;
        CHECK(!payload_prepare(&bad,original));
        op.kind=1;op.offset=p->literal_size;
        CHECK(!payload_prepare(&bad,original));
        op.kind=0;op.offset=0;op.length=0;
        CHECK(!payload_prepare(&bad,original));
        op.length=1;
        CHECK(!payload_prepare(&bad,original));
        bad=*p;bad.op_count=0;
        CHECK(!payload_prepare(&bad,original));
        CHECK(!memcmp(original,fixture_original_copies[i],p->size));
    }
    printf("PASS: %u native patch checks across %u resources\n",cases,PAYLOAD_COUNT);
    return 0;
}
