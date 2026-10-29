"""Runtime restore must preserve changed work and reject corrupt/out-of-root files."""
import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('wasm_runtime',ROOT/'tools/wasm/runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
class RuntimeTests(unittest.TestCase):
    def fixture(self,base):
        web=base/'web';source=base/'source';web.mkdir();source.mkdir();(source/'engine').mkdir()
        payload=b'wasm fixture';(source/'engine/test.wasm').write_bytes(payload)
        lock={'base_url':'https://invalid.example/','files':{'engine/test.wasm':{'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}}}
        (web/'runtime-lock.json').write_text(json.dumps(lock));return web,source
    def test_restore_verify_and_refuse_changed_file(self):
        with tempfile.TemporaryDirectory() as td:
            web,source=self.fixture(Path(td));self.assertEqual(runtime.restore(web,source),1)
            self.assertEqual(runtime.restore(web,verify=True),1)
            p=web/'engine/test.wasm';p.write_bytes(b'local work')
            with self.assertRaises(ValueError):runtime.restore(web,source)
            self.assertEqual(p.read_bytes(),b'local work')
    def test_corrupt_source_not_installed(self):
        with tempfile.TemporaryDirectory() as td:
            web,source=self.fixture(Path(td));(source/'engine/test.wasm').write_bytes(b'wrong')
            with self.assertRaises(ValueError):runtime.restore(web,source)
            self.assertFalse((web/'engine/test.wasm').exists())
            self.assertFalse(list(web.rglob('*.part')))
    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):runtime.inside(Path(td),'../outside')
if __name__=='__main__':unittest.main()
