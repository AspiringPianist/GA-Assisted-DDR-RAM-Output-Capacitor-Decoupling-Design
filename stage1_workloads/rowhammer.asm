; rowhammer.asm — Adversarial double-sided row hammering workload
; Hammers two rows in the same bank with clflush + mfence between accesses.
; Maximises simultaneous switching events on VDDQ.
; Industry stress test used in reliability qualification.

section .data
    BUFFER_SIZE   equ 256 * 1024 * 1024  ; 256 MB
    ROW_OFFSET    equ 8192               ; Row size (8KB typical for DDR4)
    HAMMER_COUNT  equ 2000000            ; Number of hammer iterations

section .text
global _start
extern setup_mmap, exit_program

_start:
    ; Allocate 256MB buffer
    call    setup_mmap
    mov     r12, rax                    ; r12 = buffer base

    ; Select two rows in the same bank, separated by one row
    ; Row A: base + 0
    ; Row B: base + 2 * ROW_OFFSET (skip one row in between = double-sided)
    lea     r13, [r12]                  ; row_a address
    lea     r14, [r12 + 2 * ROW_OFFSET] ; row_b address

    mov     rcx, HAMMER_COUNT           ; iteration count

    ; Align to prevent straddling cache lines
    align   16

.hammer_loop:
    ; Access row A
    mov     rax, [r13]          ; read row A (triggers ACT if not in row buffer)
    clflush [r13]               ; evict from all cache levels
    mfence                      ; serialise — ensure flush completes before next access

    ; Access row B (same bank, different row)
    mov     rbx, [r14]          ; read row B (forces PRE + ACT)
    clflush [r14]               ; evict from cache
    mfence                      ; serialise

    dec     rcx
    jnz     .hammer_loop

    call    exit_program
