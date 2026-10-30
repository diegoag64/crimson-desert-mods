"""Native ABI, replacement, and fail-closed fixture suites."""
from pathlib import Path
import json
import subprocess
import tempfile
from .compiler import compile_flexible
from .pe import exported_rva

SOURCE = Path(__file__).resolve().parent

def test(output, gcc, minhook):
    folder=Path(tempfile.mkdtemp(prefix='native-flex-test-',dir=output));exe=folder/'fixture.exe'
    subprocess.run([str(gcc),'-O2','-Wall','-Wextra','-Werror','-static','-o',str(exe),str(SOURCE/'fixtures/native_grid_fixture.c')],check=True,timeout=60)
    data=exe.read_bytes(); rvas=[exported_rva(data,n) for n in ['fixture_read','fixture_full','fixture_resize']]
    payloads=[('ui/bin__/inventoryequipmentpanel_game.uibinary',b'fixture original grid column=6 row=8',b'fixture modified grid column=8 row=9'),
        ('ui/bin__/fixture-layout.uibinary',b'grid row=9',b'grid row=11')]
    results=[]
    def run(name,args,enabled):
        r=subprocess.run([str(exe),str(folder/'NativeGrid.asi')]+args,capture_output=True,text=True,timeout=25)
        log=(folder/'runtime.log').read_text()
        expected=f'full=10 resizes={3 if enabled else 0} replacements={4 if enabled else 0} active={int(enabled)}'
        assert r.returncode==0 and expected in r.stdout,(name,r.returncode,r.stdout,r.stderr,log)
        if enabled:assert log.count('REPLACED resized:')==2 and 'FAILED: native buffer resize' in log
        results.append(dict(case=name,passed=True,output=r.stdout,log=log));print('PASS:',name,flush=True)
    compile_flexible(folder,data,payloads,rvas,gcc,minhook)
    run('legacy nine raw-read cases plus ten full-read resize cases',[],True)
    run('missing named interface',['missing'],False)
    with exe.open('ab') as f:f.write(b'changed executable')
    run('changed executable',[],False);exe.write_bytes(data)
    for index,name in [(0,'raw read'),(1,'full read'),(2,'buffer resize')]:
        compile_flexible(folder,data,payloads,rvas,gcc,minhook,bad=index);run('changed '+name+' fingerprint',[],False)
    # Localization recompression can shrink a resource. Exercise the existing
    # allocation-reuse path, descriptor length, terminators and failure behavior.
    subprocess.run([str(gcc),'-DFIXTURE_SHRINK','-O2','-Wall','-Wextra','-Werror','-static','-o',str(exe),str(SOURCE/'fixtures/native_grid_fixture.c')],check=True,timeout=60)
    data=exe.read_bytes(); rvas=[exported_rva(data,n) for n in ['fixture_read','fixture_full','fixture_resize']]
    payloads[1]=(payloads[1][0],payloads[1][1],b'grid')
    compile_flexible(folder,data,payloads,rvas,gcc,minhook)
    run('shorter payload preserves descriptor, terminators and read failures',[],True)
    (output/'fixture-results.json').write_text(json.dumps(results,indent=2)+'\n')
    return results
