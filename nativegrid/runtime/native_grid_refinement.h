/* Build-pinned presentation filter. Native helpers own class storage and layout. */
typedef void (*StyleRefreshFn)(void *);
typedef unsigned char (*AddClassFn)(void *,const uint32_t *);
typedef void (*SortClassesFn)(void *);
static StyleRefreshFn original_style_refresh;
static AddClassFn refinement_add_class;
static SortClassesFn refinement_sort_classes;
static const uint32_t *refinement_hidden_atom;

static int refinement_read(uintptr_t base,size_t offset,void *out,size_t size) {
    if (base<0x10000 || base>UINTPTR_MAX-offset-size) return 0;
    return read_memory(base+offset,out,size);
}
static uintptr_t refinement_pointer(uintptr_t base,size_t offset) {
    uintptr_t value=0;
    return refinement_read(base,offset,&value,sizeof(value)) ? value : 0;
}
static int refinement_control(uintptr_t control,uintptr_t element,uintptr_t vtable_rva) {
    return refinement_pointer(control,0)==image_base+vtable_rva &&
        refinement_pointer(control,8)==element;
}
static int refinement_equipped_badge(uintptr_t badge) {
    uintptr_t card=refinement_pointer(badge,0x38);
    uintptr_t description=refinement_pointer(card,0xe0);
    if (!refinement_control(description,card,REFINEMENT_DESCRIPTION_VT) ||
        refinement_pointer(description,0x358)!=badge) return 0;
    uintptr_t list=0,ancestor=card;
    /* Bound traversal even if a UI object is incomplete, destroyed, or cyclic. */
    for (unsigned depth=0;depth<12;depth++) {
        uintptr_t parent=refinement_pointer(ancestor,0x38);
        if (!parent || parent==ancestor) return 0;
        ancestor=parent;
        uintptr_t control=refinement_pointer(ancestor,0xe0);
        if (refinement_control(control,ancestor,REFINEMENT_LIST_VT)) {
            if (list) return 0;
            list=control;
        }
        if (refinement_control(control,ancestor,REFINEMENT_ROOT_VT)) {
            unsigned char equipped_only=0;
            return list && refinement_pointer(control,0x1a0)==list &&
                refinement_read(list,0x21f,&equipped_only,1) && equipped_only==1;
        }
    }
    return 0;
}
static void hooked_style_refresh(void *style) {
    DWORD saved_error=GetLastError();
    uintptr_t badge=refinement_pointer((uintptr_t)style,0);
    uint32_t atom=0;
    if (refinement_pointer(badge,0x20)==(uintptr_t)style &&
        refinement_equipped_badge(badge) &&
        read_memory((uintptr_t)refinement_hidden_atom,&atom,sizeof(atom)) && atom) {
        uintptr_t vector=refinement_pointer((uintptr_t)style,8);
        uint32_t count=0,capacity=0,classes[256];
        if (refinement_read(vector,8,&count,4) && refinement_read(vector,12,&capacity,4) &&
            count<=256 && capacity>=count && capacity<=4096 &&
            (!count || read_memory(refinement_pointer(vector,0),classes,count*4))) {
            unsigned i=0;
            while (i<count && classes[i]!=atom) i++;
            if (i==count && refinement_add_class((void *)vector,refinement_hidden_atom)) {
                refinement_sort_classes((void *)vector);
#ifdef REFINEMENT_REPORT_HIDE
                REFINEMENT_REPORT_HIDE();
#endif
            }
        }
    }
    SetLastError(saved_error);
    original_style_refresh(style);
}
