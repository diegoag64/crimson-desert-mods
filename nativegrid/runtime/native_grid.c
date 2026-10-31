/* Exact-byte decoded substitutions, including native resizing. Signed archives remain untouched. */
#include <windows.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "MinHook.h"
#include "native_grid_config.h"

struct Payload { const char *path; const unsigned char *before,*after; DWORD size,after_size; };
#include "native_grid_payloads.h"
typedef unsigned char (*ReadFn)(void *,void *,void *,DWORD,DWORD,DWORD);
static ReadFn original_read;
typedef unsigned char (*FullReadFn)(void *,void *,void *,void *,DWORD,DWORD);
typedef void *(*ResizeFn)(void *,DWORD,void *);
static FullReadFn original_full;
static ResizeFn resize_buffer;
struct BufferDescriptor { void *data; DWORD capacity,length; unsigned char tracking; unsigned char padding[7]; };
_Static_assert(sizeof(struct BufferDescriptor)==24,"Native buffer descriptor size");
static uintptr_t image_base;
static DWORD image_size;
static HANDLE log_file=INVALID_HANDLE_VALUE;
static SRWLOCK log_lock=SRWLOCK_INIT;
static LONG initialized,active,calls,replacements;
static LONG reports[PAYLOAD_COUNT];

static int read_memory(uintptr_t address,void *out,size_t size) {
    SIZE_T got=0;
    return address>0xffff && address+size>=address &&
        ReadProcessMemory(GetCurrentProcess(),(void *)address,out,size,&got) && got==size;
}
static void write_log(const char *text) {
    if (log_file==INVALID_HANDLE_VALUE) return;
    DWORD written;
    AcquireSRWLockExclusive(&log_lock);
    WriteFile(log_file,text,(DWORD)strlen(text),&written,NULL);
    ReleaseSRWLockExclusive(&log_lock);
}
#ifdef REFINEMENT_REFRESH_RVA
static LONG refinement_hides;
static void refinement_report_hide(void) {
    if (InterlockedIncrement(&refinement_hides)<=8)
        write_log("REFINEMENT: kept Equipped Gear badge hidden during native style refresh.\r\n");
}
#define REFINEMENT_REPORT_HIDE refinement_report_hide
#include "native_grid_refinement.h"
#endif
#ifdef CRAFTING_LAYOUT_RVA
static LONG crafting_repairs;
static void crafting_report_repair(void) {
    if (InterlockedIncrement(&crafting_repairs)<=8)
        write_log("CRAFTING: repaired empty recipe background with native layout helpers.\r\n");
}
#define CRAFTING_REPORT_REPAIR crafting_report_repair
#include "native_grid_crafting.h"
#endif
#include "native_grid_flexible_resolver.h"

static int handle_path(uintptr_t handle,char path[512]) {
    uintptr_t descriptor,text;
    if (!read_memory(handle+0x28,&descriptor,8) || !read_memory(descriptor,&text,8)) return 0;
    for (size_t i=0;i<512;i++) {
        char c;
        if (!read_memory(text+i,&c,1)) return 0;
        if (!c) {path[i]=0; return i>0;}
        if ((unsigned char)c<32 || (unsigned char)c>126) return 0;
        if (c>='A' && c<='Z') c+='a'-'A';
        path[i]=c=='\\' ? '/' : c;
    }
    return 0;
}
static int writable(void *buffer,DWORD size) {
    uintptr_t at=(uintptr_t)buffer,end=at+size;
    if (at<0x10000 || end<at) return 0;
    while (at<end) {
        MEMORY_BASIC_INFORMATION m;
        if (!VirtualQuery((void *)at,&m,sizeof(m)) || m.State!=MEM_COMMIT ||
            (m.Protect&(PAGE_GUARD|PAGE_NOACCESS)) ||
            !(m.Protect&(PAGE_READWRITE|PAGE_WRITECOPY))) return 0;
        uintptr_t next=(uintptr_t)m.BaseAddress+m.RegionSize;
        if (next<=at) return 0;
        at=next;
    }
    return 1;
}
static void substitute(void *self,void *handle,void *buffer,DWORD capacity,DWORD length,DWORD offset,unsigned char result) {
    DWORD declared=0; uintptr_t owner=0;
    if (!read_memory((uintptr_t)handle+0x38,&declared,4)) return;
    int candidate=0;
    for (unsigned i=0;i<PAYLOAD_COUNT;i++) if (declared==payloads[i].size) candidate=1;
    if (!candidate) return;
    char path[512];
    if (!handle_path((uintptr_t)handle,path)) return;
    for (unsigned i=0;i<PAYLOAD_COUNT;i++) {
        const struct Payload *p=&payloads[i];
        if (p->after_size!=p->size || strcmp(path,p->path)) continue;
        const char *status="SKIP: failed, partial or unexpected read";
        if (result && declared==p->size && capacity>=p->size && offset==0 &&
            (length==0 || length==p->size) &&
            read_memory((uintptr_t)handle+0x20,&owner,8) && owner==(uintptr_t)self &&
            writable(buffer,p->size)) {
            unsigned char *copy=HeapAlloc(GetProcessHeap(),0,p->size);
            status="SKIP: original bytes differ or unavailable";
            if (copy && read_memory((uintptr_t)buffer,copy,p->size) && !memcmp(copy,p->before,p->size)) {
                memcpy(buffer,p->after,p->size);
                InterlockedIncrement(&replacements);
                status="REPLACED: original bytes matched exactly";
            }
            if (copy) HeapFree(GetProcessHeap(),0,copy);
        }
        if (InterlockedIncrement(&reports[i])<=8) {
            char line[768];
            snprintf(line,sizeof(line),"%s | %s | bytes=%lu capacity=%lu length=%lu offset=%lu result=%u\r\n",
                status,path,(unsigned long)declared,(unsigned long)capacity,(unsigned long)length,(unsigned long)offset,result);
            write_log(line);
        }
        return;
    }
}
static unsigned char hooked_read(void *self,void *handle,void *buffer,DWORD capacity,DWORD length,DWORD offset) {
    /* Six arguments and AL result established from both callers and callee. */
    unsigned char result=original_read(self,handle,buffer,capacity,length,offset);
    DWORD last_error=GetLastError();
    LONG count=InterlockedIncrement(&calls);
    if (count==1 || count==1000 || count==10000 || count==100000) {
        char line[100]; snprintf(line,sizeof(line),"read calls=%ld replacements=%ld\r\n",count,replacements); write_log(line);
    }
    substitute(self,handle,buffer,capacity,length,offset,result);
    SetLastError(last_error);
    return result;
}
static unsigned char hooked_full(void *self,void *handle,void *descriptor,void *context,DWORD length,DWORD offset) {
    unsigned char result=original_full(self,handle,descriptor,context,length,offset);
    DWORD last_error=GetLastError();
    DWORD declared=0; uintptr_t owner=0; char path[512];
    struct BufferDescriptor buffer;
    if (!result || offset || !read_memory((uintptr_t)handle+0x38,&declared,4) ||
        (length && length!=declared)) goto done;
    int candidate=0;
    for (unsigned i=0;i<PAYLOAD_COUNT;i++)
        if (payloads[i].after_size!=payloads[i].size && payloads[i].size==declared) candidate=1;
    if (!candidate || !read_memory((uintptr_t)handle+0x20,&owner,8) || owner!=(uintptr_t)self ||
        !handle_path((uintptr_t)handle,path) ||
        !read_memory((uintptr_t)descriptor,&buffer,sizeof(buffer)) || !writable(descriptor,sizeof(buffer)) ||
        buffer.length!=declared || buffer.capacity<declared+2 || !writable(buffer.data,buffer.capacity)) goto done;
    for (unsigned i=0;i<PAYLOAD_COUNT;i++) {
        const struct Payload *p=&payloads[i];
        if (p->after_size==p->size || p->size!=declared || strcmp(path,p->path)) continue;
        const char *status="SKIP resized: original bytes differ or unavailable";
        unsigned char *copy=HeapAlloc(GetProcessHeap(),0,p->size);
        if (copy && read_memory((uintptr_t)buffer.data,copy,p->size) && !memcmp(copy,p->before,p->size)) {
            /* The game's own resize routine owns allocation, release, length and terminators. */
            void *destination=resize_buffer(descriptor,p->after_size,context);
            struct BufferDescriptor resized;
            if (destination && read_memory((uintptr_t)descriptor,&resized,sizeof(resized)) &&
                resized.data==destination && resized.length==p->after_size && resized.capacity>=p->after_size+2 &&
                writable(destination,p->after_size+2)) {
                memcpy(destination,p->after,p->after_size);
                InterlockedIncrement(&replacements);
                status="REPLACED resized: original bytes matched exactly";
            } else {
                /* Never return an uninitialized or truncated asset as a successful read. */
                result=0; status="FAILED: native buffer resize";
            }
        }
        if (copy) HeapFree(GetProcessHeap(),0,copy);
        if (InterlockedIncrement(&reports[i])<=8) {
            char line[768]; snprintf(line,sizeof(line),"%s | %s | before=%lu after=%lu\r\n",status,path,(unsigned long)p->size,(unsigned long)p->after_size); write_log(line);
        }
        break;
    }
done:
    SetLastError(last_error); return result;
}
__declspec(dllexport) LONG GridStatus(void) {return active;}
__declspec(dllexport) LONG GridReplacements(void) {return replacements;}
__declspec(dllexport) void InitializeASI(void) {
    if (InterlockedExchange(&initialized,1)) return;
    log_file=CreateFileW(PROBE_LOG,GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if (log_file==INVALID_HANDLE_VALUE) return;
    write_log("NativeGrid v5: exact-byte decoded UI replacement; no archive writes.\r\n");
    wchar_t exe[32768]; DWORD n=GetModuleFileNameW(NULL,exe,32768);
    if (!n || n>=32768 || !fingerprint(exe)) {write_log("DISABLED: executable fingerprint mismatch.\r\n"); return;}
    image_base=(uintptr_t)GetModuleHandleW(NULL);
    void *target=resolve_named_read(5,expected_prefix);
    if (!target) {write_log("DISABLED: named interface or function fingerprint not unique/valid.\r\n"); return;}
    void *full=resolve_named_read(4,expected_full_prefix);
    unsigned char prefix[24];
    if (!full || !read_memory(image_base+RESIZE_RVA,prefix,sizeof(prefix)) ||
        memcmp(prefix,expected_resize_prefix,sizeof(prefix))) {write_log("DISABLED: full read or resize fingerprint mismatch.\r\n"); return;}
    resize_buffer=(ResizeFn)(image_base+RESIZE_RVA);
#ifdef REFINEMENT_REFRESH_RVA
    void *style_refresh=(void *)(image_base+REFINEMENT_REFRESH_RVA);
    if (!read_memory((uintptr_t)style_refresh,prefix,sizeof(prefix)) ||
        memcmp(prefix,expected_refinement_refresh_prefix,sizeof(prefix)) ||
        !read_memory(image_base+REFINEMENT_ADD_CLASS_RVA,prefix,sizeof(prefix)) ||
        memcmp(prefix,expected_refinement_add_class_prefix,sizeof(prefix)) ||
        !read_memory(image_base+REFINEMENT_SORT_CLASSES_RVA,prefix,sizeof(prefix)) ||
        memcmp(prefix,expected_refinement_sort_classes_prefix,sizeof(prefix))) {
        write_log("DISABLED: refinement style/helper fingerprint mismatch.\r\n"); return;
    }
    refinement_add_class=(AddClassFn)(image_base+REFINEMENT_ADD_CLASS_RVA);
    refinement_sort_classes=(SortClassesFn)(image_base+REFINEMENT_SORT_CLASSES_RVA);
    refinement_hidden_atom=(const uint32_t *)(image_base+REFINEMENT_HIDDEN_ATOM_RVA);
#endif
#ifdef CRAFTING_LAYOUT_RVA
    void *crafting_layout=(void *)(image_base+CRAFTING_LAYOUT_RVA);
    if (!read_memory((uintptr_t)crafting_layout,prefix,sizeof(prefix)) ||
        memcmp(prefix,expected_crafting_layout_prefix,sizeof(prefix)) ||
        !read_memory(image_base+CRAFTING_BACKGROUND_SIZE_RVA,prefix,sizeof(prefix)) ||
        memcmp(prefix,expected_crafting_background_size_prefix,sizeof(prefix)) ||
        !read_memory(image_base+CRAFTING_BACKGROUND_POSITION_RVA,prefix,sizeof(prefix)) ||
        memcmp(prefix,expected_crafting_background_position_prefix,sizeof(prefix))) {
        write_log("DISABLED: crafting layout/helper fingerprint mismatch.\r\n"); return;
    }
    crafting_background_size=(CraftingBackgroundFn)(image_base+CRAFTING_BACKGROUND_SIZE_RVA);
    crafting_background_position=(CraftingBackgroundFn)(image_base+CRAFTING_BACKGROUND_POSITION_RVA);
#endif
    MH_STATUS status=MH_Initialize();
    if (status!=MH_OK && status!=MH_ERROR_ALREADY_INITIALIZED) return;
    status=MH_CreateHook(target,hooked_read,(void **)&original_read);
    if (status!=MH_OK) {write_log("DISABLED: hook creation failed.\r\n"); return;}
    status=MH_CreateHook(full,hooked_full,(void **)&original_full);
    if (status!=MH_OK) {MH_RemoveHook(target); write_log("DISABLED: full-read hook creation failed.\r\n"); return;}
#ifdef REFINEMENT_REFRESH_RVA
    status=MH_CreateHook(style_refresh,hooked_style_refresh,(void **)&original_style_refresh);
    if (status!=MH_OK) {MH_RemoveHook(full);MH_RemoveHook(target);write_log("DISABLED: refinement hook creation failed.\r\n");return;}
#endif
#ifdef CRAFTING_LAYOUT_RVA
    status=MH_CreateHook(crafting_layout,hooked_crafting_layout,(void **)&original_crafting_layout);
    if (status!=MH_OK) {
#ifdef REFINEMENT_REFRESH_RVA
        MH_RemoveHook(style_refresh);
#endif
        MH_RemoveHook(full);MH_RemoveHook(target);
        write_log("DISABLED: crafting hook creation failed.\r\n");return;
    }
#endif
    HMODULE pinned=NULL;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCWSTR)&InitializeASI,&pinned)) goto activation_failed;
    if (MH_QueueEnableHook(target)!=MH_OK || MH_QueueEnableHook(full)!=MH_OK) goto activation_failed;
#ifdef REFINEMENT_REFRESH_RVA
    if (MH_QueueEnableHook(style_refresh)!=MH_OK) goto activation_failed;
#endif
#ifdef CRAFTING_LAYOUT_RVA
    if (MH_QueueEnableHook(crafting_layout)!=MH_OK) goto activation_failed;
#endif
    if (MH_ApplyQueued()!=MH_OK) goto activation_failed;
    InterlockedExchange(&active,1);
    char line[200]; snprintf(line,sizeof(line),"ACTIVE: ResourceLoadWorker_Package slots 5/4 RVA=%llx/%llx payloads=%u.\r\n",(unsigned long long)((uintptr_t)target-image_base),(unsigned long long)((uintptr_t)full-image_base),PAYLOAD_COUNT); write_log(line);
#ifdef REFINEMENT_REFRESH_RVA
    write_log("ACTIVE: refinement Equipped Gear badge filter; native class refresh, bounded owner checks.\r\n");
#endif
#ifdef CRAFTING_LAYOUT_RVA
    write_log("ACTIVE: crafting empty-background repair during native layout.\r\n");
#endif
    return;
activation_failed:
#ifdef CRAFTING_LAYOUT_RVA
    MH_DisableHook(crafting_layout);MH_RemoveHook(crafting_layout);
#endif
#ifdef REFINEMENT_REFRESH_RVA
    MH_DisableHook(style_refresh);MH_RemoveHook(style_refresh);
#endif
    MH_DisableHook(full);MH_DisableHook(target);MH_RemoveHook(full);MH_RemoveHook(target);
    write_log("DISABLED: activation failed.\r\n");
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID reserved) {
    (void)reserved; if (reason==DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(instance); return TRUE;
}
