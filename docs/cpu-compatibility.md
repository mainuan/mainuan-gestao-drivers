# Compatibilidade x86-64 basico - Gestao de Drivers 1.0

Alvo: x86-64 v1/SSE2, sem AVX/AVX2/AVX-512 obrigatorios. Versao
**1.0**, Architecture **all**. Isto NAO declara toda ISO universalmente
compativel: cliente, dependencias Ubuntu e sistema instalado sao tres camadas.

## Referencia e diferenca arquitetural

Auditoria em 2026-10-22 do Mainuan Welcome, commit
`a4c56e93696fd44ed23abc2b69d1fe06a9eeb822`:
[workflow](https://github.com/mainuan/welcome/blob/a4c56e93696fd44ed23abc2b69d1fe06a9eeb822/.github/workflows/build-deb.yml),
[check_cpu](https://github.com/mainuan/welcome/blob/a4c56e93696fd44ed23abc2b69d1fe06a9eeb822/.github/scripts/check_cpu.py),
[smoke](https://github.com/mainuan/welcome/blob/a4c56e93696fd44ed23abc2b69d1fe06a9eeb822/.github/scripts/cpu_smoke.py),
[diagnostico](https://github.com/mainuan/welcome/blob/a4c56e93696fd44ed23abc2b69d1fe06a9eeb822/docs/cpu-compatibility.md).

Welcome compila C++/QML e encontrou toolchain/startup objects amd64v3. Este
aplicativo nao compila nem linka um executavel proprio. Distribui scripts Python,
SVG/PNG, desktop/manpage, documentacao e traducoes .mo (dados independentes de
arquitetura). O executavel publico e um symlink para o script Python do pacote.
Nao ha motivo para mudar para Architecture amd64 ou acrescentar C/C++/CMake,
flags -march, compilador de teste ou bibliotecas incorporadas.

tests/inspect_deb.py agora recusa ELF mesmo com extensao .bin, outros formatos
nativos/objetos/archives, extensoes .so/.o/.a/wheels, hardlinks/links externos,
permissoes gravaveis por grupo/outros e os artefatos de desenvolvimento ja
proibidos. Symlinks POSIX 777 nao equivalem a arquivos regulares gravaveis.
O launcher precisa resolver dentro do payload. Nenhum probe e instalado.

## Workflow proprio

.github/workflows/build-mainuan-deb.yml substitui o build Mint herdado nesta
branch. Push/PR para port/kubuntu-26.04 e workflow_dispatch; sem tag/release,
secrets herdados ou permissao contents:write. O workflow administrativo stale
preexistente nao participa do empacotamento e nao foi alterado.

Runner ubuntu-26.04; container oficial fixado:

```text
ubuntu:26.04@sha256:42527649dbc4f9197a6073f426f488cbff0e9cc9f2afce32d91c383e4875634a
--platform linux/amd64
```

O registro OCI confirmou o SHA256 do manifesto, OS linux e arquitetura amd64;
config digest b9e485d4a3bc6efa60fc5150444a82f3d96991fdcec7caa1d0f3e7a0b5859321.
Isso identifica a imagem, mas nao substitui os gates sobre pacotes instalados.
As duas camadas tambem foram lidas estaticamente, sem executar/instalar a imagem:
checksums conferidos, os-release Ubuntu 26.04.1 LTS (VERSION_ID 26.04), 87 pacotes
instalados all/amd64 e nenhuma Architecture-Variant superior a baseline nos
metadados. Evidencia local em dist/cpu-base-image.json. Nao e execucao em CPU v1.
Antes do PRIMEIRO apt update/install, o job grava:

```text
#clear APT::Architecture-Variants;
APT::Architecture-Variants "";
APT::Architecture "amd64";
#clear APT::Architectures;
APT::Architectures { "amd64"; };
```

check_cpu environment exige Ubuntu 26.04/amd64, indices amd64 e variantes
explicitamente desabilitadas; verifica Architecture-Variant de TODOS os pacotes
instalados, nao apenas Architecture. Registra configuracao APT, versoes/origens,
commit e estado da arvore. --report-only e somente inventario local, nunca gate CI.
As dependencias usam repositorios Ubuntu e --no-install-recommends; bibliotecas
runtime/Recommends sao comparadas com debian/control pelos testes. Ferramentas
extras como qemu-user/binutils/python3-yaml/dbus/polkitd sao somente validacao,
nao novos Depends do aplicativo. Nenhum PPA/driver e instalado para testar.

Somente a preparacao do container e administrativa; suite, compileall, probes,
build, Lintian e auditorias usam mainuan-build sem privilegios. O system bus e
privado do container, nunca montado do host. O probe existente possui allowlist
Introspect/CreateTransaction/GetAll/SetHints/Resolve e nao solicita mutacao ou
senha. PolicyKit/PackageKit usados sao os servicos Ubuntu, nao helper Mainuan.
Os testes comuns usam fakes. O probe manual hello NAO e chamado no CI.

Checkout v7.0.1 e upload-artifact v7.0.2 estao fixados por SHA completo (refs
oficiais conferidas), token contents:read e persist-credentials:false. Upload
somente apos todos os gates; .deb, SHA256SUMS verificado, logs e JSONs CPU,
identificados por github.sha. PRs usam o commit de merge de teste do GitHub.
Pacotes APT podem receber atualizacoes; a imagem e fixa, mas nao se promete
identidade binaria eterna de todas as dependencias. Rebuild da mesma versao exige
comparar commit/checksum; APT nao interpreta recompilacao como nova versao.

## Startup e bibliotecas reais

cpu_smoke extrai o .deb (nunca instala) e chama o mesmo entry point publico.
Exercita test e a invocacao sem argumentos usada pelo Welcome. Neste ultimo
caso, somente I/O de deteccao e substituido por fixtures; nao e teste de hardware.
Cria QApplication/janela/radios, importa PyQt6/QtDBus/python-apt/UDC, renderiza,
aguarda QThread terminar e fecha normalmente. HOME/XDG temporarios, offscreen,
sem DISPLAY/Wayland/bus do host. Chamadas D-Bus e install/remove reais sao
tripwires que falham; nenhum Apply e acionado. Sem imports GTK/GI.

O modo padrao EXIGE qemu-user com CPU qemu64 e recursos pos-v1 explicitamente
removidos. O loader glibc --list-diagnostics executa no guest: confirma SSE2,
hwcaps v2/v3/v4 inativos e bits CPUID SSE3/SSSE3/SSE4/POPCNT/CX16/AVX/AVX2/
AVX512/FMA/F16C/BMI/LAHF/LZCNT ausentes. Adapter dos campos glibc 2.43 falha
fechado se o layout mudar. Nao compila nem distribui um probe C para isso.
Ambiente e auxv do loader nao sao exportados; somente campos de CPU selecionados.
Uma janela apenas bloqueada/aberta nao passa: widgets/modelos, renderizacao,
imports nativos e encerramento precisam ser confirmados. Timeout causa falha.

check_cpu dependencies audita notas GNU ISA NEEDED de todos os ELF realmente
mapeados pelo cliente, registrados em /proc/self/maps enquanto a UI esta viva.
Qt/plugins, Python/PyQt6, apt_pkg/libapt e transitivas estao incluidos. PackageKit
e helpers UDC/mokutil/openssl/kmod/polkitd sao processos separados: seus ELF e
resolucao ldd sao auditados estaticamente, sem chamar suas operacoes. O binario
QEMU e infraestrutura do teste, excluido dos mapas do cliente guest.

NEEDED v2/v3/v4 ou arquitetura diferente falham. Ausencia de nota e registrada
como NAO DECLARADA, nunca como prova de baseline; instrucoes opcionais ISA USED
podem ser dispatch por CPUID. Notas, variantes APT e execucao emulada sao
evidencias complementares, nao garantia sobre todos os caminhos do programa.

## Comandos de verificacao (usuario normal)

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q usr tests
python3 tests/probe_packagekit_readonly.py
dpkg-buildpackage -us -uc -b
python3 tests/inspect_deb.py '../mainuan-gestao-drivers_1.0_all.deb'
python3 .github/scripts/check_cpu.py environment --output /tmp/cpu-environment.json
python3 .github/scripts/cpu_smoke.py '../mainuan-gestao-drivers_1.0_all.deb' --output /tmp/cpu-startup.json
python3 .github/scripts/check_cpu.py dependencies /tmp/cpu-startup.json --output /tmp/cpu-dependencies.json
```

Um host Mainuan com multiarch e sem politica APT explicita pode reprovar o gate
environment: nao alterar o host para ocultar isso. --report-only permite somente
inventario. Sem QEMU, --native testa startup mas grava baseline_emulated=false;
NAO e prova de CPU antiga. Um container comum compartilha a CPU do runner.
Nao instalar ferramentas/configuracoes no host para executar este roteiro sem
autorizacao. Build local all sem ELF nao incorpora o toolchain nativo do host.

## Limites e responsabilidade da ISO

QEMU user-mode compartilha o kernel, nao valida boot da ISO, Plasma/Wayland,
GPU real, firmware, modulo DKMS, assinatura ou transacao de driver. Validar a
primeira ISO em VM com CPU v1 limitada e hardware AMD64 antigo elegivel; abrir
pelo Welcome sem argumentos, percorrer test e estado vazio, fechar e reabrir.
Nao forcar NVIDIA/Broadcom incompativel nem realizar enrollment/modprobe.

Na construcao da ISO, desabilitar variantes ANTES de instalar dependencias e
auditar dpkg Architecture-Variant, notas ELF e inicializacao de Python/Qt/APT/
PackageKit/Plasma. Desabilitar APT depois nao substitui bibliotecas v3 existentes.
Nao copiar libc/Qt para este .deb ou alterar bibliotecas do host manualmente.
O checksum do pacote sozinho nao prova compatibilidade de toda a imagem.

Fontes primarias adicionais:
- https://documentation.ubuntu.com/project/how-ubuntu-is-made/concepts/supported-architectures/
- https://discourse.ubuntu.com/t/introducing-architecture-variants-amd64v3-now-available-in-ubuntu-25-10/71312
- https://sourceware.org/glibc/manual/2.40/html_node/Dynamic-Linker-Diagnostics-Values.html
