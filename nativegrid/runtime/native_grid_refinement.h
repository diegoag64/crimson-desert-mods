/* Build-pinned presentation filter. Never writes a game object or polls a UI tree. */
typedef void (*ElementStateFn)(void *,const unsigned char *,unsigned char);
static ElementStateFn original_element_state;

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
static void hooked_element_state(void *element,const unsigned char *state,unsigned char enabled) {
    DWORD saved_error=GetLastError();
    unsigned char kind=0;
    /* State 5 is !cpp-none: replace only native Show with native Hide. */
    if (enabled==0 && read_memory((uintptr_t)state,&kind,1) && kind==5 &&
        refinement_equipped_badge((uintptr_t)element)) enabled=1;
    SetLastError(saved_error);
    original_element_state(element,state,enabled);
}
