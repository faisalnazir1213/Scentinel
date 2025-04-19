import os
import re

def patch_filechooser():
    src_path = os.path.join(
        '.buildozer', 'android', 'platform',
        'build-arm64-v8a_armeabi-v7a',
        'python-installs', 'Scentinel_signal',
        'arm64-v8a', 'plyer', 'platforms', 'android', 'filechooser.py'
    )

    if not os.path.exists(src_path):
        print(f"[WARN] filechooser.py not found yet: {src_path}")
        return

    with open(src_path, 'r', encoding='utf-8') as f:
        original = f.read()

    if 'Long.valueOf(file_id_part)' in original:
        print("[INFO] Patch already applied.")
        return

    # Replace buggy line with patched logic
    modified = re.sub(
        r'file_id\s*=\s*DocumentsContract\.getDocumentId\(uri\)',
        'file_id = DocumentsContract.getDocumentId(uri)\n'
        '    if \':\' in file_id:\n'
        '        _, file_id_part = file_id.split(\':\', 1)\n'
        '    else:\n'
        '        file_id_part = file_id',
        original
    )

    modified = modified.replace(
        'Long.valueOf(file_id)',
        'Long.valueOf(file_id_part)'
    )

    with open(src_path, 'w', encoding='utf-8') as f:
        f.write(modified)

    print("[✅] Patched filechooser.py successfully!")

if __name__ == '__main__':
    patch_filechooser()
