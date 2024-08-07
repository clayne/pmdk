# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2014-2024, Intel Corporation

#
# src/libpmem/Makefile -- Makefile for libpmem
#

include ../common.inc

LIBRARY_NAME = pmem
LIBRARY_SO_VERSION = 1
LIBRARY_VERSION = 0.0
SOURCE =\
	$(CORE)/alloc.c\
	$(CORE)/fs_posix.c\
	$(CORE)/os_posix.c\
	$(CORE)/os_thread_posix.c\
	$(CORE)/out.c\
	$(CORE)/util.c\
	$(CORE)/util_posix.c\
	$(CORE)/last_error_msg.c\
	$(CORE)/log.c\
	$(CORE)/log_default.c\
	$(COMMON)/file.c\
	$(COMMON)/file_posix.c\
	$(COMMON)/mmap.c\
	$(COMMON)/mmap_posix.c\
	$(COMMON)/os_deep_linux.c\
	libpmem.c\
	memops_generic.c\
	pmem.c\
	pmem_posix.c\
	$(PMEM2)/pmem2_utils.c\
	$(PMEM2)/config.c\
	$(PMEM2)/persist_posix.c\
	$(PMEM2)/source.c\
	$(PMEM2)/source_posix.c\
	$(PMEM2)/pmem2_utils_linux.c\
	$(PMEM2)/pmem2_utils_$(OS_DIMM).c\
	$(PMEM2)/auto_flush_linux.c\
	$(PMEM2)/deep_flush_linux.c\
	$(PMEM2)/region_namespace_$(OS_DIMM).c\
	$(PMEM2)/numa_$(OS_DIMM).c

INCS += -I$(TOP)/src/libpmem2

include ../libpmem2/$(ARCH)/sources.inc

SOURCE += $(LIBPMEM2_ARCH_SOURCE)

include ../Makefile.inc

include $(PMEM2)/$(ARCH)/flags.inc

CFLAGS += -I. $(LIBNDCTL_CFLAGS)
LIBS += -pthread $(LIBNDCTL_LIBS)
