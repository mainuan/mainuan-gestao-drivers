DOMAIN = mainuan-gestao-drivers
DESKTOP = usr/share/applications/org.mainuan.GestaoDrivers.desktop
DESKTOP_IN = data/org.mainuan.GestaoDrivers.desktop.in
I18N_BUILD = .i18n-build

all: buildmo $(DESKTOP)

buildmo:
	@echo "Building the mo files"
	for lang in $$(grep -v '^#' po/LINGUAS); do \
		install -d usr/share/locale/$$lang/LC_MESSAGES/; \
		msgfmt --check -o usr/share/locale/$$lang/LC_MESSAGES/mainuan-gestao-drivers.mo po/$(DOMAIN)-$$lang.po; \
	done

# msgfmt --desktop reads <lang>.po and LINGUAS from one directory; the catalogs
# keep their historical po/$(DOMAIN)-<lang>.po names, so they are linked there.
$(DESKTOP): $(DESKTOP_IN) po/LINGUAS $(wildcard po/$(DOMAIN)-*.po)
	rm -rf $(I18N_BUILD)/desktop-po
	install -d $(I18N_BUILD)/desktop-po $(dir $@)
	for lang in $$(grep -v '^#' po/LINGUAS); do \
		ln -s $(CURDIR)/po/$(DOMAIN)-$$lang.po $(I18N_BUILD)/desktop-po/$$lang.po; \
	done
	cp po/LINGUAS $(I18N_BUILD)/desktop-po/LINGUAS
	msgfmt --desktop --template=$(DESKTOP_IN) -d $(I18N_BUILD)/desktop-po -o $@

clean:
	rm -rf usr/share/locale $(DESKTOP) $(I18N_BUILD)

.PHONY: all buildmo clean
