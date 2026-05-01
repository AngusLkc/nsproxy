#pragma once
#include <stddef.h>
#include <sys/socket.h>
#include "loop.h"

struct buff {
    size_t capacity;
    size_t size;
    char data[];
};

#define buff_calloc(n) __extension__ ({                         \
    size_t n__ = (n);                                           \
    struct buff *buff__ = calloc(1, sizeof(struct buff) + n__); \
    if (buff__ != NULL) buff__->capacity = n__;                 \
    buff__;                                                     \
})

struct skinfo {
    char desc[64];
    size_t nsent;
    size_t nread;
};

int skutils_connect(struct skinfo *info, const char *addr, uint16_t port,
                    int type);
int skutils_evctl(struct skinfo *info, struct loopctx *loop, int sfd,
                  unsigned int *events, struct epcb_ops *epcb,
                  unsigned int mask, int enable);
ssize_t skutils_send(struct skinfo *info, int sfd, const char *data,
                     size_t size);
ssize_t skutils_sendmsg(struct skinfo *info, int sfd, struct msghdr *msg);
ssize_t skutils_recv(struct skinfo *info, int sfd, char *data, size_t size);
int skutils_shutdown(struct skinfo *info, struct loopctx *loop, int *sfd,
                     int how, int rst);
void skutils_close_unreg(struct skinfo *info, struct loopctx *loop, int *sfd);
