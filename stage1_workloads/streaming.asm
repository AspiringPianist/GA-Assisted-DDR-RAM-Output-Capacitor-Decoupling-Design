; streaming.asm — Sequential movnti (non-temporal store) workload
; Models a memory controller performing sequential prefetch fills.
; Uses cache-bypassing writes with 64-byte stride.
; Every access is a sequential row hit = best-case (minimum ACT/PRE rate).

section .data
    BUFFER_SIZE equ 256 * 1024 * 1024   ; 256 MB
    ITERATIONS  equ 4                    ; Number of full passes

section .text
global _start
extern setup_mmap, exit_program

_start:
    ; Allocate 256MB buffer
    call    setup_mmap
    mov     r12, rax                    ; r12 = buffer base address

    ; Outer loop: multiple passes over the buffer
    mov     r13, ITERATIONS
.outer_loop:
    mov     rdi, r12                    ; rdi = current write pointer
    lea     rsi, [r12 + BUFFER_SIZE]    ; rsi = end of buffer

    ; Inner loop: sequential movnti with 64-byte stride (cache-line sized)
.inner_loop:
    movnti  [rdi],      rax            ; Non-temporal store (bypasses cache)
    movnti  [rdi + 8],  rax
    movnti  [rdi + 16], rax
    movnti  [rdi + 24], rax
    movnti  [rdi + 32], rax
    movnti  [rdi + 40], rax
    movnti  [rdi + 48], rax
    movnti  [rdi + 56], rax

    add     rdi, 64                     ; Advance by one cache line
    cmp     rdi, rsi
    jb      .inner_loop

    sfence                              ; Ensure all NT stores are visible

    dec     r13
    jnz     .outer_loop

    call    exit_program
