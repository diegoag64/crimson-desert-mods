/* Exercise the real detour and classifier against synthetic native UI objects. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "MinHook.h"
#define REFINEMENT_DESCRIPTION_VT 0x1000u
#define REFINEMENT_LIST_VT 0x2000u
#define REFINEMENT_ROOT_VT 0x3000u
static uintptr_t image_base=0x140000000ull;
static int read_memory(uintptr_t address,void *out,size_t size) {
    SIZE_T got=0;
    int ok=address>0xffff && address+size>=address &&
        ReadProcessMemory(GetCurrentProcess(),(void *)address,out,size,&got) && got==size;
    SetLastError(999); /* The hook must not leak inspection side effects. */
    return ok;
}
#include "../runtime/native_grid_refinement.h"
static unsigned char badge[0x400],card[0x400],middle[0x400],list_element[0x400],root_element[0x400];
static unsigned char description[0x400],list[0x400],root[0x400],state=5;
static unsigned calls,hidden;
static void *seen_element;
static const unsigned char *seen_state;
static DWORD seen_error;
static void put(void *object,size_t offset,uintptr_t value) {memcpy((char *)object+offset,&value,8);}
static void reset(void) {
    memset(badge,0,sizeof(badge));memset(card,0,sizeof(card));memset(middle,0,sizeof(middle));
    memset(list_element,0,sizeof(list_element));memset(root_element,0,sizeof(root_element));
    memset(description,0,sizeof(description));memset(list,0,sizeof(list));memset(root,0,sizeof(root));
    put(badge,0x38,(uintptr_t)card);put(card,0xe0,(uintptr_t)description);
    put(description,0,image_base+REFINEMENT_DESCRIPTION_VT);put(description,8,(uintptr_t)card);
    put(description,0x358,(uintptr_t)badge);put(card,0x38,(uintptr_t)middle);
    put(middle,0x38,(uintptr_t)list_element);put(list_element,0xe0,(uintptr_t)list);
    put(list,0,image_base+REFINEMENT_LIST_VT);put(list,8,(uintptr_t)list_element);
    put(list_element,0x38,(uintptr_t)root_element);put(root_element,0xe0,(uintptr_t)root);
    put(root,0,image_base+REFINEMENT_ROOT_VT);put(root,8,(uintptr_t)root_element);
    put(root,0x1a0,(uintptr_t)list);list[0x21f]=1;state=5;
}
__attribute__((noinline,noclone)) static void native_state(void *element,const unsigned char *kind,unsigned char enabled) {
    seen_error=GetLastError();seen_element=element;seen_state=kind;hidden=enabled;calls++;
    SetLastError(4321);
}
static ElementStateFn volatile invoke=native_state;
static int verify(const char *name,void *element,const unsigned char *kind,unsigned char enabled,unsigned expected) {
    unsigned before=calls;SetLastError(1234);invoke(element,kind,enabled);
    if (calls!=before+1 || seen_element!=element || seen_state!=kind || hidden!=expected ||
        seen_error!=1234 || GetLastError()!=4321) {fprintf(stderr,"FAIL: %s\n",name);return 0;}
    printf("PASS: %s\n",name);return 1;
}
#define CHECK(name,enabled,expected) do {if (!verify(name,badge,&state,enabled,expected)) return 1;} while (0)
int main(void) {
    if (MH_Initialize()!=MH_OK || MH_CreateHook(native_state,hooked_element_state,(void **)&original_element_state)!=MH_OK ||
        MH_EnableHook(native_state)!=MH_OK) return 2;
    reset();CHECK("equipped-only tab suppresses native show",0,1);
    list[0x21f]=0;CHECK("same card shows equipped badge after switching to inventory",0,0);
    list[0x21f]=1;CHECK("same card suppresses badge after switching back",0,1);
    CHECK("native hide remains hidden",1,1);CHECK("nonboolean argument preserved",2,2);
    state=3;CHECK("unrelated native state preserved",0,0);
    reset();put(description,0x358,(uintptr_t)middle);CHECK("other child of same card unchanged",0,0);
    reset();put(description,0,image_base+REFINEMENT_LIST_VT);CHECK("wrong description type unchanged",0,0);
    reset();put(description,8,(uintptr_t)middle);CHECK("wrong description owner unchanged",0,0);
    reset();put(list,0,image_base+REFINEMENT_ROOT_VT);CHECK("wrong list type unchanged",0,0);
    reset();put(list,8,(uintptr_t)middle);CHECK("wrong list owner unchanged",0,0);
    reset();put(root,0,image_base+REFINEMENT_LIST_VT);CHECK("other menu unchanged",0,0);
    reset();put(root,8,(uintptr_t)middle);CHECK("wrong root owner unchanged",0,0);
    reset();put(root,0x1a0,(uintptr_t)description);CHECK("ingredient list unchanged",0,0);
    reset();list[0x21f]=2;CHECK("unknown filter value unchanged",0,0);
    reset();put(card,0xe0,0x12345);CHECK("unreadable control fails open",0,0);
    reset();put(card,0xe0,UINTPTR_MAX-4);CHECK("overflowing control fails open",0,0);
    reset();put(middle,0x38,(uintptr_t)card);CHECK("cyclic parent chain bounded",0,0);
    reset();put(middle,0x38,(uintptr_t)middle);CHECK("self parent bounded",0,0);
    reset();put(middle,0xe0,(uintptr_t)list);put(list,8,(uintptr_t)middle);
    put(list_element,0xe0,(uintptr_t)description);put(description,0,image_base+REFINEMENT_LIST_VT);
    /* The description guard itself rejects this inconsistent tree. */
    CHECK("inconsistent owner graph fails open",0,0);
    if (!verify("unreadable state forwarded intact",badge,(const unsigned char *)1,0,0)) return 1;
    if (!verify("unreadable element forwarded intact",(void *)1,&state,0,0)) return 1;
    if (MH_DisableHook(native_state)!=MH_OK || MH_RemoveHook(native_state)!=MH_OK || MH_Uninitialize()!=MH_OK) return 3;
    puts("Refinement detour: 22 cases passed; arguments and LastError preserved.");return 0;
}
