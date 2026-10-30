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
static unsigned char description[0x400],list[0x400],root[0x400],style[0x80];
struct ClassVector { uint32_t *data,count,capacity; };
static uint32_t class_data[16],hidden_atom=571;
static struct ClassVector classes;
static unsigned adds,sorts,cases;
static int add_failure;
static void *seen_vector;
static const uint32_t *seen_atom;
static unsigned calls,hidden;
static void *seen_element;
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
    put(root,0x1a0,(uintptr_t)list);list[0x21f]=1;
    memset(style,0,sizeof(style));put(style,0,(uintptr_t)badge);put(badge,0x20,(uintptr_t)style);
    memset(class_data,0,sizeof(class_data));classes=(struct ClassVector){class_data,2,16};class_data[0]=7;class_data[1]=3;
    put(style,8,(uintptr_t)&classes);hidden_atom=571;add_failure=0;
    refinement_hidden_atom=&hidden_atom;
}
static unsigned char add_class(void *vector,const uint32_t *atom) {
    seen_vector=vector;seen_atom=atom;adds++;SetLastError(888);
    if (add_failure) return 0;
    struct ClassVector *v=vector;
    if (v!=&classes || atom!=&hidden_atom || v->count>=v->capacity) ExitProcess(4);
    v->data[v->count++]=*atom;return 1;
}
static void sort_classes(void *vector) {
    if (vector!=&classes) ExitProcess(5);
    sorts++;SetLastError(777);
    /* A small sort models the native helper without using game code. */
    for (unsigned i=0;i<classes.count;i++) for (unsigned j=i+1;j<classes.count;j++)
        if (classes.data[i]>classes.data[j]) {uint32_t a=classes.data[i];classes.data[i]=classes.data[j];classes.data[j]=a;}
}
__attribute__((noinline,noclone)) static void native_refresh(void *input) {
    seen_error=GetLastError();seen_element=input;hidden=0;calls++;
    for (unsigned i=0;i<classes.count && i<16;i++) if (classes.data[i]==hidden_atom) hidden=1;
    SetLastError(4321);
}
static StyleRefreshFn volatile invoke=native_refresh;
static int verify(const char *name,void *input,unsigned expected,unsigned expected_add) {
    unsigned before=calls,old_adds=adds,old_sorts=sorts;SetLastError(1234);invoke(input);
    if (calls!=before+1 || seen_element!=input || hidden!=expected ||
        seen_error!=1234 || GetLastError()!=4321 || adds!=old_adds+expected_add ||
        sorts!=old_sorts+(expected_add && !add_failure) ||
        (expected_add && (seen_vector!=&classes || seen_atom!=&hidden_atom))) {
        fprintf(stderr,"FAIL: %s\n",name);return 0;
    }
    cases++;printf("PASS: %s\n",name);return 1;
}
#define CHECK(name,expected,added) do {if (!verify(name,style,expected,added)) return 1;} while (0)
int main(void) {
    refinement_add_class=add_class;refinement_sort_classes=sort_classes;
    if (MH_Initialize()!=MH_OK || MH_CreateHook(native_refresh,hooked_style_refresh,(void **)&original_style_refresh)!=MH_OK ||
        MH_EnableHook(native_refresh)!=MH_OK) return 2;
    reset();CHECK("equipped-only tab restores hidden class before native refresh",1,1);
    CHECK("already hidden is idempotent",1,0);
    /* Model both native update paths: removal helper and inlined removal. */
    list[0x21f]=0;classes.count=2;CHECK("inventory tab allows native class removal",0,0);
    list[0x21f]=1;CHECK("return to equipped tab hides reused badge",1,1);
    classes.count=2;CHECK("inlined native removal is corrected at refresh",1,1);
    list[0x21f]=0;CHECK("native hide in inventory stays hidden",1,0);
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
    reset();put(badge,0x20,(uintptr_t)middle);CHECK("wrong style owner fails open",0,0);
    reset();hidden_atom=0;CHECK("uninitialized atom fails open",0,0);
    reset();refinement_hidden_atom=(void *)1;CHECK("unreadable atom fails open",0,0);
    reset();classes.capacity=0;CHECK("invalid vector capacity fails open",0,0);
    reset();classes.count=257;CHECK("oversized vector count bounded",0,0);
    reset();put(style,8,0x12345);CHECK("unreadable vector fails open",0,0);
    reset();add_failure=1;CHECK("failed native addition skips sorting",0,1);
    reset();if (!verify("unreadable style forwarded intact",(void *)1,0,0)) return 1;
    if (MH_DisableHook(native_refresh)!=MH_OK || MH_RemoveHook(native_refresh)!=MH_OK || MH_Uninitialize()!=MH_OK) return 3;
    printf("Refinement refresh detour: %u cases passed; native helper ordering and LastError preserved.\n",cases);return 0;
}
