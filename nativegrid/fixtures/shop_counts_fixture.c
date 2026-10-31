/* Exercise pooled stock-label state through the shared native layout detour. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "MinHook.h"
static unsigned char atoms[32];
static uintptr_t image_base;
#define SHOP_COUNTS_NEGATIVE_ATOM_RVA 0u
#define SHOP_COUNTS_DESCRIPTION_VT 0x1000u
#define SHOP_COUNTS_LIST_VT 0x2000u
#define SHOP_COUNTS_ROOT_VT 0x3000u
#define CRAFTING_DESCRIPTION_VT 0x4000u
#define CRAFTING_CARD_VT 0x5000u
#define CRAFTING_LIST_VT 0x6000u
#define CRAFTING_ROOT_VT 0x7000u
static int read_memory(uintptr_t address,void *out,size_t size) {
    SIZE_T got=0;
    int ok=address>0xffff && address+size>=address &&
        ReadProcessMemory(GetCurrentProcess(),(void *)address,out,size,&got) && got==size;
    SetLastError(999);return ok;
}
#include "../runtime/native_grid_shop_counts.h"
#ifndef FIXTURE_NO_SHOP_REPAIR
#define SHOP_COUNTS_PREPARE shop_counts_prepare
#endif
#include "../runtime/native_grid_crafting.h"
static unsigned char label[0x200],wrap[0x200],card[0x200],list[0x200],root[0x200];
static unsigned char controls[3][32],style[0x100],layout[0x80],parent_layout[0x80];
static unsigned char local[0xc0],rule[0xc0],local_map[85],rule_map[85],local_value[16],rule_value[16];
static unsigned char vector[16],bounds[8],size_arg[8],state[8],context[8];
static uint32_t classes[2];static uintptr_t rules[1],name;
static unsigned removes,calls,cases,want_removes,depth;
static int nested,helper_reentry;
static unsigned char native_layout(void *,void *,void *,void *,void *);
static void put(void *p,size_t offset,uintptr_t value) {memcpy((char *)p+offset,&value,8);}
static void put32(void *p,size_t offset,uint32_t value) {memcpy((char *)p+offset,&value,4);}
static void property(void *p,float f) {
    memset(p,0,16);memcpy(p,&f,4);((unsigned char *)p)[8]=149;
    ((unsigned char *)p)[12]=84;((unsigned char *)p)[13]=1;
}
static void reset(void) {
    void *nodes[]={label,wrap,card,list,root};
    for (unsigned i=0;i<5;i++) memset(nodes[i],0,0x200);
    memset(style,0,sizeof(style));memset(layout,0,sizeof(layout));
    memset(local,0,sizeof(local));memset(rule,0,sizeof(rule));
    memset(local_map,255,sizeof(local_map));memset(rule_map,255,sizeof(rule_map));
    image_base=(uintptr_t)atoms;put32(atoms,0,77);classes[0]=88;classes[1]=77;
    put(vector,0,(uintptr_t)classes);put32(vector,8,1);
    put(layout,0,(uintptr_t)label);put(label,0x18,(uintptr_t)layout);
    put(label,0x20,(uintptr_t)style);put(style,0,(uintptr_t)label);
    put(style,8,(uintptr_t)vector);put(style,0x30,(uintptr_t)local);
    rules[0]=(uintptr_t)rule;put(style,0x10,(uintptr_t)rules);put32(style,0x18,1);
    name=(uintptr_t)"ItemAvailableCountText";put(label,0x60,(uintptr_t)&name);
    put(label,0x38,(uintptr_t)wrap);put(wrap,0x38,(uintptr_t)card);
    put(card,0x38,(uintptr_t)list);put(list,0x38,(uintptr_t)root);
    void *owners[]={card,list,root};
    for (unsigned i=0;i<3;i++) {
        put(owners[i],0xe0,(uintptr_t)controls[i]);
        put(controls[i],0,image_base+0x1000*(i+1));put(controls[i],8,(uintptr_t)owners[i]);
    }
    void *blocks[]={local,rule};unsigned char *maps[]={local_map,rule_map};void *values[]={local_value,rule_value};
    for (unsigned i=0;i<2;i++) {
        put(blocks[i],0x70,(uintptr_t)values[i]);put32(blocks[i],0x78,1);
        put(blocks[i],0x80,(uintptr_t)maps[i]);put32(blocks[i],0x88,85);maps[i][84]=0;
    }
    property(local_value,27);property(rule_value,14);
    removes=calls=depth=0;nested=helper_reentry=0;
}
static void remove_property(void *s,const unsigned char *key,unsigned char flag) {
    if (s!=style || *key!=84 || flag || shop_count_depth!=1) ExitProcess(10);
    removes++;
    if (helper_reentry) {
        SetLastError(123);
        if (native_layout(layout,bounds,size_arg,state,context)!=167 || GetLastError()!=456) ExitProcess(11);
    }
    local_map[84]=255;SetLastError(777);
}
__attribute__((noinline)) static unsigned char native_body(void *a,void *b,void *c,void *d,void *e) {
    if (b!=bounds || c!=size_arg || d!=state || e!=context || GetLastError()!=123) ExitProcess(12);
    calls++;
    if (a==parent_layout && !depth++) {
        if (native_layout(layout,b,c,d,e)!=167 || GetLastError()!=456) ExitProcess(13);
    } else if (a!=layout) ExitProcess(14);
    /* The removal must precede text measurement in ordinary layout. */
    if (!shop_count_depth && removes!=want_removes) ExitProcess(15);
    SetLastError(456);return 167;
}
__attribute__((noinline,optimize("O0"))) static unsigned char native_layout(void *a,void *b,void *c,void *d,void *e) {
    return native_body(a,b,c,d,e);
}
static int check(const char *name_test,unsigned expected,unsigned expected_calls) {
    want_removes=expected;SetLastError(123);
    unsigned char result=native_layout(nested ? parent_layout : layout,bounds,size_arg,state,context);
    if (result!=167 || GetLastError()!=456 || removes!=expected || calls!=expected_calls || shop_count_depth) {
        fprintf(stderr,"FAIL %s: removes=%u calls=%u error=%lu\n",name_test,removes,calls,GetLastError());return 0;
    }
    cases++;return 1;
}
#define CHECK(name,n,c) do {if (!check(name,n,c)) return 1;} while (0)
int main(void) {
    shop_remove_property=remove_property;
    /* Keep the excluded repair reachable in the before-fix regression build. */
    if (GetEnvironmentVariableA("FIXTURE_UNUSED",NULL,0)) shop_counts_prepare(NULL);
    if (MH_Initialize()!=MH_OK || MH_CreateHook(native_layout,hooked_crafting_layout,(void **)&original_crafting_layout)!=MH_OK || MH_EnableHook(native_layout)!=MH_OK) return 2;
    reset();CHECK("recycled numeric count cleared before layout",1,1);
    calls=0;CHECK("second layout is idempotent",1,1);
    reset();nested=1;CHECK("parent to child native traversal",1,2);
    reset();helper_reentry=1;CHECK("helper reentry does not recurse",1,2);
    reset();put32(vector,8,2);CHECK("requirement state retains inline height",0,1);
    put32(vector,8,1);calls=0;CHECK("requirement becomes numeric",1,1);
    for (unsigned i=0;i<20;i++) {
        local_map[84]=0;put32(vector,8,2);calls=0;CHECK("recycled requirement retains formatting",1,1);
        put32(vector,8,1);calls=removes=0;CHECK("recycled number clears override again",1,1);
    }
    reset();put32(label,0x48,2);CHECK("generated requirement children excluded",0,1);
    reset();local_map[84]=255;CHECK("fresh numeric label unchanged",0,1);
    reset();property(local_value,14);CHECK("correct inline height unchanged",0,1);
    reset();property(local_value,30);CHECK("unknown inline height unchanged",0,1);
    reset();local_value[13]=2;CHECK("percentage unit excluded",0,1);
    reset();local_value[8]=0;CHECK("wrong property type excluded",0,1);
    reset();name=(uintptr_t)"ItemInventoryHaveCountText";CHECK("owned count excluded",0,1);
    reset();put(label,0x60,1);CHECK("unreadable ID excluded",0,1);
    reset();put(label,0x18,1);CHECK("layout back pointer required",0,1);
    reset();put(style,0,1);CHECK("style back pointer required",0,1);
    reset();put32(vector,8,257);CHECK("oversized class vector excluded",0,1);
    reset();put32(atoms,0,0);CHECK("uninitialized requirement atom excluded",0,1);
    reset();put(vector,0,1);CHECK("unreadable class storage excluded",0,1);
    reset();put32(local,0x88,300);CHECK("oversized property map excluded",0,1);
    reset();local_map[84]=2;CHECK("property index bounded",0,1);
    reset();put(local,0x70,1);CHECK("unreadable property excluded",0,1);
    reset();property(rule_value,26);CHECK("unmodified list stylesheet excluded",0,1);
    reset();put32(style,0x18,65);CHECK("oversized rules excluded",0,1);
    reset();put(controls[0],0,0);CHECK("wrong card owner excluded",0,1);
    reset();put(controls[0],8,0);CHECK("owner back pointer required",0,1);
    reset();put(controls[1],0,0);CHECK("stock list required",0,1);
    reset();put(controls[2],0,image_base+CRAFTING_ROOT_VT);CHECK("other menu excluded",0,1);
    reset();put(list,0x38,(uintptr_t)list);CHECK("cyclic ancestor bounded",0,1);
    MH_DisableHook(native_layout);MH_Uninitialize();
    printf("Shop stock layout: %u cases passed; pooled states, scope, ABI and LastError preserved.\n",cases);
    return 0;
}
