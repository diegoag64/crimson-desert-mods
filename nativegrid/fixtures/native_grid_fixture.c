#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
struct Type {uintptr_t vptr,spare; char name[64];};
struct COL {uint32_t signature,offset,constructor,type,hierarchy,self;};
static struct Type type={0,0,".?AVResourceLoadWorker_Package@pa@@"};
static struct COL locator;
static uint32_t hierarchy[4];
static struct {uintptr_t locator,slots[6];} table;
static uintptr_t worker;
static unsigned char handle[0x48], buffer[128];
static char filename[512]="UI/BIN__/INVENTORYEQUIPMENTPANEL_GAME.UIBINARY";
static char *descriptor=filename;
static unsigned original_calls,mode;
static unsigned inside_full,nested_raw_calls;
static DWORD arg_length,arg_offset;
static const unsigned char before[]="fixture original grid column=6 row=8";
static const unsigned char after[] ="fixture modified grid column=8 row=9";

__declspec(dllexport) __attribute__((noinline,optimize("O0")))
unsigned char fixture_read(void *self,void *h,void *out,DWORD capacity,DWORD length,DWORD offset) {
    if (inside_full) {
        nested_raw_calls++;
        if (self!=&worker || h!=handle || capacity!=10 || length!=arg_length || offset!=arg_offset || GetLastError()!=0x4567) return 0;
        memcpy(out,"grid row=9",10);
        SetLastError(0x7654);return 1;
    }
    original_calls++;
    if (self!=&worker || h!=handle || !out || capacity!=128 || length!=arg_length || offset!=arg_offset || GetLastError()!=0x4567) return 0;
    if (mode!=6) memcpy(out,before,sizeof(before)-1);
    if (mode==2) ((unsigned char *)out)[0]='X';
    SetLastError(0x7654);
    return mode==3 ? 0 : 1;
}

unsigned char fixture_full(void *,void *,void *,void *,DWORD,DWORD);
int legacy_tests(int argc,char **argv) {
    if (argc<2) return 2;
    uintptr_t base=(uintptr_t)GetModuleHandleW(NULL);
    locator.signature=1; locator.type=(uint32_t)((uintptr_t)&type-base);
    locator.hierarchy=(uint32_t)((uintptr_t)&hierarchy-base); locator.self=(uint32_t)((uintptr_t)&locator-base);
    table.locator=(uintptr_t)&locator;
    for (int i=0;i<6;i++) table.slots[i]=(uintptr_t)&fixture_read;
    table.slots[4]=(uintptr_t)&fixture_full;
    worker=(uintptr_t)&table.slots;
    uintptr_t owner=(uintptr_t)&worker,desc=(uintptr_t)&descriptor;
    DWORD size=sizeof(before)-1;
    memcpy(handle+0x20,&owner,8); memcpy(handle+0x28,&desc,8); memcpy(handle+0x38,&size,4);
    if (argc>2 && !strcmp(argv[2],"missing")) type.name[3]='X';
    HMODULE module=LoadLibraryA(argv[1]); if (!module) return 3;
    void (*init)(void)=(void (*)(void))(void *)GetProcAddress(module,"InitializeASI");
    LONG (*status)(void)=(LONG (*)(void))(void *)GetProcAddress(module,"GridStatus");
    LONG (*replaced)(void)=(LONG (*)(void))(void *)GetProcAddress(module,"GridReplacements");
    if (!init || !status || !replaced) return 4;
    init(); init();
    int enabled=status();
    for (unsigned test=0;test<9;test++) {
        mode=0; arg_length=0; arg_offset=0; strcpy(filename,"UI/BIN__/INVENTORYEQUIPMENTPANEL_GAME.UIBINARY");
        memcpy(handle+0x28,&desc,8); memcpy(handle+0x20,&owner,8);
        if (test==1) {arg_length=7; arg_offset=11;} // partial-read args must reach original unchanged.
        if (test==2) mode=2; // original-byte mismatch.
        if (test==3) mode=3; // original failure.
        if (test==4) strcpy(filename,"ui/bin__/unrelated.uibinary");
        if (test==5) {uintptr_t invalid=1; memcpy(handle+0x28,&invalid,8);}
        if (test==6) {uintptr_t invalid=1; memcpy(handle+0x20,&invalid,8);}
        if (test==8) arg_length=sizeof(before)-1;
        memset(buffer,0xcc,sizeof(buffer));
        void *destination=buffer;
        if (test==7) { // Read-only data: original returns success without writing.
            mode=6; destination=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
            if (!destination) return 10;
            memcpy(destination,before,sizeof(before)-1);
            DWORD old; VirtualProtect(destination,4096,PAGE_READONLY,&old);
        }
        SetLastError(0x4567);
        unsigned char result=fixture_read(&worker,handle,destination,128,arg_length,arg_offset);
        if (GetLastError()!=0x7654 || result!=(mode==3 ? 0 : 1)) return 11;
        int change=enabled && (test==0 || test==8);
        if (memcmp(destination,change ? after : before,sizeof(before)-1) && test!=2) return 12;
        if (test==2 && ((unsigned char *)destination)[0]!='X') return 13;
        if (test!=7 && buffer[sizeof(before)-1]!=0xcc) return 14;
        if (test==7) VirtualFree(destination,0,MEM_RELEASE);
    }
    printf("active=%d replacements=%ld original=%u cases=9\n",enabled,replaced(),original_calls);
    return original_calls==9 && replaced()==(enabled ? 2 : 0) ? 0 : 15;
}

struct Buffer {void *data; DWORD capacity,length; unsigned char tracking,pad[7];};
static const char variable_before[]="grid row=9";
#ifdef FIXTURE_SHRINK
static const char variable_after[]="grid";
#else
static const char variable_after[]="grid row=11";
#endif
static unsigned full_mode,full_calls,resize_calls;
static int context_value;

__declspec(dllexport) __attribute__((noinline,optimize("O0")))
void *fixture_resize(void *ptr,DWORD size,void *context) {
    struct Buffer *b=ptr;
    resize_calls++;
    if (context!=&context_value || full_mode==8) return NULL;
    if (b->capacity<size+2) {
        void *next=HeapAlloc(GetProcessHeap(),0,size+2);
        if (!next) return NULL;
        if (b->data) HeapFree(GetProcessHeap(),0,b->data);
        b->data=next; b->capacity=size+2;
    }
    b->length=size;
    ((char *)b->data)[size]=0; ((char *)b->data)[size+1]=0;
    return b->data;
}

__declspec(dllexport) __attribute__((noinline,optimize("O0")))
unsigned char fixture_full(void *self,void *h,void *ptr,void *context,DWORD length,DWORD offset) {
    full_calls++;
    if (self!=&worker || h!=handle || context!=&context_value || length!=arg_length || offset!=arg_offset || GetLastError()!=0x4567) return 0;
    if (full_mode!=7) {
        struct Buffer *b=ptr;
        b->capacity=sizeof(variable_before)+1;
        b->length=sizeof(variable_before)-1; b->tracking=0xff;
        b->data=HeapAlloc(GetProcessHeap(),0,b->capacity);
        inside_full=1;SetLastError(0x4567);
        unsigned char raw=fixture_read(self,h,b->data,b->length,length,offset);
        inside_full=0;
        if (!raw) return 0;
        ((char *)b->data)[b->length]=0;
        ((char *)b->data)[b->length+1]=0;
        if (full_mode==1) ((char *)b->data)[0]='X';
        if (full_mode==6) {DWORD old;VirtualProtect(ptr,4096,PAGE_READONLY,&old);}
    }
    SetLastError(0x7654);
    return full_mode==3 ? 0 : 1;
}

int main(int argc,char **argv) {
    int legacy=legacy_tests(argc,argv); if (legacy) return legacy;
    HMODULE module=GetModuleHandleA(argv[1]);
    if (!module) return 20;
    LONG (*status)(void)=(LONG (*)(void))(void *)GetProcAddress(module,"GridStatus");
    LONG (*replaced)(void)=(LONG (*)(void))(void *)GetProcAddress(module,"GridReplacements");
    int enabled=status();
    for (unsigned test=0;test<10;test++) {
        full_mode=test; arg_length=0;arg_offset=0;
        if (test==2) {arg_length=7;arg_offset=11;}
        if (test==9) arg_length=sizeof(variable_before)-1;
        strcpy(filename,test==5 ? "ui/bin__/unrelated.uibinary" : "ui/bin__/fixture-layout.uibinary");
        uintptr_t owner=test==4 ? 1 : (uintptr_t)&worker,desc=(uintptr_t)&descriptor;
        DWORD size=sizeof(variable_before)-1;
        memcpy(handle+0x20,&owner,8);memcpy(handle+0x28,&desc,8);memcpy(handle+0x38,&size,4);
        struct Buffer *b=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
        if (!b) return 21;
        SetLastError(0x4567);
        unsigned char result=fixture_full(&worker,handle,test==7 ? (void *)1 : b,&context_value,arg_length,arg_offset);
        if (GetLastError()!=0x7654 || result!=(test==3 || (enabled && test==8) ? 0 : 1)) return 22;
        if (test!=7) {
            int change=enabled && (test==0 || test==9);
            const char *expect=change ? variable_after : variable_before;
            DWORD expected=(DWORD)strlen(expect);
            if (b->length!=expected || b->capacity<expected+2 || (test!=1 && memcmp(b->data,expect,expected))) return 23;
            if (((char *)b->data)[expected] || ((char *)b->data)[expected+1]) return 24;
            if (test==1 && ((char *)b->data)[0]!='X') return 25;
            HeapFree(GetProcessHeap(),0,b->data);
        }
        VirtualFree(b,0,MEM_RELEASE);
    }
    printf("full=%u resizes=%u replacements=%ld active=%d nested_raw=%u\n",full_calls,resize_calls,replaced(),enabled,nested_raw_calls);
    return full_calls==10 && nested_raw_calls==9 && resize_calls==(enabled ? 3u : 0u) && replaced()==(enabled ? 4 : 0) ? 0 : 26;
}
