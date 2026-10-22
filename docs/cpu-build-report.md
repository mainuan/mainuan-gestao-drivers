# Auditoria CPU e empacotamento RC1 - 2026-10-22

## Resultado e limites

Conteudo do pacote all aprovado; build, regressao e startup nativo aprovados.
Workflow baseline preparado, mas **ainda nao executado no GitHub nesta tarefa**.
**Nao houve emulacao local nem comprovacao em hardware x86-64 v1/ISO.**
O host nao possui Docker/Podman/QEMU instalados; nao foram instalados para
contornar essa limitacao. Nenhum pacote/driver foi instalado no host.

1. Arquitetura original: Architecture all, scripts Python e recursos. Base
   limpa `6eac643e8a9c68d6b3febabc660bc4fff7f469f5`, branch port/kubuntu-26.04.
   Nao havia .deb anterior disponivel localmente; foi reconstruida a mesma
   versao com runtime usr integralmente inalterado. Nenhum build C/C++/CMake,
   extensao compilada, dependencia vendorizada ou helper nativo proprio.
2. .deb final: **zero ELF**, 152 arquivos regulares, 21 .py, 100 .mo, 8 SVG e
   1 PNG. O unico launcher e o symlink usr/bin/mainuan-gestao-drivers para o
   script do pacote. .mo sao dados gettext, nao instrucoes de CPU. Gate agora
   recusa magic ELF/outros formatos nativos mesmo sob nome .bin, extensoes
   nativas/archives/wheels, permissoes inseguras e links externos/quebrados.
3. Dependencias nativas observadas no host:

| Componente | Versao local | Evidencia ISA |
| --- | --- | --- |
| Python 3 | wrapper 3.14.3-0ubuntu2, executavel Python 3.14 | Nota NEEDED baseline |
| PyQt6 | 6.10.2-2build5 | Notas ISA ausentes nos bindings observados |
| Qt6 Widgets/DBus/Core | 6.10.2+dfsg-7 | Notas ISA ausentes nos ELF observados |
| python3-apt | 3.1.0ubuntu1.1 | apt_pkg/libapt observados sem nota ISA |
| ubuntu-drivers-common | 1:0.10.9 | Import real; helpers nativos auditados estaticamente |
| PackageKit | 1.3.4-3ubuntu1.2 | Resolve real; daemon/backend e ldd auditados estaticamente |
| libc6 | 2.43-2ubuntu2.4 | Nota NEEDED baseline |

64 ELF efetivamente carregados pelo cliente: 3 com NEEDED baseline, 61 sem nota.
Nenhuma declaracao NEEDED superior a baseline encontrada. **Sem nota significa
ISA nao declarada, nao prova v1.** Nao inferir AVX2 obrigatorio da CPU moderna
do host/runner, nem de instrucoes opcionais selecionadas por CPUID.
Resolucoes estaticas: PackageKit 72 entradas; UDC 11, mokutil 9, openssl 7,
kmod 6, polkitd 27 (grupos podem compartilhar bibliotecas). Nao sao mapas de
processos de daemon realmente executando sob CPU v1. libpackagekit-glib2/libglib
do servico Ubuntu sao dependencias nativas legitimas, nao importacao Python
PackageKitGlib/GTK pelo frontend Qt. Nenhuma biblioteca do sistema foi incorporada.

4. Welcome: consultados os quatro arquivos solicitados no commit atual
   a4c56e93696fd44ed23abc2b69d1fe06a9eeb822. O problema de codegen/link/startup
   objects C++ nao se transfere ao payload Python; adaptados isolamento, variantes,
   notas de dependencias, emulacao e evidencia. Sem flags -march/copias de CMake,
   novo executavel CPUID C, bibliotecas incluidas ou mudanca all -> amd64.
5. Actions: novo build-mainuan-deb.yml proprio; push/PR da branch portada e
   dispatch, checkout do SHA exato, token contents:read, credenciais nao persistidas,
   Actions fixadas por SHA conferido. Removido build.yml Mint/master/secrets-inherit.
   Sem tags ou Releases. stale.yml administrativo permanece fora do build.
   Preparacao root somente no container; testes/build/auditorias como mainuan-build.
   Upload somente apos todos os gates: .deb, SHA256SUMS validado, logs e JSONs,
   nomeados pelo commit. Nao se executa o probe manual hello em CI.
6. Imagem oficial Ubuntu 26.04, linux/amd64, manifesto fixado/conferido:
   sha256:42527649dbc4f9197a6073f426f488cbff0e9cc9f2afce32d91c383e4875634a.
   Config OCI: b9e485d4a3bc6efa60fc5150444a82f3d96991fdcec7caa1d0f3e7a0b5859321.
   Leitura estatica das duas camadas com SHA256 conferido: Ubuntu 26.04.1 LTS,
   VERSION_ID 26.04, 87 pacotes instalados all/amd64, nenhuma variante nao-baseline
   nos metadados. Nenhum binario dessa imagem foi instalado/executado no host.
   Pipeline desabilita variantes ANTES do primeiro apt update/install, verifica
   campo Architecture-Variant de todos os pacotes e registra origens/versoes.
   Os testes do guard incluem libc6 Architecture amd64 + Variant amd64v3.
   No host, inventario report-only corretamente NAO aprova o contrato CI:
   Mainuan VERSION_ID 2026, multiarch e sem politica de variantes explicita.
   Isso nao afirma que o host exige AVX2; nao alteramos sua configuracao APT.
7. Testes: **357 total, 357 passed, 0 skipped, 0 failed**. Todos os 341 anteriores
   preservados, 16 novos para payload, links/permissoes, variantes, notas, CPUID
   diagnostico e workflow. Compileall usr/tests/.github/scripts OK. PackageKit
   read-only Introspect/CreateTransaction/Resolve/Package/Finished OK,
   mutation_observed=False. Nenhum teste automatico instalou/removeu drivers,
   mudou DKMS/modulos/MOK/Secure Boot/repositorios ou reiniciou o sistema.
8. Startup: pacote extraido, nao instalado; modulos carregados do proprio payload
   (assertion do caminho), QApplication/Qt Widgets/QtDBus/APT/UDC reais. Invocacoes
   test e sem argumentos passaram, UI/radios/renderizacao criados e encerramento
   normal depois do QThread. I/O normal de deteccao e substituido por fixtures no
   harness; nao e teste de hardware. Transport/install/remove mutadores sao
   tripwires. Sem imports GTK/GI, sem erro CPU ISA. Aviso offscreen conhecido
   propagateSizeHints() nao impediu criacao/renderizacao/fechamento.
9. CPU: startup local grava baseline_emulated=false. QEMU ausente causa exit 2
   no modo padrao, sem fallback silencioso. No CI QEMU e OBRIGATORIO, com recursos
   pos-v1 removidos e CPU efetiva conferida pelo loader glibc (SSE2/CPUID/hwcaps).
   Adapter dos indices conferido no header glibc instalado; testes de campos
   ausentes/recursos proibidos falham fechado. Esse gate NAO foi executado aqui;
   container comum nao limita a CPU e nao foi apresentado como prova.
10. dpkg-buildpackage -us -uc -b: OK, Package mainuan-gestao-drivers,
    Version 1.0~rc1, Architecture all. Versao/changelog/rules/control/desktop,
    codigo de drivers e interface publica usr nao foram alterados.
11. Lintian --fail-on error,warning: OK, sem erros/warnings. Desktop validation,
    dpkg-deb -I/-c, permissoes, gate all/Qt-only/links e migracao conffile OK.
    Creditos/Linux Mint/GPL preservados. Sem .pyc/__pycache__, ELF/archives nativos,
    GTK/XApp legado, sudoers ou helpers proprios; probes/CI nao instalados.
12. Pacote absoluto:
    /home/daigo/Github/mainuan-gestao-drivers_1.0~rc1_all.deb.
    Copia e SHA256SUMS em /home/daigo/Github/mainuan-gestao-drivers/dist/.
13. SHA256: `f36508f0f82e9c901fee1db7f799bb8c00bc8aa3a11b3f65ef1bb78b6ecce318`.
    sha256sum --check SHA256SUMS aprovado. O checksum comprova integridade,
    nao compatibilidade da ISO nem autenticidade de uma origem desconhecida.
14. Criados: .github/workflows/build-mainuan-deb.yml; .github/scripts/check_cpu.py,
    cpu_smoke.py, qt_startup_probe.py; tests/test_cpu_packaging.py;
    docs/cpu-compatibility.md e este relatorio. Removido .github/workflows/build.yml.
    Modificados: .gitignore (dist gerado), README.md, debian/docs e tests/inspect_deb.py.
    Nenhuma dependencia runtime nova. Depends e Recommends originais preservados.
15. Pendencias: primeira execucao real do novo workflow, QEMU baseline efetivo,
    boot/Wayland/PackageKit/helpers em CPU v1 e hardware antigo na primeira ISO.
    Auditar a ISO inteira e configurar variantes antes de instalar componentes;
    nao tentar corrigir bibliotecas v3 simplesmente mudando APT depois. APT pode
    atualizar dependencias mesmo com imagem fixada, por isso os gates sao repetidos.
    Hardware sem drivers adicionais e valido; nao forcar NVIDIA/Broadcom.
    QEMU user-mode compartilha kernel e startup nao cobre todos os caminhos.
16. Git: branch portada, base 6eac643e8a9c68d6b3febabc660bc4fff7f469f5, alteracoes
    para revisao, sem staging/commit/push/tag/release; master nao alterada.
    git diff --check limpo; dist ignorado e artefatos debhelper limpos da arvore.
    Artefato local deriva da base MAIS alteracoes nao commitadas; nao foi chamado
    de build do SHA puro. Futuro Actions exige HEAD == github.sha e registra
    proveniencia. Comando Welcome mainuan-gestao-drivers e desktop ID preservados,
    sem argumento adicional, acoplamento de versao ou recompilacao do Welcome.

## Evidencias locais

dist/SHA256SUMS, cpu-base-image.json, cpu-environment-host.json,
cpu-startup-native.json, cpu-dependencies-native.json, cpu-smoke-native.log,
unit-tests.log, packagekit-readonly.log, build.log, lintian.log e package-files.log.
Esses arquivos gerados nao fazem parte do pacote nem sao versionados.
Politica, comandos, referencias primarias e limites em cpu-compatibility.md.
