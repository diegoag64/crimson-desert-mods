/* Detour ABI and cache lifecycle tests. No game process is opened. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "MinHook.h"
#define CRAFTING_DESCRIPTION_VT 0x1000u
#define CRAFTING_CARD_VT 0x2000u
#define CRAFTING_LIST_VT 0x3000u
#define CRAFTING_ROOT_VT 0x4000u
static uintptr_t image_base=0x140000000ull;
static int read_memory(uintptr_t address,void *out,size_t size) {
    SIZE_T got=0;
    int ok=address>0xffff && address+size>=address &&
        ReadProcessMemory(GetCurrentProcess(),(void *)address,out,size,&got) && got==size;
    SetLastError(999);return ok;
}
#include "../runtime/native_grid_crafting.h"
static unsigned char image[0x200],card[0x200],outer[0x200],list_node[0x200],root_node[0x200];
static unsigned char description[0x200],outer_control[0x200],list_control[0x200],root_control[0x200];
static unsigned char layout[0x80],style[0x80],bounds[32],size_arg[16],state[320],context[32];
static unsigned char parent_layouts[3][0x80];
static uintptr_t images[8];
static unsigned cases,calls,sizes,positions;
static unsigned char native_result;
static int helper_fails,helper_empty,nested_call,native_fills;
static unsigned tree_depth;
static unsigned char native_layout(void *,void *,void *,void *,void *);
static void *expected_layout;
static void put(void *object,size_t offset,uintptr_t value) {memcpy((char *)object+offset,&value,8);}
static void floats(void *object,size_t offset,const float *values,size_t count) {
    memcpy((char *)object+offset,values,count*sizeof(float));
}
static void control(void *element,void *owner,uintptr_t type) {
    put(element,0xe0,(uintptr_t)owner);put(owner,0,image_base+type);put(owner,8,(uintptr_t)element);
}
static void reset(void) {
    void *objects[]={image,card,outer,list_node,root_node,description,outer_control,list_control,root_control};
    for (unsigned i=0;i<sizeof(objects)/sizeof(*objects);i++) memset(objects[i],0,0x200);
    memset(layout,0,sizeof(layout));memset(style,0,sizeof(style));memset(images,0,sizeof(images));
    memset(parent_layouts,0,sizeof(parent_layouts));tree_depth=0;
    put(layout,0,(uintptr_t)image);put(image,0x18,(uintptr_t)layout);
    put(image,0x20,(uintptr_t)style);put(style,0,(uintptr_t)image);
    floats(image,0x78,(float[]){165.333f,101.333f},2);
    put(image,0x38,(uintptr_t)card);control(card,description,CRAFTING_DESCRIPTION_VT);
    images[0]=(uintptr_t)image;put(description,0x168,(uintptr_t)images);description[0x170]=1;
    put(card,0x38,(uintptr_t)outer);control(outer,outer_control,CRAFTING_CARD_VT);
    put(outer,0x38,(uintptr_t)list_node);control(list_node,list_control,CRAFTING_LIST_VT);
    put(list_node,0x38,(uintptr_t)root_node);control(root_node,root_control,CRAFTING_ROOT_VT);
    calls=sizes=positions=0;native_result=0xa7;helper_fails=helper_empty=nested_call=native_fills=0;
    expected_layout=layout;
}
__attribute__((noinline)) static unsigned char native_layout_body(void *a,void *b,void *c,void *d,void *e) {
    int parent=-1;
    for (unsigned i=0;i<tree_depth;i++) if (a==parent_layouts[i]) parent=(int)i;
    if ((a!=expected_layout && !(tree_depth && (a==layout || parent>=0))) ||
        b!=bounds || c!=size_arg || d!=state || e!=context ||
        GetLastError()!=123) ExitProcess(4);
    calls++;
    if (parent>=0) {
        void *child=(unsigned)(parent+1)<tree_depth ? parent_layouts[parent+1] : layout;
        unsigned char child_result=native_layout(child,b,c,d,e);
        if (child_result!=native_result || GetLastError()!=456) ExitProcess(7);
        SetLastError(456);return native_result;
    }
    if (native_fills) floats(style,0x3c,(float[]){48,26.667f,69.333f,69.333f},4);
    SetLastError(456);return native_result;
}
/* A stable, unoptimized prologue makes the fixture exercise MinHook itself. */
__attribute__((noinline,optimize("O0"))) static unsigned char native_layout(void *a,void *b,void *c,void *d,void *e) {
    return native_layout_body(a,b,c,d,e);
}
static unsigned char background_size(void *a,void *b,unsigned char c,unsigned char d) {
    if (a!=layout || b!=context || c!=38 || d!=40 || !calls || positions) ExitProcess(5);
    sizes++;
    if (nested_call) {
        nested_call=0;SetLastError(123);
        native_layout(layout,bounds,size_arg,state,context);
    }
    if (!helper_fails && !helper_empty) floats(style,0x44,(float[]){69.333f,69.333f},2);
    SetLastError(888);return !helper_fails;
}
static unsigned char background_position(void *a,void *b,unsigned char c,unsigned char d) {
    if (a!=layout || b!=context || c!=38 || d!=39 || sizes!=1) ExitProcess(6);
    positions++;floats(style,0x3c,(float[]){48,26.667f},2);SetLastError(777);return 1;
}
static int verify(const char *name,unsigned want_size,unsigned want_position,unsigned want_calls) {
    SetLastError(123);
    unsigned char result=native_layout(expected_layout,bounds,size_arg,state,context);
    if (result!=native_result || GetLastError()!=456 || sizes!=want_size ||
        positions!=want_position || calls!=want_calls || crafting_repair_depth) {
        fprintf(stderr,"FAIL %s: return=%u calls=%u size=%u position=%u error=%lu\n",
                name,result,calls,sizes,positions,GetLastError());return 0;
    }
    cases++;return 1;
}
#define CHECK(name,s,p,c) do {if (!verify(name,s,p,c)) return 1;} while (0)
int main(void) {
    crafting_background_size=background_size;crafting_background_position=background_position;
    if (MH_Initialize()!=MH_OK ||
        MH_CreateHook(native_layout,hooked_crafting_layout,(void **)&original_crafting_layout)!=MH_OK ||
        MH_EnableHook(native_layout)!=MH_OK) return 3;
    reset();CHECK("first blank card",1,1,1);
    sizes=positions=calls=0;CHECK("settled card needs no repeat",0,0,1);
    memset(style+0x3c,0,16);sizes=positions=calls=0;CHECK("recycled card cache cleared",1,1,1);
    reset();native_fills=1;CHECK("native layout already populated cache",0,0,1);
    reset();helper_fails=1;CHECK("resource unavailable",1,0,1);
    helper_fails=0;sizes=positions=calls=0;CHECK("retry on later native pass",1,1,1);
    reset();helper_empty=1;CHECK("helper succeeded without image",1,0,1);
    reset();nested_call=1;CHECK("nested layout cannot recurse repair",1,1,2);
    reset();tree_depth=1;expected_layout=parent_layouts[0];CHECK("native parent lays out recipe image",1,1,2);
    reset();tree_depth=3;expected_layout=parent_layouts[0];CHECK("native document card and description descend to image",1,1,4);
    reset();tree_depth=3;nested_call=1;expected_layout=parent_layouts[0];CHECK("native tree allowed while helper reentry is blocked",1,1,5);
    reset();tree_depth=3;helper_fails=1;expected_layout=parent_layouts[0];CHECK("nested image resource unavailable",1,0,4);
    helper_fails=0;sizes=positions=calls=0;CHECK("nested image retries on next document layout",1,1,4);
    reset();native_result=0;CHECK("native failure forwarded",0,0,1);
    reset();floats(style,0x3c,(float[]){1,0,0,0},4);CHECK("nonempty cache untouched",0,0,1);
    reset();floats(style,0x3c,(float[]){NAN,0,0,0},4);CHECK("invalid cache untouched",0,0,1);
    reset();floats(image,0x78,(float[]){0,101},2);CHECK("zero width untouched",0,0,1);
    reset();floats(image,0x78,(float[]){124,NAN},2);CHECK("invalid size untouched",0,0,1);
    reset();put(image,0x18,0);CHECK("wrong layout back pointer",0,0,1);
    reset();put(style,0,0);CHECK("wrong style owner",0,0,1);
    reset();put(description,0,image_base+CRAFTING_CARD_VT);CHECK("wrong description type",0,0,1);
    reset();put(description,8,0);CHECK("wrong description owner",0,0,1);
    reset();description[0x170]=0;CHECK("empty image vector",0,0,1);
    reset();description[0x170]=9;CHECK("oversized image vector bounded",0,0,1);
    reset();put(description,0x168,1);CHECK("unreadable image vector",0,0,1);
    reset();images[0]=(uintptr_t)card;CHECK("other InfoDescription child",0,0,1);
    reset();put(outer_control,0,image_base+CRAFTING_ROOT_VT);CHECK("not a recipe card",0,0,1);
    reset();put(list_control,8,0);CHECK("wrong list owner",0,0,1);
    reset();put(root_control,0,image_base+CRAFTING_LIST_VT);CHECK("other menu",0,0,1);
    reset();put(root_control,8,0);CHECK("wrong root owner",0,0,1);
    reset();put(outer,0x38,(uintptr_t)root_node);CHECK("missing recipe list",0,0,1);
    reset();put(root_node,0xe0,0);put(root_node,0x38,(uintptr_t)outer);CHECK("cyclic tree bounded",0,0,1);
    reset();put(list_node,0x38,(uintptr_t)list_node);CHECK("self parent",0,0,1);
    reset();put(image,0x20,UINTPTR_MAX-4);CHECK("overflowing style address",0,0,1);
    reset();expected_layout=(void *)1;CHECK("unreadable layout forwarded",0,0,1);
    if (MH_DisableHook(native_layout)!=MH_OK || MH_RemoveHook(native_layout)!=MH_OK || MH_Uninitialize()!=MH_OK) return 3;
    printf("Crafting cache detour: %u cases passed; five arguments, return, reentrancy and LastError preserved.\n",cases);
    return 0;
}
