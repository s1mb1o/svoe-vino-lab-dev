from pathlib import Path
import subprocess,tempfile,hashlib,json
R=Path('/Volumes/Storage/svoe-vino-final');repo=R/'code/svoe-vino-lab-main-selector';N=R/'datasets/main-selector-hardcases-v2-localization-fixes-20261020';W=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tracked=subprocess.check_output(['git','diff','--name-only','HEAD','--','matcher'],cwd=repo,text=True).splitlines();untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','matcher'],cwd=repo,text=True).splitlines();files=tracked+untracked;expected={name:sha(repo/name) for name in files};(N/'tested-source-hashes.json').write_text(json.dumps(expected,indent=2)+'\n')
parts=[subprocess.check_output(['git','diff','--binary','HEAD','--','matcher'],cwd=repo)]
for name in untracked:
 a=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',name],cwd=repo,capture_output=True);assert a.returncode==1;parts.append(a.stdout)
patch=b''.join(parts);(N/'implementation.patch').write_bytes(patch)
with tempfile.TemporaryDirectory(prefix='localization-patch-check-',dir='/private/tmp') as d:
 root=Path(d)
 for name in expected:
  p=subprocess.run(['git','show','HEAD:'+name],cwd=repo,capture_output=True)
  if p.returncode==0:
   dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.stdout)
 subprocess.run(['git','apply','--check',str(N/'implementation.patch')],cwd=root,check=True);subprocess.run(['git','apply',str(N/'implementation.patch')],cwd=root,check=True)
 for name,digest in expected.items():assert sha(root/name)==digest,name
out=dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),patch_sha256=sha(N/'implementation.patch'),patch_applies_to_base=True,reconstructed_files_match_tested_source=True,files=expected)
(N/'patch-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(len(expected),'source files reconstruct exactly')
