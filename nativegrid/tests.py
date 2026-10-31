"""Native ABI, replacement, and fail-closed fixture suites."""
from pathlib import Path
import json
import subprocess
import tempfile
import shutil
from .compiler import compile_flexible
from .pe import exported_rva

SOURCE = Path(__file__).resolve().parent

def test(output, gcc, minhook, release_patches=False):
    folder=Path(tempfile.mkdtemp(prefix='native-flex-test-',dir=output));exe=folder/'fixture.exe'
    subprocess.run([str(gcc),'-O2','-Wall','-Wextra','-Werror','-static','-o',str(exe),str(SOURCE/'fixtures/native_grid_fixture.c')],check=True,timeout=60)
    data=exe.read_bytes(); rvas=[exported_rva(data,n) for n in ['fixture_read','fixture_full','fixture_resize']]
    payloads=[('ui/bin__/inventoryequipmentpanel_game.uibinary',b'fixture original grid column=6 row=8',b'fixture modified grid column=8 row=9'),
        ('ui/bin__/fixture-layout.uibinary',b'grid row=9',b'grid row=11')]
    results=[]
    def run(name,args,enabled,plugin=None,logging=True):
        r=subprocess.run([str(exe),str(plugin or folder/'NativeGrid.asi')]+args,capture_output=True,text=True,timeout=25)
        log_path=(plugin.parent if plugin else folder)/('NativeGrid.log' if release_patches else 'runtime.log')
        log=log_path.read_text() if logging else ''
        expected=f'full=10 resizes={3 if enabled else 0} replacements={4 if enabled else 0} active={int(enabled)}'
        assert r.returncode==0 and expected in r.stdout,(name,r.returncode,r.stdout,r.stderr,log)
        if enabled and logging:assert log.count('REPLACED resized:')==2 and 'FAILED: native buffer resize' in log
        results.append(dict(case=name,passed=True,output=r.stdout,log=log));print('PASS:',name,flush=True)
    compile_flexible(folder,data,payloads,rvas,gcc,minhook,release_patches=release_patches)
    run('nine raw-read cases plus ten full-read resize cases',[],True)
    if release_patches:
        relocated=folder/'relocated plugin with spaces'
        relocated.mkdir()
        plugin=relocated/'NativeGrid.asi'
        shutil.copy2(folder/'NativeGrid.asi',plugin)
        run('relocated plugin initializes and logs beside itself',[],True,plugin)
        (relocated/'NativeGrid.log').unlink()
        (relocated/'NativeGrid.log').mkdir()
        run('unwritable log does not disable plugin',[],True,plugin,False)
    run('missing named interface',['missing'],False)
    with exe.open('ab') as f:f.write(b'changed executable')
    run('changed executable',[],False);exe.write_bytes(data)
    for index,name in [(0,'raw read'),(1,'full read'),(2,'buffer resize')]:
        compile_flexible(folder,data,payloads,rvas,gcc,minhook,bad=index,release_patches=release_patches);run('changed '+name+' fingerprint',[],False)
    # Localization recompression can shrink a resource. Exercise the existing
    # allocation-reuse path, descriptor length, terminators and failure behavior.
    subprocess.run([str(gcc),'-DFIXTURE_SHRINK','-O2','-Wall','-Wextra','-Werror','-static','-o',str(exe),str(SOURCE/'fixtures/native_grid_fixture.c')],check=True,timeout=60)
    data=exe.read_bytes(); rvas=[exported_rva(data,n) for n in ['fixture_read','fixture_full','fixture_resize']]
    payloads[1]=(payloads[1][0],payloads[1][1],b'grid')
    compile_flexible(folder,data,payloads,rvas,gcc,minhook,release_patches=release_patches)
    run('shorter payload preserves descriptor, terminators and read failures',[],True)
    refinement_exe=folder/'refinement-fixture.exe'
    sources=[SOURCE/'fixtures/refinement_fixture.c']+[minhook/'src'/s for s in ['buffer.c','hook.c','trampoline.c','hde/hde64.c']]
    subprocess.run([str(gcc),'-O2','-Wall','-Wextra','-Werror','-static','-I',str(minhook/'include'),
                    '-o',str(refinement_exe)]+list(map(str,sources)),check=True,timeout=60)
    refinement_result=subprocess.run([str(refinement_exe)],capture_output=True,text=True,timeout=25)
    assert refinement_result.returncode==0, (refinement_result.stdout,refinement_result.stderr)
    results.append(dict(case='refinement conditional badge detour',passed=True,output=refinement_result.stdout))
    print('PASS: refinement conditional badge detour',flush=True)
    crafting_exe=folder/'crafting-fixture.exe'
    sources=[SOURCE/'fixtures/crafting_fixture.c']+[minhook/'src'/s for s in ['buffer.c','hook.c','trampoline.c','hde/hde64.c']]
    subprocess.run([str(gcc),'-O2','-Wall','-Wextra','-Werror','-static','-I',str(minhook/'include'),
                    '-o',str(crafting_exe)]+list(map(str,sources)),check=True,timeout=60)
    crafting_result=subprocess.run([str(crafting_exe)],capture_output=True,text=True,timeout=25)
    assert crafting_result.returncode==0, (crafting_result.stdout,crafting_result.stderr)
    results.append(dict(case='crafting empty background detour',passed=True,output=crafting_result.stdout))
    print('PASS: crafting empty background detour',flush=True)
    shop_exe=folder/'shop-counts-fixture.exe'
    sources=[SOURCE/'fixtures/shop_counts_fixture.c']+[minhook/'src'/s for s in ['buffer.c','hook.c','trampoline.c','hde/hde64.c']]
    subprocess.run([str(gcc),'-O2','-Wall','-Wextra','-Werror','-static','-I',str(minhook/'include'),
                    '-o',str(shop_exe)]+list(map(str,sources)),check=True,timeout=60)
    shop_result=subprocess.run([str(shop_exe)],capture_output=True,text=True,timeout=25)
    assert shop_result.returncode==0, (shop_result.returncode,shop_result.stdout,shop_result.stderr)
    results.append(dict(case='recycled shop stock line height',passed=True,output=shop_result.stdout))
    print('PASS: recycled shop stock line height',flush=True)
    (output/('release-fixture-results.json' if release_patches else 'fixture-results.json')).write_text(json.dumps(results,indent=2)+'\n')
    return results
