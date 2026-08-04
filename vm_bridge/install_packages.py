import os
import sys
import tarfile
import urllib.request
import shutil

NODE_MODULES = os.path.join(os.path.dirname(__file__), 'node_modules')
ajv_dir = os.path.join(NODE_MODULES, 'ajv')
if os.path.exists(ajv_dir):
    shutil.rmtree(ajv_dir)

url = "https://registry.npmjs.org/ajv/-/ajv-6.12.6.tgz"
print(f"Downloading ajv@6.12.6...")
tgz_path = os.path.join(os.path.dirname(__file__), "tmp_pkg.tgz")
urllib.request.urlretrieve(url, tgz_path)
with tarfile.open(tgz_path, "r:gz") as tar:
    for member in tar.getmembers():
        if member.name.startswith("package/"):
            rel_path = member.name[len("package/"):]
            if not rel_path:
                continue
            dest_path = os.path.join(ajv_dir, rel_path)
            if member.isdir():
                os.makedirs(dest_path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with tar.extractfile(member) as source, open(dest_path, "wb") as target:
                    target.write(source.read())
os.remove(tgz_path)
print("Installed ajv@6.12.6!")
