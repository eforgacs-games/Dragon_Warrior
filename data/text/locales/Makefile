i18n:
	xgettext --files-from=POTFILES.in --directory=.. --output=base.pot && msgmerge --update --no-fuzzy-matching --backup=off ko/LC_MESSAGES/base.po base.pot && msgfmt ko/LC_MESSAGES/base.po --output-file ko/LC_MESSAGES/base.mo
clean:
	rm ko/LC_MESSAGES/base.mo