#include <endian.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

uint64_t r[1] = {0xffffffffffffffff};

int main(void) {
  	syscall(__NR_mmap, 0x1ffff000ul, 0x1000ul, 0ul, 0x32ul, -1, 0ul);
	syscall(__NR_mmap, 0x20000000ul, 0x1000000ul, 7ul, 0x32ul, -1, 0ul);
	syscall(__NR_mmap, 0x21000000ul, 0x1000ul, 0ul, 0x32ul, -1, 0ul);
      	intptr_t res = 0;
memcpy((void*)0x20000000, "./file0\000", 8);
	syscall(__NR_mkdirat, 0xffffff9c, 0x20000000ul, 0ul);
memcpy((void*)0x200000c0, "./file0/../file0\000", 17);
	res = syscall(__NR_open, 0x200000c0ul, 0ul, 0ul);
	if (res != -1)
		r[0] = res;
	syscall(__NR_ioctl, r[0], 0xc008666c, 0ul);
  return 0;
}
