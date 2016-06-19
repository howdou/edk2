# edk2 llvm branch
Please see all the updated in the llvm branch from edk2 upstream by below command:
* $ git diff master --name-only


This project is forked from edk2 to apply the LLVM compiler and toolchain technologies on edk2 codebase. So far, this project focus on below items:
* Clang compiler optimization for edk2 code size improvement, e.g. Link Time Optimization (LTO) 
* Clang Static Analyzer (scan-build) for edk2, e.g. sepcial checkers for edk2 security,  checkers for Intel Firmware Engine automation

There are 4 new tool chains are introduced in branch llvm:
* CLANG38:      Clang3.8.0 build tool chain, and enable code size optimization flag (-Os) by default on both Ia32 and X64. X64 code is large code model.
* CLANGLTO38:   Base on CLANG38 to enable LLVM Link Time Optimization (LTO) for more aggressive code size improvement. X64 code is small code model + PIE.
* CLANGSCAN38:  Base on CLANG38 to seamlessly integrate Clang scan-build analyzer infrastructure into edk2 build infrastructure. X64 code small code model + PIE.
* GCCLTO53:     Enabled GCC Link Time Optimization (LTO) and code size optimization (–Os) for more aggressive code size improvement. X64 code small + PIE

Example steps to use the CLANGLTO38 tool chain to build Qemu platform:
  1.  Download and extract the llvm 3.8.0 Pre-Built Binaries from  http://www.llvm.org/releases/ (e.g. http://www.llvm.org/releases/3.8.0/clang+llvm-3.8.0-x86_64-linux-gnu-ubuntu-16.04.tar.xz and extract it as ~/clang38).
  2.  Copy BaseTools/Bin/LLVMgold.so to above clang lib folder (e.g. ~/clang38/lib/LLVMgold.so, this step is needed only for CLANGLTO38)
  3.  Install new version linker with plugin support (e.g. ld 2.26 in GNU Binutils 2.26 or Ubuntu16.04, this step is needed only for CLANGLTO38)
  4.  $ cd edk2
  5.  $ git checkout llvm
  6.  $ export CLANG38_BIN=path/to/your/clang38/ (e.g. export CLANG38_BIN=~/clang38/bin/)
  7.  $ source edksetup.sh
  8.  $ make -C BaseTools/Source/C
  9.  $ build -a X64 -t CLANGLTO38 -p OvmfPkg/OvmfPkgX64.dsc -n 5 -b DEBUG -DDEBUG_ON_SERIAL_PORT
  10. $ cd edk2/Build/OvmfX64/DEBUG_CLANGLTO38/FV
  11. $ qemu-system-x86_64.exe  -bios OVMF.fd -serial file:serial.log -m 512 -hda fat:.

If you want, you can build and install GNU Binutils 2.26 as below steps in Ubuntu
  1. Download binutils-2.26 source code from http://ftp.gnu.org/gnu/binutils/ and extract it to ~/binutils-2.26
  2. $sudo apt-get install bison
  3. $sudo apt-get install flex
  4. Install other necessary binutils build tools if missing
  5. $ mkdir build
  6. $ cd build
  7. $ ../binutils-2.26/configure --enable-gold --enable-plugins --disable-werror --prefix=/usr
  8. $ make -j 5
  9. $ sudo make install

If you want, you can build LLVMgold.so as below steps
  1. Download llvm-3.8.0 source code from http://www.llvm.org/releases/3.8.0/llvm-3.8.0.src.tar.xz and extract it to ~/llvm-3.8.0.src
  2. Download clang3.8.0 source code from http://www.llvm.org/releases/3.8.0/cfe-3.8.0.src.tar.xz and extract it to ~/llvm-3.8.0.src/tools/clang
  3. Refer http://clang.llvm.org/get_started.html to Install other necessary clang build tools if missing
  5. $ mkdir llvm38build
  6. $ cd llvm38build
  7. If your GNU Binutils 2.26 is in  /home/jshi19/binutils-2.26, $ cmake ../llvm-3.8.0.src -G "Unix Makefiles" -DCMAKE_BUILD_TYPE="Release" -DLLVM_TARGETS_TO_BUILD="X86" -DCMAKE_VERBOSE_MAKEFILE=ON -DCMAKE_CXX_COMPILER="/usr/bin/g++" -DCMAKE_C_COMPILER="/usr/bin/gcc" -DLLVM_BINUTILS_INCDIR=/home/jshi19/binutils-2.26/include
  8. $ make -j 5 LLVMgold
  The LLVMgold.so is in ~/llvm38build/lib/LLVMgold.so

======================================================================================================
There are several issues as bleow. WELCOME and APPRECIATE any suggestion to them:
* Not use gold linker, but directly use standard ld. GNU gold linker ld-new (GNU Binutils 2.26.20160125) 1.11 fails to link edk2 static library file (*.dll) with error message: "ld: internal error in do_layout, at ../../binutils-2.26/gold/object.cc:1819" Have submitted the gold bug in Bug 20062  - Gold2.26 fail to link Uefi firmware with internal error in do_layout, but ld works (https://sourceware.org/bugzilla/show_bug.cgi?id=20062) 


