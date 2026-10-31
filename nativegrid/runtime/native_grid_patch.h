/* Copy/XOR reconstruction requires the exact original resource at runtime. */
struct PatchOp { DWORD offset,length,kind; };
struct Payload {
    const char *path;
    unsigned char before_digest[32],after_digest[32];
    const unsigned char *literals;
    DWORD literal_size;
    const struct PatchOp *ops;
    DWORD op_count,size,after_size;
};
static int payload_digest(const unsigned char *data,DWORD size,const unsigned char expected[32]) {
    BCRYPT_ALG_HANDLE algorithm=NULL;
    BCRYPT_HASH_HANDLE hash=NULL;
    unsigned char digest[32];
    int ok=0;
    if (BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,NULL,0)<0) goto done;
    if (BCryptCreateHash(algorithm,&hash,NULL,0,NULL,0,0)<0) goto done;
    if (BCryptHashData(hash,(PUCHAR)data,size,0)<0 || BCryptFinishHash(hash,digest,32,0)<0) goto done;
    ok=!memcmp(digest,expected,32);
done:
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm,0);
    return ok;
}
static const unsigned char *payload_prepare(const struct Payload *p,const unsigned char *original) {
    if (!p->size || p->size>=2000000 || !p->after_size || p->after_size>=2000000 ||
        !p->op_count || p->op_count>p->after_size || !payload_digest(original,p->size,p->before_digest)) return NULL;
    unsigned char *output=HeapAlloc(GetProcessHeap(),0,p->after_size);
    if (!output) return NULL;
    DWORD written=0;
    for (DWORD i=0;i<p->op_count;i++) {
        const struct PatchOp *op=&p->ops[i];
        DWORD limit=op->kind ? p->literal_size : p->size;
        if (op->kind>1 || !op->length || op->offset>limit || op->length>limit-op->offset ||
            op->length>p->after_size-written) goto failed;
        if (op->kind) {
            for (DWORD j=0;j<op->length;j++)
                output[written+j]=p->literals[op->offset+j]^original[(written+j)%p->size];
        } else memcpy(output+written,original+op->offset,op->length);
        written+=op->length;
    }
    if (written!=p->after_size || !payload_digest(output,written,p->after_digest)) goto failed;
    return output;
failed:
    HeapFree(GetProcessHeap(),0,output);
    return NULL;
}
static void payload_release(const unsigned char *data) {
    HeapFree(GetProcessHeap(),0,(void *)data);
}
