# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2019-2023, Intel Corporation

#
# src/test/pmem2_persist/Makefile -- build pmem2_persist unit test
#
TOP = ../../..

vpath %.c $(TOP)/src/libpmem2
vpath %.c $(TOP)/src/core

INCS += -I$(TOP)/src/libpmem2

TARGET = pmem2_persist

LIBPMEMCORE=internal-debug
OBJS += pmem2_persist.o\
	persist.o\
	memops_generic.o\
	deep_flush_linux.o\
	pmem2_utils_linux.o\
	region_namespace_$(OS_DIMM).o

ifeq ($(OS_DIMM),ndctl)
LINK_NDCTL=y
endif

include ../Makefile.inc
