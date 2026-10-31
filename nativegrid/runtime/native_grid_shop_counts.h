/* Recycled buy cards can retain the requirement formatter's inline line height. */
typedef void (*ShopRemovePropertyFn)(void *,const unsigned char *,unsigned char);
static ShopRemovePropertyFn shop_remove_property;
static __thread unsigned shop_count_depth;

static int shop_read(uintptr_t object,size_t offset,void *out,size_t size) {
    return object>=0x10000 && object<=UINTPTR_MAX-offset-size &&
        read_memory(object+offset,out,size);
}
static uintptr_t shop_pointer(uintptr_t object,size_t offset) {
    uintptr_t value=0;
    return shop_read(object,offset,&value,8) ? value : 0;
}
static int shop_control(uintptr_t element,uintptr_t type) {
    uintptr_t control=shop_pointer(element,0xe0);
    return shop_pointer(control,0)==image_base+type && shop_pointer(control,8)==element;
}
static int shop_line_height(uintptr_t block,float expected) {
    uint32_t map_count=0,value_count=0;
    unsigned char index=255,value[16];float height;
    if (!shop_read(block,0x88,&map_count,4) || map_count<=84 || map_count>256 ||
        !shop_read(block,0x78,&value_count,4) || !value_count || value_count>256 ||
        !shop_read(shop_pointer(block,0x80),84,&index,1) || index>=value_count ||
        !shop_read(shop_pointer(block,0x70),index*16,value,16)) return 0;
    memcpy(&height,value,4);
    return height==expected && value[8]==149 && value[9]==0 && value[10]==0 &&
        value[11]==0 && value[12]==84 && value[13]==1 && value[14]==0;
}
static uintptr_t shop_stale_count(uintptr_t layout) {
    uintptr_t element=shop_pointer(layout,0),style=shop_pointer(element,0x20);
    if (shop_pointer(element,0x18)!=layout || shop_pointer(style,0)!=element ||
        !shop_line_height(shop_pointer(style,0x30),27.0f)) return 0;
    char id[sizeof("ItemAvailableCountText")];
    uintptr_t name=shop_pointer(shop_pointer(element,0x60),0);
    if (!read_memory(name,id,sizeof(id)) || memcmp(id,"ItemAvailableCountText",sizeof(id))) return 0;
    uint32_t children=0,count=0,atom=0,classes[256];
    uintptr_t vector=shop_pointer(style,8);
    if (!shop_read(element,0x48,&children,4) || children ||
        !read_memory(image_base+SHOP_COUNTS_NEGATIVE_ATOM_RVA,&atom,4) || !atom ||
        !shop_read(vector,8,&count,4) || !count || count>256 ||
        !read_memory(shop_pointer(vector,0),classes,count*4)) return 0;
    for (unsigned i=0;i<count;i++) if (classes[i]==atom) return 0;
    /* Require the compact card's actual winning stylesheet rule. */
    uint32_t rules=0;
    if (!shop_read(style,0x18,&rules,4) || !rules || rules>64) return 0;
    uintptr_t rule=shop_pointer(shop_pointer(style,0x10),(rules-1)*8);
    if (!shop_line_height(rule,14.0f)) return 0;
    uintptr_t wrap=shop_pointer(element,0x38),card=shop_pointer(wrap,0x38);
    if (!shop_control(card,SHOP_COUNTS_DESCRIPTION_VT)) return 0;
    uintptr_t ancestor=card;int list_seen=0;
    for (unsigned depth=0;depth<12;depth++) {
        uintptr_t parent=shop_pointer(ancestor,0x38);
        if (!parent || parent==ancestor) return 0;
        ancestor=parent;
        if (shop_control(ancestor,SHOP_COUNTS_LIST_VT)) {
            if (list_seen) return 0;
            list_seen=1;
        }
        if (shop_control(ancestor,SHOP_COUNTS_ROOT_VT)) return list_seen ? style : 0;
    }
    return 0;
}
static void shop_counts_prepare(void *layout) {
    DWORD saved=GetLastError();
    uintptr_t style=shop_count_depth ? 0 : shop_stale_count((uintptr_t)layout);
    if (style) {
        unsigned char property=84;
        shop_count_depth++;
        /* The native helper removes the override and invalidates text/layout. */
        shop_remove_property((void *)style,&property,0);
        shop_count_depth--;
#ifdef SHOP_COUNTS_REPORT_REPAIR
        SHOP_COUNTS_REPORT_REPAIR();
#endif
    }
    SetLastError(saved);
}
