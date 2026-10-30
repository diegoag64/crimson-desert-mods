/* Named package worker resolver; slot 5 returns decoded bytes synchronously. */
static int fingerprint(const wchar_t *path) {
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_DELETE,NULL,OPEN_EXISTING,0,NULL);
    if (file==INVALID_HANDLE_VALUE) return 0;
    BCRYPT_ALG_HANDLE alg=NULL; BCRYPT_HASH_HANDLE hash=NULL;
    unsigned char digest[32],*buffer=NULL; char hex[65]; int ok=0;
    if (BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,NULL,0)<0) goto done;
    if (BCryptCreateHash(alg,&hash,NULL,0,NULL,0,0)<0) goto done;
    buffer=HeapAlloc(GetProcessHeap(),0,1048576); if (!buffer) goto done;
    for (;;) {
        DWORD got;
        if (!ReadFile(file,buffer,1048576,&got,NULL)) goto done;
        if (!got) break;
        if (BCryptHashData(hash,buffer,got,0)<0) goto done;
    }
    if (BCryptFinishHash(hash,digest,32,0)<0) goto done;
    for (unsigned i=0;i<32;i++) sprintf(hex+2*i,"%02x",digest[i]);
    hex[64]=0; ok=!strcmp(hex,EXPECTED_SHA256);
done:
    if (buffer) HeapFree(GetProcessHeap(),0,buffer);
    if (hash) BCryptDestroyHash(hash);
    if (alg) BCryptCloseAlgorithmProvider(alg,0);
    CloseHandle(file); return ok;
}

struct Section { DWORD rva,size,flags; unsigned char *copy; };
static int executable_rva(struct Section *sections,unsigned count,uintptr_t address) {
    if (address<image_base || address-image_base>=image_size) return 0;
    DWORD rva=(DWORD)(address-image_base);
    for (unsigned i=0;i<count;i++)
        if ((sections[i].flags&IMAGE_SCN_MEM_EXECUTE) && rva>=sections[i].rva &&
            rva-sections[i].rva<sections[i].size) return 1;
    return 0;
}

static void *resolve_named_read(unsigned slot,const unsigned char *prefix_expected) {
    IMAGE_DOS_HEADER dos; IMAGE_NT_HEADERS64 nt;
    if (!read_memory(image_base,&dos,sizeof(dos)) || dos.e_magic!=IMAGE_DOS_SIGNATURE ||
        dos.e_lfanew<=0 || dos.e_lfanew>1048576 ||
        !read_memory(image_base+dos.e_lfanew,&nt,sizeof(nt)) || nt.Signature!=IMAGE_NT_SIGNATURE ||
        nt.OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC || nt.FileHeader.NumberOfSections>64) return NULL;
    image_size=nt.OptionalHeader.SizeOfImage;
    struct Section sections[64]={0}; unsigned count=nt.FileHeader.NumberOfSections;
    uintptr_t headers=image_base+dos.e_lfanew+24+nt.FileHeader.SizeOfOptionalHeader;
    void *result=NULL; unsigned matches=0;
    for (unsigned i=0;i<count;i++) {
        IMAGE_SECTION_HEADER header;
        if (!read_memory(headers+i*sizeof(header),&header,sizeof(header))) goto done;
        struct Section *s=&sections[i];
        s->rva=header.VirtualAddress; s->size=header.Misc.VirtualSize; s->flags=header.Characteristics;
        if (s->rva>image_size || s->size>image_size-s->rva) goto done;
        if (!(s->flags&IMAGE_SCN_MEM_READ) || (s->flags&IMAGE_SCN_MEM_EXECUTE) || !s->size) continue;
        s->copy=HeapAlloc(GetProcessHeap(),0,s->size); if (!s->copy) goto done;
        if (!read_memory(image_base+s->rva,s->copy,s->size)) { HeapFree(GetProcessHeap(),0,s->copy); s->copy=NULL; }
    }
    const char name[]=".?AVResourceLoadWorker_Package@pa@@";
    for (unsigned i=0;i<count;i++) {
        struct Section *s=&sections[i]; if (!s->copy || s->size<sizeof(name)+16) continue;
        for (DWORD off=16;off<=s->size-sizeof(name);off++) {
            if (s->copy[off]!='.' || memcmp(s->copy+off,name,sizeof(name))) continue;
            DWORD type=s->rva+off-16;
            for (unsigned j=0;j<count;j++) {
                struct Section *c=&sections[j]; if (!c->copy || c->size<24) continue;
                for (DWORD at=0;at<=c->size-24;at+=4) {
                    DWORD fields[6]; memcpy(fields,c->copy+at,24);
                    if (fields[0]!=1 || fields[1]!=0 || fields[3]!=type || fields[5]!=c->rva+at) continue;
                    uintptr_t locator=image_base+c->rva+at;
                    for (unsigned k=0;k<count;k++) {
                        struct Section *v=&sections[k]; if (!v->copy || v->size<56) continue;
                        for (DWORD p=0;p<=v->size-56;p+=8) {
                            uintptr_t ptr; memcpy(&ptr,v->copy+p,8); if (ptr!=locator) continue;
                            uintptr_t target; memcpy(&target,v->copy+p+8+slot*8,8);
                            if (!executable_rva(sections,count,target)) continue;
                            unsigned char prefix[24];
                            if (!read_memory(target,prefix,sizeof(prefix)) || memcmp(prefix,prefix_expected,sizeof(prefix))) continue;
                            result=(void *)target; matches++;
                        }
                    }
                }
            }
        }
    }
done:
    for (unsigned i=0;i<count;i++) if (sections[i].copy) HeapFree(GetProcessHeap(),0,sections[i].copy);
    return matches==1 ? result : NULL;
}
