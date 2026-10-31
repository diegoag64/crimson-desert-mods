/* Repair an empty recipe-image cache during the game's own layout pass. */
typedef unsigned char (*CraftingLayoutFn)(void *,void *,void *,void *,void *);
typedef unsigned char (*CraftingBackgroundFn)(void *,void *,unsigned char,unsigned char);
static CraftingLayoutFn original_crafting_layout;
static CraftingBackgroundFn crafting_background_size,crafting_background_position;
static __thread unsigned crafting_repair_depth;

static int crafting_read(uintptr_t object,size_t offset,void *out,size_t size) {
    return object>=0x10000 && object<=UINTPTR_MAX-offset-size &&
        read_memory(object+offset,out,size);
}
static uintptr_t crafting_pointer(uintptr_t object,size_t offset) {
    uintptr_t value=0;
    return crafting_read(object,offset,&value,sizeof(value)) ? value : 0;
}
static int crafting_control(uintptr_t element,uintptr_t type) {
    uintptr_t control=crafting_pointer(element,0xe0);
    return crafting_pointer(control,0)==image_base+type &&
        crafting_pointer(control,8)==element;
}
static int crafting_empty_image(uintptr_t layout) {
    uintptr_t image=crafting_pointer(layout,0);
    if (crafting_pointer(image,0x18)!=layout) return 0;
    uintptr_t style=crafting_pointer(image,0x20);
    float box[4],size[2];
    if (crafting_pointer(style,0)!=image ||
        !crafting_read(style,0x3c,box,sizeof(box)) ||
        !crafting_read(image,0x78,size,sizeof(size)) ||
        !(size[0]>0 && size[0]<16384 && size[1]>0 && size[1]<16384) ||
        box[0]!=0 || box[1]!=0 || box[2]!=0 || box[3]!=0) return 0;
    uintptr_t card=crafting_pointer(image,0x38);
    if (!crafting_control(card,CRAFTING_DESCRIPTION_VT)) return 0;
    uintptr_t description=crafting_pointer(card,0xe0);
    uint32_t count=0;
    uintptr_t images[8];
    if (!crafting_read(description,0x170,&count,4) || !count || count>8 ||
        !read_memory(crafting_pointer(description,0x168),images,count*sizeof(*images))) return 0;
    unsigned i=0;
    while (i<count && images[i]!=image) i++;
    if (i==count) return 0;
    uintptr_t ancestor=crafting_pointer(card,0x38);
    if (!crafting_control(ancestor,CRAFTING_CARD_VT)) return 0;
    int list_seen=0;
    for (unsigned depth=0;depth<12;depth++) {
        uintptr_t parent=crafting_pointer(ancestor,0x38);
        if (!parent || parent==ancestor) return 0;
        ancestor=parent;
        if (crafting_control(ancestor,CRAFTING_LIST_VT)) {
            if (list_seen) return 0;
            list_seen=1;
        }
        if (crafting_control(ancestor,CRAFTING_ROOT_VT)) return list_seen;
    }
    return 0;
}
static unsigned char hooked_crafting_layout(void *layout,void *bounds,void *size,
                                            void *state,void *context) {
#ifdef SHOP_COUNTS_PREPARE
    SHOP_COUNTS_PREPARE(layout);
#endif
    /* Forward all five ABI arguments. The native pass owns geometry and lifetime. */
    unsigned char result=original_crafting_layout(layout,bounds,size,state,context);
    DWORD outgoing=GetLastError();
    if (!crafting_repair_depth && result && context && crafting_empty_image((uintptr_t)layout)) {
        /* Normal parent layout recursively lays out its children. Guard only
           reentry caused by our helpers, or every nested recipe image is skipped. */
        crafting_repair_depth++;
        /* Native property IDs: image=38, size=40, position=39. These helpers
           resolve assets and UI scale; never synthesize a rectangle or texture. */
        if (crafting_background_size(layout,context,38,40)) {
            uintptr_t element=crafting_pointer((uintptr_t)layout,0);
            uintptr_t style=crafting_pointer(element,0x20);
            float resolved[2];
            if (crafting_read(style,0x44,resolved,sizeof(resolved)) &&
                resolved[0]>0 && resolved[1]>0) {
                crafting_background_position(layout,context,38,39);
#ifdef CRAFTING_REPORT_REPAIR
                CRAFTING_REPORT_REPAIR();
#endif
            }
        }
        crafting_repair_depth--;
    }
    SetLastError(outgoing);
    return result;
}
