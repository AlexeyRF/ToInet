CC ?= gcc
CFLAGS ?= -O2 -Wall -Isrc
LDFLAGS = -lws2_32 -lmswsock -ladvapi32

SRCS = src/conev.c \
       src/desync.c \
       src/extend.c \
       src/fake_data.c \
       src/helpers.c \
       src/main.c \
       src/mpool.c \
       src/packets.c \
       src/protocol.c \
       src/proxy.c \
       src/win_service.c \
       src/crypto/aes-ctr.c \
       src/crypto/aes-gcm.c \
       src/crypto/aes.c \
       src/crypto/gcm.c \
       src/crypto/hkdf.c \
       src/crypto/hmac.c \
       src/crypto/sha224-256.c \
       src/crypto/usha.c

OBJS = $(SRCS:.c=.o)
TARGET = zdpi.exe

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) -o $@ $(OBJS) $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

ifeq ($(OS),Windows_NT)
    RM = cmd /C del /F /Q
    FIXPATH = $(subst /,\,$1)
else
    RM = rm -f
    FIXPATH = $1
endif

clean:
	-$(RM) $(call FIXPATH,$(OBJS)) $(TARGET)

.PHONY: all clean
