#
#
# OneFichier Makefile

# Tools
RM      = rm -rf
LN      = ln -sf
MKDIR   = mkdir -p
CP      = cp

# Files
FILES   = onefichier.py
CONFIG  = config.sample.json
DOCS    = README.md

# Target paths
NAME	= onefichier
BINDIR  = /usr/bin/$(NAME)
DATADIR	= /usr/share/$(NAME)

install:
	@# Copy script
	@$(MKDIR) $(DATADIR)
	@$(CP) $(FILES) $(DATADIR)/
	@$(LN) $(DATADIR)/$(FILES) /usr/bin/$(NAME)


uninstall:
	@$(RM) $(BINDIR)
	@$(RM) $(DATADIR)
