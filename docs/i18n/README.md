# Internacionalização — mainuan-gestao-drivers

Contrato comum: `docs/03-arquitetura-i18n-kde.md` do repositório `mainuan`.

## Resumo

| Item | Valor |
|---|---|
| Domínio gettext | `mainuan-gestao-drivers` |
| Idioma-fonte (msgid) | inglês |
| POT | `mainuan-gestao-drivers.pot` (raiz do repositório) |
| Catálogos | `po/mainuan-gestao-drivers-<lang>.po` (layout histórico, mantido) |
| Idiomas compilados | `po/LINGUAS` |
| Fontes extraídas | `po/POTFILES.in` |
| Configuração | `po/i18n.conf` (usado por `po/i18n.sh`) |
| `.desktop` | modelo `data/org.mainuan.GestaoDrivers.desktop.in`, gerado no build |
| Instalação | `/usr/share/locale/<lang>/LC_MESSAGES/mainuan-gestao-drivers.mo` |

## Execução

`mainuan_drivers/qt/application.py` liga o domínio a `<prefixo>/share/locale`
(`LOCALE_DIR` em `mainuan_drivers/__init__.py`): `/usr/share/locale` quando
instalado e `usr/share/locale` do repositório quando executado do código-fonte
depois de `make`. Os módulos usam `gettext.gettext`, que resolve o idioma por
`LANGUAGE`, `LC_ALL`, `LC_MESSAGES` e `LANG`. Nenhum idioma é forçado. Os botões
padrão do Qt vêm de `qtbase_<lang>.qm`, carregado para `QLocale.system()`.

O nome exibido vem de `display_name()` (msgid `Driver Manager`; pt_BR
`Gestão de Drivers`). `DISPLAY_NAME` continua sendo a identidade oficial do
produto e é o que `--version` imprime.

## Tarefas

```sh
./makepot                 # = po/i18n.sh extract && po/i18n.sh update
po/i18n.sh check-pot      # falha se o POT não corresponde ao código (CI)
po/i18n.sh validate       # msgfmt --check + placeholders (CI)
po/i18n.sh coverage       # estatística por idioma
make                      # compila .mo em usr/share/locale e gera o .desktop
make clean
```

Adicionar idioma: `po/i18n.sh add <lang>` (cria o catálogo com Plural-Forms
verificado e acrescenta a `po/LINGUAS`). Strings novas: envolva com `_()`,
`gettext.ngettext()` ou `gettext.pgettext()`, acrescente o arquivo a
`po/POTFILES.in` se for novo, rode `./makepot` e traduza `pt_BR`.

## Testes

```sh
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests
```

`tests/test_i18n.py` compila o catálogo pt_BR e executa a janela real com
`LANGUAGE=pt_BR` (texto português) e `LANGUAGE=en`/`C` (texto inglês).

## Empacotamento

`debian/rules` usa `dh`; `dh_auto_build` executa `make`, que compila os `.mo`
listados em `po/LINGUAS` e gera
`usr/share/applications/org.mainuan.GestaoDrivers.desktop` com
`msgfmt --desktop` (o `msgfmt` exige `<lang>.po` + `LINGUAS` num diretório, por
isso o Makefile cria links em `.i18n-build/desktop-po`). `debian/install`
(`usr`) instala tudo. Build-dep: `gettext`. Os artefatos gerados estão no
`.gitignore`.

## Origem dos catálogos herdados

Os catálogos de outros idiomas vêm do **mintdrivers** do Linux Mint
(cabeçalhos "translation for linuxmint", "Rosetta Contributors and Canonical
Ltd", `X-Generator: Launchpad`; no histórico git, commits "Own translations" /
"l10n: Update translations" de Clement Lefebvre, 2020–2021). Foram traduzidos no
Launchpad (projeto `linuxmint`) e declaram a mesma licença do pacote
(GPL-2+). Créditos de tradutores são mantidos nos cabeçalhos; ver
`debian/copyright`.

Eles cobrem a interface GTK antiga; após `msgmerge` com o POT atual, apenas
as mensagens com o mesmo msgid ficam traduzidas (≈7 por idioma). O restante
fica como `fuzzy` (sugestão, não compilada) ou obsoleto `#~` (preservado para
referência). Revisão por idioma será feita centralmente.
