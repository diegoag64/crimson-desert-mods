"""Generate local-only payload headers and compile the guarded runtime."""
from pathlib import Path
import hashlib
import json
import subprocess
from .pe import PE

SOURCE = Path(__file__).resolve().parent

def compile_flexible(folder,exe_data,payloads,rvas,gcc,minhook,bad=None,refinement=None,crafting=None,shop_counts=None,release_patches=False):
    folder.mkdir(parents=True,exist_ok=True); pe=PE(exe_data)
    header='#define EXPECTED_SHA256 "'+hashlib.sha256(exe_data).hexdigest()+'"\n'
    if release_patches:
        header+='#define NATIVEGRID_RELEASE_PATCHES 1\n'
    else:
        header+='#define PROBE_LOG L'+json.dumps(str((folder/'runtime.log').resolve()))+'\n'
    header+=f'#define RESIZE_RVA {rvas[2]}u\n'
    if refinement:
        from .refinement import audit_runtime
        audit_runtime(exe_data, refinement)
        for name in ('refresh', 'add_class', 'sort_classes'):
            method=refinement['methods'][name]
            header+=f'#define REFINEMENT_{name.upper()}_RVA {method["rva"]}u\n'
            prefix=bytes.fromhex(method['prefix'])
            header+='static const unsigned char expected_refinement_'+name+'_prefix[] = {'+','.join(map(str,prefix))+'};\n'
        header+=f'#define REFINEMENT_HIDDEN_ATOM_RVA {refinement["hidden_atom_rva"]}u\n'
        for name in ('description', 'list', 'root'):
            header+=f'#define REFINEMENT_{name.upper()}_VT {refinement[name+"_vtable"]["rva"]}u\n'
    if crafting:
        from .crafting import audit_runtime
        audit_runtime(exe_data, crafting)
        for name,method in crafting['methods'].items():
            header+=f'#define CRAFTING_{name.upper()}_RVA {method["rva"]}u\n'
            header+='static const unsigned char expected_crafting_'+name+'_prefix[] = {'+','.join(map(str,bytes.fromhex(method['prefix'])))+'};\n'
        for name in ('description', 'card', 'list', 'root'):
            header+=f'#define CRAFTING_{name.upper()}_VT {crafting[name+"_vtable"]["rva"]}u\n'
    if shop_counts:
        from .shop_counts import audit_runtime
        if not crafting:
            raise ValueError('Shop count repair requires the native layout hook')
        audit_runtime(exe_data, shop_counts)
        method=shop_counts['remove_property']
        header+=f'#define SHOP_COUNTS_REMOVE_PROPERTY_RVA {method["rva"]}u\n'
        header+='static const unsigned char expected_shop_counts_prefix[] = {'+','.join(map(str,bytes.fromhex(method['prefix'])))+'};\n'
        header+=f'#define SHOP_COUNTS_NEGATIVE_ATOM_RVA {shop_counts["negative_atom_rva"]}u\n'
        for name in ('description', 'list', 'root'):
            header+=f'#define SHOP_COUNTS_{name.upper()}_VT {shop_counts[name+"_vtable"]["rva"]}u\n'
    for index,name in enumerate(['expected_prefix','expected_full_prefix','expected_resize_prefix']):
        prefix=exe_data[pe.raw(rvas[index]):pe.raw(rvas[index])+24]
        if bad==index:prefix=bytes(24)
        header+='static const unsigned char '+name+'[] = {'+','.join(map(str,prefix))+'};\n'
    (folder/'native_grid_config.h').write_text(header)
    arrays=[];entries=[]
    for i,(path,before,after) in enumerate([] if release_patches else payloads):
        assert before!=after and 0<len(before)<2000000 and 0<len(after)<2000000
        for name,data in [('before',before),('after',after)]:
            arrays.append(f'static const unsigned char {name}_{i}[] = {{'+','.join(map(str,data))+'};')
        entries.append('{'+json.dumps(path)+f',before_{i},after_{i},{len(before)},{len(after)}'+'}')
    arrays+=['static const struct Payload payloads[] = {'+','.join(entries)+'};',f'#define PAYLOAD_COUNT {len(payloads)}u']
    payload_header='\n'.join(arrays)+'\n'
    if release_patches:
        from .delta import emit_payloads
        payload_header,patch_report=emit_payloads(payloads)
        (folder/'patch-report.json').write_text(json.dumps(patch_report,indent=2)+'\n')
    (folder/'native_grid_payloads.h').write_text(payload_header)
    mh=minhook
    sources=[SOURCE/'runtime/native_grid.c']+[mh/'src'/s for s in ['buffer.c','hook.c','trampoline.c','hde/hde64.c']]
    subprocess.run([str(gcc),'-O2','-Wall','-Wextra','-Werror','-shared','-static','-Wl,--no-insert-timestamp']+(['-Wl,--image-base,0x180000000'] if release_patches else [])+['-I',str(folder),'-I',str(mh/'include'),
        '-o',str(folder/'NativeGrid.asi')]+list(map(str,sources))+['-lbcrypt'],check=True,timeout=90)
