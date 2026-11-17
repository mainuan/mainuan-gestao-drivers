<div align="center">

<img src="usr/share/icons/hicolor/scalable/apps/mainuan-gestao-drivers.svg" width="96" alt="Ícone do Mainuan Gestão de Drivers">

# Mainuan Gestão de Drivers

Detecta os drivers adicionais do computador e instala ou troca drivers com segurança, pelo PackageKit e pelo PolicyKit do Plasma.

[![CI](https://github.com/mainuan/mainuan-gestao-drivers/actions/workflows/build-mainuan-deb.yml/badge.svg)](https://github.com/mainuan/mainuan-gestao-drivers/actions/workflows/build-mainuan-deb.yml)
[![Release](https://img.shields.io/github/v/release/mainuan/mainuan-gestao-drivers)](https://github.com/mainuan/mainuan-gestao-drivers/releases/latest)
![Plataforma](https://img.shields.io/badge/Kubuntu%2026.04%20%7C%20Plasma%206.6-1d99f3)

**Português** · [English](README.en.md)

</div>

---

## O que é

O Mainuan Gestão de Drivers é a ferramenta de hardware do Mainuan Linux. Ela lista os drivers adicionais recomendados para placas de vídeo NVIDIA, Wi-Fi Broadcom e outros dispositivos, mostra uma prévia das mudanças de pacotes e só aplica o que o usuário confirmar.

É um derivado do Driver Manager do **Linux Mint** (mintdrivers), reescrito em Qt 6 Widgets/PyQt6, sem frontend GTK ou XApp. A detecção usa o `ubuntu-drivers-common` e consultas APT, num backend Python independente da interface. As alterações são feitas pelo PackageKit (via `PyQt6.QtDBus`) e autorizadas pelo agente PolicyKit do Plasma: o aplicativo não pede senha, não executa APT nem dpkg diretamente e não tem helper privilegiado próprio.

```text
hardware → APT + repositórios configurados/PPAs → ubuntu-drivers-common
         → backend Mainuan → preflight → Qt6 → PackageKit → PolicyKit
```

A versão 1.0 é a primeira versão estável.

## Funcionalidades

- Detecção de drivers adicionais pelo `ubuntu-drivers-common`, respeitando a recomendação do Ubuntu e o candidato/pinning do APT, inclusive para repositórios de terceiros.
- Prévia das mudanças de pacotes e aplicação só após confirmação explícita de um plano revalidado.
- Verificação prévia, somente leitura, de módulo, kernel/headers, DKMS, Secure Boot e inscrição MOK. Com Secure Boot ativo, DKMS só prossegue se o certificado realmente usado pelo DKMS estiver inscrito; estado desconhecido ou inscrição pendente bloqueiam a mudança.
- Reavaliação depois de cada transação: pacote instalado não é tratado como driver ativo.
- Na sessão Live, detecção e prévia funcionam, mas as alterações ficam bloqueadas.
- Modo `test` com dispositivos fictícios (NVIDIA, Broadcom, Secure Boot, DKMS, MOK, headers, terceiros, Live, falha do backend, PackageKit indisponível, nenhum driver) que simula tudo em memória.
- Diagnóstico local copiável pelo menu Ajuda, sem envio automático, senhas, chaves privadas ou identificação pessoal.

Limites conhecidos: trocas que removem e instalam pacotes não são atômicas (em caso de falha o app detecta de novo o estado real, sem restaurar drivers sozinho); não há `autoremove`, reinício automático, gerenciamento de Mesa ou PPAs, nem geração ou inscrição de chaves MOK. Detalhes em [docs/qt-transactions.md](docs/qt-transactions.md).

## Instalação

O Gestão de Drivers já vem instalado na ISO do Mainuan. Para instalar manualmente, baixe `mainuan-gestao-drivers_1.0_all.deb` e `SHA256SUMS` da [última release](https://github.com/mainuan/mainuan-gestao-drivers/releases/latest) e, na pasta dos dois arquivos:

```bash
sha256sum --check --ignore-missing SHA256SUMS
sudo apt install ./mainuan-gestao-drivers_1.0_all.deb
```

Para remover: `sudo apt remove mainuan-gestao-drivers`. Instalar ou remover o aplicativo não mexe em dependências, repositórios, módulos ou Secure Boot. As Releases do GitHub não são um repositório APT.

## Uso

Abra **Gestão de Drivers** no menu de aplicativos (categoria Configurações) ou pelo card *Drivers adicionais* do [Mainuan Welcome](https://github.com/mainuan/welcome). Pelo terminal:

```text
mainuan-gestao-drivers [test] [--debug] [--version] [--help]
```

| Opção | Efeito |
|---|---|
| `test` | usa dispositivos fictícios e um seletor de cenários; aplicar só simula em memória, sem PackageKit e sem tocar no sistema |
| `--debug` | registros detalhados de diagnóstico, sem mudar a política de drivers |
| `--version` | mostra a versão e sai |
| `--help` | mostra o uso e sai |

Página de manual: `man mainuan-gestao-drivers`.

## Informações técnicas

| Item | Valor |
|---|---|
| Linguagem | Python 3 |
| Toolkit | Qt 6 Widgets (PyQt6), QtDBus |
| Base | Kubuntu 26.04 LTS, KDE Plasma 6.6 |
| Pacote | `mainuan-gestao-drivers` (Debian, `all`) |
| Dependências principais | `python3-pyqt6`, `python3-apt`, `ubuntu-drivers-common`, `packagekit`, `qt6-svg-plugins`; recomenda `mokutil`, `openssl`, `kmod` |
| Arquitetura | amd64; o pacote é `all`, e o CI confere a inicialização em CPU x86-64 básica |
| Lançador | `org.mainuan.GestaoDrivers.desktop` |

`Architecture: all` não garante que as bibliotecas da ISO sejam compatíveis com CPUs antigas. O CI constrói num Ubuntu 26.04 sem variantes `amd64v3` e inicia o app sob QEMU; evidências e limites em [docs/cpu-compatibility.md](docs/cpu-compatibility.md).

Mais documentação:

- [Arquitetura de transações e garantias da 1.0](docs/qt-transactions.md)
- [Notas da versão 1.0](docs/1.0-release-notes.md), [relatório final](docs/1.0-release-report.md) e [critérios para a 1.0](docs/1.0-release-criteria.md)
- [Roteiro de instalação, upgrade e purge na VM](docs/1.0-testing.md)
- [Auditoria upstream final](docs/upstream-audit-1.0.md) e [política de acompanhamento do Linux Mint](docs/upstream-sync-policy.md)

## Compilação e testes

Estes são os comandos principais do workflow [Build Mainuan Debian package](.github/workflows/build-mainuan-deb.yml), num Ubuntu/Kubuntu 26.04 (a lista completa de pacotes instalados pelo CI está no próprio workflow):

```bash
git clone https://github.com/mainuan/mainuan-gestao-drivers.git
cd mainuan-gestao-drivers
sudo apt-get build-dep --no-install-recommends ./
sudo apt-get install python3-pyqt6 qt6-svg-plugins python3-apt ubuntu-drivers-common packagekit

po/i18n.sh check-pot && po/i18n.sh validate            # catálogos de tradução
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
python3 -m compileall -q usr tests
python3 tests/probe_packagekit_readonly.py              # PackageKit só leitura
dpkg-buildpackage -us -uc -b
python3 tests/inspect_deb.py ../mainuan-gestao-drivers_1.0_all.deb
lintian --fail-on error,warning ../mainuan-gestao-drivers_1.0_all.deb
```

Para rodar sem instalar: `./usr/bin/mainuan-gestao-drivers test`. Para ver as traduções no checkout, rode antes `make`, que compila os catálogos e gera o `.desktop`. Nenhum teste altera drivers do host.

O CI também roda os testes de CPU básica (`.github/scripts/check_cpu.py` e `cpu_smoke.py`) e instala o `.deb` num contêiner Ubuntu 26.04 limpo: confere os arquivos, executa `--version` e `--help` como usuário comum, reinstala, remove e expurga sem sobras. A Release só é publicada por tag `v*` igual à versão do changelog e nunca substitui uma Release existente.

## Traduções

A interface está completa em 33 idiomas: ar, bn, cs, da, de, el, es, fa, fi, fr, he, hi, hu, id, it, ja, ko, nb, nl, pl, pt, pt_BR, ro, ru, sv, sw, th, tr, uk, ur, vi, zh_CN e zh_TW. Outros 68 catálogos, herdados do Linux Mint (Launchpad), cobrem só as poucas mensagens que não mudaram desde a interface GTK. O idioma segue o do Plasma.

Como traduzir: [docs/i18n/README.md](docs/i18n/README.md).

## Contribuição

Relate problemas em [Issues](https://github.com/mainuan/mainuan-gestao-drivers/issues) e envie pull requests para `master`. Cada PR passa pelo CI completo (testes, lintian, CPU básica e instalação limpa). Mudanças vindas do Linux Mint seguem a [política de acompanhamento](docs/upstream-sync-policy.md).

## Créditos

Mainuan:

- **Rafael Ruscher** ([@ruscher](https://github.com/ruscher))
- **Daigo** ([@daigoasuka](https://github.com/daigoasuka))

Projeto de origem: [Linux Mint mintdrivers](https://github.com/linuxmint/mintdrivers), de **Clement Lefebvre** (Copyright 2013-2014), com Michael Webster, Frédéric Gaudet e os demais colaboradores preservados no histórico Git e em `debian/changelog`. Tradutores do Launchpad (projeto `linuxmint`) estão creditados nos cabeçalhos dos catálogos.

## Licença

GPL-2.0-or-later, conforme [`debian/copyright`](debian/copyright); as modificações Mainuan usam a mesma licença. O repositório não tem um arquivo `LICENSE` na raiz.
