#! /usr/bin/env python3

import common, os, subprocess, sys, shutil
from checkout import chdir_home

def patch_pool_header():
  """Ensure <cstdint> is included in pool.h to fix int64_t errors."""
  path = os.path.join("gn", "src", "gn", "pool.h")
  if not os.path.exists(path):
    print(f"Warning: {path} does not exist for patching.")
    return

  with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

  if any("#include <cstdint>" in line for line in lines):
    return  # Already patched

  for i, line in enumerate(lines):
    if line.strip() == '#include "gn/item.h"':
      lines.insert(i + 1, "#include <cstdint>\n")
      break

  with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

  print("Patched pool.h with '#include <cstdint>'")

def main():
  chdir_home()
  patch_pool_header()

  build_type = common.build_type()
  machine = common.machine()
  host = common.host()
  host_machine = common.host_machine()
  target = common.target()
  ndk = common.ndk()
  is_win = common.windows()
  is_mingw = host == "mingw"
  isIos = target in ['ios', 'iosSim']
  isIosSim = target == 'iosSim'

  args = ['is_debug=true'] if build_type == 'Debug' else ['is_official_build=true']

  args += [
    f'target_cpu="{machine}"',
    'skia_use_system_expat=false',
    'skia_use_system_libjpeg_turbo=false',
    'skia_use_system_libpng=false',
    'skia_use_system_libwebp=false',
    'skia_use_system_zlib=false',
    'skia_use_sfntly=false',
    'skia_use_freetype=true',
    'skia_use_system_freetype2=false',
    'skia_use_system_harfbuzz=false',
    'skia_pdf_subset_harfbuzz=true',
    'skia_use_system_icu=false',
    'skia_enable_skottie=true'
  ]

  if target == 'macos' or isIos:
    args += [
      'skia_use_metal=true',
      'extra_cflags_cc=["-frtti"]'
    ]
    if isIos:
      args += ['target_os="ios"']
      if isIosSim:
        args += ['ios_use_simulator=true']
    else:
      if machine == 'arm64':
        args += ['extra_cflags=["-stdlib=libc++"]']
      else:
        args += ['extra_cflags=["-stdlib=libc++", "-mmacosx-version-min=10.13"]']

  elif target == 'linux':
    if machine == 'arm64':
      args += [
        'skia_gl_standard="gles"',
        'extra_cflags_cc=["-fno-exceptions", "-fno-rtti", "-flax-vector-conversions=all", "-D_GLIBCXX_USE_CXX11_ABI=0"]',
        'cc="clang"',
        'cxx="clang++"'
      ]
    else:
      args += [
        'extra_cflags_cc=["-fno-exceptions", "-fno-rtti", "-D_GLIBCXX_USE_CXX11_ABI=0"]',
        'cc="gcc-9"',
        'cxx="g++-9"'
      ]

  elif is_win:
    if is_mingw:
      args += [
        'extra_cflags_cc=["-fno-exceptions", "-fno-rtti", "-D_GLIBCXX_USE_CXX11_ABI=0", "-fpermissive"]',
        'cc="gcc"',
        'cxx="g++"'
      ]
    else:
      args += [
        'skia_use_direct3d=true',
        'extra_cflags=["-DSK_FONT_HOST_USE_SYSTEM_SETTINGS"]'
      ]

  elif target == 'android':
    args += [f'ndk="{ndk}"']

  elif target == 'wasm':
    args += [
      'skia_use_dng_sdk=false',
      'skia_use_libjpeg_turbo_decode=true',
      'skia_use_libjpeg_turbo_encode=true',
      'skia_use_libpng_decode=true',
      'skia_use_libpng_encode=true',
      'skia_use_libwebp_decode=true',
      'skia_use_libwebp_encode=true',
      'skia_use_wuffs=true',
      'skia_use_lua=false',
      'skia_use_webgl=true',
      'skia_use_piex=false',
      'skia_use_system_libpng=false',
      'skia_use_system_freetype2=false',
      'skia_use_system_libjpeg_turbo=false',
      'skia_use_system_libwebp=false',
      'skia_enable_tools=false',
      'skia_enable_fontmgr_custom_directory=false',
      'skia_enable_fontmgr_custom_embedded=true',
      'skia_enable_fontmgr_custom_empty=false',
      'skia_use_webgl=true',
      'skia_gl_standard="webgl"',
      'skia_use_gl=true',
      'skia_enable_gpu=true',
      'skia_enable_svg=true',
      'skia_use_expat=true',
      'extra_cflags=["-DSK_SUPPORT_GPU=1", "-DSK_GL", "-DSK_DISABLE_LEGACY_SHADERCONTEXT"]'
    ]

  ninja_path = shutil.which("ninja") or shutil.which("ninja.exe")
  if not ninja_path:
    raise FileNotFoundError(" 'ninja' not found in PATH")

  env = os.environ.copy()

  if is_mingw:
    os.chdir("gn")
    subprocess.check_call(["python", "build/gen.py", f"--out-path=out/{machine}", "--platform=mingw"], env=env)
    subprocess.check_call([ninja_path, "-C", f"out/{machine}"], env=env)
    os.chdir("..")

  os.chdir("skia")
  out = os.path.join("out", f"{build_type}-{target}-{machine}")

  gn = "gn.exe" if is_win else "gn"
  gn_path = os.path.join("..", "gn", "out", machine, gn) if is_mingw else os.path.join("bin", gn)

  print("🛠 Generating build with GN:", gn_path)
  subprocess.check_call([gn_path, "gen", out, "--args=" + " ".join(args)], env=env)
  print("🏗 Building with ninja:", ninja_path)
  subprocess.check_call([ninja_path, "-C", out, "skia", "modules"], env=env)

  return 0

if __name__ == "__main__":
  sys.exit(main())
