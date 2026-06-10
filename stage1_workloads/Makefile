# Makefile for DDR4 PDN workload binaries
# Compiles assembly microbenchmarks using NASM + ld (no libc)

ASM      = nasm
ASMFLAGS = -f elf64
LD       = ld
LDFLAGS  =

WORKLOADS = streaming random_access rowhammer
TARGETS   = $(addsuffix .elf, $(WORKLOADS))
OBJECTS   = $(addsuffix .o, $(WORKLOADS)) common.o

.PHONY: all clean

all: $(TARGETS)

# Common object file
common.o: common.asm
	$(ASM) $(ASMFLAGS) -o $@ $<

# Pattern rules for workload binaries
%.o: %.asm
	$(ASM) $(ASMFLAGS) -o $@ $<

%.elf: %.o common.o
	$(LD) $(LDFLAGS) -o $@ $^

clean:
	rm -f *.o *.elf

# Individual targets for convenience
streaming: streaming.elf
random_access: random_access.elf
rowhammer: rowhammer.elf
